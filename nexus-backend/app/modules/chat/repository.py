"""Persistência do Chat Interno (PostgreSQL).

Mensagens vivem em `chat_mensagens` por até 48h e depois são movidas para
`chat_mensagens_historico` (90 dias). Toda leitura de mensagens une as duas tabelas.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor
from app.modules.chat.regras import DIAS_HISTORICO, HORAS_TABELA_ATIVA

_COLS_MSG = ("id, conversa_id, remetente_id, tipo, texto, anexo_url, anexo_storage_key, "
             "anexo_nome, anexo_mime, anexo_tamanho, ref_tipo, ref_id, criado_em")

# Mensagens das duas tabelas (ativa + histórico) de uma conversa.
_UNIAO_MSG = f"""
    (SELECT {_COLS_MSG} FROM chat_mensagens WHERE conversa_id = %(cid)s
     UNION ALL
     SELECT {_COLS_MSG} FROM chat_mensagens_historico WHERE conversa_id = %(cid)s)
"""

_NOME_USUARIO = "TRIM(COALESCE(u.nome, '') || ' ' || COALESCE(u.sobrenome, ''))"


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in dict(row).items()}


def uuid_valido(valor: Any) -> bool:
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, TypeError):
        return False


class PostgresChatRepository:
    # ------------------------------------------------------------------
    # Usuários / contatos
    # ------------------------------------------------------------------
    def get_usuarios(self, ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        ids = [str(i) for i in ids if uuid_valido(i)]
        if not ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT u.id, {_NOME_USUARIO} AS nome, u.foto_url, u.status, u.polo_id, u.escola_id,
                           p.nome AS perfil
                      FROM usuarios u LEFT JOIN perfis p ON p.id = u.perfil_id
                     WHERE u.id::text = ANY(%s)""",
                (ids,),
            )
            return {str(r["id"]): _limpar(r) for r in cur.fetchall()}

    def buscar_contatos(self, *, busca: Optional[str], perfis: Sequence[str], excluir_id: str,
                        limite: int) -> List[Dict[str, Any]]:
        filtros = ["u.status = 'ativo'", "u.id <> %s", "LOWER(p.nome) = ANY(%s)"]
        params: List[Any] = [excluir_id, list(perfis)]
        if busca:
            filtros.append(f"({_NOME_USUARIO} ILIKE %s OR u.email ILIKE %s)")
            termo = f"%{busca.strip()}%"
            params += [termo, termo]
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT u.id, {_NOME_USUARIO} AS nome, u.foto_url, p.nome AS perfil,
                           po.nome AS polo_nome, es.nome AS escola_nome
                      FROM usuarios u
                      JOIN perfis p ON p.id = u.perfil_id
                      LEFT JOIN polos po ON po.id = u.polo_id
                      LEFT JOIN escolas es ON es.id = u.escola_id
                     WHERE {' AND '.join(filtros)}
                     ORDER BY nome LIMIT %s""",
                (*params, limite),
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Conversas e membros
    # ------------------------------------------------------------------
    def get_conversa(self, conversa_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(conversa_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM chat_conversas WHERE id = %s", (conversa_id,))
            return _limpar(cur.fetchone())

    def get_conversa_por_chave(self, chave: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM chat_conversas WHERE chave = %s", (chave,))
            return _limpar(cur.fetchone())

    def criar_conversa(self, dados: Dict[str, Any], membros: Sequence[Tuple[str, str]]) -> bool:
        """Cria a conversa e os membros. Retorna False se a chave já existia (corrida)."""
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO chat_conversas (id, chave, tipo, titulo, turma_id, criado_por)
                   VALUES (%(id)s, %(chave)s, %(tipo)s, %(titulo)s, %(turma_id)s, %(criado_por)s)
                   ON CONFLICT (chave) DO NOTHING RETURNING id""",
                dados,
            )
            if cur.fetchone() is None:
                return False
            for usuario_id, papel in membros:
                cur.execute(
                    """INSERT INTO chat_membros (conversa_id, usuario_id, papel, ultima_leitura_em)
                       VALUES (%s, %s, %s, now()) ON CONFLICT (conversa_id, usuario_id) DO NOTHING""",
                    (dados["id"], usuario_id, papel),
                )
            return True

    def get_membro(self, conversa_id: str, usuario_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(conversa_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM chat_membros WHERE conversa_id = %s AND usuario_id = %s",
                        (conversa_id, usuario_id))
            return _limpar(cur.fetchone())

    def listar_membros(self, conversa_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT m.usuario_id, m.papel, m.ultima_leitura_em, m.entrou_em,
                           {_NOME_USUARIO} AS nome, u.foto_url, p.nome AS perfil
                      FROM chat_membros m
                      JOIN usuarios u ON u.id = m.usuario_id
                      LEFT JOIN perfis p ON p.id = u.perfil_id
                     WHERE m.conversa_id = %s
                     ORDER BY m.papel DESC, nome""",
                (conversa_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def adicionar_membros(self, conversa_id: str, membros: Sequence[Tuple[str, str]]) -> List[str]:
        """Adiciona membros (ignora os existentes). Retorna os IDs efetivamente adicionados."""
        novos: List[str] = []
        with get_db_cursor() as cur:
            for usuario_id, papel in membros:
                cur.execute(
                    """INSERT INTO chat_membros (conversa_id, usuario_id, papel, ultima_leitura_em)
                       VALUES (%s, %s, %s, now()) ON CONFLICT (conversa_id, usuario_id) DO NOTHING
                       RETURNING usuario_id""",
                    (conversa_id, usuario_id, papel),
                )
                if cur.fetchone():
                    novos.append(str(usuario_id))
        return novos

    def remover_membros(self, conversa_id: str, usuario_ids: Sequence[str]) -> int:
        ids = [str(i) for i in usuario_ids if uuid_valido(i)]
        if not ids:
            return 0
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM chat_membros WHERE conversa_id = %s AND usuario_id::text = ANY(%s)",
                        (conversa_id, ids))
            return cur.rowcount

    def reexibir(self, conversa_id: str, usuario_id: Optional[str] = None) -> None:
        """Tira a ocultação ("some só para mim") de um membro ou de todos."""
        with get_db_cursor() as cur:
            if usuario_id:
                cur.execute("UPDATE chat_membros SET oculta_em = NULL WHERE conversa_id = %s AND usuario_id = %s",
                            (conversa_id, usuario_id))
            else:
                cur.execute("UPDATE chat_membros SET oculta_em = NULL WHERE conversa_id = %s AND oculta_em IS NOT NULL",
                            (conversa_id,))

    def ocultar(self, conversa_id: str, usuario_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("""UPDATE chat_membros SET oculta_em = now(), ultima_leitura_em = now()
                            WHERE conversa_id = %s AND usuario_id = %s""", (conversa_id, usuario_id))
            return cur.rowcount > 0

    def marcar_lida(self, conversa_id: str, usuario_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE chat_membros SET ultima_leitura_em = now() WHERE conversa_id = %s AND usuario_id = %s",
                        (conversa_id, usuario_id))

    def set_status(self, conversa_id: str, status: str, usuario_id: Optional[str]) -> None:
        with get_db_cursor() as cur:
            if status == "encerrada":
                cur.execute("""UPDATE chat_conversas SET status = 'encerrada', encerrada_em = now(),
                                      encerrada_por = %s, atualizado_em = now() WHERE id = %s""",
                            (usuario_id, conversa_id))
            else:
                cur.execute("""UPDATE chat_conversas SET status = 'ativa', encerrada_em = NULL,
                                      encerrada_por = NULL, atualizado_em = now() WHERE id = %s""",
                            (conversa_id,))

    def _listagem_sql(self, filtro: str) -> str:
        return f"""
            SELECT c.id, c.chave, c.tipo, c.titulo, c.turma_id, c.status, c.criado_em, c.ultima_mensagem_em,
                   m.papel, m.ultima_leitura_em,
                   (SELECT count(*) FROM chat_mensagens x
                     WHERE x.conversa_id = c.id AND x.criado_em > COALESCE(m.ultima_leitura_em, '-infinity')
                       AND x.remetente_id IS DISTINCT FROM m.usuario_id)
                 + (SELECT count(*) FROM chat_mensagens_historico x
                     WHERE x.conversa_id = c.id AND x.criado_em > COALESCE(m.ultima_leitura_em, '-infinity')
                       AND x.remetente_id IS DISTINCT FROM m.usuario_id) AS nao_lidas,
                   (SELECT json_build_object('id', u.id, 'nome', {_NOME_USUARIO}, 'perfil', p.nome, 'foto_url', u.foto_url)
                      FROM chat_membros o JOIN usuarios u ON u.id = o.usuario_id
                      LEFT JOIN perfis p ON p.id = u.perfil_id
                     WHERE o.conversa_id = c.id AND o.usuario_id <> m.usuario_id
                     ORDER BY o.entrou_em LIMIT 1) AS outro,
                   (SELECT count(*) FROM chat_membros o WHERE o.conversa_id = c.id) AS total_membros,
                   ult.tipo AS ultima_tipo, ult.texto AS ultima_texto, ult.anexo_nome AS ultima_anexo_nome,
                   ult.remetente_id AS ultima_remetente_id
              FROM chat_membros m
              JOIN chat_conversas c ON c.id = m.conversa_id
              LEFT JOIN LATERAL (
                    SELECT tipo, texto, anexo_nome, remetente_id, criado_em FROM chat_mensagens WHERE conversa_id = c.id
                    UNION ALL
                    SELECT tipo, texto, anexo_nome, remetente_id, criado_em FROM chat_mensagens_historico WHERE conversa_id = c.id
                    ORDER BY criado_em DESC LIMIT 1
              ) ult ON true
             WHERE {filtro}
             ORDER BY COALESCE(c.ultima_mensagem_em, c.criado_em) DESC
        """

    def listar_conversas_usuario(self, usuario_id: str, *, tipo: Optional[str], limite: int,
                                 offset: int) -> List[Dict[str, Any]]:
        filtro = "m.usuario_id = %s AND m.oculta_em IS NULL"
        params: List[Any] = [usuario_id]
        if tipo:
            filtro += " AND c.tipo = %s"
            params.append(tipo)
        with get_db_cursor() as cur:
            cur.execute(self._listagem_sql(filtro) + " LIMIT %s OFFSET %s", (*params, limite, offset))
            return [_limpar(r) for r in cur.fetchall()]

    def conversa_do_usuario(self, conversa_id: str, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(self._listagem_sql("m.usuario_id = %s AND c.id = %s"), (usuario_id, conversa_id))
            return _limpar(cur.fetchone())

    def contar_nao_lidas(self, usuario_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT
                     (SELECT count(*) FROM chat_membros m JOIN chat_mensagens x ON x.conversa_id = m.conversa_id
                       WHERE m.usuario_id = %(u)s AND m.oculta_em IS NULL
                         AND x.criado_em > COALESCE(m.ultima_leitura_em, '-infinity')
                         AND x.remetente_id IS DISTINCT FROM m.usuario_id)
                   + (SELECT count(*) FROM chat_membros m JOIN chat_mensagens_historico x ON x.conversa_id = m.conversa_id
                       WHERE m.usuario_id = %(u)s AND m.oculta_em IS NULL
                         AND x.criado_em > COALESCE(m.ultima_leitura_em, '-infinity')
                         AND x.remetente_id IS DISTINCT FROM m.usuario_id) AS total""",
                {"u": usuario_id},
            )
            return int(cur.fetchone()["total"] or 0)

    def listar_todas(self, *, usuario_id: Optional[str], tipo: Optional[str], busca: Optional[str],
                     limite: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        """Visão do Admin: todas as conversas, com participantes."""
        filtros, params = ["true"], []
        if usuario_id and uuid_valido(usuario_id):
            filtros.append("EXISTS (SELECT 1 FROM chat_membros f WHERE f.conversa_id = c.id AND f.usuario_id = %s)")
            params.append(usuario_id)
        if tipo:
            filtros.append("c.tipo = %s")
            params.append(tipo)
        if busca:
            filtros.append(f"""(c.titulo ILIKE %s OR EXISTS (
                SELECT 1 FROM chat_membros f JOIN usuarios u ON u.id = f.usuario_id
                 WHERE f.conversa_id = c.id AND ({_NOME_USUARIO} ILIKE %s OR u.email ILIKE %s)))""")
            termo = f"%{busca.strip()}%"
            params += [termo, termo, termo]
        where = " AND ".join(filtros)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT count(*) AS n FROM chat_conversas c WHERE {where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"""SELECT c.id, c.chave, c.tipo, c.titulo, c.turma_id, c.status, c.criado_em, c.ultima_mensagem_em,
                           (SELECT json_agg(json_build_object('id', u.id, 'nome', {_NOME_USUARIO}, 'perfil', p.nome)
                                            ORDER BY {_NOME_USUARIO})
                              FROM chat_membros f JOIN usuarios u ON u.id = f.usuario_id
                              LEFT JOIN perfis p ON p.id = u.perfil_id
                             WHERE f.conversa_id = c.id) AS membros,
                           (SELECT count(*) FROM chat_mensagens x WHERE x.conversa_id = c.id)
                         + (SELECT count(*) FROM chat_mensagens_historico x WHERE x.conversa_id = c.id) AS total_mensagens
                      FROM chat_conversas c WHERE {where}
                     ORDER BY COALESCE(c.ultima_mensagem_em, c.criado_em) DESC LIMIT %s OFFSET %s""",
                (*params, limite, offset),
            )
            return total, [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Mensagens
    # ------------------------------------------------------------------
    def listar_mensagens(self, conversa_id: str, *, antes: Optional[datetime], depois: Optional[datetime],
                         limite: int) -> List[Dict[str, Any]]:
        """Mensagens em ordem cronológica. `antes` pagina para trás; `depois` traz as novas."""
        params: Dict[str, Any] = {"cid": conversa_id, "lim": limite}
        if depois is not None:
            filtro, ordem = "WHERE t.criado_em > %(ref)s", "ASC"
            params["ref"] = depois
        elif antes is not None:
            filtro, ordem = "WHERE t.criado_em < %(ref)s", "DESC"
            params["ref"] = antes
        else:
            filtro, ordem = "", "DESC"
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT t.*, {_NOME_USUARIO} AS remetente_nome
                      FROM {_UNIAO_MSG} t LEFT JOIN usuarios u ON u.id = t.remetente_id
                      {filtro} ORDER BY t.criado_em {ordem}, t.id {ordem} LIMIT %(lim)s""",
                params,
            )
            rows = [_limpar(r) for r in cur.fetchall()]
        return rows if ordem == "ASC" else list(reversed(rows))

    def todas_mensagens(self, conversa_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT t.*, {_NOME_USUARIO} AS remetente_nome
                      FROM {_UNIAO_MSG} t LEFT JOIN usuarios u ON u.id = t.remetente_id
                     ORDER BY t.criado_em, t.id""",
                {"cid": conversa_id},
            )
            return [_limpar(r) for r in cur.fetchall()]

    def get_mensagem(self, mensagem_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(mensagem_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT {_COLS_MSG} FROM chat_mensagens WHERE id = %(id)s
                    UNION ALL SELECT {_COLS_MSG} FROM chat_mensagens_historico WHERE id = %(id)s LIMIT 1""",
                {"id": mensagem_id},
            )
            return _limpar(cur.fetchone())

    def inserir_mensagem(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Grava a mensagem, atualiza a conversa e a leitura do remetente e reexibe a conversa para todos."""
        dados = {"ref_tipo": None, "ref_id": None, **dados}
        with get_db_cursor() as cur:
            cur.execute(
                f"""INSERT INTO chat_mensagens (conversa_id, remetente_id, tipo, texto, anexo_url, anexo_storage_key,
                                                anexo_nome, anexo_mime, anexo_tamanho, ref_tipo, ref_id)
                    VALUES (%(conversa_id)s, %(remetente_id)s, %(tipo)s, %(texto)s, %(anexo_url)s,
                            %(anexo_storage_key)s, %(anexo_nome)s, %(anexo_mime)s, %(anexo_tamanho)s,
                            %(ref_tipo)s, %(ref_id)s)
                    RETURNING {_COLS_MSG}""",
                dados,
            )
            msg = _limpar(cur.fetchone())
            cur.execute("UPDATE chat_conversas SET ultima_mensagem_em = %s, atualizado_em = now() WHERE id = %s",
                        (msg["criado_em"], dados["conversa_id"]))
            cur.execute("UPDATE chat_membros SET oculta_em = NULL WHERE conversa_id = %s AND oculta_em IS NOT NULL",
                        (dados["conversa_id"],))
            if dados.get("remetente_id"):
                cur.execute("""UPDATE chat_membros SET ultima_leitura_em = %s
                                WHERE conversa_id = %s AND usuario_id = %s""",
                            (msg["criado_em"], dados["conversa_id"], dados["remetente_id"]))
            return msg

    # ------------------------------------------------------------------
    # Exclusão definitiva e retenção
    # ------------------------------------------------------------------
    def excluir_conversa(self, conversa_id: str) -> List[str]:
        """Apaga conversa, membros e mensagens (cascata). Retorna as URLs/chaves dos anexos."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT COALESCE(anexo_url, anexo_storage_key) AS ref FROM chat_mensagens
                    WHERE conversa_id = %(c)s AND anexo_storage_key IS NOT NULL
                   UNION ALL
                   SELECT COALESCE(anexo_url, anexo_storage_key) FROM chat_mensagens_historico
                    WHERE conversa_id = %(c)s AND anexo_storage_key IS NOT NULL""",
                {"c": conversa_id},
            )
            refs = [r["ref"] for r in cur.fetchall() if r["ref"]]
            cur.execute("DELETE FROM chat_conversas WHERE id = %s", (conversa_id,))
            return refs

    def rotacionar(self) -> Dict[str, Any]:
        """Move mensagens com mais de 48h para o histórico e apaga do histórico o que passou de 90 dias."""
        with get_db_cursor() as cur:
            cur.execute(
                f"""WITH movidas AS (
                        DELETE FROM chat_mensagens
                         WHERE criado_em < now() - interval '{HORAS_TABELA_ATIVA} hours'
                     RETURNING {_COLS_MSG})
                    INSERT INTO chat_mensagens_historico ({_COLS_MSG})
                    SELECT {_COLS_MSG} FROM movidas
                    ON CONFLICT (id) DO NOTHING"""
            )
            movidas = cur.rowcount
            cur.execute(
                f"""DELETE FROM chat_mensagens_historico
                     WHERE criado_em < (current_date - {DIAS_HISTORICO})
                 RETURNING COALESCE(anexo_url, anexo_storage_key) AS ref, anexo_storage_key"""
            )
            removidas = cur.fetchall()
            refs = [r["ref"] for r in removidas if r["anexo_storage_key"] and r["ref"]]
            return {"movidas_para_historico": movidas, "removidas_do_historico": len(removidas), "anexos": refs}

    # ------------------------------------------------------------------
    # Turmas
    # ------------------------------------------------------------------
    def get_turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(turma_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("""SELECT t.id, t.nome, t.polo_id, t.escola_id, c.nome AS curso_nome
                             FROM turmas t LEFT JOIN cursos c ON c.id = t.curso_id WHERE t.id = %s""", (turma_id,))
            return _limpar(cur.fetchone())

    def turmas_disponiveis(self, *, perfil: str, usuario_id: str, polo_id: Optional[str], escola_id: Optional[str],
                           busca: Optional[str], limite: int) -> List[Dict[str, Any]]:
        """Turmas cujo grupo o usuário pode abrir."""
        if perfil == "admin":
            filtro, params = "true", []
        elif perfil == "polo" and polo_id:
            filtro, params = "t.polo_id = %s", [polo_id]
        elif perfil == "escola" and escola_id:
            filtro, params = "t.escola_id = %s", [escola_id]
        elif perfil == "professor":
            filtro = """EXISTS (SELECT 1 FROM professor_disciplinas pd JOIN professores pr ON pr.id = pd.professor_id
                                 WHERE pd.turma_id = t.id AND pd.ativo AND pr.usuario_id = %s)"""
            params = [usuario_id]
        elif perfil == "aluno":
            filtro = """EXISTS (SELECT 1 FROM turma_alunos ta JOIN alunos a ON a.id = ta.aluno_id
                                 WHERE ta.turma_id = t.id AND COALESCE(ta.status, 'ativo') = 'ativo'
                                   AND a.usuario_id = %s)"""
            params = [usuario_id]
        else:
            return []
        if busca:
            filtro += " AND (t.nome ILIKE %s OR c.nome ILIKE %s OR e.nome ILIKE %s)"
            termo = f"%{busca.strip()}%"
            params += [termo, termo, termo]
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT t.id, t.nome, c.nome AS curso_nome, e.nome AS escola_nome, po.nome AS polo_nome,
                           cc.id AS conversa_id
                      FROM turmas t
                      LEFT JOIN cursos c ON c.id = t.curso_id
                      LEFT JOIN escolas e ON e.id = t.escola_id
                      LEFT JOIN polos po ON po.id = t.polo_id
                      LEFT JOIN chat_conversas cc ON cc.chave = 'turma:' || t.id::text
                     WHERE {filtro}
                     ORDER BY t.data_inicio DESC NULLS LAST, t.nome LIMIT %s""",
                (*params, limite),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def participantes_turma(self, turma: Dict[str, Any]) -> Dict[str, List[str]]:
        """Usuários que pertencem ao grupo da turma: alunos ativos, professores com vínculo ativo
        e a secretaria da escola da turma."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT DISTINCT a.usuario_id FROM turma_alunos ta
                     JOIN alunos a ON a.id = ta.aluno_id
                     JOIN usuarios u ON u.id = a.usuario_id
                    WHERE ta.turma_id = %s AND COALESCE(ta.status, 'ativo') = 'ativo' AND u.status = 'ativo'""",
                (turma["id"],),
            )
            alunos = [str(r["usuario_id"]) for r in cur.fetchall()]
            cur.execute(
                """SELECT DISTINCT pr.usuario_id FROM professor_disciplinas pd
                     JOIN professores pr ON pr.id = pd.professor_id
                     JOIN usuarios u ON u.id = pr.usuario_id
                    WHERE pd.turma_id = %s AND pd.ativo AND u.status = 'ativo'""",
                (turma["id"],),
            )
            professores = [str(r["usuario_id"]) for r in cur.fetchall()]
            secretaria: List[str] = []
            if turma.get("escola_id"):
                cur.execute(
                    """SELECT u.id FROM usuarios u JOIN perfis p ON p.id = u.perfil_id
                        WHERE u.escola_id = %s AND u.status = 'ativo'
                          AND LOWER(p.nome) IN ('escola', 'secretario_escola')""",
                    (turma["escola_id"],),
                )
                secretaria = [str(r["id"]) for r in cur.fetchall()]
        return {"alunos": alunos, "professores": professores, "secretaria": secretaria}

    # ------------------------------------------------------------------
    # Auditoria
    # ------------------------------------------------------------------
    def auditar(self, *, usuario_id: Optional[str], acao: str, entidade_id: str,
                dados: Optional[Dict[str, Any]], ip: Optional[str]) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO logs_auditoria (usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip,
                                               criado_em, atualizado_em)
                   VALUES (%s, %s, 'chat_conversas', %s, NULL, %s, %s, now(), now())""",
                (usuario_id, acao, entidade_id, json.dumps(dados or {}, default=str), ip),
            )


_repo: Optional[PostgresChatRepository] = None


def get_chat_repository() -> PostgresChatRepository:
    global _repo
    if _repo is None:
        _repo = PostgresChatRepository()
    return _repo
