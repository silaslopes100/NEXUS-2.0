"""Módulo de Notas, Avaliações e Histórico Unificado do NEXUS 2.0."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.alunos_gestao.pdf import gerar_boletim_pdf
from app.modules.alunos_gestao.schemas import (
    AcademicoResponse,
    CursoAcademicoResponse,
    DisciplinaAcademicaResponse,
)
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.repository import get_auth_repository
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import (
    aluno_vinculado_a_turma,
    exigir_vinculo_turma_docente,
    listar_vinculos_academicos_docente,
    usuario_eh_professor,
)

router = APIRouter(prefix="/notas-historico", tags=["Notas & Histórico Unificado"])


class NotaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aluno_id: str = Field(min_length=1)
    disciplina_id: str = Field(min_length=1)
    turma_id: str = Field(min_length=1)
    origem: Literal["ava", "manual"] = "manual"
    valor: float = Field(ge=0, le=10)


class NotaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: float = Field(ge=0, le=10)


class NotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    aluno_nome: Optional[str] = None
    disciplina_id: Optional[str] = None
    disciplina_nome: Optional[str] = None
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    origem: str = "ava"
    valor: float
    lancado_por: Optional[str] = None
    lancado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class AdminNotaResponse(NotaResponse):
    aluno_email: Optional[str] = None
    aluno_matricula: Optional[str] = None
    aluno_cpf: Optional[str] = None


class AdminNotaListResponse(BaseModel):
    items: List[AdminNotaResponse]
    total: int
    limit: int
    offset: int


class HistoricoUnificadoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    aluno_id: str
    disciplina_id: Optional[str] = None
    disciplina_nome: Optional[str] = None
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    nota_final: Optional[float] = None
    status: str = "cursando"
    eh_extra_grade: bool = False


_notas_db: Dict[str, Dict[str, Any]] = {}
_historico_db: Dict[str, Dict[str, Any]] = {}


def _perfil_aluno(user: UserResponse) -> bool:
    return perfil_do_usuario(user) == "aluno"


def _aluno_id_do_usuario(user: UserResponse) -> str:
    if settings.PG_DSN:
        with get_db_cursor() as cur:
            cur.execute("SELECT id FROM alunos WHERE usuario_id = %s LIMIT 1", (str(user.id),))
            row = cur.fetchone()
        if row:
            return str(row["id"])
    else:
        from app.modules.alunos import _alunos_db

        aluno = next(
            (
                item for item in _alunos_db.values()
                if str(item.get("usuario_id")) == str(user.id)
            ),
            None,
        )
        if aluno:
            return str(aluno["id"])
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Cadastro de aluno não encontrado para o usuário autenticado",
    )


def _aluno_no_escopo(aluno_id: str, user: UserResponse) -> bool:
    perfil = perfil_do_usuario(user)
    if perfil == "admin":
        return True
    if perfil == "aluno" or user.tambem_aluno:
        return str(aluno_id) == _aluno_id_do_usuario(user)
    if perfil not in {"polo", "escola"}:
        return True

    if settings.PG_DSN:
        coluna = "polo_id" if perfil == "polo" else "escola_id"
        unidade_id = user.polo_id if perfil == "polo" else user.escola_id
        if not unidade_id:
            return False
        with get_db_cursor() as cur:
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM alunos WHERE id = %s AND {coluna} = %s) AS permitido", (aluno_id, unidade_id))
            return bool(cur.fetchone()["permitido"])

    from app.modules.alunos import _alunos_db

    aluno = _alunos_db.get(str(aluno_id))
    unidade_id = user.polo_id if perfil == "polo" else user.escola_id
    coluna = "polo_id" if perfil == "polo" else "escola_id"
    return bool(aluno and unidade_id and str(aluno.get(coluna)) == str(unidade_id))


def _registrar_auditoria(
    *,
    user: UserResponse,
    action: str,
    nota_id: str,
    before: Optional[Dict[str, Any]],
    after: Dict[str, Any],
    ip: Optional[str],
    cursor: Any = None,
) -> None:
    if cursor is not None:
        cursor.execute(
            """
            INSERT INTO logs_auditoria (
                usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois,
                ip, criado_em, atualizado_em
            ) VALUES (%s, %s, 'notas', %s, %s, %s, %s, now(), now())
            """,
            (
                str(user.id),
                action,
                nota_id,
                json.dumps(before, default=str) if before is not None else None,
                json.dumps(after, default=str),
                ip,
            ),
        )
        return

    get_auth_repository().record_audit_log(
        usuario_id=str(user.id),
        acao=action,
        entidade="notas",
        entidade_id=nota_id,
        dados_antes=before,
        dados_depois=after,
        ip=ip,
    )


def _atualizar_historico_memoria(aluno_id: str, disciplina_id: str) -> None:
    notas = [
        item for item in _notas_db.values()
        if str(item.get("aluno_id")) == aluno_id
        and str(item.get("disciplina_id")) == disciplina_id
    ]
    if not notas:
        return
    nota_final = max(float(item["valor"]) for item in notas)
    existente = next(
        (
            item for item in _historico_db.values()
            if str(item.get("aluno_id")) == aluno_id
            and str(item.get("disciplina_id")) == disciplina_id
        ),
        None,
    )
    registro = {
        "id": str(existente["id"]) if existente else str(uuid.uuid4()),
        "aluno_id": aluno_id,
        "disciplina_id": disciplina_id,
        "nota_final": nota_final,
        "status": "aprovado" if nota_final >= 6 else "reprovado",
        "eh_extra_grade": bool(existente.get("eh_extra_grade")) if existente else False,
    }
    if existente:
        _historico_db[str(existente["id"])] = registro
    else:
        _historico_db[registro["id"]] = registro


def _atualizar_historico_postgres(cursor: Any, aluno_id: str, disciplina_id: str) -> None:
    cursor.execute(
        """
        INSERT INTO historico_unificado (
            aluno_id, disciplina_id, nota_final, status, eh_extra_grade, atualizado_em
        )
        SELECT n.aluno_id, n.disciplina_id, MAX(n.valor),
               CASE WHEN MAX(n.valor) >= 6 THEN 'aprovado' ELSE 'reprovado' END,
               COALESCE(bool_or(d.eh_extra_grade), false), now()
        FROM notas n
        LEFT JOIN disciplinas d ON d.id = n.disciplina_id
        WHERE n.aluno_id = %s AND n.disciplina_id = %s
        GROUP BY n.aluno_id, n.disciplina_id
        ON CONFLICT (aluno_id, disciplina_id) DO UPDATE
        SET nota_final = EXCLUDED.nota_final,
            status = EXCLUDED.status,
            eh_extra_grade = EXCLUDED.eh_extra_grade,
            atualizado_em = now()
        """,
        (aluno_id, disciplina_id),
    )


def _enriquecer_nota_memoria(nota: Dict[str, Any]) -> Dict[str, Any]:
    from app.modules.alunos import _alunos_db
    from app.modules.cursos_disciplinas import _disciplinas_db

    resultado = dict(nota)
    aluno = _alunos_db.get(str(nota.get("aluno_id")), {})
    usuario_id = aluno.get("usuario_id")
    usuario = get_auth_repository().get_user_by_id(str(usuario_id)) if usuario_id else None
    if usuario:
        resultado["aluno_nome"] = " ".join(
            filter(None, [usuario.get("nome"), usuario.get("sobrenome")])
        )
        resultado["aluno_email"] = usuario.get("email")
        resultado["aluno_cpf"] = usuario.get("cpf")
    resultado["aluno_matricula"] = aluno.get("numero_matricula")
    disciplina = _disciplinas_db.get(str(nota.get("disciplina_id")), {})
    resultado["disciplina_nome"] = (
        resultado.get("disciplina_nome") or disciplina.get("nome")
    )
    return resultado


def _ordenacao_atualizacao(nota: Dict[str, Any]) -> tuple[int, float, str]:
    atualizado_em = nota.get("atualizado_em")
    if isinstance(atualizado_em, datetime):
        if atualizado_em.tzinfo is None:
            atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
        return (1, atualizado_em.timestamp(), str(nota.get("id") or ""))
    return (0, 0, str(nota.get("id") or ""))


@router.get(
    "/notas/admin",
    response_model=AdminNotaListResponse,
    dependencies=[Depends(require_role(["admin"]))],
)
async def listar_notas_admin(
    q: Optional[str] = Query(default=None, max_length=100),
    aluno_id: Optional[str] = None,
    disciplina_id: Optional[str] = None,
    disciplina_nome: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(default=30, ge=30, le=30),
    offset: int = Query(default=0, ge=0),
):
    termo = (q or "").strip()
    if not settings.PG_DSN:
        notas = [_enriquecer_nota_memoria(nota) for nota in _notas_db.values()]
        if aluno_id:
            notas = [nota for nota in notas if str(nota.get("aluno_id")) == str(aluno_id)]
        if disciplina_id:
            notas = [
                nota for nota in notas
                if str(nota.get("disciplina_id")) == str(disciplina_id)
            ]
        if disciplina_nome and disciplina_nome.strip():
            nome_busca = disciplina_nome.strip().casefold()
            notas = [
                nota for nota in notas
                if nome_busca in str(nota.get("disciplina_nome") or "").casefold()
            ]
        if termo:
            termo_normalizado = termo.casefold()
            cpf_busca = re.sub(r"\D", "", termo)
            notas = [
                nota for nota in notas
                if any(
                    termo_normalizado in str(nota.get(campo) or "").casefold()
                    for campo in (
                        "aluno_nome",
                        "aluno_email",
                        "aluno_matricula",
                        "aluno_cpf",
                    )
                )
                or (
                    bool(cpf_busca)
                    and cpf_busca in re.sub(r"\D", "", str(nota.get("aluno_cpf") or ""))
                )
            ]
        notas.sort(key=_ordenacao_atualizacao, reverse=True)
        total = len(notas)
        return {
            "items": notas[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    conds: List[str] = []
    params: List[Any] = []
    if aluno_id:
        conds.append("nota.aluno_id = %s")
        params.append(aluno_id)
    if disciplina_id:
        conds.append("nota.disciplina_id = %s")
        params.append(disciplina_id)
    if disciplina_nome and disciplina_nome.strip():
        conds.append("disciplina.nome ILIKE %s")
        params.append(f"%{disciplina_nome.strip()}%")
    if termo:
        busca = f"%{termo}%"
        busca_conds = [
            "concat_ws(' ', usuario.nome, usuario.sobrenome) ILIKE %s",
            "usuario.email ILIKE %s",
            "aluno.numero_matricula ILIKE %s",
        ]
        params.extend([busca, busca, busca])
        cpf_busca = re.sub(r"\D", "", termo)
        if cpf_busca:
            busca_conds.append(
                "regexp_replace(COALESCE(usuario.cpf, ''), '[^0-9]', '', 'g') ILIKE %s"
            )
            params.append(f"%{cpf_busca}%")
        conds.append("(" + " OR ".join(busca_conds) + ")")

    from_sql = """
        FROM notas nota
        JOIN alunos aluno ON aluno.id = nota.aluno_id
        JOIN usuarios usuario ON usuario.id = aluno.usuario_id
        LEFT JOIN disciplinas disciplina ON disciplina.id = nota.disciplina_id
        LEFT JOIN turmas turma ON turma.id = nota.turma_id
    """
    where_sql = " WHERE " + " AND ".join(conds) if conds else ""
    with get_db_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total {from_sql}{where_sql}", tuple(params))
        total = int(cur.fetchone()["total"])
        sql = f"""
        SELECT nota.id, nota.aluno_id,
               concat_ws(' ', usuario.nome, usuario.sobrenome) AS aluno_nome,
               usuario.email AS aluno_email, usuario.cpf AS aluno_cpf,
               aluno.numero_matricula AS aluno_matricula,
               nota.disciplina_id, disciplina.nome AS disciplina_nome,
               nota.turma_id, turma.nome AS turma_nome, nota.origem, nota.valor,
               nota.lancado_por, nota.lancado_em, nota.atualizado_em
        {from_sql}
        {where_sql}
        ORDER BY nota.atualizado_em DESC NULLS LAST, nota.id DESC
        LIMIT %s OFFSET %s
        """
        cur.execute(sql, (*params, limit, offset))
        items = [dict(row) for row in cur.fetchall()]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/notas",
    response_model=List[NotaResponse],
    dependencies=[Depends(require_role(["admin", "professor", "polo", "escola", "aluno"]))],
)
async def list_notas(
    aluno_id: Optional[str] = None,
    disciplina_id: Optional[str] = None,
    turma_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    perfil = perfil_do_usuario(current_user)
    if perfil == "aluno" or (current_user.tambem_aluno and perfil != "admin"):
        proprio_aluno_id = _aluno_id_do_usuario(current_user)
        if aluno_id and str(aluno_id) != proprio_aluno_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso permitido somente às próprias notas")
        aluno_id = proprio_aluno_id
    elif perfil in {"polo", "escola"}:
        if not (current_user.polo_id if perfil == "polo" else current_user.escola_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário sem vínculo com sua unidade")

    eh_professor = usuario_eh_professor(current_user)
    if not settings.PG_DSN:
        notas = list(_notas_db.values())
        if aluno_id:
            notas = [nota for nota in notas if str(nota.get("aluno_id")) == str(aluno_id)]
        if disciplina_id:
            notas = [nota for nota in notas if str(nota.get("disciplina_id")) == str(disciplina_id)]
        if turma_id:
            notas = [nota for nota in notas if str(nota.get("turma_id")) == str(turma_id)]
        if perfil in {"polo", "escola"}:
            from app.modules.alunos import _alunos_db

            coluna = "polo_id" if perfil == "polo" else "escola_id"
            unidade_id = current_user.polo_id if perfil == "polo" else current_user.escola_id
            alunos_unidade = {
                str(a["id"]) for a in _alunos_db.values()
                if str(a.get(coluna)) == str(unidade_id)
            }
            notas = [nota for nota in notas if str(nota.get("aluno_id")) in alunos_unidade]
        if eh_professor:
            vinculos = listar_vinculos_academicos_docente(current_user)
            atribuicoes = {
                (str(v["disciplina_id"]), str(v["turma_id"]))
                for v in vinculos if v.get("disciplina_id") and v.get("turma_id")
            }
            notas = [
                nota for nota in notas
                if (str(nota.get("disciplina_id")), str(nota.get("turma_id"))) in atribuicoes
                and aluno_vinculado_a_turma(str(nota.get("aluno_id")), str(nota.get("turma_id")))
            ]
        return sorted(notas, key=lambda nota: str(nota.get("lancado_em") or ""), reverse=True)

    conds: List[str] = []
    params: List[Any] = []
    if aluno_id:
        conds.append("nota.aluno_id = %s")
        params.append(aluno_id)
    if disciplina_id:
        conds.append("nota.disciplina_id = %s")
        params.append(disciplina_id)
    if turma_id:
        conds.append("nota.turma_id = %s")
        params.append(turma_id)
    if perfil in {"polo", "escola"}:
        coluna = "polo_id" if perfil == "polo" else "escola_id"
        unidade_id = current_user.polo_id if perfil == "polo" else current_user.escola_id
        conds.append(f"EXISTS (SELECT 1 FROM alunos a WHERE a.id = nota.aluno_id AND a.{coluna} = %s)")
        params.append(unidade_id)
    if eh_professor:
        conds.append(
            """
            EXISTS (
                SELECT 1
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN turma_alunos matricula
                  ON matricula.turma_id = vinculo.turma_id
                 AND matricula.aluno_id = nota.aluno_id
                WHERE professor.usuario_id = %s
                  AND vinculo.disciplina_id = nota.disciplina_id
                  AND vinculo.turma_id = nota.turma_id
                  AND vinculo.ativo = true
            )
            """
        )
        params.append(str(current_user.id))

    sql = """
        SELECT nota.id, nota.aluno_id,
               concat_ws(' ', usuario.nome, usuario.sobrenome) AS aluno_nome,
               nota.disciplina_id, disciplina.nome AS disciplina_nome,
               nota.turma_id, turma.nome AS turma_nome, nota.origem, nota.valor,
               nota.lancado_por, nota.lancado_em, nota.atualizado_em
        FROM notas nota
        JOIN alunos aluno ON aluno.id = nota.aluno_id
        JOIN usuarios usuario ON usuario.id = aluno.usuario_id
        LEFT JOIN disciplinas disciplina ON disciplina.id = nota.disciplina_id
        LEFT JOIN turmas turma ON turma.id = nota.turma_id
    """
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY nota.lancado_em DESC NULLS LAST, nota.id"
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


@router.post(
    "/notas",
    response_model=NotaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "professor"]))],
)
async def lancar_nota(
    dados: NotaCreateRequest,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
):
    exigir_vinculo_turma_docente(
        current_user,
        aluno_id=dados.aluno_id,
        disciplina_id=dados.disciplina_id,
        turma_id=dados.turma_id,
    )
    new_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    nota = {
        **dados.model_dump(),
        "id": new_id,
        "lancado_por": str(current_user.id),
        "lancado_em": agora,
        "atualizado_em": agora,
    }
    dados_depois = {
        "aluno_id": dados.aluno_id,
        "disciplina_id": dados.disciplina_id,
        "turma_id": dados.turma_id,
        "origem": dados.origem,
        "valor": dados.valor,
    }

    if not settings.PG_DSN:
        _notas_db[new_id] = nota
        _atualizar_historico_memoria(dados.aluno_id, dados.disciplina_id)
        _registrar_auditoria(
            user=current_user,
            action="nota_lancada",
            nota_id=new_id,
            before=None,
            after=dados_depois,
            ip=get_client_ip(request),
        )
        return nota

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO notas (
                id, aluno_id, disciplina_id, turma_id, origem, valor, lancado_por,
                lancado_em, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now(), now())
            """,
            (
                new_id,
                dados.aluno_id,
                dados.disciplina_id,
                dados.turma_id,
                dados.origem,
                dados.valor,
                str(current_user.id),
            ),
        )
        _atualizar_historico_postgres(cur, dados.aluno_id, dados.disciplina_id)
        _registrar_auditoria(
            user=current_user,
            action="nota_lancada",
            nota_id=new_id,
            before=None,
            after=dados_depois,
            ip=get_client_ip(request),
            cursor=cur,
        )
    return nota


