"""Módulo de presenças e diário de frequência."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import usuario_eh_professor
from app.modules.professores.repository import get_professores_repository

router = APIRouter(prefix="/presencas", tags=["Presenças & Frequência"])

_PERFIS_DIARIO = ["admin", "professor"]


class PresencaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    professor_disciplina_id: Optional[str] = None
    numero_aula: Optional[int] = 1
    data_aula: Optional[date] = None
    presente: bool = False


class VinculoPresencaSchema(BaseModel):
    id: str
    disciplina_id: str
    turma_id: str
    disciplina_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    professor_nome: Optional[str] = None


class AlunoChamadaSchema(BaseModel):
    aluno_id: str
    nome: str
    numero_matricula: Optional[str] = None
    presente: Optional[bool] = None


class AlunoChamadaInput(BaseModel):
    aluno_id: uuid.UUID
    presente: bool


class ChamadaInput(BaseModel):
    professor_disciplina_id: uuid.UUID
    data_aula: date
    numero_aula: int = Field(ge=1)
    presencas: List[AlunoChamadaInput] = Field(min_length=1)


class ChamadaResponse(BaseModel):
    professor_disciplina_id: str
    data_aula: date
    numero_aula: int
    presencas: List[PresencaSchema]


_presencas_db: Dict[str, Dict[str, Any]] = {}


def _lista_vinculos(current_user: UserResponse) -> List[Dict[str, Any]]:
    eh_admin = perfil_do_usuario(current_user) == "admin"
    if settings.PG_DSN:
        condicao_docente = "" if eh_admin else "AND professor.usuario_id = %s"
        parametros = () if eh_admin else (str(current_user.id),)
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT vinculo.id::text AS id,
                       vinculo.professor_id::text AS professor_id,
                       vinculo.disciplina_id::text AS disciplina_id,
                       vinculo.turma_id::text AS turma_id,
                       disciplina.nome AS disciplina_nome,
                       turma.nome AS turma_nome,
                       usuario.nome AS professor_nome
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN usuarios usuario ON usuario.id = professor.usuario_id
                JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
                JOIN turmas turma ON turma.id = vinculo.turma_id
                WHERE vinculo.ativo = true
                  AND vinculo.turma_id IS NOT NULL
                  {condicao_docente}
                ORDER BY turma.nome, disciplina.nome, usuario.nome
                """,
                parametros,
            )
            return [dict(row) for row in cur.fetchall()]

    repository = get_professores_repository()
    if usuario_eh_professor(current_user):
        vinculos = repository.list_vinculos_academicos_por_usuario(str(current_user.id))
    else:
        vinculos = getattr(repository, "professor_disciplinas", [])
    return [
        {
            "id": str(vinculo["id"]),
            "professor_id": str(vinculo.get("professor_id") or ""),
            "disciplina_id": str(vinculo["disciplina_id"]),
            "turma_id": str(vinculo["turma_id"]),
            "disciplina_nome": vinculo.get("disciplina_nome"),
            "turma_nome": vinculo.get("turma_nome"),
            "professor_nome": vinculo.get("professor_nome"),
        }
        for vinculo in vinculos
        if vinculo.get("id")
        and vinculo.get("disciplina_id")
        and vinculo.get("turma_id")
        and vinculo.get("ativo", True)
    ]


def _obter_vinculo(
    current_user: UserResponse,
    professor_disciplina_id: str,
) -> Dict[str, Any]:
    vinculo = next(
        (
            item
            for item in _lista_vinculos(current_user)
            if str(item["id"]) == str(professor_disciplina_id)
        ),
        None,
    )
    if not vinculo:
        _erro_vinculo_indisponivel(current_user, professor_disciplina_id)
    return vinculo


