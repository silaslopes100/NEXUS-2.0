"""Módulo de Turmas e Calendários Oficiais do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.polos_escolas.repository import get_polos_escolas_repository

router = APIRouter(prefix="/turmas", tags=["Turmas & Calendários"])

_PERFIS_TURMA = ["admin", "polo", "escola"]

NomeTurma = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]


class TurmaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    nome: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    calendario_oficial_id: Optional[str] = None


class TurmaDetalheSchema(TurmaSchema):
    curso_nome: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    total_alunos: int = 0


class TurmaWriteSchema(BaseModel):
    curso_id: Optional[uuid.UUID] = None
    polo_id: Optional[uuid.UUID] = None
    escola_id: Optional[uuid.UUID] = None
    nome: NomeTurma
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    calendario_oficial_id: Optional[uuid.UUID] = None


class TurmasPaginaSchema(BaseModel):
    items: List[TurmaDetalheSchema]
    total: int
    limit: int
    offset: int


class AlunoTurmaSchema(BaseModel):
    aluno_id: str
    nome: Optional[str] = None
    email: Optional[str] = None
    numero_matricula: Optional[str] = None
    status: Optional[str] = None
    data_matricula: Optional[datetime] = None


class AlunosTurmaPaginaSchema(BaseModel):
    items: List[AlunoTurmaSchema]
    total: int
    limit: int
    offset: int


class CalendarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    disciplina_id: Optional[str] = None
    data_liberacao: Optional[date] = None
    data_encerramento: Optional[date] = None
    curso_nome: Optional[str] = None
    disciplina_nome: Optional[str] = None


class CalendarioWriteSchema(BaseModel):
    curso_id: Optional[uuid.UUID] = None
    disciplina_id: Optional[uuid.UUID] = None
    data_liberacao: Optional[date] = None
    data_encerramento: Optional[date] = None


class CursoDetalhesSchema(BaseModel):
    disciplinas: List[Dict[str, Any]]
    turmas: List[TurmaSchema]


_turmas_db: Dict[str, Dict[str, Any]] = {}
_calendarios_db: Dict[str, Dict[str, Any]] = {}
_turma_alunos_db: List[Dict[str, Any]] = []

_TURMA_SELECT = """
    SELECT t.id, t.curso_id, t.polo_id, t.escola_id, t.nome, t.data_inicio,
           t.data_fim, t.calendario_oficial_id,
           c.nome AS curso_nome, p.nome AS polo_nome, e.nome AS escola_nome,
           (SELECT COUNT(*) FROM turma_alunos ta WHERE ta.turma_id = t.id) AS total_alunos
    FROM turmas t
    LEFT JOIN cursos c ON c.id = t.curso_id
    LEFT JOIN polos p ON p.id = t.polo_id
    LEFT JOIN escolas e ON e.id = t.escola_id
"""

_CALENDARIO_SELECT = """
    SELECT co.id, co.curso_id, co.disciplina_id, co.data_liberacao, co.data_encerramento,
           c.nome AS curso_nome, d.nome AS disciplina_nome
    FROM calendarios_oficiais co
    LEFT JOIN cursos c ON c.id = co.curso_id
    LEFT JOIN disciplinas d ON d.id = co.disciplina_id
"""

_ALUNO_NOME_SQL = "trim(concat(u.nome, ' ', u.sobrenome))"


def _texto(valor: Any) -> Optional[str]:
    return str(valor) if valor else None


def _escopo_usuario(user: UserResponse) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (polo_id, escola_id) a que o usuário está restrito; admin não tem restrição."""
    perfil = perfil_do_usuario(user)
    if perfil == "polo":
        if not user.polo_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
        return str(user.polo_id), None
    if perfil == "escola":
        if not user.escola_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo")
        return None, str(user.escola_id)
    return None, None


