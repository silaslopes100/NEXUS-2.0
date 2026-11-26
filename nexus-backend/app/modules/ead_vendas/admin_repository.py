"""Persistência da Gestão de Matrículas EAD (admin): matrículas, compras/liberações e movimentações."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import get_db_cursor
from app.modules.ava.repository import _limpar, uuid_valido

# Compra paga pelo aluno (loja/legado), sem contar as liberações manuais.
_PAGA = """(c.origem NOT IN ('manual', 'bolsa')
            AND (c.liberada_em IS NOT NULL
                 OR lower(COALESCE(c.status_pagamento, '')) IN ('pago', 'paga', 'aprovado', 'confirmado', 'paid', 'received')))"""
_CANCELADA = "lower(COALESCE(c.status_pagamento, '')) IN ('cancelado', 'cancelada')"

_SELECT_MATRICULA = f"""
    SELECT m.id, m.aluno_id, m.curso_id, cu.nome AS curso_nome, t.id AS turma_id, t.nome AS turma_nome,
           m.tipo, m.origem, m.status, m.data_matricula, m.observacao,
           TRIM(CONCAT(u.nome, ' ', u.sobrenome)) AS nome, u.email, u.cpf, a.numero_matricula,
           (a.status = 'desistente') AS aluno_desistente,
           COALESCE(cp.pagas, 0) AS disciplinas_pagas, COALESCE(cp.liberadas, 0) AS disciplinas_liberadas,
           COALESCE(cp.pendentes, 0) AS disciplinas_pendentes,
           GREATEST(m.data_matricula, m.cancelada_em, cp.ultimo) AS ultimo_movimento,
           COUNT(*) OVER () AS total_geral
      FROM matriculas_ead m
      JOIN alunos a ON a.id = m.aluno_id
      JOIN usuarios u ON u.id = a.usuario_id
      LEFT JOIN cursos cu ON cu.id = m.curso_id
      LEFT JOIN LATERAL (
          SELECT tt.id, tt.nome FROM turmas tt WHERE tt.id = m.turma_id
          UNION ALL
          SELECT tt.id, tt.nome FROM turma_alunos ta JOIN turmas tt ON tt.id = ta.turma_id
           WHERE m.turma_id IS NULL AND ta.aluno_id = m.aluno_id AND tt.curso_id = m.curso_id AND tt.modalidade = 'ead'
          LIMIT 1
      ) t ON true
      LEFT JOIN LATERAL (
          SELECT COUNT(*) FILTER (WHERE {_PAGA}) AS pagas,
                 COUNT(*) FILTER (WHERE c.origem IN ('manual', 'bolsa') AND NOT {_CANCELADA}) AS liberadas,
                 COUNT(*) FILTER (WHERE c.status_pagamento = 'pendente') AS pendentes,
                 MAX(GREATEST(c.criado_em, c.liberada_em, c.cancelada_em)) AS ultimo
            FROM compras_disciplina_ead c JOIN disciplinas d ON d.id = c.disciplina_id
           WHERE c.aluno_id = m.aluno_id AND d.curso_id = m.curso_id
      ) cp ON true