def _erro_vinculo_indisponivel(
    current_user: UserResponse,
    professor_disciplina_id: str,
    cur: Any = None,
) -> None:
    if usuario_eh_professor(current_user):
        if cur is not None:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM professor_disciplinas
                    WHERE id = %s AND ativo = true
                ) AS existe
                """,
                (str(professor_disciplina_id),),
            )
            existe = bool(cur.fetchone()["existe"])
        elif settings.PG_DSN:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM professor_disciplinas
                        WHERE id = %s AND ativo = true
                    ) AS existe
                    """,
                    (str(professor_disciplina_id),),
                )
                existe = bool(cursor.fetchone()["existe"])
        else:
            repository = get_professores_repository()
            existe = any(
                str(item.get("id")) == str(professor_disciplina_id)
                and item.get("ativo", True)
                for item in getattr(repository, "professor_disciplinas", [])
            )
        if existe:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Professor sem vínculo com esta turma",
            )
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail="Vínculo docente não encontrado ou inativo",
    )


def _alunos_matriculados(turma_id: str) -> List[Dict[str, Any]]:
    if settings.PG_DSN:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT aluno.id::text AS aluno_id,
                       COALESCE(usuario.nome, usuario.email, aluno.numero_matricula, aluno.id::text) AS nome,
                       aluno.numero_matricula
                FROM turma_alunos matricula
                JOIN alunos aluno ON aluno.id = matricula.aluno_id
                LEFT JOIN usuarios usuario ON usuario.id = aluno.usuario_id
                WHERE matricula.turma_id = %s
                  AND COALESCE(matricula.status, 'ativo') = 'ativo'
                ORDER BY nome, aluno.id
                """,
                (str(turma_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    from app.modules.turmas import _turma_alunos_db

    return [
        {
            "aluno_id": str(matricula["aluno_id"]),
            "nome": str(matricula.get("nome") or matricula["aluno_id"]),
            "numero_matricula": matricula.get("numero_matricula"),
        }
        for matricula in _turma_alunos_db
        if str(matricula.get("turma_id")) == str(turma_id)
        and matricula.get("status", "ativo") == "ativo"
    ]


def _validar_chamada_completa(
    presencas: List[AlunoChamadaInput],
    alunos: List[Dict[str, Any]],
) -> None:
    ids_enviados = [str(item.aluno_id) for item in presencas]
    if len(ids_enviados) != len(set(ids_enviados)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A chamada contém aluno duplicado",
        )

    ids_matriculados = {str(aluno["aluno_id"]) for aluno in alunos}
    if set(ids_enviados) != ids_matriculados:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A chamada deve incluir todos os alunos ativos da turma",
        )


@router.get(
    "/vinculos",
    response_model=List[VinculoPresencaSchema],
    dependencies=[Depends(require_role(_PERFIS_DIARIO))],
)
async def listar_vinculos_presenca(
    current_user: UserResponse = Depends(get_current_user),
):
    return _lista_vinculos(current_user)


@router.get(
    "/vinculos/{professor_disciplina_id}/alunos",
    response_model=List[AlunoChamadaSchema],
    dependencies=[Depends(require_role(_PERFIS_DIARIO))],
)
async def listar_alunos_chamada(
    professor_disciplina_id: uuid.UUID,
    data_aula: date = Query(...),
    numero_aula: int = Query(..., ge=1),
    current_user: UserResponse = Depends(get_current_user),
):
    vinculo = _obter_vinculo(current_user, str(professor_disciplina_id))
    alunos = _alunos_matriculados(str(vinculo["turma_id"]))

    if settings.PG_DSN:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT presenca.aluno_id::text AS aluno_id, presenca.presente
                FROM presencas presenca
                WHERE presenca.professor_disciplina_id = %s
                  AND presenca.data_aula = %s
                  AND presenca.numero_aula = %s
                """,
                (str(professor_disciplina_id), data_aula, numero_aula),
            )
            registros = {str(row["aluno_id"]): row["presente"] for row in cur.fetchall()}
    else:
        registros = {
            str(item["aluno_id"]): item["presente"]
            for item in _presencas_db.values()
            if str(item.get("professor_disciplina_id")) == str(professor_disciplina_id)
            and item.get("data_aula") == data_aula
            and item.get("numero_aula") == numero_aula
        }

    return [
        {**aluno, "presente": registros.get(str(aluno["aluno_id"]))}
        for aluno in alunos
    ]


