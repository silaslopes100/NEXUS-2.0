"""Persistência da Central de Estágio (Postgres; versão em memória para testes)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from app.core.database import get_db_cursor
from app.modules.estagios.schemas import FiltrosRelatorio, FiltrosSubmissoes

Escopo = Dict[str, Optional[str]]  # {"polo_id": ..., "escola_id": ...} — vazio = global


class SubmissaoIndisponivel(Exception):
    """A etapa já tem submissão em análise ou aprovada (envio concorrente ou repetido)."""


class EstagiosRepositoryInterface(Protocol):
    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def submissoes_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def get_submissao(self, submissao_id: str) -> Optional[Dict[str, Any]]: ...
    def salvar_envio(self, aluno_id: str, etapa: str, arquivos: Sequence[Dict[str, Any]],
                     usuario_id: str) -> Tuple[str, List[str], bool]: ...
    def avaliar(self, submissao_id: str, status: str, comentario: Optional[str], usuario_id: str,
                codigo: Optional[str]) -> bool: ...
    def listar(self, filtros: FiltrosSubmissoes, escopo: Escopo, limit: int,
               offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...
    def contar_pendentes(self) -> int: ...
    def contar_nao_vistos(self, aluno_id: str) -> int: ...
    def marcar_vistos(self, aluno_id: str) -> None: ...
    def relatorio(self, filtros: FiltrosRelatorio, escopo: Escopo) -> List[Dict[str, Any]]: ...
    def arquivos_base(self) -> List[Dict[str, Any]]: ...
    def salvar_arquivo_base(self, chave: str, dados: Dict[str, Any], usuario_id: str) -> Optional[str]: ...
    def get_config(self) -> Dict[str, Any]: ...
    def salvar_config(self, video_url: Optional[str]) -> None: ...


def _limites(de: Optional[date], ate: Optional[date]) -> Tuple[Optional[datetime], Optional[datetime]]:
    ini = datetime.combine(de, time.min, tzinfo=timezone.utc) if de else None
    fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=timezone.utc) if ate else None
    return ini, fim


def _str_ids(d: Dict[str, Any], *campos: str) -> Dict[str, Any]:
    for c in campos:
        if d.get(c) is not None:
            d[c] = str(d[c])
    return d


_ALUNO_COLS = """
    a.id AS aluno_id, a.usuario_id AS aluno_usuario_id, a.numero_matricula, a.polo_id, a.escola_id,
    concat_ws(' ', u.nome, u.sobrenome) AS aluno_nome, u.cpf, u.email,
    COALESCE(u.celular, u.telefone) AS telefone, u.foto_url,
    po.nome AS polo_nome, es.nome AS escola_nome
"""
_ALUNO_JOINS = """
    JOIN alunos a ON a.id = s.aluno_id
    JOIN usuarios u ON u.id = a.usuario_id
    LEFT JOIN polos po ON po.id = a.polo_id
    LEFT JOIN escolas es ON es.id = a.escola_id
