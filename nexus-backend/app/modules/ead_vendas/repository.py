"""Persistência das vendas EAD (vitrine, inscrição, compras e pedidos do aluno)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.core.database import get_db_cursor
from app.modules.ava.repository import VALOR_EAD_PADRAO, VALOR_LIVRO_EAD_PADRAO, _limpar, uuid_valido


class TurmaLotada(Exception):
    pass


class JaInscrito(Exception):
    pass


# Turmas EAD abertas (não canceladas nem concluídas) de cursos ativos.
_SELECT_TURMA = """
    SELECT t.id, t.nome, t.codigo, t.data_inicio, t.data_fim, t.vagas, t.turno,
           cu.id AS curso_id, cu.nome AS curso_nome, cu.descricao AS curso_descricao,
           cu.nivel_academico, cu.carga_horaria_total, cu.semestres,
           (SELECT COUNT(*) FROM turma_alunos ta
             WHERE ta.turma_id = t.id AND COALESCE(ta.status, 'ativo') = 'ativo') AS total_alunos,
           (SELECT COUNT(*) FROM disciplinas d
             WHERE d.curso_id = cu.id AND COALESCE(d.ativo, true)
               AND NOT COALESCE(d.eh_extra_grade, false)) AS total_disciplinas,
           (SELECT MIN(COALESCE(cfg.valor_ead, %(valor_padrao)s)) FROM disciplinas d
              LEFT JOIN ava_disciplina_config cfg ON cfg.disciplina_id = d.id
             WHERE d.curso_id = cu.id AND COALESCE(d.ativo, true)
               AND NOT COALESCE(d.eh_extra_grade, false)) AS valor_minimo
      FROM turmas t
      JOIN cursos cu ON cu.id = t.curso_id
     WHERE t.modalidade = 'ead' AND t.cancelada_em IS NULL AND t.concluida_em IS NULL
       AND COALESCE(cu.status, 'ativo') = 'ativo'