@router.put(
    "/chamadas",
    response_model=ChamadaResponse,
    dependencies=[Depends(require_role(_PERFIS_DIARIO))],
)
async def salvar_chamada(
    dados: ChamadaInput,
    current_user: UserResponse = Depends(get_current_user),
):
    if len({str(item.aluno_id) for item in dados.presencas}) != len(dados.presencas):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A chamada contém aluno duplicado",
        )

    vinculo_id = str(dados.professor_disciplina_id)
    if settings.PG_DSN:
        saved = []
        with get_db_cursor() as cur:
            condicao_docente = "" if perfil_do_usuario(current_user) == "admin" else "AND professor.usuario_id = %s"
            parametros: tuple[Any, ...] = (vinculo_id,)
            if condicao_docente:
                parametros += (str(current_user.id),)
            cur.execute(
                f"""
                SELECT vinculo.turma_id::text AS turma_id
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                WHERE vinculo.id = %s
                  AND vinculo.ativo = true
                  AND vinculo.turma_id IS NOT NULL
                  {condicao_docente}
                FOR UPDATE OF vinculo
                """,
                parametros,
            )
            vinculo = cur.fetchone()
            if not vinculo:
                _erro_vinculo_indisponivel(current_user, vinculo_id, cur)

            cur.execute(
                """
                SELECT aluno_id::text AS aluno_id
                FROM turma_alunos
                WHERE turma_id = %s
                  AND COALESCE(status, 'ativo') = 'ativo'
                """,
                (str(vinculo["turma_id"]),),
            )
            alunos = [{"aluno_id": row["aluno_id"]} for row in cur.fetchall()]
            _validar_chamada_completa(dados.presencas, alunos)

            for item in dados.presencas:
                presenca_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO presencas (
                        id, aluno_id, professor_disciplina_id, numero_aula,
                        data_aula, presente, criado_em, atualizado_em
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                    ON CONFLICT (
                        professor_disciplina_id, aluno_id, data_aula, numero_aula
                    )
                    WHERE professor_disciplina_id IS NOT NULL
                      AND data_aula IS NOT NULL
                      AND numero_aula IS NOT NULL
                    DO UPDATE SET presente = EXCLUDED.presente,
                                  atualizado_em = now()
                    RETURNING id::text AS id, aluno_id::text AS aluno_id,
                              professor_disciplina_id::text AS professor_disciplina_id,
                              numero_aula, data_aula, presente
                    """,
                    (
                        presenca_id,
                        str(item.aluno_id),
                        vinculo_id,
                        dados.numero_aula,
                        dados.data_aula,
                        item.presente,
                    ),
                )
                saved.append(dict(cur.fetchone()))
    else:
        vinculo = _obter_vinculo(current_user, vinculo_id)
        alunos = _alunos_matriculados(str(vinculo["turma_id"]))
        _validar_chamada_completa(dados.presencas, alunos)
        saved = []
        for item in dados.presencas:
            existing = next(
                (
                    registro
                    for registro in _presencas_db.values()
                    if str(registro.get("aluno_id")) == str(item.aluno_id)
                    and str(registro.get("professor_disciplina_id")) == vinculo_id
                    and registro.get("data_aula") == dados.data_aula
                    and registro.get("numero_aula") == dados.numero_aula
                ),
                None,
            )
            if existing:
                existing["presente"] = item.presente
                saved.append(dict(existing))
                continue
            registro = {
                "id": str(uuid.uuid4()),
                "aluno_id": str(item.aluno_id),
                "professor_disciplina_id": vinculo_id,
                "numero_aula": dados.numero_aula,
                "data_aula": dados.data_aula,
                "presente": item.presente,
            }
            _presencas_db[registro["id"]] = registro
            saved.append(dict(registro))

    return {
        "professor_disciplina_id": vinculo_id,
        "data_aula": dados.data_aula,
        "numero_aula": dados.numero_aula,
        "presencas": saved,
    }


@router.get(
    "",
    response_model=List[PresencaSchema],
    dependencies=[Depends(require_role(_PERFIS_DIARIO))],
)
async def list_presencas(
    aluno_id: Optional[str] = None,
    professor_disciplina_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
):
    eh_professor = usuario_eh_professor(current_user)
    vinculos_docente = _lista_vinculos(current_user) if eh_professor else []
    ids_vinculos = {str(vinculo["id"]) for vinculo in vinculos_docente}
    if eh_professor and not ids_vinculos:
        return []

    if not settings.PG_DSN:
        presencas = list(_presencas_db.values())
        if aluno_id:
            presencas = [item for item in presencas if str(item.get("aluno_id")) == str(aluno_id)]
        if professor_disciplina_id:
            presencas = [
                item for item in presencas
                if str(item.get("professor_disciplina_id")) == str(professor_disciplina_id)
            ]
        if eh_professor:
            turma_por_vinculo = {
                str(vinculo["id"]): str(vinculo["turma_id"])
                for vinculo in vinculos_docente
            }
            presencas = [
                item
                for item in presencas
                if str(item.get("professor_disciplina_id")) in ids_vinculos
                and str(item.get("aluno_id")) in {
                    str(aluno["aluno_id"])
                    for aluno in _alunos_matriculados(
                        turma_por_vinculo[str(item["professor_disciplina_id"])]
                    )
                }
            ]
        presencas.sort(
            key=lambda item: (
                str(item.get("data_aula") or ""),
                int(item.get("numero_aula") or 0),
            ),
            reverse=True,
        )
        return presencas[offset : offset + limit]

    conds, params = [], []
    if aluno_id:
        conds.append("presenca.aluno_id = %s")
        params.append(aluno_id)
    if professor_disciplina_id:
        conds.append("presenca.professor_disciplina_id = %s")
        params.append(professor_disciplina_id)
    if eh_professor:
        conds.append("presenca.professor_disciplina_id = ANY(%s::uuid[])")
        params.append(list(ids_vinculos))
        conds.append(
            """
            EXISTS (
                SELECT 1
                FROM turma_alunos matricula
                WHERE matricula.turma_id = (
                    SELECT vinculo.turma_id
                    FROM professor_disciplinas vinculo
                    WHERE vinculo.id = presenca.professor_disciplina_id
                      AND vinculo.ativo = true
                )
                  AND COALESCE(matricula.status, 'ativo') = 'ativo'
                  AND matricula.aluno_id = presenca.aluno_id
            )
            """
        )
    sql = (
        "SELECT presenca.id, presenca.aluno_id, presenca.professor_disciplina_id, "
        "presenca.numero_aula, presenca.data_aula, presenca.presente FROM presencas presenca"
    )
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY presenca.data_aula DESC NULLS LAST, presenca.numero_aula DESC, presenca.id"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


@router.post(
    "/lancar",
    response_model=PresencaSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_PERFIS_DIARIO))],
)
async def lancar_presenca(
    dados: PresencaSchema,
    current_user: UserResponse = Depends(get_current_user),
):
    if not dados.professor_disciplina_id or not dados.data_aula:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vínculo docente e data da aula são obrigatórios",
        )
    if not dados.numero_aula or dados.numero_aula < 1:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Número da aula deve ser maior que zero",
        )

    vinculo_id = str(dados.professor_disciplina_id)
    if settings.PG_DSN:
        saved = None
        with get_db_cursor() as cur:
            condicao_docente = "" if perfil_do_usuario(current_user) == "admin" else "AND professor.usuario_id = %s"
            parametros: tuple[Any, ...] = (vinculo_id,)
            if condicao_docente:
                parametros += (str(current_user.id),)
            cur.execute(
                f"""
                SELECT vinculo.turma_id::text AS turma_id
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                WHERE vinculo.id = %s
                  AND vinculo.ativo = true
                  AND vinculo.turma_id IS NOT NULL
                  {condicao_docente}
                """,
                parametros,
            )
            vinculo = cur.fetchone()
            if not vinculo:
                _erro_vinculo_indisponivel(current_user, vinculo_id, cur)
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM turma_alunos
                    WHERE turma_id = %s AND aluno_id = %s
                      AND COALESCE(status, 'ativo') = 'ativo'
                ) AS vinculado
                """,
                (str(vinculo["turma_id"]), dados.aluno_id),
            )
            if not cur.fetchone()["vinculado"]:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Aluno não matriculado na turma vinculada",
                )
            cur.execute(
                """
                INSERT INTO presencas (
                    id, aluno_id, professor_disciplina_id, numero_aula,
                    data_aula, presente, criado_em, atualizado_em
                )
                VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (
                    professor_disciplina_id, aluno_id, data_aula, numero_aula
                )
                WHERE professor_disciplina_id IS NOT NULL
                  AND data_aula IS NOT NULL
                  AND numero_aula IS NOT NULL
                DO NOTHING
                RETURNING id::text AS id, aluno_id::text AS aluno_id,
                          professor_disciplina_id::text AS professor_disciplina_id,
                          numero_aula, data_aula, presente
                """,
                (
                    str(uuid.uuid4()),
                    dados.aluno_id,
                    vinculo_id,
                    dados.numero_aula,
                    dados.data_aula,
                    dados.presente,
                ),
            )
            saved = cur.fetchone()
            if not saved:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="A presença deste aluno nesta aula já foi lançada",
                )
            return dict(saved)
    else:
        vinculo = _obter_vinculo(current_user, vinculo_id)
        alunos = {
            str(aluno["aluno_id"])
            for aluno in _alunos_matriculados(str(vinculo["turma_id"]))
        }
        if str(dados.aluno_id) not in alunos:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Aluno não matriculado na turma vinculada",
            )
        duplicado = next(
            (
                item
                for item in _presencas_db.values()
                if str(item.get("aluno_id")) == str(dados.aluno_id)
                and str(item.get("professor_disciplina_id")) == vinculo_id
                and item.get("data_aula") == dados.data_aula
                and item.get("numero_aula") == dados.numero_aula
            ),
            None,
        )
        if duplicado:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A presença deste aluno nesta aula já foi lançada",
            )
        saved_id = str(uuid.uuid4())
        _presencas_db[saved_id] = {
            **dados.model_dump(),
            "id": saved_id,
            "professor_disciplina_id": vinculo_id,
        }

    return _presencas_db[saved_id]


