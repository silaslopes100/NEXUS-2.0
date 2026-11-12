"""Repositório de dados do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Protocol, Tuple

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from psycopg2 import sql

from app.core.database import get_db_cursor

_SELECT_BASE = """
    SELECT prof.*, u.nome, u.email,
           p.nome AS polo_nome, e.nome AS escola_nome,
           COALESCE(vinculos.disciplina_ids, ARRAY[]::text[]) AS disciplina_ids,
           COALESCE(vinculos.disciplina_nomes, ARRAY[]::text[]) AS disciplina_nomes,
           COALESCE(lot.lotacoes, '[]'::json) AS lotacoes
    FROM professores prof
    LEFT JOIN usuarios u ON u.id = prof.usuario_id
    LEFT JOIN polos p ON p.id = prof.polo_id
    LEFT JOIN escolas e ON e.id = prof.escola_id
    LEFT JOIN LATERAL (
        SELECT
            array_agg(vinculo.disciplina_id::text ORDER BY vinculo.disciplina_id::text) AS disciplina_ids,
            array_agg(DISTINCT disciplina.nome ORDER BY disciplina.nome) AS disciplina_nomes
        FROM professor_disciplinas vinculo
        JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
        WHERE vinculo.professor_id = prof.id AND vinculo.turma_id IS NULL
    ) vinculos ON TRUE
    LEFT JOIN LATERAL (
        SELECT json_agg(
                   json_build_object(
                       'id', lotacao.id::text,
                       'polo_id', lotacao.polo_id::text,
                       'polo_nome', lotacao_polo.nome,
                       'escola_id', lotacao.escola_id::text,
                       'escola_nome', lotacao_escola.nome
                   )
                   ORDER BY lotacao_polo.nome, lotacao_escola.nome NULLS FIRST
               ) AS lotacoes
        FROM professor_lotacoes lotacao
        JOIN polos lotacao_polo ON lotacao_polo.id = lotacao.polo_id
        LEFT JOIN escolas lotacao_escola ON lotacao_escola.id = lotacao.escola_id
        WHERE lotacao.professor_id = prof.id
    ) lot ON TRUE
"""

_LOTACAO_SELECT = """
    SELECT lotacao.id::text AS id, lotacao.professor_id::text AS professor_id,
           lotacao.polo_id::text AS polo_id, polo.nome AS polo_nome,
           lotacao.escola_id::text AS escola_id, escola.nome AS escola_nome
    FROM professor_lotacoes lotacao
    JOIN polos polo ON polo.id = lotacao.polo_id
    LEFT JOIN escolas escola ON escola.id = lotacao.escola_id
