"""Módulo de Cursos, Disciplinas e Conteúdos AVA do NEXUS 2.0."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import exigir_vinculo_disciplina

router = APIRouter(prefix="/cursos-disciplinas", tags=["Cursos & Disciplinas (AVA)"])

NivelAcademico = Literal[
    "bacharelado",
    "licenciatura",
    "tecnologo",
    "pos_graduacao",
    "mestrado",
    "curso_livre",
]
ModalidadeCurso = Literal["hibrido", "presencial", "ead"]
StatusCurso = Literal["ativo", "cancelado"]
# "polo" e "inativo" só existem em cursos importados do legado; a edição precisa preservá-los.
ModalidadeCursoEdicao = Literal["hibrido", "presencial", "ead", "polo"]
StatusCursoEdicao = Literal["ativo", "cancelado", "inativo"]


class CursoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    nome: str = Field(min_length=2, max_length=255)
    descricao: Optional[str] = None
    modalidade: str = "hibrido"
    carga_horaria_total: Optional[int] = 0
    semestres: int = 3
    status: str = "ativo"
    nivel_academico: Optional[NivelAcademico] = None


class CursoCreateSchema(CursoSchema):
    nome: str = Field(min_length=2, max_length=255)
    descricao: str = Field(min_length=1)
    modalidade: ModalidadeCurso
    carga_horaria_total: int = Field(gt=0)
    semestres: int = Field(gt=0)
    status: StatusCurso
    nivel_academico: NivelAcademico
    disciplina_ids: List[uuid.UUID] = Field(default_factory=list)


class CursoUpdateSchema(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    descricao: str = Field(min_length=1)
    modalidade: ModalidadeCursoEdicao
    carga_horaria_total: int = Field(gt=0)
    semestres: int = Field(gt=0)
    status: StatusCursoEdicao
    nivel_academico: NivelAcademico
    # None mantém os vínculos atuais; uma lista substitui todos os vínculos do curso.
    disciplina_ids: Optional[List[uuid.UUID]] = None


class CursosPaginaSchema(BaseModel):
    items: List[CursoSchema]
    total: int
    limit: int
    offset: int


class DisciplinaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    semestre: Optional[int] = Field(default=1, ge=0)
    nome: str = Field(min_length=1, max_length=255)
    ordem: int = 0
    carga_horaria: Optional[int] = Field(default=40, ge=0)
    qtd_aulas_prevista: Optional[int] = Field(default=10, ge=0)
    tipo: str = Field(default="presencial", min_length=1, max_length=16)
    eh_extra_grade: bool = False


class DisciplinaWriteSchema(BaseModel):
    curso_id: Optional[str] = None
    semestre: Optional[int] = Field(default=1, ge=0)
    nome: str = Field(min_length=1, max_length=255)
    ordem: int = 0
    carga_horaria: Optional[int] = Field(default=40, ge=0)
    qtd_aulas_prevista: Optional[int] = Field(default=10, ge=0)
    tipo: str = Field(default="presencial", min_length=1, max_length=16)
    eh_extra_grade: bool = False


class DisciplinaConteudoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: str
    titulo: Optional[str] = None
    tipo_midia: Optional[str] = "video"
    url_arquivo: Optional[str] = None
    ordem: int = 0


class ProfessorVinculadoSchema(BaseModel):
    professor_id: str
    usuario_id: Optional[str] = None
    nome: str
    email: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    valor_hora_aula: Optional[float] = None
    quantidade_aulas: int = 0


_cursos_db: Dict[str, Dict[str, Any]] = {}
_disciplinas_db: Dict[str, Dict[str, Any]] = {}
_conteudos_db: Dict[str, Dict[str, Any]] = {}

CURSO_COM_VINCULOS_DETAIL = (
    "Não é possível excluir um curso que possui disciplinas, turmas, calendários, "
    "matrículas EAD ou certificados vinculados."
)


def _vincular_disciplinas(cur: Any, curso_id: str, disciplina_ids: List[str]) -> None:
    cur.execute(
        """
        UPDATE disciplinas
        SET curso_id = %s, atualizado_em = now()
        WHERE id = ANY(%s::uuid[])
        RETURNING id
        """,
        (curso_id, disciplina_ids),
    )
    updated_ids = {str(row["id"]) for row in cur.fetchall()}
    if updated_ids != set(disciplina_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uma ou mais disciplinas não foram encontradas.",
        )


@router.get(
    "/cursos",
    response_model=List[CursoSchema],
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def list_cursos():
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, nome, descricao, modalidade, carga_horaria_total,
                       semestres, status, nivel_academico
                FROM cursos
                ORDER BY nome
                """
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_cursos_db.values())


