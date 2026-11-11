"""Repositório de dados do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor

_SELECT_BASE = """
    SELECT prof.*, u.nome, u.email,
           p.nome AS polo_nome, e.nome AS escola_nome,
           COALESCE(vinculos.disciplina_ids, ARRAY[]::text[]) AS disciplina_ids,
           COALESCE(vinculos.disciplina_nomes, ARRAY[]::text[]) AS disciplina_nomes
    FROM professores prof
    LEFT JOIN usuarios u ON u.id = prof.usuario_id
    LEFT JOIN polos p ON p.id = prof.polo_id
    LEFT JOIN escolas e ON e.id = prof.escola_id
    LEFT JOIN LATERAL (
        SELECT
            array_agg(vinculo.disciplina_id::text ORDER BY vinculo.disciplina_id::text) AS disciplina_ids,
            array_agg(DISTINCT disciplina.nome ORDER BY disciplina.nome) AS disciplina_nomes
        FROM professor_disciplina_vinculos vinculo
        JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
        WHERE vinculo.professor_id = prof.id
    ) vinculos ON TRUE
"""


class ProfessoresRepositoryInterface(Protocol):
    def get_turma_vinculo_scope(self, turma_id: str) -> Optional[Dict[str, Any]]: ...

    def get_disciplina_curso(self, disciplina_id: str) -> Optional[str]: ...

    def list_vinculos_ativos_por_turma(
        self, turma_id: str, scope_column: Optional[str] = None, scope_id: Optional[str] = None
    ) -> List[Dict[str, Any]]: ...

    def create_or_reactivate_vinculo_turma(
        self,
        professor_id: str,
        disciplina_id: str,
        turma_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[str, str]: ...

    def archive_vinculo_turma(
        self,
        turma_id: str,
        vinculo_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], str]: ...

    def list_disciplinas_turmas_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]: ...

    def list_conteudos_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]: ...

    def list_materiais_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]: ...

    def get_conteudo(self, conteudo_id: str) -> Optional[Dict[str, Any]]: ...

    def create_conteudo(self, data: Dict[str, Any]) -> Dict[str, Any]: ...

    def update_conteudo(self, conteudo_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    def get_material(self, material_id: str) -> Optional[Dict[str, Any]]: ...

    def create_material(self, data: Dict[str, Any]) -> Dict[str, Any]: ...

    def update_material(self, material_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    def get_vinculo_academico(self, vinculo_id: str) -> Optional[Dict[str, Any]]: ...

    def list_vinculos_academicos_por_usuario(self, usuario_id: str) -> List[Dict[str, Any]]: ...

    def professor_tem_disciplina(self, usuario_id: str, disciplina_id: str) -> bool: ...

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]: ...

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def get_invalid_disciplina_ids(self, disciplina_ids: List[str]) -> List[str]: ...

    def create_professor(self, data: Dict[str, Any]) -> str: ...

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None: ...

    def set_usuario_perfil(self, usuario_id: str, perfil_nome: str) -> Optional[str]:
        """Define o perfil do usuário; retorna o nome do perfil anterior (ou None se não mudou)."""
        ...

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None: ...


class PostgresProfessoresRepository:
    """Implementação PostgreSQL (SQL crudo via psycopg2, padrão do NEXUS 2.0)."""

    def get_turma_vinculo_scope(self, turma_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, curso_id::text AS curso_id,
                       polo_id::text AS polo_id, escola_id::text AS escola_id
                FROM turmas
                WHERE id = %s
                """,
                (str(turma_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_disciplina_curso(self, disciplina_id: str) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT curso_id::text AS curso_id FROM disciplinas WHERE id = %s",
                (str(disciplina_id),),
            )
            row = cur.fetchone()
            return str(row["curso_id"]) if row and row.get("curso_id") else None

    def list_vinculos_ativos_por_turma(
        self, turma_id: str, scope_column: Optional[str] = None, scope_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if scope_column not in (None, "polo_id", "escola_id"):
            raise ValueError("Coluna de escopo inválida")
        scope_filter = f" AND turma.{scope_column} = %s" if scope_column else ""
        params: Tuple[Any, ...] = (str(turma_id),)
        if scope_column:
            params = (str(turma_id), str(scope_id))
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT vinculo.id::text AS id,
                       professor.id::text AS professor_id,
                       trim(concat(usuario.nome, ' ', usuario.sobrenome)) AS professor_nome,
                       usuario.email AS professor_email,
                       disciplina.id::text AS disciplina_id,
                       disciplina.nome AS disciplina_nome,
                       vinculo.turma_id::text AS turma_id
                FROM professor_disciplinas vinculo
                JOIN turmas turma ON turma.id = vinculo.turma_id
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN usuarios usuario ON usuario.id = professor.usuario_id
                JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
                WHERE vinculo.turma_id = %s AND vinculo.ativo = true
                """
                + scope_filter
                + """
                ORDER BY disciplina.nome, professor_nome
                """,
                params,
            )
            return [dict(row) for row in cur.fetchall()]

    def create_or_reactivate_vinculo_turma(
        self,
        professor_id: str,
        disciplina_id: str,
        turma_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        vinculo_id = str(uuid.uuid4())
        if scope_column not in (None, "polo_id", "escola_id"):
            raise ValueError("Coluna de escopo inválida")
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, curso_id::text AS curso_id,
                       polo_id::text AS polo_id, escola_id::text AS escola_id
                FROM turmas
                WHERE id = %s
                FOR UPDATE
                """,
                (str(turma_id),),
            )
            turma = cur.fetchone()
            if not turma:
                return "", "missing_turma"
            if scope_column and str(turma[scope_column]) != str(scope_id):
                return "", "out_of_scope"
            cur.execute(
                "SELECT curso_id::text AS curso_id FROM disciplinas WHERE id = %s",
                (str(disciplina_id),),
            )
            disciplina = cur.fetchone()
            if not disciplina:
                return "", "missing_discipline"
            if not turma["curso_id"] or str(disciplina["curso_id"]) != str(turma["curso_id"]):
                return "", "course_mismatch"
            cur.execute(
                """
                SELECT professor.status AS professor_status,
                       professor.polo_id::text AS polo_id,
                       professor.escola_id::text AS escola_id,
                       usuario.status AS usuario_status
                FROM professores professor
                JOIN usuarios usuario ON usuario.id = professor.usuario_id
                WHERE professor.id = %s
                FOR SHARE OF professor, usuario
                """,
                (str(professor_id),),
            )
            professor = cur.fetchone()
            if (
                not professor
                or professor["professor_status"] != "ativo"
                or professor["usuario_status"] != "ativo"
            ):
                return "", "inactive_professor"
            if scope_column and str(professor[scope_column]) != str(scope_id):
                return "", "professor_out_of_scope"
            cur.execute(
                """
                SELECT id::text AS id, ativo
                FROM professor_disciplinas
                WHERE professor_id = %s AND disciplina_id = %s AND turma_id = %s
                ORDER BY ativo DESC, criado_em DESC NULLS LAST, id DESC
                LIMIT 1
                FOR UPDATE
                """,
                (str(professor_id), str(disciplina_id), str(turma_id)),
            )
            existing = cur.fetchone()
            if existing and existing["ativo"]:
                return str(existing["id"]), "exists"
            if existing:
                vinculo_id = str(existing["id"])
                cur.execute(
                    """
                    UPDATE professor_disciplinas
                    SET ativo = true, atualizado_em = now()
                    WHERE id = %s
                    """,
                    (vinculo_id,),
                )
                return vinculo_id, "reactivated"
            cur.execute(
                """
                INSERT INTO professor_disciplinas (
                    id, professor_id, disciplina_id, turma_id, ativo, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, true, now(), now())
                """,
                (vinculo_id, str(professor_id), str(disciplina_id), str(turma_id)),
            )
        return vinculo_id, "created"

    def archive_vinculo_turma(
        self,
        turma_id: str,
        vinculo_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        if scope_column not in (None, "polo_id", "escola_id"):
            raise ValueError("Coluna de escopo inválida")
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT {scope_column or 'id'} FROM turmas WHERE id = %s FOR UPDATE",
                (str(turma_id),),
            )
            turma = cur.fetchone()
            if not turma:
                return None, "missing_turma"
            if scope_column and str(turma[scope_column]) != str(scope_id):
                return None, "out_of_scope"
            cur.execute(
                """
                UPDATE professor_disciplinas
                SET ativo = false, atualizado_em = now()
                WHERE id = %s AND turma_id = %s AND ativo = true
                RETURNING id::text AS id, professor_id::text AS professor_id,
                          disciplina_id::text AS disciplina_id, turma_id::text AS turma_id
                """,
                (str(vinculo_id), str(turma_id)),
            )
            row = cur.fetchone()
            return (dict(row), "archived") if row else (None, "missing_vinculo")

    def list_vinculos_academicos_por_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT vinculo.id::text AS id,
                       vinculo.disciplina_id::text AS disciplina_id,
                       vinculo.turma_id::text AS turma_id
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                WHERE professor.usuario_id = %s AND vinculo.ativo = true
                ORDER BY vinculo.id
                """,
                (str(usuario_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    def professor_tem_disciplina(self, usuario_id: str, disciplina_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM professores professor
                    WHERE professor.usuario_id = %s
                      AND (
                          EXISTS (
                              SELECT 1
                              FROM professor_disciplina_vinculos vinculo
                              WHERE vinculo.professor_id = professor.id
                                AND vinculo.disciplina_id = %s
                          )
                          OR EXISTS (
                              SELECT 1
                              FROM professor_disciplinas vinculo
                              WHERE vinculo.professor_id = professor.id
                                AND vinculo.disciplina_id = %s
                          )
                      )
                ) AS vinculado
                """,
                (str(usuario_id), str(disciplina_id), str(disciplina_id)),
            )
            return bool(cur.fetchone()["vinculado"])

    def list_disciplinas_turmas_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                WITH professor AS (
                    SELECT id FROM professores WHERE usuario_id = %s
                ),
                disciplinas_professor AS (
                    SELECT vinculo.disciplina_id
                    FROM professor_disciplina_vinculos vinculo
                    JOIN professor docente ON docente.id = vinculo.professor_id
                    UNION
                    SELECT vinculo.disciplina_id
                    FROM professor_disciplinas vinculo
                    JOIN professor docente ON docente.id = vinculo.professor_id
                    WHERE vinculo.ativo = true
                ),
                turmas_professor AS (
                    SELECT DISTINCT
                        vinculo.disciplina_id,
                        vinculo.id AS professor_disciplina_id,
                        turma.id AS turma_id,
                        turma.nome AS turma_nome,
                        turma.data_inicio,
                        turma.data_fim,
                        polo.nome AS polo_nome,
                        escola.nome AS escola_nome
                    FROM professor_disciplinas vinculo
                    JOIN professor docente ON docente.id = vinculo.professor_id
                    JOIN turmas turma ON turma.id = vinculo.turma_id
                    LEFT JOIN polos polo ON polo.id = turma.polo_id
                    LEFT JOIN escolas escola ON escola.id = turma.escola_id
                    WHERE vinculo.ativo = true
                )
                SELECT
                    disciplina.id::text AS disciplina_id,
                    disciplina.nome AS disciplina_nome,
                    curso.nome AS curso_nome,
                    disciplina.semestre,
                    disciplina.carga_horaria,
                    disciplina.qtd_aulas_prevista,
                    turma.turma_id::text AS turma_id,
                    turma.professor_disciplina_id::text AS professor_disciplina_id,
                    turma.turma_nome,
                    turma.data_inicio,
                    turma.data_fim,
                    turma.polo_nome,
                    turma.escola_nome
                FROM disciplinas_professor vinculo
                JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
                LEFT JOIN cursos curso ON curso.id = disciplina.curso_id
                LEFT JOIN turmas_professor turma ON turma.disciplina_id = disciplina.id
                ORDER BY disciplina.nome, turma.turma_nome NULLS LAST, turma.turma_id
                """,
                (str(usuario_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_conteudos_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                WITH disciplinas_docente AS (
                    SELECT vinculo.disciplina_id
                    FROM professor_disciplina_vinculos vinculo
                    JOIN professores professor ON professor.id = vinculo.professor_id
                    WHERE professor.usuario_id = %s
                    UNION
                    SELECT vinculo.disciplina_id
                    FROM professor_disciplinas vinculo
                    JOIN professores professor ON professor.id = vinculo.professor_id
                    WHERE professor.usuario_id = %s AND vinculo.ativo = true
                )
                SELECT conteudo.id::text AS id,
                       disciplina.id::text AS disciplina_id,
                       conteudo.titulo,
                       conteudo.tipo_midia,
                       conteudo.url_arquivo,
                       COALESCE(conteudo.ordem, 0) AS ordem,
                       conteudo.arquivo_nome,
                       conteudo.arquivo_mime_type,
                       conteudo.arquivo_tamanho_bytes,
                       conteudo.arquivo_storage_key IS NOT NULL AS tem_arquivo
                FROM disciplinas_docente vinculo
                JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
                LEFT JOIN disciplina_conteudos conteudo
                    ON conteudo.disciplina_id = disciplina.id
                WHERE conteudo.id IS NOT NULL
                ORDER BY disciplina.nome, conteudo.ordem, conteudo.id
                """,
                (str(usuario_id), str(usuario_id)),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_materiais_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT material.id::text AS id,
                       vinculo.id::text AS professor_disciplina_id,
                       disciplina.id::text AS disciplina_id,
                       vinculo.turma_id::text AS turma_id,
                       turma.nome AS turma_nome,
                       material.arquivo_url,
                       material.data_aula,
                       material.descricao,
                       material.expira_em,
                       material.arquivo_nome,
                       material.arquivo_mime_type,
                       material.arquivo_tamanho_bytes,
                       material.arquivo_storage_key IS NOT NULL AS tem_arquivo
                FROM professor_materiais material
                JOIN professor_disciplinas vinculo
                    ON vinculo.id = material.professor_disciplina_id
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
                LEFT JOIN turmas turma ON turma.id = vinculo.turma_id
                WHERE professor.usuario_id = %s
                  AND vinculo.ativo = true
                ORDER BY disciplina.nome, turma.nome NULLS LAST,
                         material.data_aula DESC NULLS LAST, material.id
                """,
                (str(usuario_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_conteudo(self, conteudo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, disciplina_id::text AS disciplina_id,
                       titulo, tipo_midia, url_arquivo, COALESCE(ordem, 0) AS ordem,
                       arquivo_storage_key, arquivo_nome, arquivo_mime_type,
                       arquivo_tamanho_bytes
                FROM disciplina_conteudos
                WHERE id = %s
                """,
                (str(conteudo_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_conteudo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        conteudo_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO disciplina_conteudos (
                    id, disciplina_id, titulo, tipo_midia, url_arquivo, ordem,
                    arquivo_storage_key, arquivo_nome, arquivo_mime_type,
                    arquivo_tamanho_bytes, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    conteudo_id,
                    str(data["disciplina_id"]),
                    data.get("titulo"),
                    data.get("tipo_midia"),
                    data.get("url_arquivo"),
                    data.get("ordem", 0),
                    data.get("arquivo_storage_key"),
                    data.get("arquivo_nome"),
                    data.get("arquivo_mime_type"),
                    data.get("arquivo_tamanho_bytes"),
                ),
            )
        return {"id": conteudo_id, **data}

    def update_conteudo(
        self, conteudo_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                UPDATE disciplina_conteudos
                SET titulo = %s, tipo_midia = %s, url_arquivo = %s, ordem = %s,
                    arquivo_storage_key = %s, arquivo_nome = %s,
                    arquivo_mime_type = %s, arquivo_tamanho_bytes = %s,
                    atualizado_em = now()
                WHERE id = %s
                RETURNING id::text AS id
                """,
                (
                    data.get("titulo"),
                    data.get("tipo_midia"),
                    data.get("url_arquivo"),
                    data.get("ordem", 0),
                    data.get("arquivo_storage_key"),
                    data.get("arquivo_nome"),
                    data.get("arquivo_mime_type"),
                    data.get("arquivo_tamanho_bytes"),
                    str(conteudo_id),
                ),
            )
            if not cur.fetchone():
                return None
        return self.get_conteudo(conteudo_id)

    def get_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT material.id::text AS id,
                       material.professor_disciplina_id::text AS professor_disciplina_id,
                       vinculo.professor_id::text AS professor_id,
                       vinculo.disciplina_id::text AS disciplina_id,
                       vinculo.turma_id::text AS turma_id,
                       turma.nome AS turma_nome,
                       material.arquivo_url, material.data_aula, material.descricao,
                       material.expira_em, material.arquivo_storage_key,
                       material.arquivo_nome, material.arquivo_mime_type,
                       material.arquivo_tamanho_bytes
                FROM professor_materiais material
                JOIN professor_disciplinas vinculo
                    ON vinculo.id = material.professor_disciplina_id
                LEFT JOIN turmas turma ON turma.id = vinculo.turma_id
                WHERE material.id = %s AND vinculo.ativo = true
                """,
                (str(material_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_vinculo_academico(self, vinculo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, professor_id::text AS professor_id,
                       disciplina_id::text AS disciplina_id, turma_id::text AS turma_id,
                       ativo
                FROM professor_disciplinas
                WHERE id = %s AND ativo = true
                """,
                (str(vinculo_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_material(self, data: Dict[str, Any]) -> Dict[str, Any]:
        material_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO professor_materiais (
                    id, professor_disciplina_id, arquivo_url, data_aula, descricao,
                    expira_em, arquivo_storage_key, arquivo_nome, arquivo_mime_type,
                    arquivo_tamanho_bytes, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    material_id,
                    str(data["professor_disciplina_id"]),
                    data.get("arquivo_url"),
                    data.get("data_aula"),
                    data.get("descricao"),
                    data.get("expira_em"),
                    data.get("arquivo_storage_key"),
                    data.get("arquivo_nome"),
                    data.get("arquivo_mime_type"),
                    data.get("arquivo_tamanho_bytes"),
                ),
            )
        return self.get_material(material_id) or {"id": material_id, **data}

    def update_material(
        self, material_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                UPDATE professor_materiais
                SET arquivo_url = %s, data_aula = %s, descricao = %s,
                    expira_em = %s, arquivo_storage_key = %s, arquivo_nome = %s,
                    arquivo_mime_type = %s, arquivo_tamanho_bytes = %s,
                    atualizado_em = now()
                WHERE id = %s
                RETURNING id::text AS id
                """,
                (
                    data.get("arquivo_url"),
                    data.get("data_aula"),
                    data.get("descricao"),
                    data.get("expira_em"),
                    data.get("arquivo_storage_key"),
                    data.get("arquivo_nome"),
                    data.get("arquivo_mime_type"),
                    data.get("arquivo_tamanho_bytes"),
                    str(material_id),
                ),
            )
            if not cur.fetchone():
                return None
        return self.get_material(material_id)

    # ---------- Listagem ----------

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds: List[str] = []
        params: List[Any] = []

        if search and search.strip():
            conds.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(u.email) LIKE %s)")
            like = f"%{search.strip().lower()}%"
            params.extend([like, like, like])
        if polo_id:
            conds.append("prof.polo_id = %s")
            params.append(str(polo_id))
        if escola_id:
            conds.append("prof.escola_id = %s")
            params.append(str(escola_id))
        if disciplina and disciplina.strip():
            conds.append(
                "(prof.materias::text ILIKE %s OR EXISTS ("
                "SELECT 1 FROM professor_disciplina_vinculos vinculo "
                "JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id "
                "WHERE vinculo.professor_id = prof.id AND disciplina.nome ILIKE %s))"
            )
            term = f"%{disciplina.strip()}%"
            params.extend([term, term])
        if status_filter:
            conds.append("prof.status = %s")
            params.append(status_filter)

        where = "WHERE " + " AND ".join(conds) if conds else ""
        count_sql = (
            "SELECT COUNT(*) AS total FROM professores prof "
            "LEFT JOIN usuarios u ON u.id = prof.usuario_id"
        )

        with get_db_cursor() as cur:
            cur.execute(f"{count_sql} {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"{_SELECT_BASE} {where} ORDER BY u.nome ASC, u.email ASC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Registro ----------

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(f"{_SELECT_BASE} WHERE prof.id = %s LIMIT 1", (str(professor_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(f"{_SELECT_BASE} WHERE prof.usuario_id = %s LIMIT 1", (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, sobrenome, email, status FROM usuarios WHERE id = %s LIMIT 1", (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_invalid_disciplina_ids(self, disciplina_ids: List[str]) -> List[str]:
        ids = list(dict.fromkeys(str(item) for item in disciplina_ids))
        if not ids:
            return []
        with get_db_cursor() as cur:
            cur.execute("SELECT id::text FROM disciplinas WHERE id = ANY(%s::uuid[])", (ids,))
            encontrados = {str(row["id"]) for row in cur.fetchall()}
        return [disciplina_id for disciplina_id in ids if disciplina_id not in encontrados]

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO professores (
                    id, usuario_id, polo_id, escola_id, materias, data_inicio,
                    quantidade_aulas, horas_totais, valor_hora_aula, pix,
                    conteudo_programatico, status, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo', now(), now())
                """,
                (
                    new_id,
                    str(data["usuario_id"]),
                    data.get("polo_id"),
                    data.get("escola_id"),
                    json.dumps(data.get("materias") or []),
                    data.get("data_inicio"),
                    data.get("quantidade_aulas") or 0,
                    data.get("horas_totais") or 0,
                    data.get("valor_hora_aula"),
                    data.get("pix"),
                    data.get("conteudo_programatico"),
                ),
            )
            self._sync_disciplina_ids(cur, new_id, data.get("disciplina_ids") or [])
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields: List[str] = []
        params: List[Any] = []
        for key, value in data.items():
            if key == "disciplina_ids":
                continue
            if key == "materias":
                fields.append("materias = %s")
                params.append(json.dumps(value or []))
            else:
                fields.append(f"{key} = %s")
                params.append(value)
        with get_db_cursor() as cur:
            if fields:
                fields.append("atualizado_em = now()")
                params.append(str(professor_id))
                cur.execute(
                    f"UPDATE professores SET {', '.join(fields)} WHERE id = %s",
                    tuple(params),
                )
            if "disciplina_ids" in data:
                self._sync_disciplina_ids(cur, str(professor_id), data.get("disciplina_ids") or [])

    @staticmethod
    def _sync_disciplina_ids(cur: Any, professor_id: str, disciplina_ids: List[str]) -> None:
        ids = list(dict.fromkeys(str(item) for item in disciplina_ids))
        cur.execute(
            "DELETE FROM professor_disciplina_vinculos WHERE professor_id = %s",
            (str(professor_id),),
        )
        if ids:
            cur.executemany(
                """
                INSERT INTO professor_disciplina_vinculos (professor_id, disciplina_id)
                VALUES (%s, %s)
                """,
                [(str(professor_id), disciplina_id) for disciplina_id in ids],
            )


    def set_usuario_perfil(self, usuario_id: str, perfil_nome: str) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT pa.nome AS anterior, pn.id AS novo_id
                FROM usuarios u
                LEFT JOIN perfis pa ON pa.id = u.perfil_id
                JOIN perfis pn ON lower(pn.nome) = lower(%s)
                WHERE u.id = %s
                LIMIT 1
                """,
                (perfil_nome, str(usuario_id)),
            )
            row = cur.fetchone()
            if not row or (row["anterior"] or "").lower() == perfil_nome.lower():
                return None
            cur.execute(
                "UPDATE usuarios SET perfil_id = %s, atualizado_em = now() WHERE id = %s",
                (row["novo_id"], str(usuario_id)),
            )
            return row["anterior"] or ""

    # ---------- Auditoria ----------

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs_auditoria (
                    usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    str(usuario_id) if usuario_id else None,
                    acao,
                    entidade,
                    str(entidade_id) if entidade_id else None,
                    json.dumps(dados_antes) if dados_antes is not None else None,
                    json.dumps(dados_depois) if dados_depois is not None else None,
                    ip,
                ),
            )


class InMemoryProfessoresRepository:
    """Implementação em memória para testes unitários isolados."""

    def __init__(self) -> None:
        self.professores: Dict[str, Dict[str, Any]] = {}
        self.professor_disciplina_vinculos: Dict[str, List[str]] = {}
        self.professor_disciplinas: List[Dict[str, Any]] = []
        self.disciplina_conteudos: List[Dict[str, Any]] = []
        self.professor_materiais: List[Dict[str, Any]] = []
        self.disciplinas: Dict[str, Dict[str, Any]] = {}
        self.cursos: Dict[str, Dict[str, Any]] = {}
        self.turmas: Dict[str, Dict[str, Any]] = {}
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.perfis: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.logs_auditoria: List[Dict[str, Any]] = []

    def get_turma_vinculo_scope(self, turma_id: str) -> Optional[Dict[str, Any]]:
        turma = self.turmas.get(str(turma_id))
        return dict(turma) if turma else None

    def get_disciplina_curso(self, disciplina_id: str) -> Optional[str]:
        disciplina = self.disciplinas.get(str(disciplina_id))
        curso_id = disciplina.get("curso_id") if disciplina else None
        return str(curso_id) if curso_id else None

    def list_vinculos_ativos_por_turma(
        self, turma_id: str, scope_column: Optional[str] = None, scope_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        turma = self.turmas.get(str(turma_id))
        if not turma:
            return []
        if scope_column and str(turma.get(scope_column)) != str(scope_id):
            return []
        rows: List[Dict[str, Any]] = []
        for vinculo in self.professor_disciplinas:
            if (
                str(vinculo.get("turma_id")) != str(turma_id)
                or not vinculo.get("ativo", True)
            ):
                continue
            professor = self.professores.get(str(vinculo.get("professor_id")), {})
            usuario = self.usuarios.get(str(professor.get("usuario_id")), {})
            disciplina = self.disciplinas.get(str(vinculo.get("disciplina_id")), {})
            rows.append(
                {
                    "id": str(vinculo["id"]),
                    "professor_id": str(vinculo["professor_id"]),
                    "professor_nome": " ".join(
                        part for part in (usuario.get("nome"), usuario.get("sobrenome")) if part
                    ),
                    "professor_email": usuario.get("email"),
                    "disciplina_id": str(vinculo["disciplina_id"]),
                    "disciplina_nome": disciplina.get("nome", ""),
                    "turma_id": str(turma_id),
                }
            )
        return rows

    def create_or_reactivate_vinculo_turma(
        self,
        professor_id: str,
        disciplina_id: str,
        turma_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        if str(turma_id) not in self.turmas:
            return "", "missing_turma"
        if scope_column and str(self.turmas[str(turma_id)].get(scope_column)) != str(scope_id):
            return "", "out_of_scope"
        disciplina = self.disciplinas.get(str(disciplina_id))
        if not disciplina:
            return "", "missing_discipline"
        if str(disciplina.get("curso_id")) != str(self.turmas[str(turma_id)].get("curso_id")):
            return "", "course_mismatch"
        professor = self.professores.get(str(professor_id))
        usuario = self.usuarios.get(str(professor.get("usuario_id"))) if professor else None
        if not professor or professor.get("status") != "ativo" or not usuario or usuario.get("status") != "ativo":
            return "", "inactive_professor"
        if scope_column and str(professor.get(scope_column)) != str(scope_id):
            return "", "professor_out_of_scope"
        same = [
            row for row in self.professor_disciplinas
            if str(row.get("professor_id")) == str(professor_id)
            and str(row.get("disciplina_id")) == str(disciplina_id)
            and str(row.get("turma_id")) == str(turma_id)
        ]
        existing = next((row for row in same if row.get("ativo", True)), None)
        if existing:
            return str(existing["id"]), "exists"
        if same:
            archived = same[0]
            archived["ativo"] = True
            return str(archived["id"]), "reactivated"
        vinculo_id = str(uuid.uuid4())
        self.professor_disciplinas.append(
            {
                "id": vinculo_id,
                "professor_id": str(professor_id),
                "disciplina_id": str(disciplina_id),
                "turma_id": str(turma_id),
                "ativo": True,
            }
        )
        return vinculo_id, "created"

    def archive_vinculo_turma(
        self,
        turma_id: str,
        vinculo_id: str,
        scope_column: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        turma = self.turmas.get(str(turma_id))
        if not turma:
            return None, "missing_turma"
        if scope_column and str(turma.get(scope_column)) != str(scope_id):
            return None, "out_of_scope"
        row = next(
            (
                item for item in self.professor_disciplinas
                if str(item.get("id")) == str(vinculo_id)
                and str(item.get("turma_id")) == str(turma_id)
                and item.get("ativo", True)
            ),
            None,
        )
        if not row:
            return None, "missing_vinculo"
        row["ativo"] = False
        return {
            "id": str(row["id"]),
            "professor_id": str(row["professor_id"]),
            "disciplina_id": str(row["disciplina_id"]),
            "turma_id": str(row["turma_id"]),
        }, "archived"

    def list_disciplinas_turmas_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        professor = next(
            (
                row
                for row in self.professores.values()
                if str(row.get("usuario_id")) == str(usuario_id)
            ),
            None,
        )
        if not professor:
            return []

        professor_id = str(professor["id"])
        vinculos_turma = [
            row
            for row in self.professor_disciplinas
            if str(row.get("professor_id")) == professor_id
            and row.get("ativo", True)
        ]
        disciplina_ids = set(
            str(item) for item in self.professor_disciplina_vinculos.get(professor_id, [])
        )
        disciplina_ids.update(str(row["disciplina_id"]) for row in vinculos_turma)

        rows: List[Dict[str, Any]] = []
        for disciplina_id in sorted(disciplina_ids):
            disciplina = self.disciplinas.get(disciplina_id)
            if not disciplina:
                continue
            curso = self.cursos.get(str(disciplina.get("curso_id")), {})
            turmas: Dict[str, Dict[str, Any]] = {}
            for vinculo in vinculos_turma:
                if str(vinculo.get("disciplina_id")) != disciplina_id or not vinculo.get("turma_id"):
                    continue
                turma = self.turmas.get(str(vinculo["turma_id"]))
                if turma:
                    turmas[str(turma["id"])] = turma

            turma_rows = list(turmas.values()) or [None]
            for turma in turma_rows:
                polo = self.polos.get(str(turma.get("polo_id")), {}) if turma else {}
                escola = self.escolas.get(str(turma.get("escola_id")), {}) if turma else {}
                rows.append(
                    {
                        "disciplina_id": disciplina_id,
                        "disciplina_nome": disciplina.get("nome"),
                        "curso_nome": curso.get("nome"),
                        "semestre": disciplina.get("semestre"),
                        "carga_horaria": disciplina.get("carga_horaria"),
                        "qtd_aulas_prevista": disciplina.get("qtd_aulas_prevista"),
                        "turma_id": str(turma["id"]) if turma else None,
                        "professor_disciplina_id": (
                            str(next(
                                link["id"]
                                for link in vinculos_turma
                                if str(link.get("disciplina_id")) == disciplina_id
                                and str(link.get("turma_id")) == str(turma["id"])
                                and link.get("id")
                            ))
                            if turma
                            and any(
                                str(link.get("disciplina_id")) == disciplina_id
                                and str(link.get("turma_id")) == str(turma["id"])
                                and link.get("id")
                                for link in vinculos_turma
                            )
                            else None
                        ),
                        "turma_nome": turma.get("nome") if turma else None,
                        "data_inicio": turma.get("data_inicio") if turma else None,
                        "data_fim": turma.get("data_fim") if turma else None,
                        "polo_nome": polo.get("nome"),
                        "escola_nome": escola.get("nome"),
                    }
                )
        return rows

    def list_conteudos_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        disciplina_ids = {
            str(row["disciplina_id"])
            for row in self.list_disciplinas_turmas_by_usuario(usuario_id)
        }
        return [
            {
                **conteudo,
                "id": str(conteudo["id"]),
                "disciplina_id": str(conteudo["disciplina_id"]),
                "tem_arquivo": bool(conteudo.get("arquivo_storage_key")),
            }
            for conteudo in self.disciplina_conteudos
            if str(conteudo.get("disciplina_id")) in disciplina_ids and conteudo.get("id")
        ]

    def list_materiais_by_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        professor = next(
            (
                row
                for row in self.professores.values()
                if str(row.get("usuario_id")) == str(usuario_id)
            ),
            None,
        )
        if not professor:
            return []

        vinculos = {
            str(vinculo["id"]): vinculo
            for vinculo in self.professor_disciplinas
            if str(vinculo.get("professor_id")) == str(professor["id"])
            and vinculo.get("ativo", True)
            and vinculo.get("id")
        }
        materiais: List[Dict[str, Any]] = []
        for material in self.professor_materiais:
            vinculo_id = str(material.get("professor_disciplina_id"))
            vinculo = vinculos.get(vinculo_id)
            if not vinculo:
                continue
            turma = self.turmas.get(str(vinculo.get("turma_id")), {})
            materiais.append(
                {
                    **material,
                    "id": str(material["id"]),
                    "professor_disciplina_id": vinculo_id,
                    "disciplina_id": str(vinculo["disciplina_id"]),
                    "turma_id": str(vinculo["turma_id"]) if vinculo.get("turma_id") else None,
                    "turma_nome": turma.get("nome"),
                    "tem_arquivo": bool(material.get("arquivo_storage_key")),
                }
            )
        return materiais

    def get_conteudo(self, conteudo_id: str) -> Optional[Dict[str, Any]]:
        row = next(
            (item for item in self.disciplina_conteudos if str(item.get("id")) == str(conteudo_id)),
            None,
        )
        return dict(row) if row else None

    def create_conteudo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        row = {"id": str(uuid.uuid4()), **data}
        self.disciplina_conteudos.append(row)
        return dict(row)

    def update_conteudo(
        self, conteudo_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        row = self.get_conteudo(conteudo_id)
        if not row:
            return None
        row.update(data)
        for index, item in enumerate(self.disciplina_conteudos):
            if str(item.get("id")) == str(conteudo_id):
                self.disciplina_conteudos[index] = row
                return dict(row)
        return None

    def get_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        material = next(
            (item for item in self.professor_materiais if str(item.get("id")) == str(material_id)),
            None,
        )
        if not material:
            return None
        link_id = str(material.get("professor_disciplina_id"))
        vinculo = next(
            (item for item in self.professor_disciplinas if str(item.get("id")) == link_id),
            None,
        )
        if not vinculo or not vinculo.get("ativo", True):
            return None
        turma = self.turmas.get(str(vinculo.get("turma_id")), {})
        return {
            **material,
            "id": str(material["id"]),
            "professor_id": str(vinculo["professor_id"]),
            "disciplina_id": str(vinculo["disciplina_id"]),
            "turma_id": str(vinculo["turma_id"]) if vinculo.get("turma_id") else None,
            "turma_nome": turma.get("nome"),
            "professor_disciplina_id": link_id,
        }

    def get_vinculo_academico(self, vinculo_id: str) -> Optional[Dict[str, Any]]:
        row = next(
            (item for item in self.professor_disciplinas if str(item.get("id")) == str(vinculo_id)),
            None,
        )
        return dict(row) if row and row.get("ativo", True) else None

    def create_material(self, data: Dict[str, Any]) -> Dict[str, Any]:
        row = {"id": str(uuid.uuid4()), **data}
        self.professor_materiais.append(row)
        return self.get_material(row["id"]) or row

    def update_material(
        self, material_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        row = next(
            (item for item in self.professor_materiais if str(item.get("id")) == str(material_id)),
            None,
        )
        if not row:
            return None
        row.update(data)
        return self.get_material(material_id)

    def list_vinculos_academicos_por_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        professor = next(
            (
                row
                for row in self.professores.values()
                if str(row.get("usuario_id")) == str(usuario_id)
            ),
            None,
        )
        if not professor:
            return []
        professor_id = str(professor["id"])
        return [
            {
                **row,
                "id": str(row["id"]),
                "disciplina_id": str(row["disciplina_id"]),
                "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
            }
            for row in self.professor_disciplinas
            if str(row.get("professor_id")) == professor_id and row.get("id")
        ]

    def professor_tem_disciplina(self, usuario_id: str, disciplina_id: str) -> bool:
        professor = next(
            (
                row
                for row in self.professores.values()
                if str(row.get("usuario_id")) == str(usuario_id)
            ),
            None,
        )
        if not professor:
            return False
        professor_id = str(professor["id"])
        if str(disciplina_id) in {
            str(item) for item in self.professor_disciplina_vinculos.get(professor_id, [])
        }:
            return True
        return any(
            str(row.get("professor_id")) == professor_id
            and str(row.get("disciplina_id")) == str(disciplina_id)
            and row.get("ativo", True)
            for row in self.professor_disciplinas
        )

    def _join(self, row: Dict[str, Any]) -> Dict[str, Any]:
        usuario = self.usuarios.get(str(row.get("usuario_id")), {})
        polo = self.polos.get(str(row.get("polo_id")), {}) if row.get("polo_id") else {}
        escola = self.escolas.get(str(row.get("escola_id")), {}) if row.get("escola_id") else {}
        return {
            **row,
            "disciplina_ids": list(self.professor_disciplina_vinculos.get(str(row.get("id")), [])),
            "nome": usuario.get("nome"),
            "email": usuario.get("email"),
            "polo_nome": polo.get("nome"),
            "escola_nome": escola.get("nome"),
        }

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [self._join(p) for p in self.professores.values()]
        if search and search.strip():
            termo = search.strip().lower()
            items = [
                p
                for p in items
                if termo in str(p.get("nome") or "").lower()
                or termo in str(p.get("email") or "").lower()
            ]
        if polo_id:
            items = [p for p in items if str(p.get("polo_id")) == str(polo_id)]
        if escola_id:
            items = [p for p in items if str(p.get("escola_id")) == str(escola_id)]
        if disciplina and disciplina.strip():
            termo = disciplina.strip().lower()
            items = [p for p in items if any(termo in str(m).lower() for m in (p.get("materias") or []))]
        if status_filter:
            items = [p for p in items if p.get("status") == status_filter]
        items = sorted(items, key=lambda p: str(p.get("nome") or ""))
        return len(items), items[offset : offset + limit]

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        row = self.professores.get(str(professor_id))
        return self._join(row) if row else None

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        for row in self.professores.values():
            if str(row.get("usuario_id")) == str(usuario_id):
                return self._join(row)
        return None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        row = self.usuarios.get(str(usuario_id))
        return dict(row) if row else None

    def get_invalid_disciplina_ids(self, disciplina_ids: List[str]) -> List[str]:
        return []

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.professores[new_id] = {
            "id": new_id,
            "status": "ativo",
            "materias": list(data.get("materias") or []),
            "quantidade_aulas": data.get("quantidade_aulas") or 0,
            "horas_totais": data.get("horas_totais") or 0,
            "criado_em": None,
            "atualizado_em": None,
            **{k: v for k, v in data.items() if k not in ("materias", "quantidade_aulas", "horas_totais")},
        }
        self.professor_disciplina_vinculos[new_id] = list(dict.fromkeys(
            str(item) for item in (data.get("disciplina_ids") or [])
        ))
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        row = self.professores.get(str(professor_id))
        if row:
            row.update({key: value for key, value in data.items() if key != "disciplina_ids"})
            if "disciplina_ids" in data:
                self.professor_disciplina_vinculos[str(professor_id)] = list(dict.fromkeys(
                    str(item) for item in (data.get("disciplina_ids") or [])
                ))

    def set_usuario_perfil(self, usuario_id: str, perfil_nome: str) -> Optional[str]:
        usuario = self.usuarios.get(str(usuario_id))
        novo = next(
            (p for p in self.perfis.values() if str(p.get("nome")).lower() == perfil_nome.lower()),
            None,
        )
        if not usuario or not novo:
            return None
        anterior = self.perfis.get(str(usuario.get("perfil_id")), {}).get("nome") or ""
        if anterior.lower() == perfil_nome.lower():
            return None
        usuario["perfil_id"] = novo["id"]
        return anterior

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        self.logs_auditoria.append(
            {
                "usuario_id": usuario_id,
                "acao": acao,
                "entidade": entidade,
                "entidade_id": entidade_id,
                "dados_antes": dados_antes,
                "dados_depois": dados_depois,
                "ip": ip,
            }
        )


_repo_instance: Optional[ProfessoresRepositoryInterface] = None


def get_professores_repository() -> ProfessoresRepositoryInterface:
    """Provedor padrão do repositório (PostgreSQL em produção)."""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresProfessoresRepository()
    return _repo_instance


def set_professores_repository(repo: ProfessoresRepositoryInterface) -> None:
    """Permite injeção de um repositório alternativo (ex: InMemory nos testes)."""
    global _repo_instance
    _repo_instance = repo