"""


def _uuid_valido(valor: Any) -> bool:
    try:
        uuid.UUID(str(valor))
    except (TypeError, ValueError):
        return False
    return True


def lotacao_cobre_unidade(
    lotacao: Dict[str, Any], polo_id: Optional[str], escola_id: Optional[str]
) -> bool:
    """A lotação atende a unidade? Lotação só de polo cobre todas as escolas do polo."""
    if str(lotacao.get("polo_id")) != str(polo_id):
        return False
    return not lotacao.get("escola_id") or str(lotacao.get("escola_id")) == str(escola_id)


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

    def list_disciplinas_cadastro(self, professor_id: str) -> List[Dict[str, Any]]: ...

    def list_turmas_alunos(
        self, professor_id: str, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> List[Dict[str, Any]]: ...

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def get_invalid_disciplina_ids(self, disciplina_ids: List[str]) -> List[str]: ...

    def create_professor(self, data: Dict[str, Any]) -> str: ...

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None: ...

    def set_usuario_perfil(self, usuario_id: str, perfil_nome: str) -> Optional[str]:
        """Define o perfil do usuário; retorna o nome do perfil anterior (ou None se não mudou)."""
        ...

    # ---------- Lotações (N polos / N escolas) ----------

    def get_escola_polo(self, escola_id: str) -> Optional[str]:
        """Polo ao qual a escola pertence (None se a escola não existe)."""
        ...

    def polo_existe(self, polo_id: str) -> bool: ...

    def list_lotacoes(self, professor_id: str) -> List[Dict[str, Any]]: ...

    def add_lotacao(
        self,
        professor_id: str,
        polo_id: str,
        escola_id: Optional[str] = None,
        criado_por: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """Inclui a lotação (idempotente); retorna (lotação, criada_agora)."""
        ...

    def remove_lotacao(self, professor_id: str, lotacao_id: str) -> Optional[Dict[str, Any]]: ...

    def replace_lotacoes(
        self, professor_id: str, lotacoes: List[Dict[str, Any]], criado_por: Optional[str] = None
    ) -> None: ...

    def list_unidades_turmas_ativas(self, professor_id: str) -> List[Dict[str, Any]]:
        """Polo/escola das turmas em que o professor tem vínculo ativo."""
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
                  AND vinculo.turma_id IS NOT NULL
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
                      AND EXISTS (
                          SELECT 1 FROM professor_disciplinas vinculo
                          WHERE vinculo.professor_id = professor.id
                            AND vinculo.disciplina_id = %s
                      )
                ) AS vinculado
                """,
                (str(usuario_id), str(disciplina_id)),
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
                    SELECT DISTINCT vinculo.disciplina_id
                    FROM professor_disciplinas vinculo
                    JOIN professor docente ON docente.id = vinculo.professor_id
                    WHERE vinculo.turma_id IS NULL OR vinculo.ativo = true
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
                    SELECT DISTINCT vinculo.disciplina_id
                    FROM professor_disciplinas vinculo
                    JOIN professores professor ON professor.id = vinculo.professor_id
                    WHERE professor.usuario_id = %s
                      AND (vinculo.turma_id IS NULL OR vinculo.ativo = true)
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
                (str(usuario_id),),
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
                WHERE id = %s AND ativo = true AND turma_id IS NOT NULL
                """,
                (str(vinculo_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_material(self, data: Dict[str, Any]) -> Dict[str, Any]:
        material_id = str(uuid.uuid4())
        # `aula_id` só entra no INSERT quando informado (coluna criada pela migração 008).
        com_aula = bool(data.get("aula_id"))
        coluna_aula = ", aula_id" if com_aula else ""
        valor_aula = ", %s" if com_aula else ""
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO professor_materiais (
                    id, professor_disciplina_id, arquivo_url, data_aula, descricao,
                    expira_em, arquivo_storage_key, arquivo_nome, arquivo_mime_type,
                    arquivo_tamanho_bytes, criado_em, atualizado_em{coluna_aula}
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now(){valor_aula})
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
                    *([data["aula_id"]] if com_aula else []),
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
            conds.append(
                "EXISTS (SELECT 1 FROM professor_lotacoes lotacao "
                "WHERE lotacao.professor_id = prof.id AND lotacao.polo_id = %s)"
            )
            params.append(str(polo_id))
        if escola_id:
            conds.append(
                "EXISTS (SELECT 1 FROM professor_lotacoes lotacao "
                "WHERE lotacao.professor_id = prof.id AND lotacao.escola_id = %s)"
            )
            params.append(str(escola_id))
        if disciplina and disciplina.strip():
            conds.append(
                "(prof.materias::text ILIKE %s OR EXISTS ("
                "SELECT 1 FROM professor_disciplinas vinculo "
                "JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id "
                "WHERE vinculo.professor_id = prof.id AND vinculo.turma_id IS NULL "
                "AND disciplina.nome ILIKE %s))"
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

    def list_disciplinas_cadastro(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT d.id::text AS id, d.nome, d.curso_id::text AS curso_id,
                       c.nome AS curso_nome, d.carga_horaria, d.qtd_aulas_prevista
                FROM professor_disciplinas v
                JOIN disciplinas d ON d.id = v.disciplina_id
                LEFT JOIN cursos c ON c.id = d.curso_id
                WHERE v.professor_id = %s AND v.turma_id IS NULL
                ORDER BY d.nome, d.id
                """,
                (str(professor_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_turmas_alunos(
        self, professor_id: str, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT t.id::text AS turma_id, t.nome AS turma_nome,
                       t.polo_id::text AS polo_id, p.nome AS polo_nome,
                       t.escola_id::text AS escola_id, e.nome AS escola_nome,
                       a.id::text AS aluno_id,
                       NULLIF(trim(concat(u.nome, ' ', u.sobrenome)), '') AS aluno_nome,
                       a.numero_matricula, u.email AS aluno_email
                FROM professor_disciplinas pd
                JOIN professor_disciplinas v
                  ON v.professor_id = pd.professor_id AND v.disciplina_id = pd.disciplina_id
                 AND v.turma_id IS NULL
                JOIN turmas t ON t.id = pd.turma_id
                LEFT JOIN polos p ON p.id = t.polo_id
                LEFT JOIN escolas e ON e.id = t.escola_id
                LEFT JOIN turma_alunos ta ON ta.turma_id = t.id
                  AND COALESCE(ta.status, 'ativo') = 'ativo'
                LEFT JOIN alunos a ON a.id = ta.aluno_id
                LEFT JOIN usuarios u ON u.id = a.usuario_id
                WHERE pd.professor_id = %s AND pd.ativo = true
                  AND (%s::uuid IS NULL OR t.polo_id = %s::uuid)
                  AND (%s::uuid IS NULL OR t.escola_id = %s::uuid)
                ORDER BY polo_nome, escola_nome, turma_nome, aluno_nome, aluno_id
                """,
                (str(professor_id), polo_id, polo_id, escola_id, escola_id),
            )
            return [dict(row) for row in cur.fetchall()]

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
        data = dict(data)
        lotacoes = data.pop("lotacoes", None)
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
            if lotacoes is not None:
                self._replace_lotacoes(cur, new_id, lotacoes, data.get("criado_por"))
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields: List[str] = []
        params: List[Any] = []
        lotacoes = data.get("lotacoes")
        for key, value in data.items():
            if key in ("disciplina_ids", "lotacoes", "criado_por"):
                continue
            if lotacoes is not None and key in ("polo_id", "escola_id"):
                continue  # a lotação principal é derivada da lista
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
            if lotacoes is not None:
                self._replace_lotacoes(cur, str(professor_id), lotacoes, data.get("criado_por"))

    # ---------- Lotações ----------

    def get_escola_polo(self, escola_id: str) -> Optional[str]:
        if not _uuid_valido(escola_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT polo_id::text AS polo_id FROM escolas WHERE id = %s", (str(escola_id),))
            row = cur.fetchone()
            return str(row["polo_id"]) if row and row.get("polo_id") else None

    def polo_existe(self, polo_id: str) -> bool:
        if not _uuid_valido(polo_id):
            return False
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 FROM polos WHERE id = %s", (str(polo_id),))
            return cur.fetchone() is not None

    def list_lotacoes(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _LOTACAO_SELECT
                + " WHERE lotacao.professor_id = %s ORDER BY polo.nome, escola.nome NULLS FIRST",
                (str(professor_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    def add_lotacao(
        self,
        professor_id: str,
        polo_id: str,
        escola_id: Optional[str] = None,
        criado_por: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        with get_db_cursor() as cur:
            criada = self._insert_lotacao(cur, str(professor_id), str(polo_id), escola_id, criado_por)
            self._sync_lotacao_principal(cur, str(professor_id))
            cur.execute(
                _LOTACAO_SELECT
                + """ WHERE lotacao.professor_id = %s AND lotacao.polo_id = %s
                  AND lotacao.escola_id IS NOT DISTINCT FROM %s::uuid""",
                (str(professor_id), str(polo_id), str(escola_id) if escola_id else None),
            )
            row = cur.fetchone()
        return dict(row), criada

    def remove_lotacao(self, professor_id: str, lotacao_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _LOTACAO_SELECT + " WHERE lotacao.id = %s AND lotacao.professor_id = %s",
                (str(lotacao_id), str(professor_id)),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("DELETE FROM professor_lotacoes WHERE id = %s", (str(lotacao_id),))
            self._sync_lotacao_principal(cur, str(professor_id))
            return dict(row)

    def replace_lotacoes(
        self, professor_id: str, lotacoes: List[Dict[str, Any]], criado_por: Optional[str] = None
    ) -> None:
        with get_db_cursor() as cur:
            self._replace_lotacoes(cur, str(professor_id), lotacoes, criado_por)

    def list_unidades_turmas_ativas(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT COALESCE(t.polo_id, escola.polo_id)::text AS polo_id,
                       t.escola_id::text AS escola_id
                FROM professor_disciplinas pd
                JOIN turmas t ON t.id = pd.turma_id
                LEFT JOIN escolas escola ON escola.id = t.escola_id
                WHERE pd.professor_id = %s AND pd.ativo = true
                """,
                (str(professor_id),),
            )
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _insert_lotacao(
        cur: Any, professor_id: str, polo_id: str, escola_id: Optional[str], criado_por: Optional[str]
    ) -> bool:
        cur.execute(
            """
            INSERT INTO professor_lotacoes (professor_id, polo_id, escola_id, criado_por)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (professor_id, polo_id, str(escola_id) if escola_id else None, str(criado_por) if criado_por else None),
        )
        return cur.fetchone() is not None

    def _replace_lotacoes(
        self, cur: Any, professor_id: str, lotacoes: List[Dict[str, Any]], criado_por: Optional[str]
    ) -> None:
        cur.execute("DELETE FROM professor_lotacoes WHERE professor_id = %s", (professor_id,))
        for lotacao in lotacoes:
            self._insert_lotacao(
                cur, professor_id, str(lotacao["polo_id"]), lotacao.get("escola_id"), criado_por
            )
        self._sync_lotacao_principal(cur, professor_id)

    @staticmethod
    def _sync_lotacao_principal(cur: Any, professor_id: str) -> None:
        """Mantém professores.polo_id/escola_id apontando para uma lotação existente."""
        cur.execute(
            """
            UPDATE professores prof
            SET polo_id = principal.polo_id, escola_id = principal.escola_id, atualizado_em = now()
            FROM (
                SELECT polo_id, escola_id FROM professor_lotacoes
                WHERE professor_id = %s
                ORDER BY criado_em, id
                LIMIT 1
            ) principal
            WHERE prof.id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM professor_lotacoes atual
                  WHERE atual.professor_id = prof.id
                    AND atual.polo_id IS NOT DISTINCT FROM prof.polo_id
                    AND atual.escola_id IS NOT DISTINCT FROM prof.escola_id
              )
            """,
            (professor_id, professor_id),
        )
        cur.execute(
            """
            UPDATE professores SET polo_id = NULL, escola_id = NULL, atualizado_em = now()
            WHERE id = %s AND (polo_id IS NOT NULL OR escola_id IS NOT NULL)
              AND NOT EXISTS (SELECT 1 FROM professor_lotacoes WHERE professor_id = %s)
            """,
            (professor_id, professor_id),
        )

    @staticmethod
    def _sync_disciplina_ids(cur: Any, professor_id: str, disciplina_ids: List[str]) -> None:
        ids = list(dict.fromkeys(str(item) for item in disciplina_ids))
        cur.execute("SELECT id FROM professores WHERE id = %s FOR UPDATE", (str(professor_id),))
        cur.execute(
            """
            SELECT id FROM professor_disciplinas
            WHERE professor_id = %s AND turma_id IS NULL
              AND NOT (disciplina_id = ANY(%s::uuid[]))
            FOR UPDATE
            """,
            (str(professor_id), ids),
        )
        removidos = [str(row["id"]) for row in cur.fetchall()]
        if removidos:
            cur.execute(
                """
                SELECT n.nspname AS schema_name, c.relname AS table_name,
                       a.attname AS column_name, target.attname AS target_column,
                       cardinality(fk.conkey) AS columns_count, c.relrowsecurity
                FROM pg_constraint fk
                JOIN pg_class c ON c.oid = fk.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = fk.conkey[1]
                JOIN pg_attribute target ON target.attrelid = fk.confrelid AND target.attnum = fk.confkey[1]
                WHERE fk.contype = 'f' AND fk.confrelid = 'professor_disciplinas'::regclass
                """
            )
            for reference in cur.fetchall():
                if (reference["columns_count"] != 1 or reference["target_column"] != "id"
                        or reference["relrowsecurity"]):
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail="Não é possível verificar com segurança as referências deste vínculo.",
                    )
                cur.execute(
                    sql.SQL("SELECT EXISTS (SELECT 1 FROM {}.{} WHERE {} = ANY(%s::uuid[])) AS existe").format(
                        sql.Identifier(reference["schema_name"]),
                        sql.Identifier(reference["table_name"]),
                        sql.Identifier(reference["column_name"]),
                    ),
                    (removidos,),
                )
                if cur.fetchone()["existe"]:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail="Não é possível remover uma disciplina com dados vinculados ao cadastro.",
                    )
            cur.execute(
                "DELETE FROM professor_disciplinas WHERE id = ANY(%s::uuid[])",
                (removidos,),
            )
        if ids:
            cur.executemany(
                """
                INSERT INTO professor_disciplinas (professor_id, disciplina_id)
                VALUES (%s, %s)
                ON CONFLICT (professor_id, disciplina_id) WHERE turma_id IS NULL DO NOTHING
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
                    json.dumps(jsonable_encoder(dados_antes)) if dados_antes is not None else None,
                    json.dumps(jsonable_encoder(dados_depois)) if dados_depois is not None else None,
                    ip,
                ),
            )