@router.get(
    "/cursos/paginados",
    response_model=CursosPaginaSchema,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def list_cursos_paginados(
    q: Optional[str] = Query(None, max_length=255),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    search_term = q.strip().lower() if q and q.strip() else None
    if not settings.PG_DSN:
        filtered = list(_cursos_db.values())
        if search_term:
            filtered = [
                course
                for course in filtered
                if search_term in (course.get("nome") or "").lower()
                or search_term in (course.get("descricao") or "").lower()
            ]
        filtered.sort(
            key=lambda course: (
                (course.get("nome") or "").lower(),
                str(course.get("id") or ""),
            )
        )
        total = len(filtered)
        return {
            "items": filtered[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    conditions = ""
    params: List[Any] = []
    if search_term:
        conditions = "WHERE lower(nome) LIKE %s OR lower(coalesce(descricao, '')) LIKE %s"
        pattern = f"%{search_term}%"
        params.extend([pattern, pattern])

    with get_db_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM cursos {conditions}", tuple(params))
        total_row = cur.fetchone()
        total = int(total_row["total"]) if total_row else 0

        cur.execute(
            f"""
            SELECT id, nome, descricao, modalidade, carga_horaria_total,
                   semestres, status, nivel_academico
            FROM cursos
            {conditions}
            ORDER BY nome, id
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        return {
            "items": [dict(row) for row in cur.fetchall()],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/cursos", response_model=CursoSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_curso(dados: CursoCreateSchema):
    new_id = str(uuid.uuid4())
    disciplina_ids = list(dict.fromkeys(str(disciplina_id) for disciplina_id in dados.disciplina_ids))
    c_dict = dados.model_dump(exclude={"disciplina_ids"})
    c_dict["id"] = new_id
    if not settings.PG_DSN:
        missing_ids = [disciplina_id for disciplina_id in disciplina_ids if disciplina_id not in _disciplinas_db]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uma ou mais disciplinas não foram encontradas.",
            )
        _cursos_db[new_id] = c_dict
        for disciplina_id in disciplina_ids:
            _disciplinas_db[disciplina_id]["curso_id"] = new_id
        return c_dict

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO cursos (
                id, nome, descricao, modalidade, carga_horaria_total, semestres,
                status, nivel_academico, criado_em, atualizado_em
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """,
            (
                new_id,
                dados.nome,
                dados.descricao,
                dados.modalidade,
                dados.carga_horaria_total,
                dados.semestres,
                dados.status,
                dados.nivel_academico,
            ),
        )
        if disciplina_ids:
            _vincular_disciplinas(cur, new_id, disciplina_ids)
    return c_dict


@router.put(
    "/cursos/{curso_id}",
    response_model=CursoSchema,
    dependencies=[Depends(require_role(["admin"]))],
)
async def update_curso(curso_id: uuid.UUID, dados: CursoUpdateSchema):
    uid = str(curso_id)
    disciplina_ids = (
        None
        if dados.disciplina_ids is None
        else list(dict.fromkeys(str(disciplina_id) for disciplina_id in dados.disciplina_ids))
    )
    if not settings.PG_DSN:
        current = _cursos_db.get(uid)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado")
        if disciplina_ids is not None:
            if any(disciplina_id not in _disciplinas_db for disciplina_id in disciplina_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Uma ou mais disciplinas não foram encontradas.",
                )
            for disciplina_id, disciplina in _disciplinas_db.items():
                if disciplina_id in disciplina_ids:
                    disciplina["curso_id"] = uid
                elif disciplina.get("curso_id") == uid:
                    disciplina["curso_id"] = None
        current.update(dados.model_dump(exclude={"disciplina_ids"}))
        return current

    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE cursos
            SET nome = %s, descricao = %s, modalidade = %s, carga_horaria_total = %s,
                semestres = %s, status = %s, nivel_academico = %s, atualizado_em = now()
            WHERE id = %s
            RETURNING id, nome, descricao, modalidade, carga_horaria_total,
                      semestres, status, nivel_academico
            """,
            (
                dados.nome,
                dados.descricao,
                dados.modalidade,
                dados.carga_horaria_total,
                dados.semestres,
                dados.status,
                dados.nivel_academico,
                uid,
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado")
        if disciplina_ids is not None:
            cur.execute(
                """
                UPDATE disciplinas
                SET curso_id = NULL, atualizado_em = now()
                WHERE curso_id = %s AND NOT (id = ANY(%s::uuid[]))
                """,
                (uid, disciplina_ids),
            )
            if disciplina_ids:
                _vincular_disciplinas(cur, uid, disciplina_ids)
        return dict(row)


@router.delete(
    "/cursos/{curso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(["admin"]))],
)
async def delete_curso(curso_id: uuid.UUID) -> Response:
    uid = str(curso_id)
    if not settings.PG_DSN:
        from app.modules.turmas import _calendarios_db, _turmas_db

        if uid not in _cursos_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado")
        vinculados = (*_disciplinas_db.values(), *_turmas_db.values(), *_calendarios_db.values())
        if any(item.get("curso_id") == uid for item in vinculados):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CURSO_COM_VINCULOS_DETAIL)
        del _cursos_db[uid]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # As FKs usam ON DELETE SET NULL: sem esta verificação, os registros ficariam órfãos.
    references_sql = """
        SELECT
            EXISTS (SELECT 1 FROM disciplinas WHERE curso_id = %s)
            OR EXISTS (SELECT 1 FROM turmas WHERE curso_id = %s)
            OR EXISTS (SELECT 1 FROM calendarios_oficiais WHERE curso_id = %s)
            OR EXISTS (SELECT 1 FROM matriculas_ead WHERE curso_id = %s)
            OR EXISTS (SELECT 1 FROM certificados WHERE curso_id = %s)
            AS em_uso
    """
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM cursos WHERE id = %s FOR UPDATE", (uid,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso não encontrado")

        cur.execute(references_sql, (uid,) * 5)
        row = cur.fetchone()
        if row is None or row["em_uso"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CURSO_COM_VINCULOS_DETAIL)

        cur.execute("DELETE FROM cursos WHERE id = %s", (uid,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/disciplinas",
    response_model=List[DisciplinaSchema],
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def list_disciplinas(
    curso_id: Optional[str] = None,
    semestre: Optional[int] = Query(None, ge=0),
):
    if not settings.PG_DSN:
        discs = list(_disciplinas_db.values())
        if curso_id:
            discs = [d for d in discs if d.get("curso_id") == curso_id]
        if semestre is not None:
            discs = [d for d in discs if d.get("semestre") == semestre]
        return discs

    sql = "SELECT id, curso_id, semestre, nome, ordem, carga_horaria, qtd_aulas_prevista, tipo, eh_extra_grade FROM disciplinas"
    conds = []
    params = []
    if curso_id:
        conds.append("curso_id = %s")
        params.append(curso_id)
    if semestre is not None:
        conds.append("semestre = %s")
        params.append(semestre)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY ordem ASC"
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]


@router.get(
    "/disciplinas/{disciplina_id}/professores",
    response_model=List[ProfessorVinculadoSchema],
    dependencies=[Depends(require_role(["admin"]))],
)
async def list_professores_disciplina(disciplina_id: uuid.UUID):
    uid = str(disciplina_id)
    if not settings.PG_DSN:
        if uid not in _disciplinas_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        return []

    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM disciplinas WHERE id = %s LIMIT 1", (uid,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")

        cur.execute(
            """
            WITH professores_vinculados AS (
                SELECT professor_id
                FROM professor_disciplina_vinculos
                WHERE disciplina_id = %s
                UNION
                SELECT prof.id
                FROM professores prof
                JOIN disciplinas disc ON disc.id = %s
                CROSS JOIN LATERAL jsonb_array_elements_text(
                    CASE
                        WHEN jsonb_typeof(prof.materias) = 'array' THEN prof.materias
                        ELSE '[]'::jsonb
                    END
                ) AS materia(nome)
                WHERE lower(trim(materia.nome)) = lower(trim(disc.nome))
            )
            SELECT
                prof.id::text AS professor_id,
                prof.usuario_id::text AS usuario_id,
                concat_ws(' ', usuario.nome, usuario.sobrenome) AS nome,
                usuario.email,
                polo.nome AS polo_nome,
                escola.nome AS escola_nome,
                prof.valor_hora_aula,
                COALESCE(prof.quantidade_aulas, 0) AS quantidade_aulas
            FROM professores_vinculados vinculo
            JOIN professores prof ON prof.id = vinculo.professor_id
            LEFT JOIN usuarios usuario ON usuario.id = prof.usuario_id
            LEFT JOIN polos polo ON polo.id = prof.polo_id
            LEFT JOIN escolas escola ON escola.id = prof.escola_id
            ORDER BY usuario.nome, usuario.sobrenome, usuario.email
            """,
            (uid, uid),
        )
        return [dict(row) for row in cur.fetchall()]


@router.post(
    "/disciplinas",
    response_model=DisciplinaSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin"]))],
)
async def create_disciplina(dados: DisciplinaWriteSchema):
    new_id = str(uuid.uuid4())
    d_dict = dados.model_dump()
    d_dict["id"] = new_id
    if not settings.PG_DSN:
        _disciplinas_db[new_id] = d_dict
        return d_dict

    sql = """
        INSERT INTO disciplinas (
            id, curso_id, semestre, nome, ordem, carga_horaria,
            qtd_aulas_prevista, tipo, eh_extra_grade, criado_em, atualizado_em
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        RETURNING id, curso_id, semestre, nome, ordem, carga_horaria,
                  qtd_aulas_prevista, tipo, eh_extra_grade
    """
    params = (
        new_id,
        dados.curso_id,
        dados.semestre,
        dados.nome,
        dados.ordem,
        dados.carga_horaria,
        dados.qtd_aulas_prevista,
        dados.tipo,
        dados.eh_extra_grade,
    )
    with get_db_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Não foi possível cadastrar a disciplina.")
        return dict(row)


@router.put(
    "/disciplinas/{disciplina_id}",
    response_model=DisciplinaSchema,
    dependencies=[Depends(require_role(["admin"]))],
)
async def update_disciplina(disciplina_id: uuid.UUID, dados: DisciplinaWriteSchema):
    uid = str(disciplina_id)
    updated = dados.model_dump()
    if not settings.PG_DSN:
        current = _disciplinas_db.get(uid)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        current.update(updated)
        return current

    sql = """
        UPDATE disciplinas
        SET curso_id = %s, semestre = %s, nome = %s, ordem = %s,
            carga_horaria = %s, qtd_aulas_prevista = %s, tipo = %s,
            eh_extra_grade = %s, atualizado_em = now()
        WHERE id = %s
        RETURNING id, curso_id, semestre, nome, ordem, carga_horaria,
                  qtd_aulas_prevista, tipo, eh_extra_grade
    """
    params = (
        dados.curso_id,
        dados.semestre,
        dados.nome,
        dados.ordem,
        dados.carga_horaria,
        dados.qtd_aulas_prevista,
        dados.tipo,
        dados.eh_extra_grade,
        uid,
    )
    with get_db_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        return dict(row)


@router.delete(
    "/disciplinas/{disciplina_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(["admin"]))],
)
async def delete_disciplina(disciplina_id: uuid.UUID) -> Response:
    uid = str(disciplina_id)
    if not settings.PG_DSN:
        if uid not in _disciplinas_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        if any(content.get("disciplina_id") == uid for content in _conteudos_db.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível excluir uma disciplina que possui conteúdos ou vínculos acadêmicos.",
            )
        del _disciplinas_db[uid]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    references_sql = """
        SELECT
            EXISTS (SELECT 1 FROM calendarios_oficiais WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM disciplina_conteudos WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM professor_disciplinas WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM professor_disciplina_vinculos WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM compras_disciplina_ead WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM avisos_liberacao_ead WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM notas WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM historico_unificado WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM estoque_licencas WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM licencas_atribuidas WHERE disciplina_id = %s)
            OR EXISTS (SELECT 1 FROM pedidos_livros_itens WHERE disciplina_id = %s)
            AS em_uso
    """
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM disciplinas WHERE id = %s FOR UPDATE", (uid,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")

        cur.execute(references_sql, (uid,) * 11)
        row = cur.fetchone()
        if row is None or row["em_uso"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível excluir uma disciplina que possui conteúdos ou vínculos acadêmicos.",
            )

        cur.execute("DELETE FROM disciplinas WHERE id = %s", (uid,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/disciplinas/{disciplina_id}/conteudos",
    response_model=List[DisciplinaConteudoSchema],
    dependencies=[Depends(require_role(["admin", "polo", "escola", "professor", "aluno"]))],
)
async def list_disciplina_conteudos(
    disciplina_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    exigir_vinculo_disciplina(current_user, disciplina_id)
    if not settings.PG_DSN:
        return [c for c in _conteudos_db.values() if c.get("disciplina_id") == disciplina_id]

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id, disciplina_id, titulo, tipo_midia, url_arquivo, ordem "
            "FROM disciplina_conteudos WHERE disciplina_id = %s ORDER BY ordem ASC",
            (disciplina_id,),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post(
    "/disciplinas/{disciplina_id}/conteudos",
    response_model=DisciplinaConteudoSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "professor"]))],
)
async def create_disciplina_conteudo(
    disciplina_id: str,
    dados: DisciplinaConteudoSchema,
    current_user: UserResponse = Depends(get_current_user),
):
    exigir_vinculo_disciplina(current_user, disciplina_id)
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    c_dict["disciplina_id"] = disciplina_id
    if not settings.PG_DSN:
        _conteudos_db[new_id] = c_dict
        return c_dict

    sql = (
        "INSERT INTO disciplina_conteudos "
        "(id, disciplina_id, titulo, tipo_midia, url_arquivo, ordem, criado_em, atualizado_em) "
        "VALUES (%s, %s, %s, %s, %s, %s, now(), now())"
    )
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (new_id, disciplina_id, dados.titulo, dados.tipo_midia, dados.url_arquivo, dados.ordem),
        )
    return c_dict
