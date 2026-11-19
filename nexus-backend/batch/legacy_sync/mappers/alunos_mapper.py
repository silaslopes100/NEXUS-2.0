"""Alunos. Fonte legado: `users` com perfil aluno (role/aluno ou sem flags).

- numero_matricula: padrao NEXUS `NX-AAAA-NNNNNNN` (sequence
  seq_matricula_aluno), gerado so na criacao pelo passo
  `gerar_matriculas_nx` apos a carga. Nada do codigo legado e reaproveitado.
- modalidade: 'ead' se esta na escola "EAD" do NEXUS (ou sem polo/escola),
  senao 'polo'. polo/escola sao copiados do usuario migrado.
- data_nascimento: `users.nascimento` (varchar livre, parse tolerante).
- status: 'desistente' quando `users.revalidacao` indica revalidacao pendente
  (heuristica); detalhes de churn (>1 ano parado) sao job diario do batch.
"""
from __future__ import annotations

import logging
from typing import ClassVar

from psycopg2.extras import execute_values

from .base import BaseMapper
from .perfis_mapper import perfil_nome
from .usuarios_mapper import USERS_COLUMNS, carregar_lotacao_ead, carregar_usuarios_migrados

logger = logging.getLogger(__name__)


class AlunoMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS
    target_table: ClassVar[str] = "alunos"
    order_by: ClassVar[str | None] = "id"

    def iter_source(self, source, last_run=None):
        # Apenas quem ficou com perfil ALUNO em usuarios (fonte unica);
        # sem acesso ao destino (testes), usa a classificacao por role/flags.
        self._usuarios = carregar_usuarios_migrados(self.registry)
        ead = carregar_lotacao_ead(self.registry)
        self._escola_ead = ead[1] if ead else None
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            if self._usuarios is not None:
                nome = (self._usuarios.get(int(row["id"])) or {}).get("perfil")
            else:
                nome = perfil_nome(self.registry, row)
            if nome == "aluno":
                yield row

    def _lotacao(self, row: dict) -> tuple[str | None, str | None]:
        """(polo_id, escola_id): os mesmos gravados no usuario (inclui o
        fallback polo-da-escola e o vinculo por CPF)."""
        u = (getattr(self, "_usuarios", None) or {}).get(self.as_int(row.get("id")))
        if u is not None:
            return u["polo_id"], u["escola_id"]
        if not self.registry:
            return None, None
        return (
            self.registry.resolve("polos", "users", row.get("polo")),
            self.registry.resolve("escolas", "users", row.get("escola")),
        )

    def map(self, row: dict) -> dict | None:
        usuario_id = self.registry.resolve("usuarios", "users", row.get("id")) if self.registry else None
        if not usuario_id:
            self.warn(f"aluno sem usuario migrado: id={row.get('id')}")
            return None

        polo_id, escola_id = self._lotacao(row)
        escola_ead = getattr(self, "_escola_ead", None)
        if escola_id and escola_id == escola_ead:
            modalidade = "ead"  # vinculado ao polo/escola EAD do NEXUS
        else:
            modalidade = "polo" if (polo_id or escola_id) else "ead"

        nascimento = self.parse_date(row.get("nascimento"))

        revalidacao = self.str_clean(row.get("revalidacao"))
        status = "desistente" if revalidacao else "ativo"

        return {
            "usuario_id": usuario_id,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "modalidade": modalidade,
            "data_nascimento": nascimento,
            "status": status,
            "ultima_movimentacao_em": self.parse_ts(row.get("last_modified")),
        }

def gerar_matriculas_nx(target) -> int:
    """Atribui `NX-AAAA-NNNNNNN` (padrao NEXUS) aos alunos sem matricula.

    Mesma formula do NEXUS (polos_escolas/alunos_gestao): ano corrente +
    nextval('seq_matricula_aluno') com 7 digitos. Numeros em ordem de
    users.id legado. Idempotente: so preenche quem esta NULL, nunca troca.
    """
    with target.conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM alunos WHERE numero_matricula IS NULL "
            "ORDER BY legacy_id NULLS LAST, criado_em"
        )
        ids = [str(r[0]) for r in cur.fetchall()]
        if not ids:
            return 0
        cur.execute("SELECT to_char(now(), 'YYYY')")
        ano = cur.fetchone()[0]
        cur.execute(
            "SELECT nextval('seq_matricula_aluno') FROM generate_series(1, %s)", (len(ids),)
        )
        numeros = sorted(int(r[0]) for r in cur.fetchall())
        valores = [(aid, f"NX-{ano}-{n:07d}") for aid, n in zip(ids, numeros)]
        execute_values(
            cur,
            "UPDATE alunos a SET numero_matricula = v.m, atualizado_em = now() "
            "FROM (VALUES %s) AS v(id, m) WHERE a.id = v.id::uuid AND a.numero_matricula IS NULL",
            valores, page_size=1000,
        )
    target.commit()
    logger.info("matricula NX gerada para %d alunos (%s .. %s)", len(valores), valores[0][1], valores[-1][1])
    return len(valores)