def _exigir_no_escopo(turma: Optional[Dict[str, Any]], user: UserResponse) -> Dict[str, Any]:
    if turma is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
    polo_id, escola_id = _escopo_usuario(user)
    if (polo_id and str(turma.get("polo_id")) != polo_id) or (
        escola_id and str(turma.get("escola_id")) != escola_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Turma")
    return turma


def _resolver_vinculo(user: UserResponse, dados: TurmaWriteSchema) -> Tuple[Optional[str], Optional[str]]:
    """Define polo e escola da turma: a escola determina o polo, e o perfil limita ambos."""
    polo_escopo, escola_escopo = _escopo_usuario(user)
    polo_id = _texto(dados.polo_id)
    escola_id = escola_escopo or _texto(dados.escola_id)
    if escola_id:
        escola = get_polos_escolas_repository().get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        polo_id = _texto(escola.get("polo_id")) or polo_id
    if polo_escopo:
        if polo_id and polo_id != polo_escopo:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        polo_id = polo_escopo
    return polo_id, escola_id


def _validar_periodo(inicio: Optional[date], fim: Optional[date], mensagem: str) -> None:
    if inicio and fim and fim < inicio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=mensagem)


def _validar_existencia(cur: Any, referencias: List[Tuple[str, Optional[str], str]]) -> None:
    """Confere chaves estrangeiras antes da escrita, para responder 404 em vez de erro do banco."""
    for tabela, valor, mensagem in referencias:
        if not valor:
            continue
        cur.execute(f"SELECT 1 FROM {tabela} WHERE id = %s", (valor,))
        if cur.fetchone() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=mensagem)


def _auditar(
    user: UserResponse,
    acao: str,
    entidade: str,
    entidade_id: str,
    ip: Optional[str],
    antes: Optional[Dict[str, Any]] = None,
    depois: Optional[Dict[str, Any]] = None,
) -> None:
    if not settings.PG_DSN:
        return
    get_polos_escolas_repository().record_audit_log(
        usuario_id=user.id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        dados_antes=jsonable_encoder(antes) if antes else None,
        dados_depois=jsonable_encoder(depois) if depois else None,
        ip=ip,
    )


