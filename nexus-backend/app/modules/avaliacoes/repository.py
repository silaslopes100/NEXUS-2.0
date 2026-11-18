"""Persistência das Avaliações (Postgres) + implementação em memória para testes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from psycopg2.extras import Json

from app.core.database import get_db_cursor


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    out: Dict[str, Any] = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class AvaliacoesRepositoryInterface(Protocol):
    def get_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]: ...
    def list_avaliacoes(self, disciplina_id: Optional[str] = None) -> List[Dict[str, Any]]: ...
    def get_avaliacao(self, avaliacao_id: str) -> Optional[Dict[str, Any]]: ...
    def get_avaliacao_da_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]: ...
    def salvar_avaliacao(self, disciplina_id: str, dados: Dict[str, Any], questoes: List[Dict[str, Any]],
                         usuario_id: Optional[str], origem: str = "manual") -> str: ...
    def set_ativo(self, avaliacao_id: str, ativo: bool) -> None: ...
    # aluno
    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def list_disciplinas_licenciadas(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def get_licenca_ativa(self, aluno_id: str, disciplina_id: str) -> Optional[Dict[str, Any]]: ...
    def turma_do_aluno(self, aluno_id: str, disciplina_id: str) -> Optional[str]: ...
    def list_tentativas(self, avaliacao_id: str, aluno_id: str) -> List[Dict[str, Any]]: ...
    def criar_tentativa(self, dados: Dict[str, Any]) -> str: ...
    def get_tentativa(self, tentativa_id: str) -> Optional[Dict[str, Any]]: ...
    def salvar_respostas(self, tentativa_id: str, respostas: Dict[str, str]) -> None: ...
    def finalizar_tentativa(self, tentativa_id: str, nota: float, status: str, nota_id: Optional[str]) -> None: ...


class PostgresAvaliacoesRepository:
    def get_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(disciplina_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, curso_id FROM disciplinas WHERE id = %s", (str(disciplina_id),))
            return _limpar(cur.fetchone())

    def list_avaliacoes(self, disciplina_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT a.id, a.disciplina_id, a.titulo, a.ativo, a.origem,
                   (SELECT COUNT(*) FROM avaliacao_questoes q WHERE q.avaliacao_id = a.id) AS total_questoes
              FROM avaliacoes a
        """
        params: List[Any] = []
        if disciplina_id:
            sql += " WHERE a.disciplina_id = %s"
            params.append(str(disciplina_id))
        with get_db_cursor() as cur:
            cur.execute(sql + " ORDER BY a.atualizado_em DESC", tuple(params))
            return [_limpar(r) for r in cur.fetchall()]

    def _completa(self, cur: Any, avaliacao: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not avaliacao:
            return None
        cur.execute("SELECT id, enunciado, peso, ordem FROM avaliacao_questoes WHERE avaliacao_id = %s ORDER BY ordem, id",
                    (avaliacao["id"],))
        questoes = [_limpar(q) for q in cur.fetchall()]
        if questoes:
            cur.execute(
                "SELECT id, questao_id, texto, correta, ordem FROM avaliacao_alternativas "
                "WHERE questao_id::text = ANY(%s) ORDER BY ordem, id",
                ([q["id"] for q in questoes],),
            )
            alts: Dict[str, List[Dict[str, Any]]] = {}
            for a in (_limpar(r) for r in cur.fetchall()):
                alts.setdefault(a["questao_id"], []).append(a)
            for q in questoes:
                q["alternativas"] = alts.get(q["id"], [])
        avaliacao["questoes"] = questoes
        return avaliacao

    _SELECT = """
        SELECT a.*, d.nome AS disciplina_nome FROM avaliacoes a JOIN disciplinas d ON d.id = a.disciplina_id
    """

    def get_avaliacao(self, avaliacao_id: str) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(avaliacao_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute(self._SELECT + " WHERE a.id = %s", (str(avaliacao_id),))
            return self._completa(cur, _limpar(cur.fetchone()))

    def get_avaliacao_da_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(self._SELECT + " WHERE a.disciplina_id = %s ORDER BY a.ativo DESC, a.atualizado_em DESC LIMIT 1",
                        (str(disciplina_id),))
            return self._completa(cur, _limpar(cur.fetchone()))

    def salvar_avaliacao(self, disciplina_id: str, dados: Dict[str, Any], questoes: List[Dict[str, Any]],
                         usuario_id: Optional[str], origem: str = "manual") -> str:
        """Uma avaliação por disciplina: cria ou substitui título, regras e questões numa transação."""
        campos = ("titulo", "instrucoes", "tempo_limite_min", "tentativas_max", "nota_minima", "embaralhar", "ativo")
        with get_db_cursor() as cur:
            cur.execute("SELECT id FROM avaliacoes WHERE disciplina_id = %s ORDER BY atualizado_em DESC LIMIT 1 FOR UPDATE",
                        (str(disciplina_id),))
            row = cur.fetchone()
            if row:
                avaliacao_id = str(row["id"])
                sets = ", ".join(f"{c} = %s" for c in campos)
                cur.execute(f"UPDATE avaliacoes SET {sets}, origem = %s, atualizado_em = now() WHERE id = %s",
                            (*[dados.get(c) for c in campos], origem, avaliacao_id))
                cur.execute("DELETE FROM avaliacao_questoes WHERE avaliacao_id = %s", (avaliacao_id,))
            else:
                cur.execute(
                    f"INSERT INTO avaliacoes (disciplina_id, {', '.join(campos)}, origem, criado_por) "
                    f"VALUES (%s, {', '.join(['%s'] * len(campos))}, %s, %s) RETURNING id",
                    (str(disciplina_id), *[dados.get(c) for c in campos], origem, usuario_id),
                )
                avaliacao_id = str(cur.fetchone()["id"])
            for ordem, q in enumerate(questoes):
                cur.execute(
                    "INSERT INTO avaliacao_questoes (avaliacao_id, enunciado, peso, ordem) VALUES (%s, %s, %s, %s) RETURNING id",
                    (avaliacao_id, q["enunciado"], q.get("peso", 1), ordem),
                )
                questao_id = str(cur.fetchone()["id"])
                for ordem_a, a in enumerate(q["alternativas"]):
                    cur.execute(
                        "INSERT INTO avaliacao_alternativas (questao_id, texto, correta, ordem) VALUES (%s, %s, %s, %s)",
                        (questao_id, a["texto"], bool(a.get("correta")), ordem_a),
                    )
        return avaliacao_id

    def set_ativo(self, avaliacao_id: str, ativo: bool) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE avaliacoes SET ativo = %s, atualizado_em = now() WHERE id = %s", (ativo, str(avaliacao_id)))

    # ---------------- aluno ----------------

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, modalidade, status, polo_id, escola_id FROM alunos WHERE usuario_id = %s LIMIT 1",
                        (str(usuario_id),))
            return _limpar(cur.fetchone())

    def list_disciplinas_licenciadas(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT la.id AS licenca_id, la.materia_id AS disciplina_id, d.nome AS disciplina_nome, d.curso_id
                  FROM licencas_alunos la JOIN disciplinas d ON d.id = la.materia_id
                 WHERE la.aluno_id = %s AND la.status = 'ativa'
                 ORDER BY d.nome
                """,
                (str(aluno_id),),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def get_licenca_ativa(self, aluno_id: str, disciplina_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM licencas_alunos WHERE aluno_id = %s AND materia_id = %s AND status = 'ativa' LIMIT 1",
                (str(aluno_id), str(disciplina_id)),
            )
            return _limpar(cur.fetchone())

    def turma_do_aluno(self, aluno_id: str, disciplina_id: str) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT t.id FROM turma_alunos ta JOIN turmas t ON t.id = ta.turma_id
                  JOIN disciplinas d ON d.curso_id = t.curso_id
                 WHERE ta.aluno_id = %s AND d.id = %s
                 ORDER BY t.data_inicio DESC NULLS LAST LIMIT 1
                """,
                (str(aluno_id), str(disciplina_id)),
            )
            row = cur.fetchone()
            return str(row["id"]) if row else None

    def list_tentativas(self, avaliacao_id: str, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM avaliacao_tentativas WHERE avaliacao_id = %s AND aluno_id = %s ORDER BY iniciada_em",
                        (str(avaliacao_id), str(aluno_id)))
            return [_limpar(r) for r in cur.fetchall()]

    def criar_tentativa(self, dados: Dict[str, Any]) -> str:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO avaliacao_tentativas (avaliacao_id, aluno_id, licenca_id, contexto, ordem_questoes, expira_em)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (dados["avaliacao_id"], dados["aluno_id"], dados.get("licenca_id"), dados.get("contexto", "prova_licenca"),
                 Json(dados.get("ordem_questoes") or []), dados.get("expira_em")),
            )
            return str(cur.fetchone()["id"])

    def get_tentativa(self, tentativa_id: str) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(tentativa_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM avaliacao_tentativas WHERE id = %s", (str(tentativa_id),))
            return _limpar(cur.fetchone())

    def salvar_respostas(self, tentativa_id: str, respostas: Dict[str, str]) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE avaliacao_tentativas SET respostas = %s WHERE id = %s AND status = 'em_andamento'",
                        (Json(respostas), str(tentativa_id)))

    def finalizar_tentativa(self, tentativa_id: str, nota: float, status: str, nota_id: Optional[str]) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE avaliacao_tentativas SET nota = %s, status = %s, nota_id = %s, finalizada_em = now() WHERE id = %s",
                (nota, status, nota_id, str(tentativa_id)),
            )