"""

# Linha do tempo única de tudo o que acontece no EAD.
_EVENTOS = f"""
    WITH ev AS (
        SELECT (CASE m.origem WHEN 'manual' THEN 'matricula_manual' WHEN 'site' THEN 'matricula_site'
                              ELSE 'matricula' END)::text AS evento,
               m.data_matricula AS data, m.aluno_id::uuid AS aluno_id, m.turma_id::uuid AS turma_id,
               NULL::uuid AS disciplina_id, NULL::numeric AS valor,
               (CASE WHEN m.tipo = 'bolsista' THEN 'Bolsista' END)::text AS detalhe,
               NULL::uuid AS pedido_id, m.criado_por::uuid AS autor_id
          FROM matriculas_ead m
        UNION ALL
        SELECT 'matricula_cancelada', m.cancelada_em, m.aluno_id, m.turma_id, NULL, NULL, m.motivo_cancelamento,
               NULL, m.cancelada_por
          FROM matriculas_ead m WHERE m.cancelada_em IS NOT NULL
        UNION ALL
        SELECT 'compra_criada', c.criado_em, c.aluno_id, c.turma_id, c.disciplina_id, p.valor_total,
               CASE WHEN c.com_livro THEN 'Com livro físico' END, c.pedido_id, NULL
          FROM compras_disciplina_ead c LEFT JOIN pedidos p ON p.id = c.pedido_id WHERE c.origem = 'loja'
        UNION ALL
        SELECT 'pagamento_confirmado', c.liberada_em, c.aluno_id, c.turma_id, c.disciplina_id, c.valor_pago,
               CASE WHEN c.com_livro THEN 'Com livro físico' END, c.pedido_id, NULL
          FROM compras_disciplina_ead c WHERE c.origem <> 'manual' AND c.origem <> 'bolsa' AND c.liberada_em IS NOT NULL
        UNION ALL
        SELECT 'liberacao_manual', COALESCE(c.liberada_em, c.criado_em), c.aluno_id, c.turma_id, c.disciplina_id, 0,
               CONCAT_WS(' — ', c.motivo, c.motivo_texto), NULL, c.liberada_por
          FROM compras_disciplina_ead c WHERE c.origem IN ('manual', 'bolsa')
        UNION ALL
        SELECT 'compra_cancelada', COALESCE(c.cancelada_em, c.atualizado_em), c.aluno_id, c.turma_id, c.disciplina_id,
               NULL, NULL, c.pedido_id, c.cancelada_por
          FROM compras_disciplina_ead c
         WHERE {_CANCELADA} AND c.cancelada_por IS NULL  -- revogação/cancelamento pelo admin já tem evento próprio
        UNION ALL
        SELECT 'livro_enviado', e.criado_em, p.aluno_id, c.turma_id, c.disciplina_id, NULL,
               CONCAT_WS(' ', e.transportadora, e.codigo_rastreio), p.id, NULL
          FROM envios e JOIN pedidos p ON p.id = e.pedido_id AND p.tipo = 'ead_livro'
          LEFT JOIN compras_disciplina_ead c ON c.pedido_id = p.id
        UNION ALL
        SELECT l.acao, l.criado_em,
               CASE WHEN l.entidade_id ~* '^[0-9a-f-]{{36}}$' THEN l.entidade_id::uuid END,
               NULLIF(l.dados_depois->>'turma_id', '')::uuid, NULL, NULL, l.dados_depois->>'detalhe', NULL, l.usuario_id
          FROM logs_auditoria l
         WHERE l.acao IN ('ead_tipo_alterado', 'ead_transferencia', 'ead_matricula_reativada', 'ead_compra_revogada')
    )
    SELECT ev.evento, ev.data, ev.aluno_id, ev.pedido_id, ev.valor, ev.detalhe,
           TRIM(CONCAT(u.nome, ' ', u.sobrenome)) AS aluno_nome, a.numero_matricula,
           t.nome AS turma_nome, d.nome AS disciplina_nome, TRIM(CONCAT(au.nome, ' ', au.sobrenome)) AS autor_nome,
           COUNT(*) OVER () AS total_geral
      FROM ev
      LEFT JOIN alunos a ON a.id = ev.aluno_id
      LEFT JOIN usuarios u ON u.id = a.usuario_id
      LEFT JOIN turmas t ON t.id = ev.turma_id
      LEFT JOIN disciplinas d ON d.id = ev.disciplina_id
      LEFT JOIN usuarios au ON au.id = ev.autor_id