# ---------------------------------------------------------------------------
# Visão do aluno: presenças e frequência (vindas das chamadas/atas dos professores)
# ---------------------------------------------------------------------------

FREQUENCIA_MINIMA = 75.0  # % mínimo usual de frequência


class AulaFrequenciaSchema(BaseModel):
    data_aula: Optional[date] = None
    numero_aula: Optional[int] = None
    presente: bool
    conteudo_ministrado: Optional[str] = None


class DisciplinaFrequenciaSchema(BaseModel):
    disciplina_id: Optional[str] = None
    disciplina_nome: str
    turma_nome: Optional[str] = None
    professor_nome: Optional[str] = None
    total_aulas: int
    presencas: int
    faltas: int
    percentual: float
    situacao: str  # regular | em_risco
    aulas: List[AulaFrequenciaSchema] = Field(default_factory=list)


class MinhaFrequenciaSchema(BaseModel):
    total_aulas: int = 0
    presencas: int = 0
    faltas: int = 0
    percentual: Optional[float] = None
    frequencia_minima: float = FREQUENCIA_MINIMA
    disciplinas: List[DisciplinaFrequenciaSchema] = Field(default_factory=list)


def _registros_do_aluno(usuario_id: str) -> List[Dict[str, Any]]:
    if not settings.PG_DSN:
        from app.modules.cursos_disciplinas import _disciplinas_db

        return [
            {
                "disciplina_id": p.get("disciplina_id") or p.get("materia_id"),
                "disciplina_nome": (_disciplinas_db.get(str(p.get("disciplina_id") or p.get("materia_id"))) or {}).get("nome"),
                "turma_nome": None, "professor_nome": None,
                "data_aula": p.get("data_aula"), "numero_aula": p.get("numero_aula"),
                "presente": bool(p.get("presente")), "conteudo_ministrado": None,
            }
            for p in _presencas_db.values()
            if str(p.get("aluno_id")) == str(usuario_id) or str(p.get("usuario_id")) == str(usuario_id)
        ]
    with get_db_cursor() as cur:
        cur.execute(
            f"""{_SELECT_REGISTROS}
             WHERE aluno.usuario_id = %s
             ORDER BY presenca.data_aula DESC NULLS LAST, presenca.numero_aula DESC NULLS LAST
            """,
            (str(usuario_id),),
        )
        return [dict(row) for row in cur.fetchall()]