class InMemoryAvaliacoesRepository:
    def __init__(self) -> None:
        self.disciplinas: Dict[str, Dict[str, Any]] = {}
        self.avaliacoes: Dict[str, Dict[str, Any]] = {}
        self.alunos: Dict[str, Dict[str, Any]] = {}  # usuario_id -> aluno
        self.licencas: List[Dict[str, Any]] = []     # {id, aluno_id, materia_id, status}
        self.turmas: Dict[tuple, str] = {}           # (aluno_id, disciplina_id) -> turma_id
        self.tentativas: Dict[str, Dict[str, Any]] = {}

    def get_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        d = self.disciplinas.get(str(disciplina_id))
        return {"id": str(disciplina_id), **d} if d else None

    def list_avaliacoes(self, disciplina_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return [{"id": a["id"], "disciplina_id": a["disciplina_id"], "titulo": a["titulo"], "ativo": a["ativo"],
                 "origem": a["origem"], "total_questoes": len(a["questoes"])}
                for a in self.avaliacoes.values() if not disciplina_id or a["disciplina_id"] == str(disciplina_id)]

    def get_avaliacao(self, avaliacao_id: str) -> Optional[Dict[str, Any]]:
        a = self.avaliacoes.get(str(avaliacao_id))
        if not a:
            return None
        import copy
        out = copy.deepcopy(a)
        out["disciplina_nome"] = (self.disciplinas.get(a["disciplina_id"]) or {}).get("nome")
        return out

    def get_avaliacao_da_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        for a in self.avaliacoes.values():
            if a["disciplina_id"] == str(disciplina_id):
                return self.get_avaliacao(a["id"])
        return None

    def salvar_avaliacao(self, disciplina_id: str, dados: Dict[str, Any], questoes: List[Dict[str, Any]],
                         usuario_id: Optional[str], origem: str = "manual") -> str:
        atual = self.get_avaliacao_da_disciplina(disciplina_id)
        avaliacao_id = atual["id"] if atual else str(uuid.uuid4())
        self.avaliacoes[avaliacao_id] = {
            "id": avaliacao_id, "disciplina_id": str(disciplina_id), "origem": origem, "atualizado_em": _agora(),
            **dados,
            "questoes": [
                {"id": str(uuid.uuid4()), "enunciado": q["enunciado"], "peso": float(q.get("peso", 1)), "ordem": i,
                 "alternativas": [{"id": str(uuid.uuid4()), "texto": a["texto"], "correta": bool(a.get("correta")),
                                   "ordem": j} for j, a in enumerate(q["alternativas"])]}
                for i, q in enumerate(questoes)
            ],
        }
        return avaliacao_id

    def set_ativo(self, avaliacao_id: str, ativo: bool) -> None:
        self.avaliacoes[str(avaliacao_id)]["ativo"] = ativo

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        a = self.alunos.get(str(usuario_id))
        return dict(a) if a else None

    def list_disciplinas_licenciadas(self, aluno_id: str) -> List[Dict[str, Any]]:
        saida = []
        for lic in self.licencas:
            if lic["aluno_id"] == aluno_id and lic["status"] == "ativa":
                d = self.disciplinas.get(lic["materia_id"], {})
                saida.append({"licenca_id": lic["id"], "disciplina_id": lic["materia_id"],
                              "disciplina_nome": d.get("nome"), "curso_id": d.get("curso_id")})
        return saida

    def get_licenca_ativa(self, aluno_id: str, disciplina_id: str) -> Optional[Dict[str, Any]]:
        for lic in self.licencas:
            if lic["aluno_id"] == aluno_id and lic["materia_id"] == str(disciplina_id) and lic["status"] == "ativa":
                return dict(lic)
        return None

    def turma_do_aluno(self, aluno_id: str, disciplina_id: str) -> Optional[str]:
        return self.turmas.get((aluno_id, str(disciplina_id)))

    def list_tentativas(self, avaliacao_id: str, aluno_id: str) -> List[Dict[str, Any]]:
        return sorted((dict(t) for t in self.tentativas.values()
                       if t["avaliacao_id"] == str(avaliacao_id) and t["aluno_id"] == aluno_id),
                      key=lambda t: t["iniciada_em"])

    def criar_tentativa(self, dados: Dict[str, Any]) -> str:
        tid = str(uuid.uuid4())
        self.tentativas[tid] = {"id": tid, "status": "em_andamento", "respostas": {}, "nota": None,
                                "iniciada_em": _agora(), "finalizada_em": None, "contexto": "prova_licenca", **dados}
        return tid

    def get_tentativa(self, tentativa_id: str) -> Optional[Dict[str, Any]]:
        t = self.tentativas.get(str(tentativa_id))
        return dict(t) if t else None

    def salvar_respostas(self, tentativa_id: str, respostas: Dict[str, str]) -> None:
        t = self.tentativas[str(tentativa_id)]
        if t["status"] == "em_andamento":
            t["respostas"] = dict(respostas)

    def finalizar_tentativa(self, tentativa_id: str, nota: float, status: str, nota_id: Optional[str]) -> None:
        self.tentativas[str(tentativa_id)].update(nota=nota, status=status, nota_id=nota_id, finalizada_em=_agora())


_repo: Optional[AvaliacoesRepositoryInterface] = None


def get_avaliacoes_repository() -> AvaliacoesRepositoryInterface:
    global _repo
    if _repo is None:
        _repo = PostgresAvaliacoesRepository()
    return _repo


def set_avaliacoes_repository(repo: Optional[AvaliacoesRepositoryInterface]) -> None:
    global _repo
    _repo = repo
