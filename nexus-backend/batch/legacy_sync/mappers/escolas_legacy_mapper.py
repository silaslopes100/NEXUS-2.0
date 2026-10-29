"""Escolas via query legada complexa (MySQL only).

Le users com role_id=3 (coordenador polo), expande campo CSV `escolas`,
faz join com users role_id=4 (gestor escola) via escola_old.
Resolve polo_id via registry (polos ja carregados com legacy_id = u3.id).
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper


class EscolaLegacyMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = [
        "id", "role_id", "escolas", "nome_escola", "polo",
        "cep", "logradouro", "numero", "bairro", "cidade", "uf", "complemento",
    ]
    target_table: ClassVar[str] = "escolas"
    order_by: ClassVar[str | None] = "id"
    legacy_table: ClassVar[str] = "teo-eadetademp.users"

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._processados: set[int] = set()

    def initial_where(self, last_run=None) -> str | None:
        return "role_id = 3 AND COALESCE(escolas, '') <> ''"

    def current_legacy_id(self, row: dict) -> int:
        return int(row["escola_old"])

    def iter_source(self, source, last_run=None):
        where = self.initial_where(last_run)
        cols = self.source_columns
        for u3 in source.stream(self.source_table, cols, where=where, order=self.order_by):
            escolas_csv = u3.get("escolas")
            if not escolas_csv:
                continue
            escola_ids = [
                int(e) for e in escolas_csv.replace("[", "").replace("]", "").replace('"', "").split(",")
                if e.strip().isdigit()
            ]
            if not escola_ids:
                continue

            placeholders = ",".join(["%s"] * len(escola_ids))
            sql = f"""
                SELECT u4.escola_old, u4.nome_escola,
                       u4.cep, u4.logradouro, u4.numero,
                       u4.bairro, u4.cidade, u4.uf, u4.complemento
                FROM `users` u4
                WHERE u4.role_id = 4
                  AND u4.escola_old IN ({placeholders})
            """
            with source.conn.cursor() as cur:
                cur.execute(sql, tuple(escola_ids))
                u4_rows = cur.fetchall()

            for u4 in u4_rows:
                legacy_id = int(u4["escola_old"])
                if legacy_id in self._processados:
                    continue
                self._processados.add(legacy_id)

                row = {
                    "id": u3["id"],
                    "role_id": u3["role_id"],
                    "escolas": u3["escolas"],
                    "nome_escola": u4["nome_escola"],
                    "polo": u3["polo"],
                    "cep": u4["cep"],
                    "logradouro": u4["logradouro"],
                    "numero": u4["numero"],
                    "bairro": u4["bairro"],
                    "cidade": u4["cidade"],
                    "uf": u4["uf"],
                    "complemento": u4["complemento"],
                    "escola_old": u4["escola_old"],
                    "_u3_cep": u3["cep"],
                    "_u3_logradouro": u3["logradouro"],
                    "_u3_numero": u3["numero"],
                    "_u3_bairro": u3["bairro"],
                    "_u3_cidade": u3["cidade"],
                    "_u3_uf": u3["uf"],
                    "_u3_complemento": u3["complemento"],
                }
                yield row

    def map(self, row: dict) -> dict | None:
        polo_id = self.registry.resolve("polos", "teo-eadetademp.users", row["id"]) if self.registry else None

        def pick(u4_key: str, u3_key: str) -> str | None:
            val = self.str_clean(row.get(u4_key))
            if val:
                return val
            return self.str_clean(row.get(u3_key))

        return {
            "polo_id": polo_id,
            "nome": self.str_clean(row.get("nome_escola")) or f"Escola {row['escola_old']}",
            "cep": pick("cep", "_u3_cep"),
            "logradouro": pick("logradouro", "_u3_logradouro"),
            "numero": pick("numero", "_u3_numero"),
            "bairro": pick("bairro", "_u3_bairro"),
            "cidade": pick("cidade", "_u3_cidade"),
            "uf": pick("uf", "_u3_uf"),
            "complemento": pick("complemento", "_u3_complemento"),
            "status": "ativo",
        }