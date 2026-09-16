"""Repositório de dados do módulo `polos_escolas` do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor


class PolosEscolasRepositoryInterface(Protocol):
    # ---------- Usuários auxiliares ----------
    def get_perfil_id_by_nome(self, nome: str) -> Optional[str]: ...
    def get_usuario_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...
    def get_usuario_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]: ...
    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def create_usuario(self, data: Dict[str, Any]) -> str: ...
    def update_usuario(self, usuario_id: str, data: Dict[str, Any]) -> None: ...

    # ---------- Polos ----------
    def create_polo(self, data: Dict[str, Any]) -> str: ...
    def update_polo(self, polo_id: str, data: Dict[str, Any]) -> None: ...
    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def list_polos(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]: ...

    # ---------- Escolas ----------
    def create_escola(self, data: Dict[str, Any]) -> str: ...
    def update_escola(self, escola_id: str, data: Dict[str, Any]) -> None: ...
    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]: ...
    def list_escolas(
        self, polo_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    # ---------- Estoque de licenças ----------
    def get_estoque(
        self, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]: ...
    def ajustar_estoque(
        self,
        polo_id: Optional[str],
        escola_id: Optional[str],
        delta_disponivel: int,
        delta_vendida: int = 0,
    ) -> None: ...
    def list_estoques_escolas_do_polo(self, polo_id: str) -> List[Dict[str, Any]]: ...

    # ---------- Movimentações / compras / boletos ----------
    def registrar_compra(self, data: Dict[str, Any]) -> str: ...
    def registrar_movimentacao(self, data: Dict[str, Any]) -> str: ...
    def list_movimentacoes(
        self, polo_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def sum_compradas(self, polo_id: str) -> int: ...
    def sum_distribuidas(self, polo_id: str) -> int: ...
    def list_compras(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_boleto(self, data: Dict[str, Any]) -> str: ...
    def get_boleto(self, boleto_id: str) -> Optional[Dict[str, Any]]: ...
    def list_boletos(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    # ---------- Licenças de alunos ----------
    def vincular_licenca_aluno(self, data: Dict[str, Any]) -> str: ...
    def get_licenca_aluno_ativa(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def devolver_licenca_aluno(self, licenca_id: str) -> None: ...
    def count_licencas_vendidas_polo(self, polo_id: str) -> int: ...
    def count_licencas_vendidas_escola(self, escola_id: str) -> int: ...
    def list_alunos_licenciados_escola(
        self, escola_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def top_alunos_escola(self, escola_id: str, limit: int = 10) -> List[Dict[str, Any]]: ...
    def evolucao_escola(self, escola_id: str, meses: int = 12) -> List[Dict[str, Any]]: ...

    # ---------- Alunos ----------
    def get_aluno_usuario(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def list_alunos_polo(
        self,
        polo_id: str,
        q: Optional[str] = None,
        escola_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_aluno(self, data: Dict[str, Any]) -> str: ...
    def registrar_nota(self, data: Dict[str, Any]) -> str: ...
    def contar_presencas_aluno(self, aluno_id: str) -> Tuple[int, int]: ...
    def create_requisicao(self, data: Dict[str, Any]) -> str: ...
    def list_requisicoes(
        self,
        polo_id: str,
        tipo: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def list_alunos_desistentes(self, polo_id: str, dias_limite: int = 365) -> List[Dict[str, Any]]: ...
    def marcar_aluno_desistente(self, aluno_id: str) -> None: ...

    # ---------- Professores ----------
    def create_professor(self, data: Dict[str, Any]) -> str: ...
    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]: ...
    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None: ...
    def list_professores(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def dashboard_professores(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> Dict[str, Any]: ...
    def list_anexos_professor(
        self, professor_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[Dict[str, Any]]: ...
    def list_atas_professor(self, professor_id: str) -> List[Dict[str, Any]]: ...
    def list_chamada(self, professor_id: str, materia_id: str) -> List[Dict[str, Any]]: ...

    # ---------- Gestão pedagógica ----------
    def create_feed_post(self, data: Dict[str, Any]) -> str: ...
    def list_feed_posts(self, polo_id: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_lembrete(self, data: Dict[str, Any]) -> str: ...
    def list_lembretes(self, usuario_id: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_calendario_ead(self, data: Dict[str, Any]) -> str: ...
    def list_calendario_ead(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...

    # ---------- Treinamentos ----------
    def list_treinamentos(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...
    def inscrever_treinamento(self, treinamento_id: str, professor_id: str) -> str: ...
    def list_treinamentos_professor(self, professor_id: str) -> List[Dict[str, Any]]: ...

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
    ) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresPolosEscolasRepository:
    """Implementação PostgreSQL do repositório de Polos & Escolas."""

    # ---------- Usuários auxiliares ----------

    def get_perfil_id_by_nome(self, nome: str) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id FROM perfis WHERE lower(nome) = lower(%s) LIMIT 1", (nome.strip(),))
            row = cur.fetchone()
            return str(row["id"]) if row else None

    def get_usuario_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE lower(email) = lower(%s) LIMIT 1", (email.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_usuario_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        clean = "".join(filter(str.isdigit, cpf))
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM usuarios WHERE regexp_replace(cpf, '[^0-9]', '', 'g') = %s LIMIT 1", (clean,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE id = %s LIMIT 1", (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_usuario(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (
                    id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo,
                    perfil_id, polo_id, escola_id, status, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    new_id,
                    data.get("nome", ""),
                    data.get("sobrenome", ""),
                    data.get("email"),
                    data.get("cpf"),
                    data.get("senha_hash"),
                    data.get("senha_algoritmo", "argon2id"),
                    data.get("perfil_id"),
                    data.get("polo_id"),
                    data.get("escola_id"),
                    data.get("status", "ativo"),
                ),
            )
        return new_id

    def update_usuario(self, usuario_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields = [f"{k} = %s" for k in data]
        params = list(data.values())
        params.append(str(usuario_id))
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE usuarios SET {', '.join(fields)}, atualizado_em = now() WHERE id = %s",
                tuple(params),
            )

    # ---------- Polos ----------

    def create_polo(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO polos (
                    id, nome, logradouro, numero, bairro, cidade, uf, cep,
                    coordenador_usuario_id, status, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    new_id,
                    data["nome"],
                    data.get("logradouro", ""),
                    data.get("numero", ""),
                    data.get("bairro", ""),
                    data.get("cidade", ""),
                    data.get("estado", ""),
                    data.get("cep", ""),
                    data.get("coordenador_usuario_id"),
                    data.get("status", "ativo"),
                ),
            )
        return new_id

    def update_polo(self, polo_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields = [f"{k} = %s" for k in data]
        params = list(data.values())
        params.append(str(polo_id))
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE polos SET {', '.join(fields)}, atualizado_em = now() WHERE id = %s",
                tuple(params),
            )

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM polos WHERE id = %s LIMIT 1", (str(polo_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_polos(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM polos")
            total = int(cur.fetchone()["total"])
            cur.execute(
                "SELECT * FROM polos ORDER BY nome ASC LIMIT %s OFFSET %s", (limit, offset)
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Escolas ----------

    def create_escola(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO escolas (
                    id, polo_id, nome, logradouro, numero, bairro, cidade, uf, cep,
                    secretario_usuario_id, status, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    new_id,
                    data["polo_id"],
                    data["nome"],
                    data.get("logradouro", ""),
                    data.get("numero", ""),
                    data.get("bairro", ""),
                    data.get("cidade", ""),
                    data.get("estado", ""),
                    data.get("cep", ""),
                    data.get("secretario_usuario_id"),
                    data.get("status", "ativo"),
                ),
            )
        return new_id

    def update_escola(self, escola_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields = [f"{k} = %s" for k in data]
        params = list(data.values())
        params.append(str(escola_id))
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE escolas SET {', '.join(fields)}, atualizado_em = now() WHERE id = %s",
                tuple(params),
            )

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM escolas WHERE id = %s LIMIT 1", (str(escola_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_escolas(
        self, polo_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        where = "WHERE polo_id = %s" if polo_id else ""
        params = [str(polo_id)] if polo_id else []
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM escolas {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM escolas {where} ORDER BY nome ASC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Estoque ----------

    def get_estoque(
        self, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        col, value = ("polo_id", polo_id) if polo_id and not escola_id else ("escola_id", escola_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT * FROM licencas_estoque WHERE {col} = %s AND {'escola_id IS NULL' if col == 'polo_id' else 'polo_id IS NOT NULL'} LIMIT 1",
                (str(value),),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return {
                "polo_id": polo_id,
                "escola_id": escola_id,
                "quantidade_disponivel": 0,
                "quantidade_vendida": 0,
            }

    def ajustar_estoque(
        self,
        polo_id: Optional[str],
        escola_id: Optional[str],
        delta_disponivel: int,
        delta_vendida: int = 0,
    ) -> None:
        with get_db_cursor() as cur:
            col, value = ("polo_id", polo_id) if polo_id and not escola_id else ("escola_id", escola_id)
            other_check = "escola_id IS NULL" if col == "polo_id" else "polo_id IS NOT NULL"
            cur.execute(
                f"SELECT id, quantidade_disponivel, quantidade_vendida FROM licencas_estoque WHERE {col} = %s AND {other_check} LIMIT 1 FOR UPDATE",
                (str(value),),
            )
            row = cur.fetchone()
            if row is None:
                nova_disponivel = max(0, delta_disponivel)
                nova_vendida = max(0, delta_vendida)
                cur.execute(
                    """
                    INSERT INTO licencas_estoque (polo_id, escola_id, quantidade_disponivel, quantidade_vendida, atualizado_em)
                    VALUES (%s, %s, %s, %s, now())
                    """,
                    (polo_id, escola_id, nova_disponivel, nova_vendida),
                )
                return
            nova_disponivel = row["quantidade_disponivel"] + delta_disponivel
            nova_vendida = row["quantidade_vendida"] + delta_vendida
            if nova_disponivel < 0:
                raise ValueError("Estoque insuficiente para esta operação")
            cur.execute(
                "UPDATE licencas_estoque SET quantidade_disponivel = %s, quantidade_vendida = %s, atualizado_em = now() WHERE id = %s",
                (nova_disponivel, nova_vendida, row["id"]),
            )

    def list_estoques_escolas_do_polo(self, polo_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT e.id as escola_id, e.nome, COALESCE(le.quantidade_disponivel, 0) as disponivel,
                       COALESCE(le.quantidade_vendida, 0) as vendida
                FROM escolas e
                LEFT JOIN licencas_estoque le ON le.escola_id = e.id
                WHERE e.polo_id = %s
                ORDER BY e.nome ASC
                """,
                (str(polo_id),),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- Movimentações / compras / boletos ----------

    def registrar_compra(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras_licencas (id, polo_id, fornecedor, quantidade, valor_unitario, valor_total, data_compra, criado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    new_id,
                    data["polo_id"],
                    data.get("fornecedor"),
                    data["quantidade"],
                    data.get("valor_unitario", 0),
                    data.get("valor_unitario", 0) * data["quantidade"],
                    data["data_compra"],
                ),
            )
        return new_id

    def registrar_movimentacao(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO licencas_movimentacoes (
                    id, tipo, polo_id, escola_id, aluno_id, quantidade, valor_unitario,
                    status, actor_id, observacao, criado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    new_id,
                    data["tipo"],
                    data.get("polo_id"),
                    data.get("escola_id"),
                    data.get("aluno_id"),
                    data["quantidade"],
                    data.get("valor_unitario"),
                    data.get("status", "ativa"),
                    data.get("actor_id"),
                    data.get("observacao"),
                ),
            )
        return new_id

    def list_movimentacoes(
        self, polo_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total FROM licencas_movimentacoes WHERE polo_id = %s", (str(polo_id),)
            )
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                SELECT * FROM licencas_movimentacoes WHERE polo_id = %s
                ORDER BY criado_em DESC LIMIT %s OFFSET %s
                """,
                (str(polo_id), limit, offset),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def sum_compradas(self, polo_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(quantidade), 0) as total FROM compras_licencas WHERE polo_id = %s",
                (str(polo_id),),
            )
            return int(cur.fetchone()["total"])

    def sum_distribuidas(self, polo_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(quantidade), 0) as total FROM licencas_movimentacoes
                WHERE polo_id = %s AND tipo = 'distribuicao_polo_escola'
                """,
                (str(polo_id),),
            )
            return int(cur.fetchone()["total"])

    def list_compras(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds = ["polo_id = %s"]
        params: List[Any] = [str(polo_id)]
        if data_inicio:
            conds.append("data_compra >= %s")
            params.append(data_inicio)
        if data_fim:
            conds.append("data_compra <= %s")
            params.append(data_fim)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM compras_licencas {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM compras_licencas {where} ORDER BY data_compra DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def create_boleto(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO boletos (id, polo_id, compra_id, valor, status, data_vencimento, asaas_id, url_pdf, criado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    new_id,
                    data["polo_id"],
                    data.get("compra_id"),
                    data.get("valor"),
                    data.get("status", "pendente"),
                    data.get("data_vencimento"),
                    data.get("asaas_id"),
                    data.get("url_pdf"),
                ),
            )
        return new_id

    def get_boleto(self, boleto_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM boletos WHERE id = %s LIMIT 1", (str(boleto_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_boletos(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds = ["polo_id = %s"]
        params: List[Any] = [str(polo_id)]
        if data_inicio:
            conds.append("data_vencimento >= %s")
            params.append(data_inicio)
        if data_fim:
            conds.append("data_vencimento <= %s")
            params.append(data_fim)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM boletos {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM boletos {where} ORDER BY data_vencimento DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Licenças de alunos ----------

    def vincular_licenca_aluno(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO licencas_alunos (id, aluno_id, escola_id, polo_id, movimentacao_id, status, ativada_em)
                VALUES (%s, %s, %s, %s, %s, 'ativa', now())
                """,
                (new_id, data["aluno_id"], data.get("escola_id"), data.get("polo_id"), data.get("movimentacao_id")),
            )
        return new_id

    def get_licenca_aluno_ativa(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM licencas_alunos WHERE aluno_id = %s AND status = 'ativa' LIMIT 1",
                (str(aluno_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def devolver_licenca_aluno(self, licenca_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE licencas_alunos SET status = 'devolvida', cancelada_em = now() WHERE id = %s",
                (str(licenca_id),),
            )

    def count_licencas_vendidas_polo(self, polo_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total FROM licencas_alunos WHERE polo_id = %s AND status = 'ativa'",
                (str(polo_id),),
            )
            return int(cur.fetchone()["total"])

    def count_licencas_vendidas_escola(self, escola_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total FROM licencas_alunos WHERE escola_id = %s AND status = 'ativa'",
                (str(escola_id),),
            )
            return int(cur.fetchone()["total"])

    def list_alunos_licenciados_escola(
        self, escola_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as total FROM licencas_alunos WHERE escola_id = %s", (str(escola_id),)
            )
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                SELECT la.id, la.aluno_id, u.nome, u.sobrenome, la.status, la.ativada_em
                FROM licencas_alunos la
                JOIN usuarios u ON u.id = la.aluno_id
                WHERE la.escola_id = %s
                ORDER BY la.ativada_em DESC LIMIT %s OFFSET %s
                """,
                (str(escola_id), limit, offset),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def top_alunos_escola(self, escola_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT la.aluno_id, u.nome, u.sobrenome, COUNT(*) as qtd_licencas
                FROM licencas_alunos la
                JOIN usuarios u ON u.id = la.aluno_id
                WHERE la.escola_id = %s
                GROUP BY la.aluno_id, u.nome, u.sobrenome
                ORDER BY qtd_licencas DESC LIMIT %s
                """,
                (str(escola_id), limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def evolucao_escola(self, escola_id: str, meses: int = 12) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT date_trunc('month', criado_em) as mes_ref,
                       SUM(CASE WHEN tipo = 'venda_aluno' THEN quantidade ELSE 0 END) as vendidas,
                       SUM(CASE WHEN tipo = 'distribuicao_polo_escola' THEN quantidade ELSE 0 END) as distribuidas
                FROM licencas_movimentacoes
                WHERE escola_id = %s AND criado_em >= now() - (%s || ' months')::interval
                GROUP BY mes_ref
                ORDER BY mes_ref ASC
                """,
                (str(escola_id), str(meses)),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- Alunos ----------

    def get_aluno_usuario(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        return self.get_usuario_by_id(aluno_id)

    def list_alunos_polo(
        self,
        polo_id: str,
        q: Optional[str] = None,
        escola_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds = ["u.polo_id = %s"]
        params: List[Any] = [str(polo_id)]
        if q:
            conds.append("(lower(u.nome) LIKE %s OR lower(u.email) LIKE %s)")
            like = f"%{q.lower()}%"
            params.extend([like, like])
        if escola_id:
            conds.append("u.escola_id = %s")
            params.append(str(escola_id))
        if status_filter:
            conds.append("u.status = %s")
            params.append(status_filter)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) as total FROM usuarios u JOIN perfis p ON p.id = u.perfil_id {where} AND lower(p.nome) = 'aluno'",
                tuple(params),
            )
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"""
                SELECT u.* FROM usuarios u JOIN perfis p ON p.id = u.perfil_id
                {where} AND lower(p.nome) = 'aluno'
                ORDER BY u.nome ASC LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def create_aluno(self, data: Dict[str, Any]) -> str:
        return self.create_usuario(data)

    def registrar_nota(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO notas_alunos (id, aluno_id, materia_id, valor, descricao, criado_em)
                VALUES (%s, %s, %s, %s, %s, now())
                """,
                (new_id, data["aluno_id"], data["materia_id"], data["valor"], data.get("descricao")),
            )
        return new_id

    def contar_presencas_aluno(self, aluno_id: str) -> Tuple[int, int]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FILTER (WHERE presente) as presentes, COUNT(*) as total FROM presencas WHERE aluno_id = %s",
                (str(aluno_id),),
            )
            row = cur.fetchone()
            return int(row["presentes"] or 0), int(row["total"] or 0)

    def create_requisicao(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO requisicoes_troca (
                    id, aluno_id, tipo, polo_origem_id, polo_destino_id, modalidade_destino,
                    status, solicitado_por, criado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pendente', %s, now())
                """,
                (
                    new_id,
                    data["aluno_id"],
                    data["tipo"],
                    data.get("polo_origem_id"),
                    data.get("polo_destino_id"),
                    data.get("modalidade_destino"),
                    data.get("solicitado_por"),
                ),
            )
        return new_id

    def list_requisicoes(
        self,
        polo_id: str,
        tipo: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds = ["polo_origem_id = %s"]
        params: List[Any] = [str(polo_id)]
        if tipo:
            conds.append("tipo = %s")
            params.append(tipo)
        if status_filter:
            conds.append("status = %s")
            params.append(status_filter)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM requisicoes_troca {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM requisicoes_troca {where} ORDER BY criado_em DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def list_alunos_desistentes(self, polo_id: str, dias_limite: int = 365) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, nome, sobrenome, polo_id, ultimo_login_em, atualizado_em
                FROM usuarios
                WHERE polo_id = %s AND status = 'ativo'
                  AND COALESCE(atualizado_em, criado_em) < now() - (%s || ' days')::interval
                """,
                (str(polo_id), str(dias_limite)),
            )
            return [dict(r) for r in cur.fetchall()]

    def marcar_aluno_desistente(self, aluno_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET status = 'desistente', atualizado_em = now() WHERE id = %s",
                (str(aluno_id),),
            )

    # ---------- Professores ----------

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO professores (
                    id, usuario_id, polo_id, escola_id, materias, data_inicio,
                    quantidade_aulas, horas_totais, valor_hora_aula, pix, conteudo_programatico, status, criado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo', now())
                """,
                (
                    new_id,
                    data["usuario_id"],
                    data.get("polo_id"),
                    data.get("escola_id"),
                    json.dumps(data.get("materias", [])),
                    data.get("data_inicio"),
                    data.get("quantidade_aulas", 0),
                    data.get("horas_totais", 0),
                    data.get("valor_hora_aula"),
                    data.get("pix"),
                    data.get("conteudo_programatico"),
                ),
            )
        return new_id

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT prof.*, u.nome, u.email FROM professores prof
                JOIN usuarios u ON u.id = prof.usuario_id
                WHERE prof.id = %s LIMIT 1
                """,
                (str(professor_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields = []
        params: List[Any] = []
        for k, v in data.items():
            if k == "materias":
                fields.append("materias = %s")
                params.append(json.dumps(v))
            else:
                fields.append(f"{k} = %s")
                params.append(v)
        params.append(str(professor_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE professores SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def list_professores(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds = ["prof.polo_id = %s"]
        params: List[Any] = [str(polo_id)]
        if data_inicio:
            conds.append("prof.data_inicio >= %s")
            params.append(data_inicio)
        if data_fim:
            conds.append("prof.data_inicio <= %s")
            params.append(data_fim)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM professores prof {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"""
                SELECT prof.*, u.nome, u.email FROM professores prof
                JOIN usuarios u ON u.id = prof.usuario_id
                {where}
                ORDER BY u.nome ASC LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def dashboard_professores(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> Dict[str, Any]:
        conds = ["polo_id = %s"]
        params: List[Any] = [str(polo_id)]
        if data_inicio:
            conds.append("data_aula >= %s")
            params.append(data_inicio)
        if data_fim:
            conds.append("data_aula <= %s")
            params.append(data_fim)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) as qtd, COALESCE(SUM(total_aulas_previstas), 0) as horas FROM aulas {where}",
                tuple(params),
            )
            row = cur.fetchone()
            return {"quantidade_aulas": int(row["qtd"] or 0), "horas_aulas": float(row["horas"] or 0)}

    def list_anexos_professor(
        self, professor_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[Dict[str, Any]]:
        conds = ["a.professor_id = %s"]
        params: List[Any] = [str(professor_id)]
        if data_inicio:
            conds.append("aula.data_aula >= %s")
            params.append(data_inicio)
        if data_fim:
            conds.append("aula.data_aula <= %s")
            params.append(data_fim)
        where = "WHERE " + " AND ".join(conds)
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT a.*, aula.data_aula, aula.materia_id FROM anexos_aula a
                JOIN aulas aula ON aula.id = a.aula_id
                {where}
                ORDER BY aula.data_aula DESC
                """,
                tuple(params),
            )
            return [dict(r) for r in cur.fetchall()]

    def list_atas_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM atas WHERE professor_id = %s ORDER BY criado_em DESC", (str(professor_id),)
            )
            return [dict(r) for r in cur.fetchall()]

    def list_chamada(self, professor_id: str, materia_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT p.aluno_id, u.nome,
                       COUNT(*) FILTER (WHERE p.presente) as presencas,
                       COUNT(*) as total_registros,
                       MAX(aula.total_aulas_previstas) as total_previsto
                FROM presencas p
                JOIN aulas aula ON aula.id = p.aula_id
                JOIN usuarios u ON u.id = p.aluno_id
                WHERE aula.professor_id = %s AND aula.materia_id = %s
                GROUP BY p.aluno_id, u.nome
                """,
                (str(professor_id), str(materia_id)),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- Gestão pedagógica ----------

    def create_feed_post(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO feed_noticias (id, autor_id, titulo, conteudo, tags, polo_id, criado_em)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                """,
                (new_id, data["autor_id"], data["titulo"], data["conteudo"], json.dumps(data.get("tags", [])), data.get("polo_id")),
            )
        return new_id

    def list_feed_posts(
        self, polo_id: Optional[str], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        where = "WHERE polo_id = %s" if polo_id else ""
        params = [str(polo_id)] if polo_id else []
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM feed_noticias {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM feed_noticias {where} ORDER BY criado_em DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def create_lembrete(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO lembretes (id, usuario_id, titulo, mensagem, data_expiracao, criado_em)
                VALUES (%s, %s, %s, %s, %s, now())
                """,
                (new_id, data.get("usuario_id"), data["titulo"], data["mensagem"], data.get("data_expiracao")),
            )
        return new_id

    def list_lembretes(
        self, usuario_id: Optional[str], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        where = "WHERE usuario_id = %s" if usuario_id else ""
        params = [str(usuario_id)] if usuario_id else []
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as total FROM lembretes {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM lembretes {where} ORDER BY criado_em DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def create_calendario_ead(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO calendario_ead (id, materia_id, data_liberacao, semestre, ano, criado_por, criado_em)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                """,
                (new_id, data["materia_id"], data["data_liberacao"], data.get("semestre"), data.get("ano"), data.get("criado_por")),
            )
        return new_id

    def list_calendario_ead(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM calendario_ead")
            total = int(cur.fetchone()["total"])
            cur.execute(
                "SELECT * FROM calendario_ead ORDER BY data_liberacao ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Treinamentos ----------

    def list_treinamentos(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM treinamentos")
            total = int(cur.fetchone()["total"])
            cur.execute(
                "SELECT * FROM treinamentos ORDER BY criado_em DESC LIMIT %s OFFSET %s", (limit, offset)
            )
            return total, [dict(r) for r in cur.fetchall()]

    def inscrever_treinamento(self, treinamento_id: str, professor_id: str) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO treinamentos_inscricoes (id, treinamento_id, professor_id, status, criado_em)
                VALUES (%s, %s, %s, 'inscrito', now())
                """,
                (new_id, treinamento_id, professor_id),
            )
        return new_id

    def list_treinamentos_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT ti.*, t.titulo, t.carga_horaria FROM treinamentos_inscricoes ti
                JOIN treinamentos t ON t.id = ti.treinamento_id
                WHERE ti.professor_id = %s
                ORDER BY ti.criado_em DESC
                """,
                (str(professor_id),),
            )
            return [dict(r) for r in cur.fetchall()]

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


class InMemoryPolosEscolasRepository:
    """Implementação em memória para testes unitários isolados."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.perfis: Dict[str, str] = {
            "admin": "perfil-admin",
            "secretario_geral": "perfil-secgeral",
            "coordenador_polo": "perfil-coordpolo",
            "secretario_escola": "perfil-secescola",
            "professor": "perfil-professor",
            "monitor": "perfil-monitor",
            "aluno": "perfil-aluno",
        }
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.estoques: Dict[Tuple[str, str], Dict[str, Any]] = {}  # (polo_id or '', escola_id or '')
        self.compras: Dict[str, Dict[str, Any]] = {}
        self.movimentacoes: Dict[str, Dict[str, Any]] = {}
        self.boletos: Dict[str, Dict[str, Any]] = {}
        self.licencas_alunos: Dict[str, Dict[str, Any]] = {}
        self.notas: Dict[str, Dict[str, Any]] = {}
        self.requisicoes: Dict[str, Dict[str, Any]] = {}
        self.professores: Dict[str, Dict[str, Any]] = {}
        self.aulas: Dict[str, Dict[str, Any]] = {}
        self.anexos: Dict[str, Dict[str, Any]] = {}
        self.atas: Dict[str, Dict[str, Any]] = {}
        self.presencas: Dict[str, Dict[str, Any]] = {}
        self.feed: Dict[str, Dict[str, Any]] = {}
        self.lembretes: Dict[str, Dict[str, Any]] = {}
        self.calendario_ead: Dict[str, Dict[str, Any]] = {}
        self.treinamentos: Dict[str, Dict[str, Any]] = {}
        self.treinamentos_inscricoes: Dict[str, Dict[str, Any]] = {}
        self.logs_auditoria: List[Dict[str, Any]] = []

    # ---------- Usuários ----------

    def get_perfil_id_by_nome(self, nome: str) -> Optional[str]:
        return self.perfis.get(nome.strip().lower())

    def get_usuario_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_clean = email.strip().lower()
        for u in self.usuarios.values():
            if (u.get("email") or "").lower() == email_clean:
                return u.copy()
        return None

    def get_usuario_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        clean = "".join(filter(str.isdigit, cpf))
        for u in self.usuarios.values():
            if "".join(filter(str.isdigit, u.get("cpf") or "")) == clean:
                return u.copy()
        return None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        u = self.usuarios.get(str(usuario_id))
        return u.copy() if u else None

    def create_usuario(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.usuarios[new_id] = {"id": new_id, "status": "ativo", "criado_em": _now(), "atualizado_em": _now(), **data}
        return new_id

    def update_usuario(self, usuario_id: str, data: Dict[str, Any]) -> None:
        u = self.usuarios.get(str(usuario_id))
        if u:
            u.update(data)
            u["atualizado_em"] = _now()

    # ---------- Polos ----------

    def create_polo(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.polos[new_id] = {"id": new_id, "status": "ativo", "criado_em": _now(), "atualizado_em": _now(), **data}
        return new_id

    def update_polo(self, polo_id: str, data: Dict[str, Any]) -> None:
        p = self.polos.get(str(polo_id))
        if p:
            p.update(data)
            p["atualizado_em"] = _now()

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        p = self.polos.get(str(polo_id))
        return p.copy() if p else None

    def list_polos(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        items = sorted(self.polos.values(), key=lambda x: x["nome"])
        return len(items), items[offset : offset + limit]

    # ---------- Escolas ----------

    def create_escola(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.escolas[new_id] = {"id": new_id, "status": "ativo", "criado_em": _now(), "atualizado_em": _now(), **data}
        return new_id

    def update_escola(self, escola_id: str, data: Dict[str, Any]) -> None:
        e = self.escolas.get(str(escola_id))
        if e:
            e.update(data)
            e["atualizado_em"] = _now()

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        e = self.escolas.get(str(escola_id))
        return e.copy() if e else None

    def list_escolas(
        self, polo_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = list(self.escolas.values())
        if polo_id:
            items = [e for e in items if str(e.get("polo_id")) == str(polo_id)]
        items.sort(key=lambda x: x["nome"])
        return len(items), items[offset : offset + limit]

    # ---------- Estoque ----------

    def _estoque_key(self, polo_id: Optional[str], escola_id: Optional[str]) -> Tuple[str, str]:
        return (str(polo_id) if polo_id else "", str(escola_id) if escola_id else "")

    def get_estoque(
        self, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        key = self._estoque_key(polo_id, escola_id)
        estoque = self.estoques.get(key)
        if estoque:
            return estoque.copy()
        return {"polo_id": polo_id, "escola_id": escola_id, "quantidade_disponivel": 0, "quantidade_vendida": 0}

    def ajustar_estoque(
        self,
        polo_id: Optional[str],
        escola_id: Optional[str],
        delta_disponivel: int,
        delta_vendida: int = 0,
    ) -> None:
        key = self._estoque_key(polo_id, escola_id)
        estoque = self.estoques.setdefault(
            key, {"polo_id": polo_id, "escola_id": escola_id, "quantidade_disponivel": 0, "quantidade_vendida": 0}
        )
        nova_disponivel = estoque["quantidade_disponivel"] + delta_disponivel
        if nova_disponivel < 0:
            raise ValueError("Estoque insuficiente para esta operação")
        estoque["quantidade_disponivel"] = nova_disponivel
        estoque["quantidade_vendida"] += delta_vendida

    def list_estoques_escolas_do_polo(self, polo_id: str) -> List[Dict[str, Any]]:
        result = []
        for escola in self.escolas.values():
            if str(escola.get("polo_id")) != str(polo_id):
                continue
            estoque = self.get_estoque(escola_id=escola["id"])
            result.append(
                {
                    "escola_id": escola["id"],
                    "nome": escola["nome"],
                    "disponivel": estoque["quantidade_disponivel"],
                    "vendida": estoque["quantidade_vendida"],
                }
            )
        return result

    # ---------- Movimentações / compras / boletos ----------

    def registrar_compra(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        valor_unitario = data.get("valor_unitario", 0)
        self.compras[new_id] = {
            "id": new_id,
            "polo_id": data["polo_id"],
            "fornecedor": data.get("fornecedor"),
            "quantidade": data["quantidade"],
            "valor_unitario": valor_unitario,
            "valor_total": valor_unitario * data["quantidade"],
            "data_compra": data["data_compra"],
            "criado_em": _now(),
        }
        return new_id

    def registrar_movimentacao(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.movimentacoes[new_id] = {"id": new_id, "criado_em": _now(), "status": data.get("status", "ativa"), **data}
        return new_id

    def list_movimentacoes(
        self, polo_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [m for m in self.movimentacoes.values() if str(m.get("polo_id")) == str(polo_id)]
        items.sort(key=lambda x: x["criado_em"], reverse=True)
        return len(items), items[offset : offset + limit]

    def sum_compradas(self, polo_id: str) -> int:
        return sum(c["quantidade"] for c in self.compras.values() if str(c["polo_id"]) == str(polo_id))

    def sum_distribuidas(self, polo_id: str) -> int:
        return sum(
            m["quantidade"]
            for m in self.movimentacoes.values()
            if str(m.get("polo_id")) == str(polo_id) and m.get("tipo") == "distribuicao_polo_escola"
        )

    def list_compras(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [c for c in self.compras.values() if str(c["polo_id"]) == str(polo_id)]
        if data_inicio:
            items = [c for c in items if c["data_compra"] >= data_inicio]
        if data_fim:
            items = [c for c in items if c["data_compra"] <= data_fim]
        items.sort(key=lambda x: x["data_compra"], reverse=True)
        return len(items), items[offset : offset + limit]

    def create_boleto(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.boletos[new_id] = {"id": new_id, "status": data.get("status", "pendente"), "criado_em": _now(), **data}
        return new_id

    def get_boleto(self, boleto_id: str) -> Optional[Dict[str, Any]]:
        b = self.boletos.get(str(boleto_id))
        return b.copy() if b else None

    def list_boletos(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [b for b in self.boletos.values() if str(b["polo_id"]) == str(polo_id)]
        if data_inicio:
            items = [b for b in items if b.get("data_vencimento") and b["data_vencimento"] >= data_inicio]
        if data_fim:
            items = [b for b in items if b.get("data_vencimento") and b["data_vencimento"] <= data_fim]
        return len(items), items[offset : offset + limit]

    # ---------- Licenças de alunos ----------

    def vincular_licenca_aluno(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.licencas_alunos[new_id] = {
            "id": new_id,
            "status": "ativa",
            "ativada_em": _now(),
            **data,
        }
        return new_id

    def get_licenca_aluno_ativa(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        for lic in self.licencas_alunos.values():
            if str(lic["aluno_id"]) == str(aluno_id) and lic["status"] == "ativa":
                return lic.copy()
        return None

    def devolver_licenca_aluno(self, licenca_id: str) -> None:
        lic = self.licencas_alunos.get(str(licenca_id))
        if lic:
            lic["status"] = "devolvida"
            lic["cancelada_em"] = _now()

    def count_licencas_vendidas_polo(self, polo_id: str) -> int:
        return sum(
            1 for lic in self.licencas_alunos.values()
            if str(lic.get("polo_id")) == str(polo_id) and lic["status"] == "ativa"
        )

    def count_licencas_vendidas_escola(self, escola_id: str) -> int:
        return sum(
            1 for lic in self.licencas_alunos.values()
            if str(lic.get("escola_id")) == str(escola_id) and lic["status"] == "ativa"
        )

    def list_alunos_licenciados_escola(
        self, escola_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [lic for lic in self.licencas_alunos.values() if str(lic.get("escola_id")) == str(escola_id)]
        result = []
        for lic in items:
            u = self.usuarios.get(str(lic["aluno_id"]), {})
            result.append({**lic, "nome": u.get("nome", ""), "sobrenome": u.get("sobrenome", "")})
        result.sort(key=lambda x: x["ativada_em"], reverse=True)
        return len(result), result[offset : offset + limit]

    def top_alunos_escola(self, escola_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for lic in self.licencas_alunos.values():
            if str(lic.get("escola_id")) == str(escola_id):
                counts[lic["aluno_id"]] = counts.get(lic["aluno_id"], 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        result = []
        for aluno_id, qtd in ranked:
            u = self.usuarios.get(str(aluno_id), {})
            result.append({"aluno_id": aluno_id, "nome": u.get("nome", ""), "sobrenome": u.get("sobrenome", ""), "qtd_licencas": qtd})
        return result

    def evolucao_escola(self, escola_id: str, meses: int = 12) -> List[Dict[str, Any]]:
        buckets: Dict[Tuple[int, int], Dict[str, int]] = {}
        for m in self.movimentacoes.values():
            if str(m.get("escola_id")) != str(escola_id):
                continue
            criado = m["criado_em"]
            key = (criado.year, criado.month)
            bucket = buckets.setdefault(key, {"vendidas": 0, "distribuidas": 0})
            if m.get("tipo") == "venda_aluno":
                bucket["vendidas"] += m["quantidade"]
            elif m.get("tipo") == "distribuicao_polo_escola":
                bucket["distribuidas"] += m["quantidade"]
        result = [
            {"ano": ano, "mes": mes, **vals}
            for (ano, mes), vals in sorted(buckets.items())
        ]
        return result

    # ---------- Alunos ----------

    def get_aluno_usuario(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        return self.get_usuario_by_id(aluno_id)

    def list_alunos_polo(
        self,
        polo_id: str,
        q: Optional[str] = None,
        escola_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [
            u for u in self.usuarios.values()
            if str(u.get("polo_id")) == str(polo_id) and (u.get("perfil_id") == self.perfis.get("aluno"))
        ]
        if q:
            ql = q.lower()
            items = [u for u in items if ql in (u.get("nome", "") + u.get("email", "")).lower()]
        if escola_id:
            items = [u for u in items if str(u.get("escola_id")) == str(escola_id)]
        if status_filter:
            items = [u for u in items if u.get("status") == status_filter]
        items.sort(key=lambda x: x.get("nome", ""))
        return len(items), items[offset : offset + limit]

    def create_aluno(self, data: Dict[str, Any]) -> str:
        return self.create_usuario(data)

    def registrar_nota(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.notas[new_id] = {"id": new_id, "criado_em": _now(), **data}
        return new_id

    def contar_presencas_aluno(self, aluno_id: str) -> Tuple[int, int]:
        registros = [p for p in self.presencas.values() if str(p["aluno_id"]) == str(aluno_id)]
        presentes = sum(1 for p in registros if p.get("presente"))
        return presentes, len(registros)

    def create_requisicao(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.requisicoes[new_id] = {"id": new_id, "status": "pendente", "criado_em": _now(), **data}
        return new_id

    def list_requisicoes(
        self,
        polo_id: str,
        tipo: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [r for r in self.requisicoes.values() if str(r.get("polo_origem_id")) == str(polo_id)]
        if tipo:
            items = [r for r in items if r.get("tipo") == tipo]
        if status_filter:
            items = [r for r in items if r.get("status") == status_filter]
        items.sort(key=lambda x: x["criado_em"], reverse=True)
        return len(items), items[offset : offset + limit]

    def list_alunos_desistentes(self, polo_id: str, dias_limite: int = 365) -> List[Dict[str, Any]]:
        cutoff = _now()
        result = []
        for u in self.usuarios.values():
            if str(u.get("polo_id")) != str(polo_id) or u.get("status") != "ativo":
                continue
            referencia = u.get("atualizado_em") or u.get("criado_em") or cutoff
            dias = (cutoff - referencia).days
            if dias >= dias_limite:
                result.append({**u, "dias_sem_movimentacao": dias})
        return result

    def marcar_aluno_desistente(self, aluno_id: str) -> None:
        u = self.usuarios.get(str(aluno_id))
        if u:
            u["status"] = "desistente"
            u["atualizado_em"] = _now()

    # ---------- Professores ----------

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.professores[new_id] = {
            "id": new_id,
            "status": "ativo",
            "materias": data.get("materias", []),
            "quantidade_aulas": data.get("quantidade_aulas", 0),
            "horas_totais": data.get("horas_totais", 0),
            "criado_em": _now(),
            **{k: v for k, v in data.items() if k not in ("materias",)},
        }
        return new_id

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        p = self.professores.get(str(professor_id))
        if not p:
            return None
        u = self.usuarios.get(str(p["usuario_id"]), {})
        return {**p, "nome": u.get("nome", ""), "email": u.get("email", "")}

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        p = self.professores.get(str(professor_id))
        if p:
            p.update(data)

    def list_professores(
        self,
        polo_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [p for p in self.professores.values() if str(p.get("polo_id")) == str(polo_id)]
        if data_inicio:
            items = [p for p in items if p.get("data_inicio") and p["data_inicio"] >= data_inicio]
        if data_fim:
            items = [p for p in items if p.get("data_inicio") and p["data_inicio"] <= data_fim]
        result = []
        for p in items:
            u = self.usuarios.get(str(p["usuario_id"]), {})
            result.append({**p, "nome": u.get("nome", ""), "email": u.get("email", "")})
        return len(result), result[offset : offset + limit]

    def dashboard_professores(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> Dict[str, Any]:
        items = [a for a in self.aulas.values() if str(a.get("polo_id")) == str(polo_id)]
        if data_inicio:
            items = [a for a in items if a["data_aula"] >= data_inicio]
        if data_fim:
            items = [a for a in items if a["data_aula"] <= data_fim]
        horas = sum(a.get("total_aulas_previstas") or 0 for a in items)
        return {"quantidade_aulas": len(items), "horas_aulas": float(horas)}

    def list_anexos_professor(
        self, professor_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[Dict[str, Any]]:
        result = []
        for anexo in self.anexos.values():
            aula = self.aulas.get(str(anexo["aula_id"]))
            if not aula or str(aula.get("professor_id")) != str(professor_id):
                continue
            if data_inicio and aula["data_aula"] < data_inicio:
                continue
            if data_fim and aula["data_aula"] > data_fim:
                continue
            result.append({**anexo, "data_aula": aula["data_aula"], "materia_id": aula.get("materia_id")})
        return result

    def list_atas_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        return [a for a in self.atas.values() if str(a["professor_id"]) == str(professor_id)]

    def list_chamada(self, professor_id: str, materia_id: str) -> List[Dict[str, Any]]:
        aulas_prof = {
            aid: a for aid, a in self.aulas.items()
            if str(a.get("professor_id")) == str(professor_id) and str(a.get("materia_id")) == str(materia_id)
        }
        total_previsto = max((a.get("total_aulas_previstas") or 0 for a in aulas_prof.values()), default=0)
        por_aluno: Dict[str, Dict[str, int]] = {}
        for p in self.presencas.values():
            if str(p["aula_id"]) not in aulas_prof:
                continue
            info = por_aluno.setdefault(p["aluno_id"], {"presencas": 0, "total_registros": 0})
            info["total_registros"] += 1
            if p.get("presente"):
                info["presencas"] += 1
        result = []
        for aluno_id, info in por_aluno.items():
            u = self.usuarios.get(str(aluno_id), {})
            result.append({"aluno_id": aluno_id, "nome": u.get("nome", ""), "presencas": info["presencas"], "total_previsto": total_previsto})
        return result

    # ---------- Gestão pedagógica ----------

    def create_feed_post(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.feed[new_id] = {"id": new_id, "criado_em": _now(), **data}
        return new_id

    def list_feed_posts(
        self, polo_id: Optional[str], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = list(self.feed.values())
        if polo_id:
            items = [f for f in items if str(f.get("polo_id")) == str(polo_id)]
        items.sort(key=lambda x: x["criado_em"], reverse=True)
        return len(items), items[offset : offset + limit]

    def create_lembrete(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.lembretes[new_id] = {"id": new_id, "lido": False, "criado_em": _now(), **data}
        return new_id

    def list_lembretes(
        self, usuario_id: Optional[str], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = list(self.lembretes.values())
        if usuario_id:
            items = [l for l in items if str(l.get("usuario_id")) == str(usuario_id)]
        items.sort(key=lambda x: x["criado_em"], reverse=True)
        return len(items), items[offset : offset + limit]

    def create_calendario_ead(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.calendario_ead[new_id] = {"id": new_id, "criado_em": _now(), **data}
        return new_id

    def list_calendario_ead(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        items = sorted(self.calendario_ead.values(), key=lambda x: x["data_liberacao"])
        return len(items), items[offset : offset + limit]

    # ---------- Treinamentos ----------

    def list_treinamentos(self, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        items = list(self.treinamentos.values())
        return len(items), items[offset : offset + limit]

    def inscrever_treinamento(self, treinamento_id: str, professor_id: str) -> str:
        new_id = str(uuid.uuid4())
        self.treinamentos_inscricoes[new_id] = {
            "id": new_id,
            "treinamento_id": treinamento_id,
            "professor_id": professor_id,
            "status": "inscrito",
            "criado_em": _now(),
        }
        return new_id

    def list_treinamentos_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        result = []
        for insc in self.treinamentos_inscricoes.values():
            if str(insc["professor_id"]) != str(professor_id):
                continue
            t = self.treinamentos.get(str(insc["treinamento_id"]), {})
            result.append({**insc, "titulo": t.get("titulo"), "carga_horaria": t.get("carga_horaria")})
        return result

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
        self.logs_auditoria.append(
            {
                "usuario_id": usuario_id,
                "acao": acao,
                "entidade": entidade,
                "entidade_id": entidade_id,
                "dados_antes": dados_antes,
                "dados_depois": dados_depois,
                "ip": ip,
                "criado_em": _now(),
            }
        )


_repo_instance: Optional[PolosEscolasRepositoryInterface] = None


def get_polos_escolas_repository() -> PolosEscolasRepositoryInterface:
    """Provedor padrão do repositório (PostgreSQL em produção)."""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresPolosEscolasRepository()
    return _repo_instance


def set_polos_escolas_repository(repo: PolosEscolasRepositoryInterface) -> None:
    """Permite injeção de um repositório alternativo (ex: InMemory nos testes)."""
    global _repo_instance
    _repo_instance = repo