"""


def _aluno_de(linha: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(linha["aluno_id"]), "nome": linha.get("aluno_nome") or "Aluno",
        "numero_matricula": linha.get("numero_matricula"), "cpf": linha.get("cpf"),
        "email": linha.get("email"), "telefone": linha.get("telefone"), "foto_url": linha.get("foto_url"),
        "polo_id": str(linha["polo_id"]) if linha.get("polo_id") else None, "polo_nome": linha.get("polo_nome"),
        "escola_id": str(linha["escola_id"]) if linha.get("escola_id") else None,
        "escola_nome": linha.get("escola_nome"),
        "usuario_id": str(linha["aluno_usuario_id"]) if linha.get("aluno_usuario_id") else None,
    }


class PostgresEstagiosRepository:
    # ------------------------------------------------------------------ aluno

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT a.id, a.polo_id, a.escola_id, concat_ws(' ', u.nome, u.sobrenome) AS nome
                     FROM alunos a JOIN usuarios u ON u.id = a.usuario_id
                    WHERE a.usuario_id = %s LIMIT 1""",
                (usuario_id,),
            )
            r = cur.fetchone()
            return _str_ids(dict(r), "id", "polo_id", "escola_id") if r else None

    def _carregar_detalhes(self, cur: Any, submissoes: List[Dict[str, Any]]) -> None:
        if not submissoes:
            return
        ids = [s["id"] for s in submissoes]
        cur.execute(
            """SELECT id, submissao_id, tipo, nome, mime, tamanho, url, criado_em
                 FROM estagio_arquivos WHERE submissao_id = ANY(%s::uuid[])
                ORDER BY tipo, criado_em, nome""",
            (ids,),
        )
        arquivos: Dict[str, List[Dict[str, Any]]] = {}
        for r in cur.fetchall():
            arquivos.setdefault(str(r["submissao_id"]), []).append(_str_ids(dict(r), "id", "submissao_id"))
        cur.execute(
            """SELECT e.submissao_id, e.acao, e.comentario, e.criado_em,
                      concat_ws(' ', u.nome, u.sobrenome) AS usuario_nome
                 FROM estagio_eventos e LEFT JOIN usuarios u ON u.id = e.usuario_id
                WHERE e.submissao_id = ANY(%s::uuid[]) ORDER BY e.criado_em""",
            (ids,),
        )
        eventos: Dict[str, List[Dict[str, Any]]] = {}
        for r in cur.fetchall():
            eventos.setdefault(str(r["submissao_id"]), []).append(dict(r))
        for s in submissoes:
            s["arquivos"] = arquivos.get(s["id"], [])
            s["eventos"] = eventos.get(s["id"], [])

    _SUB_COLS = """s.id, s.aluno_id, s.etapa, s.status, s.horas, s.comentario_feedback, s.avaliado_em,
                   s.enviado_em, s.codigo_comprovante, s.visto_pelo_aluno,
                   concat_ws(' ', av.nome, av.sobrenome) AS avaliado_por_nome"""

    def submissoes_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT {self._SUB_COLS} FROM estagio_submissoes s
                     LEFT JOIN usuarios av ON av.id = s.avaliado_por
                    WHERE s.aluno_id = %s""",
                (aluno_id,),
            )
            itens = [_str_ids(dict(r), "id", "aluno_id") for r in cur.fetchall()]
            self._carregar_detalhes(cur, itens)
            return itens

    def get_submissao(self, submissao_id: str) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(submissao_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT {self._SUB_COLS}, {_ALUNO_COLS} FROM estagio_submissoes s
                     {_ALUNO_JOINS}
                     LEFT JOIN usuarios av ON av.id = s.avaliado_por
                    WHERE s.id = %s""",
                (submissao_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            item = _str_ids(dict(r), "id", "aluno_id")
            item["aluno"] = _aluno_de(item)
            self._carregar_detalhes(cur, [item])
            return item

    def salvar_envio(self, aluno_id, etapa, arquivos, usuario_id):
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT id, status FROM estagio_submissoes WHERE aluno_id = %s AND etapa = %s FOR UPDATE""",
                (aluno_id, etapa),
            )
            atual = cur.fetchone()
            antigos: List[str] = []
            if atual is None:
                cur.execute(
                    """INSERT INTO estagio_submissoes (aluno_id, etapa) VALUES (%s, %s)
                       ON CONFLICT (aluno_id, etapa) DO NOTHING RETURNING id""",
                    (aluno_id, etapa),
                )
                criado = cur.fetchone()
                if not criado:
                    raise SubmissaoIndisponivel()
                submissao_id, reenvio = str(criado["id"]), False
            else:
                if atual["status"] != "negado":
                    raise SubmissaoIndisponivel()
                submissao_id, reenvio = str(atual["id"]), True
                cur.execute("DELETE FROM estagio_arquivos WHERE submissao_id = %s RETURNING storage_key",
                            (submissao_id,))
                antigos = [r["storage_key"] for r in cur.fetchall()]
                cur.execute(
                    """UPDATE estagio_submissoes
                          SET status = 'em_analise', comentario_feedback = NULL, avaliado_por = NULL,
                              avaliado_em = NULL, visto_pelo_aluno = true, enviado_em = now(), atualizado_em = now()
                        WHERE id = %s""",
                    (submissao_id,),
                )
            for a in arquivos:
                cur.execute(
                    """INSERT INTO estagio_arquivos (submissao_id, tipo, nome, mime, tamanho, url, storage_key)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (submissao_id, a["tipo"], a["nome"], a["mime"], a["tamanho"], a["url"], a["storage_key"]),
                )
            cur.execute(
                "INSERT INTO estagio_eventos (submissao_id, acao, usuario_id) VALUES (%s, %s, %s)",
                (submissao_id, "reenviado" if reenvio else "enviado", usuario_id),
            )
            return submissao_id, antigos, reenvio

    def avaliar(self, submissao_id, status, comentario, usuario_id, codigo):
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE estagio_submissoes
                      SET status = %s, comentario_feedback = %s, avaliado_por = %s, avaliado_em = now(),
                          visto_pelo_aluno = false, atualizado_em = now(),
                          codigo_comprovante = COALESCE(%s, codigo_comprovante)
                    WHERE id = %s AND status = 'em_analise'""",
                (status, comentario, usuario_id, codigo, submissao_id),
            )
            if cur.rowcount == 0:
                return False
            cur.execute(
                "INSERT INTO estagio_eventos (submissao_id, acao, comentario, usuario_id) VALUES (%s, %s, %s, %s)",
                (submissao_id, status, comentario, usuario_id),
            )
            return True

    # ------------------------------------------------------------------ listagens

    @staticmethod
    def _where_escopo(escopo: Escopo, conds: List[str], params: List[Any]) -> None:
        if escopo.get("polo_id"):
            conds.append("a.polo_id = %s")
            params.append(escopo["polo_id"])
        if escopo.get("escola_id"):
            conds.append("a.escola_id = %s")
            params.append(escopo["escola_id"])

    def listar(self, filtros, escopo, limit, offset):
        conds: List[str] = []
        params: List[Any] = []
        self._where_escopo(escopo, conds, params)
        for campo in ("status", "etapa"):
            valor = getattr(filtros, campo)
            if valor:
                conds.append(f"s.{campo} = %s")
                params.append(valor)
        if filtros.polo_id:
            conds.append("a.polo_id = %s")
            params.append(filtros.polo_id)
        if filtros.escola_id:
            conds.append("a.escola_id = %s")
            params.append(filtros.escola_id)
        ini, fim = _limites(filtros.de, filtros.ate)
        if ini:
            conds.append("s.enviado_em >= %s")
            params.append(ini)
        if fim:
            conds.append("s.enviado_em < %s")
            params.append(fim)
        if filtros.busca:
            conds.append("(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s OR a.numero_matricula ILIKE %s)")
            termo = f"%{filtros.busca.lower()}%"
            params.extend([termo, termo])
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM estagio_submissoes s {_ALUNO_JOINS} {where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"""SELECT s.id, s.etapa, s.status, s.enviado_em, s.avaliado_em, s.codigo_comprovante, {_ALUNO_COLS},
                           (SELECT COUNT(*) FROM estagio_arquivos f
                             WHERE f.submissao_id = s.id AND f.tipo = 'foto') AS total_fotos,
                           (SELECT f.url FROM estagio_arquivos f
                             WHERE f.submissao_id = s.id AND f.tipo = 'foto'
                             ORDER BY f.criado_em, f.nome LIMIT 1) AS miniatura_url
                      FROM estagio_submissoes s {_ALUNO_JOINS} {where}
                     ORDER BY s.enviado_em DESC LIMIT %s OFFSET %s""",
                (*params, limit, offset),
            )
            itens = []
            for r in cur.fetchall():
                d = dict(r)
                itens.append({
                    "id": str(d["id"]), "etapa": d["etapa"], "status": d["status"], "enviado_em": d["enviado_em"],
                    "avaliado_em": d["avaliado_em"], "codigo_comprovante": d["codigo_comprovante"],
                    "total_fotos": int(d["total_fotos"] or 0), "miniatura_url": d["miniatura_url"],
                    "aluno": _aluno_de(d),
                })
            return total, itens

    def contar_pendentes(self) -> int:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM estagio_submissoes WHERE status = 'em_analise'")
            return int(cur.fetchone()["n"])

    def contar_nao_vistos(self, aluno_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM estagio_submissoes WHERE aluno_id = %s AND NOT visto_pelo_aluno",
                (aluno_id,),
            )
            return int(cur.fetchone()["n"])

    def marcar_vistos(self, aluno_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE estagio_submissoes SET visto_pelo_aluno = true WHERE aluno_id = %s AND NOT visto_pelo_aluno",
                (aluno_id,),
            )

    def relatorio(self, filtros, escopo):
        conds: List[str] = []
        params: List[Any] = []
        self._where_escopo(escopo, conds, params)
        if filtros.polo_id:
            conds.append("a.polo_id = %s")
            params.append(filtros.polo_id)
        if filtros.escola_id:
            conds.append("a.escola_id = %s")
            params.append(filtros.escola_id)
        ini, fim = _limites(filtros.de, filtros.ate)
        if ini:
            conds.append("s.enviado_em >= %s")
            params.append(ini)
        if fim:
            conds.append("s.enviado_em < %s")
            params.append(fim)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT a.id AS aluno_id, concat_ws(' ', u.nome, u.sobrenome) AS aluno_nome, a.numero_matricula,
                           po.nome AS polo_nome, es.nome AS escola_nome,
                           max(s.status) FILTER (WHERE s.etapa = 'teologia_ministerio') AS teologia_status,
                           max(s.avaliado_em) FILTER (WHERE s.etapa = 'teologia_ministerio' AND s.status = 'aprovado')
                               AS teologia_aprovado_em,
                           max(s.status) FILTER (WHERE s.etapa = 'homiletica') AS homiletica_status,
                           max(s.avaliado_em) FILTER (WHERE s.etapa = 'homiletica' AND s.status = 'aprovado')
                               AS homiletica_aprovado_em,
                           COALESCE(sum(s.horas) FILTER (WHERE s.status = 'aprovado'), 0) AS horas_cumpridas
                      FROM estagio_submissoes s {_ALUNO_JOINS} {where}
                     GROUP BY a.id, u.nome, u.sobrenome, a.numero_matricula, po.nome, es.nome
                     ORDER BY aluno_nome""",
                params,
            )
            return [_str_ids(dict(r), "aluno_id") for r in cur.fetchall()]

    # ------------------------------------------------------------------ arquivos-base / config

    def arquivos_base(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT chave, nome, mime, tamanho, url, storage_key, atualizado_em FROM estagio_arquivos_base")
            return [dict(r) for r in cur.fetchall()]

    def salvar_arquivo_base(self, chave, dados, usuario_id):
        with get_db_cursor() as cur:
            cur.execute("SELECT storage_key FROM estagio_arquivos_base WHERE chave = %s FOR UPDATE", (chave,))
            antigo = cur.fetchone()
            cur.execute(
                """INSERT INTO estagio_arquivos_base (chave, nome, mime, tamanho, url, storage_key, atualizado_por)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (chave) DO UPDATE
                      SET nome = EXCLUDED.nome, mime = EXCLUDED.mime, tamanho = EXCLUDED.tamanho, url = EXCLUDED.url,
                          storage_key = EXCLUDED.storage_key, atualizado_por = EXCLUDED.atualizado_por,
                          atualizado_em = now()""",
                (chave, dados["nome"], dados["mime"], dados["tamanho"], dados["url"], dados["storage_key"], usuario_id),
            )
            return antigo["storage_key"] if antigo else None

    def get_config(self) -> Dict[str, Any]:
        with get_db_cursor() as cur:
            cur.execute("SELECT video_url FROM estagio_config WHERE id = 1")
            r = cur.fetchone()
            return dict(r) if r else {"video_url": None}

    def salvar_config(self, video_url):
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO estagio_config (id, video_url) VALUES (1, %s)
                   ON CONFLICT (id) DO UPDATE SET video_url = EXCLUDED.video_url, atualizado_em = now()""",
                (video_url,),
            )


# ---------------------------------------------------------------------------
# Em memória (testes)
# ---------------------------------------------------------------------------

class InMemoryEstagiosRepository:
    def __init__(self) -> None:
        # aluno_id -> {id, usuario_id, nome, polo_id, escola_id, polo_nome, escola_nome, numero_matricula}
        self.alunos: Dict[str, Dict[str, Any]] = {}
        self.submissoes: Dict[str, Dict[str, Any]] = {}
        self.arquivos: List[Dict[str, Any]] = []
        self.eventos: List[Dict[str, Any]] = []
        self.base: Dict[str, Dict[str, Any]] = {}
        self.config: Dict[str, Any] = {"video_url": None}

    def get_aluno_por_usuario(self, usuario_id):
        for a in self.alunos.values():
            if a.get("usuario_id") == usuario_id:
                return dict(a)
        return None

    def _completa(self, s: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(s)
        item["arquivos"] = [dict(a) for a in self.arquivos if a["submissao_id"] == s["id"]]
        item["eventos"] = [dict(e) for e in self.eventos if e["submissao_id"] == s["id"]]
        aluno = self.alunos.get(s["aluno_id"], {})
        item["aluno"] = {"id": s["aluno_id"], "nome": aluno.get("nome") or "Aluno", "usuario_id": aluno.get("usuario_id"),
                         "numero_matricula": aluno.get("numero_matricula"), "polo_id": aluno.get("polo_id"),
                         "polo_nome": aluno.get("polo_nome"), "escola_id": aluno.get("escola_id"),
                         "escola_nome": aluno.get("escola_nome")}
        return item

    def submissoes_do_aluno(self, aluno_id):
        return [self._completa(s) for s in self.submissoes.values() if s["aluno_id"] == aluno_id]

    def get_submissao(self, submissao_id):
        s = self.submissoes.get(submissao_id)
        return self._completa(s) if s else None

    def salvar_envio(self, aluno_id, etapa, arquivos, usuario_id):
        atual = next((s for s in self.submissoes.values()
                      if s["aluno_id"] == aluno_id and s["etapa"] == etapa), None)
        agora = datetime.now(timezone.utc)
        antigos: List[str] = []
        if atual is None:
            sid = str(uuid.uuid4())
            self.submissoes[sid] = {"id": sid, "aluno_id": aluno_id, "etapa": etapa, "status": "em_analise",
                                    "horas": 50, "comentario_feedback": None, "avaliado_em": None,
                                    "avaliado_por_nome": None, "enviado_em": agora, "codigo_comprovante": None,
                                    "visto_pelo_aluno": True}
            reenvio = False
        else:
            if atual["status"] != "negado":
                raise SubmissaoIndisponivel()
            sid, reenvio = atual["id"], True
            antigos = [a["storage_key"] for a in self.arquivos if a["submissao_id"] == sid]
            self.arquivos = [a for a in self.arquivos if a["submissao_id"] != sid]
            atual.update(status="em_analise", comentario_feedback=None, avaliado_em=None, avaliado_por_nome=None,
                         enviado_em=agora, visto_pelo_aluno=True)
        for a in arquivos:
            self.arquivos.append({**a, "id": str(uuid.uuid4()), "submissao_id": sid, "criado_em": agora})
        self.eventos.append({"submissao_id": sid, "acao": "reenviado" if reenvio else "enviado",
                             "comentario": None, "usuario_nome": None, "criado_em": agora})
        return sid, antigos, reenvio

    def avaliar(self, submissao_id, status, comentario, usuario_id, codigo):
        s = self.submissoes.get(submissao_id)
        if not s or s["status"] != "em_analise":
            return False
        agora = datetime.now(timezone.utc)
        s.update(status=status, comentario_feedback=comentario, avaliado_em=agora, visto_pelo_aluno=False,
                 codigo_comprovante=codigo or s.get("codigo_comprovante"))
        self.eventos.append({"submissao_id": submissao_id, "acao": status, "comentario": comentario,
                             "usuario_nome": None, "criado_em": agora})
        return True

    def _no_escopo(self, aluno: Dict[str, Any], escopo: Escopo) -> bool:
        if escopo.get("polo_id") and aluno.get("polo_id") != escopo["polo_id"]:
            return False
        if escopo.get("escola_id") and aluno.get("escola_id") != escopo["escola_id"]:
            return False
        return True

    def listar(self, filtros, escopo, limit, offset):
        ini, fim = _limites(filtros.de, filtros.ate)
        itens = []
        for s in sorted(self.submissoes.values(), key=lambda x: x["enviado_em"], reverse=True):
            item = self._completa(s)
            aluno = item["aluno"]
            if not self._no_escopo(aluno, escopo):
                continue
            if filtros.status and s["status"] != filtros.status:
                continue
            if filtros.etapa and s["etapa"] != filtros.etapa:
                continue
            if filtros.polo_id and aluno.get("polo_id") != filtros.polo_id:
                continue
            if filtros.escola_id and aluno.get("escola_id") != filtros.escola_id:
                continue
            if (ini and s["enviado_em"] < ini) or (fim and s["enviado_em"] >= fim):
                continue
            if filtros.busca and filtros.busca.lower() not in aluno["nome"].lower():
                continue
            fotos = [a for a in item["arquivos"] if a["tipo"] == "foto"]
            itens.append({**{k: s.get(k) for k in ("id", "etapa", "status", "enviado_em", "avaliado_em",
                                                    "codigo_comprovante")},
                          "total_fotos": len(fotos), "miniatura_url": fotos[0]["url"] if fotos else None,
                          "aluno": aluno})
        return len(itens), itens[offset:offset + limit]

    def contar_pendentes(self):
        return sum(1 for s in self.submissoes.values() if s["status"] == "em_analise")

    def contar_nao_vistos(self, aluno_id):
        return sum(1 for s in self.submissoes.values() if s["aluno_id"] == aluno_id and not s["visto_pelo_aluno"])

    def marcar_vistos(self, aluno_id):
        for s in self.submissoes.values():
            if s["aluno_id"] == aluno_id:
                s["visto_pelo_aluno"] = True

    def relatorio(self, filtros, escopo):
        _, itens = self.listar(FiltrosSubmissoes(polo_id=filtros.polo_id, escola_id=filtros.escola_id,
                                                 de=filtros.de, ate=filtros.ate), escopo, 10 ** 9, 0)
        por_aluno: Dict[str, Dict[str, Any]] = {}
        for i in itens:
            s = self.submissoes[i["id"]]
            a = i["aluno"]
            linha = por_aluno.setdefault(a["id"], {
                "aluno_id": a["id"], "aluno_nome": a["nome"], "numero_matricula": a.get("numero_matricula"),
                "polo_nome": a.get("polo_nome"), "escola_nome": a.get("escola_nome"), "horas_cumpridas": 0,
                "teologia_status": None, "teologia_aprovado_em": None,
                "homiletica_status": None, "homiletica_aprovado_em": None,
            })
            prefixo = "teologia" if s["etapa"] == "teologia_ministerio" else "homiletica"
            linha[f"{prefixo}_status"] = s["status"]
            if s["status"] == "aprovado":
                linha[f"{prefixo}_aprovado_em"] = s["avaliado_em"]
                linha["horas_cumpridas"] += s["horas"]
        return sorted(por_aluno.values(), key=lambda x: x["aluno_nome"])

    def arquivos_base(self):
        return [dict(v) for v in self.base.values()]

    def salvar_arquivo_base(self, chave, dados, usuario_id):
        antigo = self.base.get(chave, {}).get("storage_key")
        self.base[chave] = {**dados, "chave": chave, "atualizado_em": datetime.now(timezone.utc)}
        return antigo

    def get_config(self):
        return dict(self.config)

    def salvar_config(self, video_url):
        self.config["video_url"] = video_url


_repo: Optional[EstagiosRepositoryInterface] = None


def get_estagios_repository() -> EstagiosRepositoryInterface:
    global _repo
    if _repo is None:
        _repo = PostgresEstagiosRepository()
    return _repo


def set_estagios_repository(repo: Optional[EstagiosRepositoryInterface]) -> None:
    global _repo
    _repo = repo