"""


class PostgresVendasEadRepository:
    # ------------------------------------------------------------------ vitrine

    def turmas_abertas(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_TURMA + " ORDER BY t.data_inicio NULLS LAST, t.nome",
                        {"valor_padrao": VALOR_EAD_PADRAO})
            return [_limpar(r) for r in cur.fetchall()]

    def turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(turma_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(_SELECT_TURMA + " AND t.id = %(t)s", {"valor_padrao": VALOR_EAD_PADRAO, "t": turma_id})
            return _limpar(cur.fetchone())

    def disciplinas_venda(self, curso_id: str) -> List[Dict[str, Any]]:
        """Disciplinas da grade com o preço EAD, o upsell do livro e se o conteúdo está publicado."""
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.nome, d.semestre, d.ordem, COALESCE(d.carga_horaria, 0) AS carga_horaria,
                       d.ead_prazo_dias, cfg.capa_url, cfg.descricao_ava,
                       COALESCE(cfg.publicado, false) AS publicado,
                       COALESCE(cfg.valor_ead, %(v)s) AS valor_ead,
                       COALESCE(cfg.livro_disponivel, false) AS livro_disponivel,
                       COALESCE(cfg.valor_livro_ead, %(l)s) AS valor_livro_ead,
                       (SELECT COUNT(*) FROM ava_aulas a JOIN ava_capitulos cap ON cap.id = a.capitulo_id
                         WHERE cap.disciplina_id = d.id AND cap.publicado AND a.publicado) AS total_aulas
                  FROM disciplinas d
                  LEFT JOIN ava_disciplina_config cfg ON cfg.disciplina_id = d.id
                 WHERE d.curso_id = %(c)s AND COALESCE(d.ativo, true) AND NOT COALESCE(d.eh_extra_grade, false)
                 ORDER BY d.semestre NULLS LAST, d.ordem, d.nome, d.id
                """,
                {"c": curso_id, "v": VALOR_EAD_PADRAO, "l": VALOR_LIVRO_EAD_PADRAO},
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ inscrição

    def email_em_uso(self, email: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 FROM usuarios WHERE lower(email) = lower(%s) LIMIT 1", (email.strip(),))
            return cur.fetchone() is not None

    def cpf_em_uso(self, cpf: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 FROM usuarios WHERE regexp_replace(COALESCE(cpf, ''), '[^0-9]', '', 'g') = %s LIMIT 1",
                        (cpf,))
            return cur.fetchone() is not None

    def perfil_aluno_id(self) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id FROM perfis WHERE lower(nome) = 'aluno' LIMIT 1")
            row = cur.fetchone()
            return str(row["id"]) if row else None

    def inscricoes_recentes_do_ip(self, ip: str, minutos: int) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS n FROM logs_auditoria
                    WHERE acao = 'inscricao_ead' AND host(ip::inet) = %s AND criado_em > now() - make_interval(mins => %s)""",
                (ip, minutos),
            )
            return int(cur.fetchone()["n"] or 0)

    @staticmethod
    def _vincular_turma(cur, aluno_id: str, turma_id: str) -> None:
        """Matrícula no curso (matriculas_ead) + vaga na turma, conferindo as vagas com a turma travada."""
        cur.execute(
            """SELECT t.id, t.curso_id, t.vagas FROM turmas t
                WHERE t.id = %s AND t.modalidade = 'ead' AND t.cancelada_em IS NULL AND t.concluida_em IS NULL
                FOR UPDATE""",
            (turma_id,),
        )
        turma = cur.fetchone()
        if not turma:
            raise LookupError("Turma EAD não encontrada ou encerrada.")
        cur.execute("SELECT status FROM turma_alunos WHERE turma_id = %s AND aluno_id = %s", (turma_id, aluno_id))
        vinculo = cur.fetchone()
        if vinculo and (vinculo["status"] or "ativo") == "ativo":
            raise JaInscrito()
        if turma["vagas"]:
            cur.execute("SELECT COUNT(*) AS n FROM turma_alunos WHERE turma_id = %s AND COALESCE(status, 'ativo') = 'ativo'",
                        (turma_id,))
            if int(cur.fetchone()["n"]) >= int(turma["vagas"]):
                raise TurmaLotada()
        if vinculo:
            cur.execute("""UPDATE turma_alunos SET status = 'ativo', data_matricula = now(), atualizado_em = now()
                            WHERE turma_id = %s AND aluno_id = %s""", (turma_id, aluno_id))
        else:
            cur.execute(
                """INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em)
                   VALUES (%s, %s, %s, now(), 'ativo', now(), now())""",
                (str(uuid.uuid4()), turma_id, aluno_id),
            )
        cur.execute("SELECT 1 FROM matriculas_ead WHERE aluno_id = %s AND curso_id = %s", (aluno_id, turma["curso_id"]))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO matriculas_ead (id, aluno_id, curso_id, ativa_automaticamente, data_matricula,
                                                criado_em, atualizado_em)
                   VALUES (%s, %s, %s, true, now(), now(), now())""",
                (str(uuid.uuid4()), aluno_id, turma["curso_id"]),
            )

    def criar_aluno_inscrito(self, dados: Dict[str, Any], turma_id: str) -> Dict[str, str]:
        """Cria usuário + aluno EAD (sem Polo) e já o matricula na turma, numa transação."""
        usuario_id, aluno_id = str(uuid.uuid4()), str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO usuarios (id, nome, sobrenome, email, cpf, celular, data_nascimento, senha_hash,
                                         senha_algoritmo, perfil_id, status, criado_em, atualizado_em)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'argon2id', %s, 'ativo', now(), now())""",
                (usuario_id, dados["nome"], dados["sobrenome"], dados["email"], dados["cpf"], dados["celular"],
                 dados["data_nascimento"], dados["senha_hash"], dados["perfil_id"]),
            )
            cur.execute(
                """INSERT INTO alunos (id, usuario_id, polo_id, escola_id, modalidade, numero_matricula, data_nascimento,
                                       status, ultima_movimentacao_em, criado_em, atualizado_em)
                   VALUES (%s, %s, NULL, NULL, 'ead',
                           'NX-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('seq_matricula_aluno')::text, 7, '0'),
                           %s, 'ativo', now(), now(), now())""",
                (aluno_id, usuario_id, dados["data_nascimento"]),
            )
            self._vincular_turma(cur, aluno_id, turma_id)
        return {"usuario_id": usuario_id, "aluno_id": aluno_id}

    def inscrever_aluno(self, aluno_id: str, turma_id: str) -> None:
        with get_db_cursor() as cur:
            self._vincular_turma(cur, aluno_id, turma_id)

    # ------------------------------------------------------------------ loja

    def turmas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT t.id, t.nome, t.codigo, t.data_inicio, t.data_fim, t.curso_id, cu.nome AS curso_nome,
                          ta.data_matricula
                     FROM turma_alunos ta
                     JOIN turmas t ON t.id = ta.turma_id
                     JOIN cursos cu ON cu.id = t.curso_id
                    WHERE ta.aluno_id = %s AND COALESCE(ta.status, 'ativo') = 'ativo'
                      AND t.modalidade = 'ead' AND t.cancelada_em IS NULL AND t.concluida_em IS NULL
                    ORDER BY t.data_inicio NULLS LAST, t.nome""",
                (aluno_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def compras_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        """Compras (não canceladas), da mais recente para a mais antiga, com o pedido e a cobrança pendente."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT c.id, c.disciplina_id, c.status_pagamento, c.liberada_em, c.prazo_conclusao,
                          COALESCE(c.reprovado_por_prazo, false) AS reprovado_por_prazo, c.pedido_id, c.com_livro,
                          c.criado_em, p.status AS pedido_status, p.numero AS pedido_numero,
                          pg.id AS pagamento_id, pg.status AS pagamento_status, pg.vencimento_em AS pagamento_vencimento
                     FROM compras_disciplina_ead c
                     LEFT JOIN pedidos p ON p.id = c.pedido_id
                     LEFT JOIN LATERAL (
                         SELECT x.id, x.status, x.vencimento_em FROM pagamentos x
                          WHERE x.pedido_id = c.pedido_id ORDER BY x.criado_em DESC LIMIT 1
                     ) pg ON true
                    WHERE c.aluno_id = %s AND COALESCE(c.status_pagamento, '') NOT IN ('cancelado', 'cancelada')
                    ORDER BY (c.liberada_em IS NOT NULL) DESC, c.liberada_em DESC NULLS LAST, c.criado_em DESC NULLS LAST""",
                (aluno_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def disciplina_do_curso(self, disciplina_id: str, curso_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(disciplina_id):
            return None
        for d in self.disciplinas_venda(curso_id):
            if d["id"] == disciplina_id:
                return d
        return None

    def dados_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT a.id AS aluno_id, u.id AS usuario_id, u.nome, u.sobrenome, u.email, u.cpf,
                          COALESCE(NULLIF(u.celular, ''), u.telefone) AS telefone,
                          u.cep, u.logradouro, u.numero, u.complemento, u.bairro, u.cidade, u.uf
                     FROM alunos a JOIN usuarios u ON u.id = a.usuario_id WHERE a.id = %s""",
                (aluno_id,),
            )
            return _limpar(cur.fetchone())

    def salvar_endereco(self, usuario_id: str, endereco: Dict[str, Any]) -> None:
        campos = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE usuarios SET {', '.join(f'{c} = %s' for c in campos)}, atualizado_em = now() WHERE id = %s",
                (*[endereco.get(c) for c in campos], usuario_id),
            )

    def cancelar_compras_abertas(self, aluno_id: str, disciplina_id: str) -> List[str]:
        """Encerra compras pendentes antigas (cobrança vencida/cancelada); devolve os pedidos para cancelar."""
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE compras_disciplina_ead SET status_pagamento = 'cancelado', atualizado_em = now()
                    WHERE aluno_id = %s AND disciplina_id = %s AND status_pagamento = 'pendente'
                RETURNING pedido_id""",
                (aluno_id, disciplina_id),
            )
            return [str(r["pedido_id"]) for r in cur.fetchall() if r["pedido_id"]]

    def criar_compra(self, dados: Dict[str, Any]) -> str:
        compra_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO compras_disciplina_ead (id, aluno_id, disciplina_id, valor_pago, status_pagamento,
                                                      pedido_id, turma_id, com_livro, reprovado_por_prazo,
                                                      criado_em, atualizado_em)
                   VALUES (%s, %s, %s, %s, 'pendente', %s, %s, %s, false, now(), now())""",
                (compra_id, dados["aluno_id"], dados["disciplina_id"], dados["valor"], dados["pedido_id"],
                 dados.get("turma_id"), dados["com_livro"]),
            )
        return compra_id

    def cancelar_compra_do_pedido(self, pedido_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("""UPDATE compras_disciplina_ead SET status_pagamento = 'cancelado', atualizado_em = now()
                            WHERE pedido_id = %s AND status_pagamento = 'pendente'""", (pedido_id,))

    def liberar_compra_do_pedido(self, pedido_id: str, pagamento_id: Optional[str], valor: Optional[float]) -> int:
        """Pagamento confirmado: a compra vira paga e a disciplina abre no AVA. Idempotente."""
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE compras_disciplina_ead
                      SET status_pagamento = 'pago', valor_pago = COALESCE(%s, valor_pago),
                          liberada_em = COALESCE(liberada_em, now()), reprovado_por_prazo = false, atualizado_em = now()
                    WHERE pedido_id = %s AND COALESCE(status_pagamento, '') <> 'pago'
                RETURNING id""",
                (valor, pedido_id),
            )
            ids = [str(r["id"]) for r in cur.fetchall()]
            if ids and pagamento_id:
                cur.execute("UPDATE pagamentos SET compra_disciplina_ead_id = %s WHERE id = %s", (ids[0], pagamento_id))
            return len(ids)

    def pedidos_do_aluno(self, aluno_id: str, pedido_id: Optional[str] = None) -> List[Dict[str, Any]]:
        filtro = " AND p.id = %s" if pedido_id else ""
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT p.id, p.numero, p.tipo, p.status, p.valor_total, p.criado_em, p.pago_em, p.enviado_em,
                           p.entregue_em, c.disciplina_id, d.nome AS disciplina_nome, c.com_livro,
                           pg.id AS pagamento_id, pg.status AS pagamento_status, pg.billing_type, pg.valor AS pagamento_valor,
                           pg.vencimento_em, pg.pix_copia_cola, pg.pix_qrcode_base64, pg.boleto_url, pg.invoice_url,
                           pg.linha_digitavel, en.transportadora, en.codigo_rastreio
                      FROM pedidos p
                      LEFT JOIN compras_disciplina_ead c ON c.pedido_id = p.id
                      LEFT JOIN disciplinas d ON d.id = c.disciplina_id
                      LEFT JOIN LATERAL (
                          SELECT x.* FROM pagamentos x WHERE x.pedido_id = p.id ORDER BY x.criado_em DESC LIMIT 1
                      ) pg ON true
                      LEFT JOIN LATERAL (
                          SELECT e.transportadora, e.codigo_rastreio FROM envios e
                           WHERE e.pedido_id = p.id ORDER BY e.criado_em DESC LIMIT 1
                      ) en ON true
                     WHERE p.aluno_id = %s AND p.tipo IN ('ead', 'ead_livro'){filtro}
                     ORDER BY p.criado_em DESC
                     LIMIT 100""",
                (aluno_id, pedido_id) if pedido_id else (aluno_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]


_repo: Optional[PostgresVendasEadRepository] = None


def get_vendas_ead_repository() -> PostgresVendasEadRepository:
    global _repo
    if _repo is None:
        _repo = PostgresVendasEadRepository()
    return _repo