@router.put(
    "/notas/{nota_id}",
    response_model=NotaResponse,
    dependencies=[Depends(require_role(["admin", "professor"]))],
)
async def corrigir_nota(
    nota_id: str,
    dados: NotaUpdateRequest,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
):
    if not settings.PG_DSN:
        nota = _notas_db.get(nota_id)
        if not nota:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota não encontrada")
        exigir_vinculo_turma_docente(
            current_user,
            aluno_id=str(nota["aluno_id"]),
            disciplina_id=str(nota["disciplina_id"]),
            turma_id=str(nota["turma_id"]),
        )
        antes = {"valor": float(nota["valor"])}
        nota["valor"] = dados.valor
        nota["atualizado_em"] = datetime.now(timezone.utc)
        _atualizar_historico_memoria(str(nota["aluno_id"]), str(nota["disciplina_id"]))
        _registrar_auditoria(
            user=current_user,
            action="nota_corrigida",
            nota_id=nota_id,
            before=antes,
            after={"valor": dados.valor},
            ip=get_client_ip(request),
        )
        return nota

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, aluno_id, disciplina_id, turma_id, valor
            FROM notas WHERE id = %s FOR UPDATE
            """,
            (nota_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota não encontrada")
        nota_anterior = dict(row)
        exigir_vinculo_turma_docente(
            current_user,
            aluno_id=str(nota_anterior["aluno_id"]),
            disciplina_id=str(nota_anterior["disciplina_id"]),
            turma_id=str(nota_anterior["turma_id"]),
        )
        cur.execute(
            "UPDATE notas SET valor = %s, atualizado_em = now() WHERE id = %s",
            (dados.valor, nota_id),
        )
        _atualizar_historico_postgres(
            cur, str(nota_anterior["aluno_id"]), str(nota_anterior["disciplina_id"])
        )
        _registrar_auditoria(
            user=current_user,
            action="nota_corrigida",
            nota_id=nota_id,
            before={"valor": float(nota_anterior["valor"])},
            after={"valor": dados.valor},
            ip=get_client_ip(request),
            cursor=cur,
        )
        cur.execute(
            """
            SELECT id, aluno_id, disciplina_id, turma_id, origem, valor, lancado_por,
                   lancado_em, atualizado_em
            FROM notas WHERE id = %s
            """,
            (nota_id,),
        )
        return dict(cur.fetchone())


def _historico_do_aluno(aluno_id: str) -> List[Dict[str, Any]]:
    if not settings.PG_DSN:
        return sorted(
            [
                dict(item)
                for item in _historico_db.values()
                if str(item.get("aluno_id")) == str(aluno_id)
            ],
            key=lambda item: str(item.get("disciplina_nome") or item.get("disciplina_id") or ""),
        )
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT historico.id, historico.aluno_id, historico.disciplina_id,
                   disciplina.nome AS disciplina_nome, disciplina.curso_id,
                   curso.nome AS curso_nome, historico.nota_final, historico.status,
                   historico.eh_extra_grade
            FROM historico_unificado historico
            LEFT JOIN disciplinas disciplina ON disciplina.id = historico.disciplina_id
            LEFT JOIN cursos curso ON curso.id = disciplina.curso_id
            WHERE historico.aluno_id = %s
            ORDER BY curso.nome NULLS LAST, disciplina.semestre NULLS LAST,
                     disciplina.ordem NULLS LAST, disciplina.nome NULLS LAST
            """,
            (aluno_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def _historico_no_escopo(aluno_id: str, user: UserResponse) -> List[Dict[str, Any]]:
    if not _aluno_no_escopo(aluno_id, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado ao histórico deste aluno")
    historico = _historico_do_aluno(aluno_id)
    if not usuario_eh_professor(user):
        return historico
    vinculos = listar_vinculos_academicos_docente(user)
    atribuicoes = {
        (str(v.get("disciplina_id")), str(v.get("turma_id")))
        for v in vinculos if v.get("disciplina_id") and v.get("turma_id")
    }
    if not settings.PG_DSN:
        return [
            item for item in historico
            if any(
                disciplina_id == str(item.get("disciplina_id"))
                and aluno_vinculado_a_turma(aluno_id, turma_id)
                for disciplina_id, turma_id in atribuicoes
            )
        ]
    if not atribuicoes:
        return []
    return [
        item for item in historico
        if any(
            disciplina_id == str(item.get("disciplina_id"))
            and aluno_vinculado_a_turma(aluno_id, turma_id)
            for disciplina_id, turma_id in atribuicoes
        )
    ]


@router.get(
    "/historico/me",
    response_model=List[HistoricoUnificadoSchema],
    dependencies=[Depends(require_role(["aluno"]))],
)
async def get_meu_historico(current_user: UserResponse = Depends(get_current_user)):
    return _historico_do_aluno(_aluno_id_do_usuario(current_user))


@router.get(
    "/historico/me/pdf",
    dependencies=[Depends(require_role(["aluno"]))],
)
async def baixar_meu_historico_pdf(current_user: UserResponse = Depends(get_current_user)):
    aluno_id = _aluno_id_do_usuario(current_user)
    historico = _historico_do_aluno(aluno_id)
    cursos: Dict[str, List[DisciplinaAcademicaResponse]] = {}
    nomes_cursos: Dict[str, str] = {}
    for item in historico:
        curso_id = str(item.get("curso_id") or "sem-curso")
        nomes_cursos[curso_id] = str(item.get("curso_nome") or "Disciplinas")
        cursos.setdefault(curso_id, []).append(
            DisciplinaAcademicaResponse(
                id=str(item.get("disciplina_id") or ""),
                nome=str(item.get("disciplina_nome") or "Disciplina"),
                semestre=None,
                carga_horaria=None,
                nota=float(item["nota_final"]) if item.get("nota_final") is not None else None,
                situacao=str(item.get("status") or "cursando"),
                em_curso=str(item.get("status") or "") == "cursando",
                total_conteudos=0,
                conteudos_concluidos=0,
                progresso=None,
            )
        )
    academico = AcademicoResponse(
        aluno_id=aluno_id,
        aluno_nome=" ".join(filter(None, [current_user.nome, current_user.sobrenome])),
        numero_matricula=None,
        cursos=[
            CursoAcademicoResponse(id=curso_id, nome=nomes_cursos[curso_id], disciplinas=disciplinas)
            for curso_id, disciplinas in cursos.items()
        ],
    )
    return Response(
        content=gerar_boletim_pdf(academico),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="meu-historico-academico.pdf"'},
    )


@router.get(
    "/historico/{aluno_id}",
    response_model=List[HistoricoUnificadoSchema],
    dependencies=[Depends(require_role(["admin", "polo", "escola", "professor", "aluno"]))],
)
async def get_historico_aluno(
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    return _historico_no_escopo(aluno_id, current_user)