def _buscar_turma(cur: Any, turma_id: str, bloquear: bool = False) -> Optional[Dict[str, Any]]:
    cur.execute(_TURMA_SELECT + " WHERE t.id = %s" + (" FOR UPDATE OF t" if bloquear else ""), (turma_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _buscar_calendario(cur: Any, calendario_id: str, bloquear: bool = False) -> Optional[Dict[str, Any]]:
    cur.execute(_CALENDARIO_SELECT + " WHERE co.id = %s" + (" FOR UPDATE OF co" if bloquear else ""), (calendario_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _turma_memoria(turma_id: str) -> Optional[Dict[str, Any]]:
    turma = _turmas_db.get(turma_id)
    if turma is None:
        return None
    total = sum(1 for vinculo in _turma_alunos_db if vinculo["turma_id"] == turma_id)
    return {**turma, "total_alunos": total}


def _filtrar_turmas_memoria(
    polo_id: Optional[str],
    escola_id: Optional[str],
    curso_id: Optional[str],
    termo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    turmas = [_turma_memoria(turma_id) for turma_id in _turmas_db]
    return [
        turma
        for turma in turmas
        if turma is not None
        and (not polo_id or turma.get("polo_id") == polo_id)
        and (not escola_id or turma.get("escola_id") == escola_id)
        and (not curso_id or turma.get("curso_id") == curso_id)
        and (not termo or termo in (turma.get("nome") or "").lower())
    ]


def _condicoes_turma(
    polo_id: Optional[str],
    escola_id: Optional[str],
    curso_id: Optional[str],
    termo: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    for coluna, valor in (("t.polo_id", polo_id), ("t.escola_id", escola_id), ("t.curso_id", curso_id)):
        if valor:
            conditions.append(f"{coluna} = %s")
            params.append(valor)
    if termo:
        conditions.append("lower(t.nome) LIKE %s")
        params.append(f"%{termo}%")
    return (" WHERE " + " AND ".join(conditions) if conditions else ""), params


@router.get(
    "",
    response_model=List[TurmaSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_turmas(
    polo_id: Optional[str] = None,
    curso_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    polo_escopo, escola_escopo = _escopo_usuario(current_user)
    polo_id = polo_escopo or polo_id
    escola_id = escola_escopo or escola_id

    if not settings.PG_DSN:
        return _filtrar_turmas_memoria(polo_id, escola_id, curso_id)

    where, params = _condicoes_turma(polo_id, escola_id, curso_id)
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT t.id, t.curso_id, t.polo_id, t.escola_id, t.nome, t.data_inicio, "
            "t.data_fim, t.calendario_oficial_id FROM turmas t" + where + " ORDER BY t.nome, t.id",
            tuple(params),
        )
        return [dict(r) for r in cur.fetchall()]


@router.get(
    "/paginadas",
    response_model=TurmasPaginaSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_turmas_paginadas(
    q: Optional[str] = Query(None, max_length=255),
    curso_id: Optional[uuid.UUID] = None,
    polo_id: Optional[uuid.UUID] = None,
    escola_id: Optional[uuid.UUID] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
):
    polo_escopo, escola_escopo = _escopo_usuario(current_user)
    polo_filtro = polo_escopo or _texto(polo_id)
    escola_filtro = escola_escopo or _texto(escola_id)
    curso_filtro = _texto(curso_id)
    termo = q.strip().lower() if q and q.strip() else None

    if not settings.PG_DSN:
        turmas = _filtrar_turmas_memoria(polo_filtro, escola_filtro, curso_filtro, termo)
        turmas.sort(key=lambda turma: ((turma.get("nome") or "").lower(), str(turma.get("id"))))
        return {"items": turmas[offset : offset + limit], "total": len(turmas), "limit": limit, "offset": offset}

    where, params = _condicoes_turma(polo_filtro, escola_filtro, curso_filtro, termo)
    with get_db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM turmas t" + where, tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            _TURMA_SELECT + where + " ORDER BY t.nome, t.id LIMIT %s OFFSET %s",
            tuple(params + [limit, offset]),
        )
        return {"items": [dict(r) for r in cur.fetchall()], "total": total, "limit": limit, "offset": offset}


@router.get(
    "/calendarios",
    response_model=List[CalendarioSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_calendarios(curso_id: Optional[uuid.UUID] = None):
    curso_filtro = _texto(curso_id)
    if not settings.PG_DSN:
        return [c for c in _calendarios_db.values() if not curso_filtro or c.get("curso_id") == curso_filtro]

    sql = _CALENDARIO_SELECT
    params: Tuple[Any, ...] = ()
    if curso_filtro:
        sql += " WHERE co.curso_id = %s"
        params = (curso_filtro,)
    with get_db_cursor() as cur:
        cur.execute(sql + " ORDER BY co.data_liberacao NULLS LAST, co.id", params)
        return [dict(r) for r in cur.fetchall()]


def _dados_calendario(dados: CalendarioWriteSchema) -> Dict[str, Any]:
    _validar_periodo(dados.data_liberacao, dados.data_encerramento, "data_encerramento anterior a data_liberacao")
    return {
        "curso_id": _texto(dados.curso_id),
        "disciplina_id": _texto(dados.disciplina_id),
        "data_liberacao": dados.data_liberacao,
        "data_encerramento": dados.data_encerramento,
    }


def _validar_referencias_calendario(cur: Any, valores: Dict[str, Any]) -> None:
    _validar_existencia(
        cur,
        [
            ("cursos", valores["curso_id"], "Curso não encontrado"),
            ("disciplinas", valores["disciplina_id"], "Disciplina não encontrada"),
        ],
    )


@router.post(
    "/calendarios",
    response_model=CalendarioSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin"]))],
)
async def create_calendario(
    dados: CalendarioWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    new_id = str(uuid.uuid4())
    valores = _dados_calendario(dados)
    if not settings.PG_DSN:
        _calendarios_db[new_id] = {"id": new_id, **valores}
        return _calendarios_db[new_id]

    with get_db_cursor() as cur:
        _validar_referencias_calendario(cur, valores)
        cur.execute(
            """
            INSERT INTO calendarios_oficiais (
                id, curso_id, disciplina_id, data_liberacao, data_encerramento, criado_em, atualizado_em
            )
            VALUES (%s, %s, %s, %s, %s, now(), now())
            """,
            (new_id, valores["curso_id"], valores["disciplina_id"], valores["data_liberacao"], valores["data_encerramento"]),
        )
        calendario = _buscar_calendario(cur, new_id)
    _auditar(current_user, "calendario_criado", "calendarios_oficiais", new_id, ip, depois=calendario)
    return calendario


@router.put(
    "/calendarios/{calendario_id}",
    response_model=CalendarioSchema,
    dependencies=[Depends(require_role(["admin"]))],
)
async def update_calendario(
    calendario_id: uuid.UUID,
    dados: CalendarioWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    uid = str(calendario_id)
    valores = _dados_calendario(dados)
    if not settings.PG_DSN:
        atual = _calendarios_db.get(uid)
        if atual is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
        atual.update(valores)
        return atual

    with get_db_cursor() as cur:
        antes = _buscar_calendario(cur, uid, bloquear=True)
        if antes is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
        _validar_referencias_calendario(cur, valores)
        cur.execute(
            """
            UPDATE calendarios_oficiais
            SET curso_id = %s, disciplina_id = %s, data_liberacao = %s,
                data_encerramento = %s, atualizado_em = now()
            WHERE id = %s
            """,
            (valores["curso_id"], valores["disciplina_id"], valores["data_liberacao"], valores["data_encerramento"], uid),
        )
        depois = _buscar_calendario(cur, uid)
    _auditar(current_user, "calendario_atualizado", "calendarios_oficiais", uid, ip, antes=antes, depois=depois)
    return depois


@router.delete(
    "/calendarios/{calendario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(["admin"]))],
)
async def delete_calendario(
    calendario_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
) -> Response:
    uid = str(calendario_id)
    mensagem_conflito = "Não é possível excluir um calendário vinculado a turmas."
    if not settings.PG_DSN:
        if uid not in _calendarios_db:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
        if any(turma.get("calendario_oficial_id") == uid for turma in _turmas_db.values()):
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        del _calendarios_db[uid]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    with get_db_cursor() as cur:
        antes = _buscar_calendario(cur, uid, bloquear=True)
        if antes is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
        cur.execute("SELECT EXISTS (SELECT 1 FROM turmas WHERE calendario_oficial_id = %s) AS em_uso", (uid,))
        if cur.fetchone()["em_uso"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        cur.execute("DELETE FROM calendarios_oficiais WHERE id = %s", (uid,))
    _auditar(current_user, "calendario_excluido", "calendarios_oficiais", uid, ip, antes=antes)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/cursos/{curso_id}/detalhes",
    response_model=CursoDetalhesSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def get_detalhes_curso(
    curso_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
) -> CursoDetalhesSchema:
    polo_id, escola_id = _escopo_usuario(current_user)

    course_key = str(curso_id)
    if not settings.PG_DSN:
        from app.modules.cursos_disciplinas import _disciplinas_db

        disciplinas = sorted(
            [
                dict(discipline)
                for discipline in _disciplinas_db.values()
                if str(discipline.get("curso_id")) == course_key
            ],
            key=lambda discipline: (discipline.get("ordem") or 0, str(discipline.get("id") or "")),
        )
        turmas = [
            dict(turma)
            for turma in _turmas_db.values()
            if str(turma.get("curso_id")) == course_key
            and (polo_id is None or str(turma.get("polo_id")) == polo_id)
            and (escola_id is None or str(turma.get("escola_id")) == escola_id)
        ]
        return CursoDetalhesSchema(disciplinas=disciplinas, turmas=turmas)

    turma_conditions = ["curso_id = %s"]
    turma_params: List[Any] = [course_key]
    if polo_id:
        turma_conditions.append("polo_id = %s")
        turma_params.append(polo_id)
    if escola_id:
        turma_conditions.append("escola_id = %s")
        turma_params.append(escola_id)

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, curso_id, semestre, nome, ordem, carga_horaria,
                   qtd_aulas_prevista, tipo, eh_extra_grade
            FROM disciplinas
            WHERE curso_id = %s
            ORDER BY ordem, id
            """,
            (course_key,),
        )
        disciplinas = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, curso_id, polo_id, escola_id, nome, data_inicio,
                   data_fim, calendario_oficial_id
            FROM turmas
            WHERE """
            + " AND ".join(turma_conditions),
            tuple(turma_params),
        )
        turmas = [dict(row) for row in cur.fetchall()]

    return CursoDetalhesSchema(disciplinas=disciplinas, turmas=turmas)


def _dados_turma(user: UserResponse, dados: TurmaWriteSchema) -> Dict[str, Any]:
    _validar_periodo(dados.data_inicio, dados.data_fim, "data_fim anterior a data_inicio")
    polo_id, escola_id = _resolver_vinculo(user, dados)
    return {
        "curso_id": _texto(dados.curso_id),
        "polo_id": polo_id,
        "escola_id": escola_id,
        "nome": dados.nome,
        "data_inicio": dados.data_inicio,
        "data_fim": dados.data_fim,
        "calendario_oficial_id": _texto(dados.calendario_oficial_id),
    }


def _validar_referencias_turma(cur: Any, valores: Dict[str, Any]) -> None:
    _validar_existencia(
        cur,
        [
            ("cursos", valores["curso_id"], "Curso não encontrado"),
            ("polos", valores["polo_id"], "Polo não encontrado"),
            ("calendarios_oficiais", valores["calendario_oficial_id"], "Calendário não encontrado"),
        ],
    )


@router.post(
    "",
    response_model=TurmaDetalheSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def create_turma(
    dados: TurmaWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    new_id = str(uuid.uuid4())
    valores = _dados_turma(current_user, dados)
    if not settings.PG_DSN:
        _turmas_db[new_id] = {"id": new_id, **valores}
        return _turma_memoria(new_id)

    with get_db_cursor() as cur:
        _validar_referencias_turma(cur, valores)
        cur.execute(
            """
            INSERT INTO turmas (
                id, curso_id, polo_id, escola_id, nome, data_inicio, data_fim,
                calendario_oficial_id, criado_em, atualizado_em
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """,
            (
                new_id,
                valores["curso_id"],
                valores["polo_id"],
                valores["escola_id"],
                valores["nome"],
                valores["data_inicio"],
                valores["data_fim"],
                valores["calendario_oficial_id"],
            ),
        )
        turma = _buscar_turma(cur, new_id)
    _auditar(current_user, "turma_criada", "turmas", new_id, ip, depois=turma)
    return turma


@router.get(
    "/{turma_id}",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def get_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        return _exigir_no_escopo(_turma_memoria(uid), current_user)
    with get_db_cursor() as cur:
        return _exigir_no_escopo(_buscar_turma(cur, uid), current_user)


@router.put(
    "/{turma_id}",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def update_turma(
    turma_id: uuid.UUID,
    dados: TurmaWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        _turmas_db[uid].update(_dados_turma(current_user, dados))
        return _turma_memoria(uid)

    with get_db_cursor() as cur:
        antes = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        valores = _dados_turma(current_user, dados)
        _validar_referencias_turma(cur, valores)
        cur.execute(
            """
            UPDATE turmas
            SET curso_id = %s, polo_id = %s, escola_id = %s, nome = %s, data_inicio = %s,
                data_fim = %s, calendario_oficial_id = %s, atualizado_em = now()
            WHERE id = %s
            """,
            (
                valores["curso_id"],
                valores["polo_id"],
                valores["escola_id"],
                valores["nome"],
                valores["data_inicio"],
                valores["data_fim"],
                valores["calendario_oficial_id"],
                uid,
            ),
        )
        depois = _buscar_turma(cur, uid)
    _auditar(current_user, "turma_atualizada", "turmas", uid, ip, antes=antes, depois=depois)
    return depois


@router.delete(
    "/{turma_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def delete_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
) -> Response:
    uid = str(turma_id)
    mensagem_conflito = "Não é possível excluir uma turma com alunos, notas ou professores vinculados."
    if not settings.PG_DSN:
        turma = _exigir_no_escopo(_turma_memoria(uid), current_user)
        if turma["total_alunos"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        del _turmas_db[uid]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    with get_db_cursor() as cur:
        antes = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        cur.execute(
            """
            SELECT
                EXISTS (SELECT 1 FROM turma_alunos WHERE turma_id = %s)
                OR EXISTS (SELECT 1 FROM notas WHERE turma_id = %s)
                OR EXISTS (SELECT 1 FROM professor_disciplinas WHERE turma_id = %s)
                AS em_uso
            """,
            (uid, uid, uid),
        )
        if cur.fetchone()["em_uso"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        cur.execute("DELETE FROM turmas WHERE id = %s", (uid,))
    _auditar(current_user, "turma_excluida", "turmas", uid, ip, antes=antes)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{turma_id}/alunos",
    response_model=AlunosTurmaPaginaSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_alunos_turma(
    turma_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        vinculos = [
            {"aluno_id": vinculo["aluno_id"], "status": "ativo"}
            for vinculo in _turma_alunos_db
            if vinculo["turma_id"] == uid
        ]
        return {"items": vinculos[offset : offset + limit], "total": len(vinculos), "limit": limit, "offset": offset}

    with get_db_cursor() as cur:
        _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        cur.execute("SELECT COUNT(*) AS total FROM turma_alunos WHERE turma_id = %s", (uid,))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT a.id AS aluno_id, {_ALUNO_NOME_SQL} AS nome, u.email, a.numero_matricula,
                   ta.status, ta.data_matricula
            FROM turma_alunos ta
            JOIN alunos a ON a.id = ta.aluno_id
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE ta.turma_id = %s
            ORDER BY nome, a.id
            LIMIT %s OFFSET %s
            """,
            (uid, limit, offset),
        )
        return {"items": [dict(r) for r in cur.fetchall()], "total": total, "limit": limit, "offset": offset}


@router.get(
    "/{turma_id}/alunos-disponiveis",
    response_model=List[AlunoTurmaSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_alunos_disponiveis(
    turma_id: uuid.UUID,
    q: Optional[str] = Query(None, max_length=255),
    limit: int = Query(20, ge=1, le=50),
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        return []

    termo = q.strip().lower() if q and q.strip() else None
    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        conditions = [
            "a.status = 'ativo'",
            "NOT EXISTS (SELECT 1 FROM turma_alunos ta WHERE ta.turma_id = %s AND ta.aluno_id = a.id)",
        ]
        params: List[Any] = [uid]
        if turma.get("escola_id"):
            conditions.append("a.escola_id = %s")
            params.append(str(turma["escola_id"]))
        elif turma.get("polo_id"):
            conditions.append("a.polo_id = %s")
            params.append(str(turma["polo_id"]))
        if termo:
            conditions.append(
                f"(lower({_ALUNO_NOME_SQL}) LIKE %s OR lower(coalesce(a.numero_matricula, '')) LIKE %s)"
            )
            params.extend([f"%{termo}%", f"%{termo}%"])
        cur.execute(
            f"""
            SELECT a.id AS aluno_id, {_ALUNO_NOME_SQL} AS nome, u.email, a.numero_matricula, a.status
            FROM alunos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE {" AND ".join(conditions)}
            ORDER BY nome, a.id
            LIMIT %s
            """,
            tuple(params + [limit]),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post(
    "/{turma_id}/matricular-aluno",
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def matricular_aluno_turma(
    turma_id: uuid.UUID,
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    uid = str(turma_id)
    mensagem = {"message": "Aluno matriculado na turma com sucesso"}
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        vinculo = {"turma_id": uid, "aluno_id": aluno_id}
        if vinculo not in _turma_alunos_db:
            _turma_alunos_db.append(vinculo)
        return mensagem

    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        cur.execute("SELECT id, polo_id, escola_id FROM alunos WHERE id::text = %s", (aluno_id,))
        aluno = cur.fetchone()
        if aluno is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
        campo = "escola_id" if turma.get("escola_id") else "polo_id"
        if turma.get(campo) and str(aluno[campo]) != str(turma[campo]):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Aluno não pertence ao polo/escola da turma.")
        cur.execute(
            """
            INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, now(), 'ativo', now(), now())
            ON CONFLICT DO NOTHING
            """,
            (str(uuid.uuid4()), uid, str(aluno["id"])),
        )
    _auditar(current_user, "turma_aluno_matriculado", "turmas", uid, ip, depois={"aluno_id": aluno_id})
    return mensagem


@router.delete(
    "/{turma_id}/alunos/{aluno_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def remover_aluno_turma(
    turma_id: uuid.UUID,
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
) -> Response:
    uid = str(turma_id)
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        vinculo = {"turma_id": uid, "aluno_id": aluno_id}
        if vinculo not in _turma_alunos_db:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não matriculado nesta turma")
        _turma_alunos_db.remove(vinculo)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    with get_db_cursor() as cur:
        _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        cur.execute(
            "DELETE FROM turma_alunos WHERE turma_id = %s AND aluno_id::text = %s RETURNING id",
            (uid, aluno_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não matriculado nesta turma")
    _auditar(current_user, "turma_aluno_removido", "turmas", uid, ip, antes={"aluno_id": aluno_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