# Presença ligada à disciplina pelo vínculo do professor (professor_disciplinas); o conteúdo vem da ata.
_FROM_REGISTROS = """
      FROM presencas presenca
      JOIN alunos aluno ON aluno.id = presenca.aluno_id
      JOIN usuarios aluno_usuario ON aluno_usuario.id = aluno.usuario_id
      LEFT JOIN escolas escola ON escola.id = aluno.escola_id
      LEFT JOIN professor_disciplinas vinculo ON vinculo.id = presenca.professor_disciplina_id
      LEFT JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
      LEFT JOIN turmas turma ON turma.id = vinculo.turma_id
"""

_SELECT_REGISTROS = f"""
    SELECT vinculo.disciplina_id::text AS disciplina_id,
           disciplina.nome AS disciplina_nome,
           turma.nome AS turma_nome,
           NULLIF(concat_ws(' ', professor_usuario.nome, professor_usuario.sobrenome), '') AS professor_nome,
           presenca.data_aula, presenca.numero_aula, presenca.presente,
           aula.conteudo_ministrado
      {_FROM_REGISTROS}
      LEFT JOIN professores professor ON professor.id = vinculo.professor_id
      LEFT JOIN usuarios professor_usuario ON professor_usuario.id = professor.usuario_id
      LEFT JOIN aulas_ministradas aula
             ON aula.professor_disciplina_id = presenca.professor_disciplina_id
            AND aula.data_aula = presenca.data_aula
            AND aula.numero_aula = presenca.numero_aula
            AND aula.visivel_aluno
"""