"""


def _total(linhas: List[Dict[str, Any]]) -> int:
    return int(linhas[0]["total_geral"]) if linhas else 0


class PostgresGestaoEadRepository:
    # ------------------------------------------------------------------ leitura

    def resumo(self, inicio: Optional[Any], fim: Optional[Any]) -> Dict[str, Any]:
        p = {"i": inicio, "f": fim}
        periodo = "(%(i)s::date IS NULL OR {c} >= %(i)s::date) AND (%(f)s::date IS NULL OR {c} < %(f)s::date + 1)"
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT COUNT(*) FILTER (WHERE m.status = 'ativa') AS matriculas_ativas,
                           COUNT(*) FILTER (WHERE m.status = 'ativa' AND m.tipo = 'bolsista') AS bolsistas,
                           COUNT(*) FILTER (WHERE m.status = 'cancelada') AS canceladas,
                           COUNT(*) FILTER (WHERE m.origem = 'site' AND {periodo.format(c='m.data_matricula')}) AS novas_site,
                           COUNT(*) FILTER (WHERE m.origem = 'manual' AND {periodo.format(c='m.data_matricula')}) AS novas_manuais
                      FROM matriculas_ead m JOIN alunos a ON a.id = m.aluno_id AND a.modalidade = 'ead'""",
                p,
            )
            r = dict(cur.fetchone())
            cur.execute(
                f"""SELECT COUNT(*) FILTER (WHERE {_PAGA} AND {periodo.format(c='COALESCE(c.liberada_em, c.criado_em)')}) AS compras_pagas,
                           COUNT(*) FILTER (WHERE c.status_pagamento = 'pendente') AS compras_pendentes,
                           COUNT(*) FILTER (WHERE c.origem IN ('manual', 'bolsa') AND NOT {_CANCELADA}
                                              AND {periodo.format(c='COALESCE(c.liberada_em, c.criado_em)')}) AS liberacoes_manuais
                      FROM compras_disciplina_ead c""",
                p,
            )
            r.update(dict(cur.fetchone()))
            cur.execute(
                f"""SELECT COALESCE(SUM(p.valor_total), 0) AS receita,
                           COUNT(*) FILTER (WHERE p.tipo = 'ead_livro') AS vendas_com_livro
                      FROM pedidos p
                     WHERE p.tipo IN ('ead', 'ead_livro') AND p.pago_em IS NOT NULL AND p.status <> 'cancelado'
                       AND {periodo.format(c='p.pago_em')}""",
                p,
            )
            r.update(_limpar(cur.fetchone()))
        return r

    def turmas_ead(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT t.id, t.nome, t.codigo, t.curso_id, cu.nome AS curso_nome,
                          (t.cancelada_em IS NULL AND t.concluida_em IS NULL) AS aberta
                     FROM turmas t JOIN cursos cu ON cu.id = t.curso_id
                    WHERE t.modalidade = 'ead'
                    ORDER BY (t.cancelada_em IS NULL AND t.concluida_em IS NULL) DESC, t.data_inicio DESC NULLS LAST, t.nome"""
            )
            return [_limpar(r) for r in cur.fetchall()]

    def listar_matriculas(self, f: Dict[str, Any], limite: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        conds, p = ["a.modalidade = 'ead'"], {}
        if f.get("busca"):
            conds.append("""(u.nome ILIKE %(q)s OR u.sobrenome ILIKE %(q)s OR CONCAT(u.nome, ' ', u.sobrenome) ILIKE %(q)s
                             OR u.email ILIKE %(q)s OR a.numero_matricula ILIKE %(q)s
                             OR regexp_replace(COALESCE(u.cpf, ''), '[^0-9]', '', 'g') LIKE %(qd)s)""")
            p["q"] = f"%{f['busca'].strip()}%"
            p["qd"] = f"%{''.join(ch for ch in f['busca'] if ch.isdigit()) or '#'}%"
        for chave, coluna in (("tipo", "m.tipo"), ("origem", "m.origem"), ("status", "m.status")):
            if f.get(chave):
                conds.append(f"{coluna} = %({chave})s")
                p[chave] = f[chave]
        if f.get("turma_id") and uuid_valido(f["turma_id"]):
            conds.append("t.id = %(turma)s")
            p["turma"] = f["turma_id"]
        if f.get("aluno_id"):
            conds.append("m.aluno_id = %(aluno)s")
            p["aluno"] = f["aluno_id"]
        if f.get("id"):
            conds.append("m.id = %(id)s")
            p["id"] = f["id"]
        if f.get("data_inicio"):
            conds.append("m.data_matricula >= %(di)s::date")
            p["di"] = f["data_inicio"]
        if f.get("data_fim"):
            conds.append("m.data_matricula < %(df)s::date + 1")
            p["df"] = f["data_fim"]
        sql = (f"{_SELECT_MATRICULA} WHERE {' AND '.join(conds)} "
               "ORDER BY m.data_matricula DESC NULLS LAST, m.id LIMIT %(lim)s OFFSET %(off)s")
        with get_db_cursor() as cur:
            cur.execute(sql, {**p, "lim": limite, "off": offset})
            linhas = [_limpar(r) for r in cur.fetchall()]
        return _total(linhas), linhas

    def matricula(self, matricula_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(matricula_id):
            return None
        _, linhas = self.listar_matriculas({"id": matricula_id}, 1, 0)
        return linhas[0] if linhas else None

    def matricula_ativa_no_curso(self, aluno_id: str, curso_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id FROM matriculas_ead WHERE aluno_id = %s AND curso_id = %s AND status = 'ativa' LIMIT 1",
                        (aluno_id, curso_id))
            return _limpar(cur.fetchone())

    def turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(turma_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("""SELECT id, nome, curso_id, modalidade, (cancelada_em IS NULL AND concluida_em IS NULL) AS aberta
                             FROM turmas WHERE id = %s""", (turma_id,))
            return _limpar(cur.fetchone())

    def aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(aluno_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT a.id AS aluno_id, u.id AS usuario_id, TRIM(CONCAT(u.nome, ' ', u.sobrenome)) AS nome, u.email,
                          u.cpf, COALESCE(NULLIF(u.celular, ''), u.telefone) AS celular, a.numero_matricula,
                          a.status AS status_aluno, a.modalidade
                     FROM alunos a JOIN usuarios u ON u.id = a.usuario_id WHERE a.id = %s""",
                (aluno_id,),
            )
            return _limpar(cur.fetchone())

    def buscar_alunos(self, q: str) -> List[Dict[str, Any]]:
        digitos = "".join(ch for ch in q if ch.isdigit())
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT a.id AS aluno_id, TRIM(CONCAT(u.nome, ' ', u.sobrenome)) AS nome, u.email, u.cpf, a.numero_matricula
                     FROM alunos a JOIN usuarios u ON u.id = a.usuario_id
                    WHERE a.modalidade = 'ead'
                      AND (CONCAT(u.nome, ' ', u.sobrenome) ILIKE %(q)s OR u.email ILIKE %(q)s OR a.numero_matricula ILIKE %(q)s
                           OR (%(d)s <> '' AND regexp_replace(COALESCE(u.cpf, ''), '[^0-9]', '', 'g') LIKE %(dl)s))
                    ORDER BY u.nome LIMIT 20""",
                {"q": f"%{q.strip()}%", "d": digitos, "dl": f"%{digitos}%"},
            )
            return [_limpar(r) for r in cur.fetchall()]

    def compras(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT c.id, c.disciplina_id, d.nome AS disciplina_nome, t.nome AS turma_nome, c.origem,
                          c.status_pagamento, c.valor_pago, COALESCE(c.com_livro, false) AS com_livro, c.liberada_em,
                          c.motivo, c.motivo_texto, TRIM(CONCAT(lu.nome, ' ', lu.sobrenome)) AS liberada_por_nome,
                          c.pedido_id, p.numero AS pedido_numero, c.criado_em, c.cancelada_em
                     FROM compras_disciplina_ead c
                     LEFT JOIN disciplinas d ON d.id = c.disciplina_id
                     LEFT JOIN turmas t ON t.id = c.turma_id
                     LEFT JOIN usuarios lu ON lu.id = c.liberada_por
                     LEFT JOIN pedidos p ON p.id = c.pedido_id
                    WHERE c.aluno_id = %s
                    ORDER BY c.criado_em DESC NULLS LAST""",
                (aluno_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def compra(self, compra_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(compra_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM compras_disciplina_ead WHERE id = %s", (compra_id,))
            return _limpar(cur.fetchone())

    def curso_da_disciplina(self, disciplina_id: str) -> Optional[str]:
        if not uuid_valido(disciplina_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT curso_id FROM disciplinas WHERE id = %s", (disciplina_id,))
            r = cur.fetchone()
            return str(r["curso_id"]) if r and r["curso_id"] else None

    def movimentacoes(self, f: Dict[str, Any], limite: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        conds, p = ["ev.data IS NOT NULL"], {}
        if f.get("aluno_id"):
            conds.append("ev.aluno_id = %(aluno)s::uuid")
            p["aluno"] = f["aluno_id"]
        if f.get("evento"):
            conds.append("ev.evento = %(evento)s")
            p["evento"] = f["evento"]
        if f.get("turma_id") and uuid_valido(f["turma_id"]):
            conds.append("ev.turma_id = %(turma)s::uuid")
            p["turma"] = f["turma_id"]
        if f.get("busca"):
            conds.append("(CONCAT(u.nome, ' ', u.sobrenome) ILIKE %(q)s OR a.numero_matricula ILIKE %(q)s OR d.nome ILIKE %(q)s)")
            p["q"] = f"%{f['busca'].strip()}%"
        if f.get("data_inicio"):
            conds.append("ev.data >= %(di)s::date")
            p["di"] = f["data_inicio"]
        if f.get("data_fim"):
            conds.append("ev.data < %(df)s::date + 1")
            p["df"] = f["data_fim"]
        sql = f"{_EVENTOS} WHERE {' AND '.join(conds)} ORDER BY ev.data DESC LIMIT %(lim)s OFFSET %(off)s"
        with get_db_cursor() as cur:
            cur.execute(sql, {**p, "lim": limite, "off": offset})
            linhas = [_limpar(r) for r in cur.fetchall()]
        return _total(linhas), linhas

    # ------------------------------------------------------------------ escrita

    def atualizar_matricula(self, matricula_id: str, campos: Dict[str, Any]) -> None:
        if not campos:
            return
        sets = ", ".join(f"{k} = %({k})s" for k in campos)
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE matriculas_ead SET {sets}, atualizado_em = now() WHERE id = %(id)s", {**campos, "id": matricula_id})

    def transferir(self, matricula: Dict[str, Any], nova_turma_id: str) -> None:
        aluno_id = matricula["aluno_id"]
        with get_db_cursor() as cur:
            if matricula.get("turma_id"):
                cur.execute("""UPDATE turma_alunos SET status = 'inativo', atualizado_em = now()
                                WHERE turma_id = %s AND aluno_id = %s""", (matricula["turma_id"], aluno_id))
            cur.execute("SELECT 1 FROM turma_alunos WHERE turma_id = %s AND aluno_id = %s", (nova_turma_id, aluno_id))
            if cur.fetchone():
                cur.execute("""UPDATE turma_alunos SET status = 'ativo', data_matricula = now(), atualizado_em = now()
                                WHERE turma_id = %s AND aluno_id = %s""", (nova_turma_id, aluno_id))
            else:
                cur.execute("""INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em)
                               VALUES (%s, %s, %s, now(), 'ativo', now(), now())""", (str(uuid.uuid4()), nova_turma_id, aluno_id))
            cur.execute("UPDATE matriculas_ead SET turma_id = %s, atualizado_em = now() WHERE id = %s",
                        (nova_turma_id, matricula["id"]))

    def cancelar_matricula(self, matricula: Dict[str, Any], motivo: str, usuario_id: str) -> List[str]:
        """Cancela a matrícula, tira o aluno das Turmas EAD do curso e devolve os pedidos pendentes a cancelar."""
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE matriculas_ead SET status = 'cancelada', cancelada_em = now(), cancelada_por = %s,
                          motivo_cancelamento = %s, atualizado_em = now() WHERE id = %s""",
                (usuario_id, motivo, matricula["id"]),
            )
            cur.execute(
                """UPDATE turma_alunos ta SET status = 'inativo', atualizado_em = now()
                     FROM turmas t WHERE t.id = ta.turma_id AND ta.aluno_id = %s AND t.curso_id = %s AND t.modalidade = 'ead'""",
                (matricula["aluno_id"], matricula["curso_id"]),
            )
            cur.execute(
                """UPDATE compras_disciplina_ead c SET status_pagamento = 'cancelado', cancelada_em = now(),
                          cancelada_por = %s, atualizado_em = now()
                     FROM disciplinas d
                    WHERE d.id = c.disciplina_id AND c.aluno_id = %s AND d.curso_id = %s AND c.status_pagamento = 'pendente'
                RETURNING c.pedido_id""",
                (usuario_id, matricula["aluno_id"], matricula["curso_id"]),
            )
            return [str(r["pedido_id"]) for r in cur.fetchall() if r["pedido_id"]]

    def reativar_matricula(self, matricula: Dict[str, Any]) -> None:
        with get_db_cursor() as cur:
            cur.execute("""UPDATE matriculas_ead SET status = 'ativa', cancelada_em = NULL, cancelada_por = NULL,
                                  motivo_cancelamento = NULL, atualizado_em = now() WHERE id = %s""", (matricula["id"],))
            if matricula.get("turma_id"):
                cur.execute("SELECT 1 FROM turma_alunos WHERE turma_id = %s AND aluno_id = %s",
                            (matricula["turma_id"], matricula["aluno_id"]))
                if cur.fetchone():
                    cur.execute("""UPDATE turma_alunos SET status = 'ativo', atualizado_em = now()
                                    WHERE turma_id = %s AND aluno_id = %s""", (matricula["turma_id"], matricula["aluno_id"]))
                else:
                    cur.execute("""INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em)
                                   VALUES (%s, %s, %s, now(), 'ativo', now(), now())""",
                                (str(uuid.uuid4()), matricula["turma_id"], matricula["aluno_id"]))

    def liberar(self, dados: Dict[str, Any]) -> str:
        compra_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO compras_disciplina_ead (id, aluno_id, disciplina_id, valor_pago, status_pagamento, liberada_em,
                                                      turma_id, com_livro, reprovado_por_prazo, origem, liberada_por, motivo,
                                                      motivo_texto, criado_em, atualizado_em)
                   VALUES (%s, %s, %s, 0, 'liberado', now(), %s, false, false, %s, %s, %s, %s, now(), now())""",
                (compra_id, dados["aluno_id"], dados["disciplina_id"], dados.get("turma_id"),
                 "bolsa" if dados["motivo"] == "bolsa" else "manual", dados["usuario_id"], dados["motivo"], dados.get("texto")),
            )
        return compra_id

    def revogar(self, compra_id: str, usuario_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("""UPDATE compras_disciplina_ead SET status_pagamento = 'cancelado', cancelada_em = now(),
                                  cancelada_por = %s, atualizado_em = now() WHERE id = %s""", (usuario_id, compra_id))


_repo: Optional[PostgresGestaoEadRepository] = None


def get_gestao_ead_repository() -> PostgresGestaoEadRepository:
    global _repo
    if _repo is None:
        _repo = PostgresGestaoEadRepository()
    return _repo