class InMemoryProfessoresRepository:
    """Implementação em memória para testes unitários isolados."""

    def __init__(self) -> None:
        self.professores: Dict[str, Dict[str, Any]] = {}
        self.professor_disciplinas: List[Dict[str, Any]] = []
        self.disciplina_conteudos: List[Dict[str, Any]] = []
        self.professor_materiais: List[Dict[str, Any]] = []
        self.disciplinas: Dict[str, Dict[str, Any]] = {}
        self.cursos: Dict[str, Dict[str, Any]] = {}
        self.turmas: Dict[str, Dict[str, Any]] = {}
        self.alunos: Dict[str, Dict[str, Any]] = {}
        self.turma_alunos: List[Dict[str, Any]] = []
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.perfis: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.logs_auditoria: List[Dict[str, Any]] = []
        # professor_id -> lotações. Sem entrada, vale o polo/escola do cadastro
        # (equivale ao backfill da migração 013).
        self.lotacoes: Dict[str, List[Dict[str, Any]]] = {}

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
        disciplina_ids = set(self._disciplinas_cadastro_ids(professor_id))
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
        return dict(row) if row and row.get("ativo", True) and row.get("turma_id") else None

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
            and row.get("turma_id") and row.get("ativo", True)
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
        return any(
            str(row.get("professor_id")) == professor_id
            and str(row.get("disciplina_id")) == str(disciplina_id)
            for row in self.professor_disciplinas
        )

    def _disciplinas_cadastro_ids(self, professor_id: str) -> List[str]:
        return list(dict.fromkeys(
            str(row["disciplina_id"]) for row in self.professor_disciplinas
            if str(row.get("professor_id")) == str(professor_id)
            and row.get("turma_id") is None and row.get("disciplina_id") is not None
        ))

    def _sync_disciplina_ids(self, professor_id: str, disciplina_ids: List[str]) -> None:
        ids = list(dict.fromkeys(str(item) for item in disciplina_ids))
        removidos = [
            row for row in self.professor_disciplinas
            if str(row.get("professor_id")) == str(professor_id)
            and row.get("turma_id") is None and str(row.get("disciplina_id")) not in ids
        ]
        if any(
            str(material.get("professor_disciplina_id")) == str(row.get("id"))
            for row in removidos for material in self.professor_materiais
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Não é possível remover uma disciplina com dados vinculados ao cadastro.",
            )
        self.professor_disciplinas = [row for row in self.professor_disciplinas if row not in removidos]
        existentes = set(self._disciplinas_cadastro_ids(professor_id))
        self.professor_disciplinas.extend(
            {"id": str(uuid.uuid4()), "professor_id": str(professor_id),
             "disciplina_id": disciplina_id, "turma_id": None, "ativo": True}
            for disciplina_id in ids if disciplina_id not in existentes
        )

    def _join(self, row: Dict[str, Any]) -> Dict[str, Any]:
        usuario = self.usuarios.get(str(row.get("usuario_id")), {})
        polo = self.polos.get(str(row.get("polo_id")), {}) if row.get("polo_id") else {}
        escola = self.escolas.get(str(row.get("escola_id")), {}) if row.get("escola_id") else {}
        disciplina_ids = self._disciplinas_cadastro_ids(str(row.get("id")))
        disciplinas = [self.disciplinas[item] for item in disciplina_ids if item in self.disciplinas]
        return {
            **row,
            "disciplina_ids": disciplina_ids,
            "disciplina_nomes": [d.get("nome") for d in disciplinas if d.get("nome")],
            "horas_totais": sum(d.get("carga_horaria") or 0 for d in disciplinas),
            "quantidade_aulas": sum(d.get("qtd_aulas_prevista") or 0 for d in disciplinas),
            "nome": usuario.get("nome"),
            "email": usuario.get("email"),
            "polo_nome": polo.get("nome"),
            "escola_nome": escola.get("nome"),
            "lotacoes": self.list_lotacoes(str(row.get("id"))),
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
            items = [
                p for p in items
                if any(str(l["polo_id"]) == str(polo_id) for l in p["lotacoes"])
            ]
        if escola_id:
            items = [
                p for p in items
                if any(str(l.get("escola_id")) == str(escola_id) for l in p["lotacoes"])
            ]
        if disciplina and disciplina.strip():
            termo = disciplina.strip().lower()
            items = [
                p for p in items
                if any(termo in str(m).lower() for m in (p.get("materias") or []))
                or any(termo in str(m).lower() for m in p["disciplina_nomes"])
            ]
        if status_filter:
            items = [p for p in items if p.get("status") == status_filter]
        items = sorted(items, key=lambda p: str(p.get("nome") or ""))
        return len(items), items[offset : offset + limit]

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        row = self.professores.get(str(professor_id))
        return self._join(row) if row else None

    def list_disciplinas_cadastro(self, professor_id: str) -> List[Dict[str, Any]]:
        rows = []
        for disciplina_id in self._disciplinas_cadastro_ids(str(professor_id)):
            disciplina = self.disciplinas.get(str(disciplina_id))
            if not disciplina:
                continue
            curso = self.cursos.get(str(disciplina.get("curso_id")), {})
            rows.append({**disciplina, "id": str(disciplina_id), "curso_nome": curso.get("nome")})
        return sorted(rows, key=lambda row: (row.get("nome") or "", row["id"]))

    def list_turmas_alunos(
        self, professor_id: str, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        disciplina_ids = set(self._disciplinas_cadastro_ids(str(professor_id)))
        turma_ids = {
            str(v["turma_id"]) for v in self.professor_disciplinas
            if str(v.get("professor_id")) == str(professor_id)
            and str(v.get("disciplina_id")) in disciplina_ids and v.get("ativo", True)
            and v.get("turma_id")
        }
        rows = []
        for turma_id in sorted(turma_ids):
            turma = self.turmas.get(turma_id)
            if not turma or (polo_id and str(turma.get("polo_id")) != str(polo_id)):
                continue
            if escola_id and str(turma.get("escola_id")) != str(escola_id):
                continue
            base = {
                "turma_id": turma_id, "turma_nome": turma.get("nome"),
                "polo_id": turma.get("polo_id"),
                "polo_nome": self.polos.get(str(turma.get("polo_id")), {}).get("nome"),
                "escola_id": turma.get("escola_id"),
                "escola_nome": self.escolas.get(str(turma.get("escola_id")), {}).get("nome"),
            }
            matriculas = [
                m for m in self.turma_alunos
                if str(m.get("turma_id")) == turma_id and (m.get("status") or "ativo") == "ativo"
            ]
            for matricula in matriculas:
                aluno_id = str(matricula["aluno_id"])
                aluno = self.alunos.get(aluno_id, {})
                usuario = self.usuarios.get(str(aluno.get("usuario_id")), {})
                rows.append({
                    **base, "aluno_id": aluno_id,
                    "aluno_nome": " ".join(filter(None, [usuario.get("nome"), usuario.get("sobrenome")])) or None,
                    "numero_matricula": aluno.get("numero_matricula"),
                    "aluno_email": usuario.get("email"),
                })
            if not matriculas:
                rows.append(base)
        return rows

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
        data = dict(data)
        lotacoes = data.pop("lotacoes", None)
        data.pop("criado_por", None)
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
        self._sync_disciplina_ids(new_id, data.get("disciplina_ids") or [])
        if lotacoes is not None:
            self.replace_lotacoes(new_id, lotacoes)
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        row = self.professores.get(str(professor_id))
        if row:
            if "disciplina_ids" in data:
                self._sync_disciplina_ids(str(professor_id), data.get("disciplina_ids") or [])
            lotacoes = data.get("lotacoes")
            ignorar = {"disciplina_ids", "horas_totais", "quantidade_aulas", "lotacoes", "criado_por"}
            if lotacoes is not None:
                ignorar |= {"polo_id", "escola_id"}
            row.update({key: value for key, value in data.items() if key not in ignorar})
            if lotacoes is not None:
                self.replace_lotacoes(str(professor_id), lotacoes)

    # ---------- Lotações ----------

    def _lotacao_view(self, lotacao: Dict[str, Any]) -> Dict[str, Any]:
        escola_id = lotacao.get("escola_id")
        return {
            **lotacao,
            "polo_nome": self.polos.get(str(lotacao["polo_id"]), {}).get("nome"),
            "escola_nome": self.escolas.get(str(escola_id), {}).get("nome") if escola_id else None,
        }

    def _lotacoes_brutas(self, professor_id: str) -> List[Dict[str, Any]]:
        professor_id = str(professor_id)
        if professor_id not in self.lotacoes:
            row = self.professores.get(professor_id) or {}
            polo_id = row.get("polo_id")
            if not polo_id and row.get("escola_id"):
                polo_id = self.get_escola_polo(str(row["escola_id"]))
            self.lotacoes[professor_id] = (
                [{
                    "id": str(uuid.uuid4()),
                    "professor_id": professor_id,
                    "polo_id": str(polo_id),
                    "escola_id": str(row["escola_id"]) if row.get("escola_id") else None,
                }]
                if polo_id else []
            )
        return self.lotacoes[professor_id]

    def _sync_principal(self, professor_id: str) -> None:
        row = self.professores.get(str(professor_id))
        if not row:
            return
        lotacoes = self._lotacoes_brutas(professor_id)
        atual = any(
            str(l["polo_id"]) == str(row.get("polo_id"))
            and str(l.get("escola_id")) == str(row.get("escola_id"))
            for l in lotacoes
        )
        if not atual:
            row["polo_id"] = lotacoes[0]["polo_id"] if lotacoes else None
            row["escola_id"] = lotacoes[0].get("escola_id") if lotacoes else None

    def get_escola_polo(self, escola_id: str) -> Optional[str]:
        escola = self.escolas.get(str(escola_id))
        return str(escola["polo_id"]) if escola and escola.get("polo_id") else None

    def polo_existe(self, polo_id: str) -> bool:
        return str(polo_id) in self.polos

    def list_lotacoes(self, professor_id: str) -> List[Dict[str, Any]]:
        rows = [self._lotacao_view(l) for l in self._lotacoes_brutas(professor_id)]
        return sorted(rows, key=lambda l: (l.get("polo_nome") or "", l.get("escola_nome") or ""))

    def add_lotacao(
        self,
        professor_id: str,
        polo_id: str,
        escola_id: Optional[str] = None,
        criado_por: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        lotacoes = self._lotacoes_brutas(professor_id)
        for lotacao in lotacoes:
            if str(lotacao["polo_id"]) == str(polo_id) and str(lotacao.get("escola_id")) == str(escola_id):
                return self._lotacao_view(lotacao), False
        nova = {
            "id": str(uuid.uuid4()),
            "professor_id": str(professor_id),
            "polo_id": str(polo_id),
            "escola_id": str(escola_id) if escola_id else None,
        }
        lotacoes.append(nova)
        self._sync_principal(professor_id)
        return self._lotacao_view(nova), True

    def remove_lotacao(self, professor_id: str, lotacao_id: str) -> Optional[Dict[str, Any]]:
        lotacoes = self._lotacoes_brutas(professor_id)
        alvo = next((l for l in lotacoes if str(l["id"]) == str(lotacao_id)), None)
        if not alvo:
            return None
        lotacoes.remove(alvo)
        self._sync_principal(professor_id)
        return self._lotacao_view(alvo)

    def replace_lotacoes(
        self, professor_id: str, lotacoes: List[Dict[str, Any]], criado_por: Optional[str] = None
    ) -> None:
        self.lotacoes[str(professor_id)] = []
        for lotacao in lotacoes:
            self.add_lotacao(str(professor_id), str(lotacao["polo_id"]), lotacao.get("escola_id"))
        self._sync_principal(professor_id)

    def list_unidades_turmas_ativas(self, professor_id: str) -> List[Dict[str, Any]]:
        unidades = []
        for vinculo in self.professor_disciplinas:
            if str(vinculo.get("professor_id")) != str(professor_id) or not vinculo.get("ativo", True):
                continue
            turma = self.turmas.get(str(vinculo.get("turma_id"))) or {}
            polo_id = turma.get("polo_id") or (
                self.get_escola_polo(str(turma["escola_id"])) if turma.get("escola_id") else None
            )
            unidade = {"polo_id": str(polo_id) if polo_id else None,
                       "escola_id": str(turma["escola_id"]) if turma.get("escola_id") else None}
            if unidade not in unidades:
                unidades.append(unidade)
        return unidades

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