def _agrupar_frequencia(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Frequência por disciplina (e turma) com a lista de aulas e o resumo geral."""
    grupos: Dict[str, Dict[str, Any]] = {}
    for registro in registros:
        chave = f"{registro.get('disciplina_id') or 'sem'}|{registro.get('turma_nome') or ''}"
        grupo = grupos.setdefault(chave, {
            "disciplina_id": registro.get("disciplina_id"),
            "disciplina_nome": registro.get("disciplina_nome") or "Disciplina não informada",
            "turma_nome": registro.get("turma_nome"),
            "professor_nome": registro.get("professor_nome"),
            "aulas": [],
        })
        grupo["aulas"].append({
            "data_aula": registro.get("data_aula"),
            "numero_aula": registro.get("numero_aula"),
            "presente": bool(registro.get("presente")),
            "conteudo_ministrado": registro.get("conteudo_ministrado"),
        })

    disciplinas = []
    for grupo in grupos.values():
        total = len(grupo["aulas"])
        presentes = sum(1 for aula in grupo["aulas"] if aula["presente"])
        percentual = round(presentes / total * 100, 1) if total else 0.0
        disciplinas.append({
            **grupo,
            "total_aulas": total,
            "presencas": presentes,
            "faltas": total - presentes,
            "percentual": percentual,
            "situacao": "regular" if percentual >= FREQUENCIA_MINIMA else "em_risco",
        })
    disciplinas.sort(key=lambda d: (d["disciplina_nome"].casefold(), d.get("turma_nome") or ""))

    total = sum(d["total_aulas"] for d in disciplinas)
    presentes = sum(d["presencas"] for d in disciplinas)
    return {
        "total_aulas": total,
        "presencas": presentes,
        "faltas": total - presentes,
        "percentual": round(presentes / total * 100, 1) if total else None,
        "disciplinas": disciplinas,
    }


@router.get(
    "/me",
    response_model=MinhaFrequenciaSchema,
    dependencies=[Depends(require_role(["aluno"]))],
)
async def minha_frequencia(current_user: UserResponse = Depends(get_current_user)):
    """Presenças do aluno logado, agrupadas por disciplina, com o conteúdo da ata de cada aula."""
    return _agrupar_frequencia(_registros_do_aluno(current_user.id))



# ---------------------------------------------------------------------------
# Frequência dos alunos da unidade (Polo / Escola; Admin vê todas) — somente leitura
# ---------------------------------------------------------------------------

class OpcaoSchema(BaseModel):
    id: str
    nome: str


class FrequenciaAlunoLinhaSchema(BaseModel):
    aluno_id: str
    aluno_nome: str
    numero_matricula: Optional[str] = None
    escola_nome: Optional[str] = None
    disciplina_id: Optional[str] = None
    disciplina_nome: str
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    total_aulas: int
    presencas: int
    faltas: int
    percentual: float
    situacao: str  # regular | em_risco


class FrequenciaUnidadeSchema(BaseModel):
    frequencia_minima: float = FREQUENCIA_MINIMA
    total_alunos: int = 0
    alunos_em_risco: int = 0
    percentual: Optional[float] = None
    disciplinas: List[OpcaoSchema] = Field(default_factory=list)
    turmas: List[OpcaoSchema] = Field(default_factory=list)
    linhas: List[FrequenciaAlunoLinhaSchema] = Field(default_factory=list)


class FrequenciaAlunoSchema(MinhaFrequenciaSchema):
    aluno_id: str
    aluno_nome: str
    numero_matricula: Optional[str] = None


def _escopo_unidade(user: UserResponse, polo_id: Optional[str], escola_id: Optional[str]) -> tuple:
    """Condição SQL de visibilidade: Polo vê os alunos do polo, Escola os da escola, Admin todos (com filtros)."""
    perfil = perfil_do_usuario(user)
    if perfil == "polo":
        if not user.polo_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo.")
        conds, params = ["aluno.polo_id = %s"], [str(user.polo_id)]
        if escola_id:
            conds.append("aluno.escola_id = %s")
            params.append(escola_id)
        return conds, params
    if perfil == "escola":
        if not user.escola_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo.")
        return ["aluno.escola_id = %s"], [str(user.escola_id)]
    conds, params = [], []
    if polo_id:
        conds.append("aluno.polo_id = %s")
        params.append(polo_id)
    if escola_id:
        conds.append("aluno.escola_id = %s")
        params.append(escola_id)
    return conds, params


def _onde(conds: List[str]) -> str:
    return f"WHERE {' AND '.join(conds)}" if conds else ""


@router.get(
    "/unidade",
    response_model=FrequenciaUnidadeSchema,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def frequencia_unidade(
    disciplina_id: Optional[str] = None,
    turma_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    polo_id: Optional[str] = None,
    busca: Optional[str] = Query(None, max_length=100),
    situacao: Optional[str] = Query(None, pattern="^(regular|em_risco)$"),
    current_user: UserResponse = Depends(get_current_user),
):
    """Frequência por aluno e disciplina (a partir das chamadas dos professores) dos alunos da unidade."""
    for valor in (disciplina_id, turma_id, escola_id, polo_id):
        if valor:
            try:
                uuid.UUID(valor)
            except ValueError:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Filtro inválido.") from None
    if not settings.PG_DSN:
        return FrequenciaUnidadeSchema()
    base_conds, base_params = _escopo_unidade(current_user, polo_id or None, escola_id or None)
    base_conds.append("vinculo.disciplina_id IS NOT NULL")
    conds, params = list(base_conds), list(base_params)
    if disciplina_id:
        conds.append("vinculo.disciplina_id = %s")
        params.append(disciplina_id)
    if turma_id:
        conds.append("vinculo.turma_id = %s")
        params.append(turma_id)
    if busca and busca.strip():
        conds.append("(lower(concat_ws(' ', aluno_usuario.nome, aluno_usuario.sobrenome)) LIKE %s "
                     "OR aluno.numero_matricula ILIKE %s)")
        termo = f"%{busca.strip().lower()}%"
        params.extend([termo, termo])

    with get_db_cursor() as cur:
        cur.execute(
            f"""SELECT DISTINCT disciplina.id::text AS id, disciplina.nome
                  {_FROM_REGISTROS} {_onde(base_conds)} ORDER BY disciplina.nome""",
            base_params,
        )
        disciplinas = [dict(r) for r in cur.fetchall() if r["id"]]
        turma_conds = base_conds + (["vinculo.disciplina_id = %s"] if disciplina_id else []) + ["turma.id IS NOT NULL"]
        cur.execute(
            f"""SELECT DISTINCT turma.id::text AS id, turma.nome
                  {_FROM_REGISTROS} {_onde(turma_conds)} ORDER BY turma.nome""",
            base_params + ([disciplina_id] if disciplina_id else []),
        )
        turmas = [dict(r) for r in cur.fetchall()]
        cur.execute(
            f"""SELECT aluno.id::text AS aluno_id,
                       concat_ws(' ', aluno_usuario.nome, aluno_usuario.sobrenome) AS aluno_nome,
                       aluno.numero_matricula, escola.nome AS escola_nome,
                       vinculo.disciplina_id::text AS disciplina_id, disciplina.nome AS disciplina_nome,
                       turma.id::text AS turma_id, turma.nome AS turma_nome,
                       COUNT(*) AS total_aulas,
                       COUNT(*) FILTER (WHERE presenca.presente) AS presencas
                  {_FROM_REGISTROS} {_onde(conds)}
                 GROUP BY aluno.id, aluno_usuario.nome, aluno_usuario.sobrenome, aluno.numero_matricula,
                          escola.nome, vinculo.disciplina_id, disciplina.nome, turma.id, turma.nome
                 ORDER BY aluno_nome, disciplina.nome, turma.nome
                 LIMIT 5000""",
            params,
        )
        linhas = []
        for r in cur.fetchall():
            total, presentes = int(r["total_aulas"]), int(r["presencas"])
            percentual = round(presentes / total * 100, 1) if total else 0.0
            linhas.append({**dict(r), "disciplina_nome": r["disciplina_nome"] or "Disciplina não informada",
                           "total_aulas": total, "presencas": presentes, "faltas": total - presentes,
                           "percentual": percentual,
                           "situacao": "regular" if percentual >= FREQUENCIA_MINIMA else "em_risco"})

    if situacao:
        linhas = [linha for linha in linhas if linha["situacao"] == situacao]
    total = sum(linha["total_aulas"] for linha in linhas)
    presentes = sum(linha["presencas"] for linha in linhas)
    return {
        "total_alunos": len({linha["aluno_id"] for linha in linhas}),
        "alunos_em_risco": len({linha["aluno_id"] for linha in linhas if linha["situacao"] == "em_risco"}),
        "percentual": round(presentes / total * 100, 1) if total else None,
        "disciplinas": disciplinas,
        "turmas": turmas,
        "linhas": linhas,
    }


@router.get(
    "/unidade/alunos/{aluno_id}",
    response_model=FrequenciaAlunoSchema,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def frequencia_aluno_unidade(aluno_id: str, current_user: UserResponse = Depends(get_current_user)):
    """Detalhe da frequência de um aluno da unidade (aulas e conteúdo das atas), por disciplina."""
    try:
        uuid.UUID(aluno_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.") from None
    if not settings.PG_DSN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")
    conds, params = _escopo_unidade(current_user, None, None)
    with get_db_cursor() as cur:
        cur.execute(
            f"""SELECT aluno.id::text AS aluno_id, aluno.numero_matricula,
                       concat_ws(' ', u.nome, u.sobrenome) AS aluno_nome
                  FROM alunos aluno JOIN usuarios u ON u.id = aluno.usuario_id
                  {_onde(conds + ['aluno.id = %s'])}""",
            params + [aluno_id],
        )
        aluno = cur.fetchone()
        if not aluno:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")
        cur.execute(
            f"""{_SELECT_REGISTROS}
             WHERE aluno.id = %s
             ORDER BY presenca.data_aula DESC NULLS LAST, presenca.numero_aula DESC NULLS LAST""",
            (aluno_id,),
        )
        registros = [dict(r) for r in cur.fetchall()]
    return {**_agrupar_frequencia(registros), **dict(aluno)}
