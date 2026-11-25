"""Consultas da ficha cadastral do usuário (dados pessoais, vínculos, histórico e exclusão).

Mixins usados por `PostgresAdminRepository` e `InMemoryAdminRepository`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor

CAMPOS_CADASTRAIS = (
    "data_nascimento", "rg", "rg_orgao_emissor", "rg_uf", "sexo", "estado_civil",
    "naturalidade_cidade", "naturalidade_uf", "nacionalidade",
    "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf",
    "contato_emergencia_nome", "contato_emergencia_parentesco", "contato_emergencia_telefone",
    "inativado_em", "inativado_por", "motivo_inativacao",
)

# Registros que tornam o usuário "com histórico": a exclusão definitiva apagaria (cascata) ou
# anonimizaria (SET NULL) esses dados. (rótulo, tabela, coluna, de quem: usuario|aluno|professor)
FONTES_HISTORICO: Tuple[Tuple[str, str, str, str], ...] = (
    ("notas", "notas", "aluno_id", "aluno"),
    ("presenças", "presencas", "aluno_id", "aluno"),
    ("turmas", "turma_alunos", "aluno_id", "aluno"),
    ("histórico acadêmico", "historico_unificado", "aluno_id", "aluno"),
    ("estágios", "estagio_submissoes", "aluno_id", "aluno"),
    ("matrículas EAD", "matriculas_ead", "aluno_id", "aluno"),
    ("licenças", "licencas_alunos", "aluno_id", "aluno"),
    ("licenças atribuídas", "licencas_atribuidas", "aluno_id", "aluno"),
    ("certificados", "certificados", "aluno_id", "aluno"),
    ("pagamentos", "pagamentos", "aluno_id", "aluno"),
    ("transferências", "solicitacoes_transferencia", "aluno_id", "aluno"),
    ("desistências", "alunos_desistentes", "aluno_id", "aluno"),
    ("vínculos docentes", "professor_disciplinas", "professor_id", "professor"),
    ("aulas", "aulas", "professor_id", "professor"),
    ("pedidos", "pedidos", "solicitante_id", "usuario"),
    ("atas de aula", "aulas_ministradas", "criado_por", "usuario"),
    ("mensagens do chat", "chat_mensagens", "remetente_id", "usuario"),
    ("mensagens", "mensagens", "remetente_id", "usuario"),
    ("ações registradas na auditoria", "logs_auditoria", "usuario_id", "usuario"),
)


def _limpar(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


class PostgresFichaMixin:
    def nomes_unidade(self, polo_id: Optional[str], escola_id: Optional[str]) -> Dict[str, Optional[str]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT (SELECT nome FROM polos WHERE id = %s::uuid) AS polo_nome, "
                "(SELECT nome FROM escolas WHERE id = %s::uuid) AS escola_nome",
                (polo_id, escola_id),
            )
            return _limpar(cur.fetchone())

    def get_dados_cadastrais(self, user_id: str) -> Dict[str, Any]:
        colunas = ", ".join(f"u.{c}" for c in CAMPOS_CADASTRAIS)
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT {colunas},
                       NULLIF(TRIM(CONCAT_WS(' ', ip.nome, ip.sobrenome)), '') AS inativado_por_nome
                  FROM usuarios u
                  LEFT JOIN usuarios ip ON ip.id = u.inativado_por
                 WHERE u.id = %s
                """,
                (str(user_id),),
            )
            return _limpar(cur.fetchone())

    def update_aluno_campos(self, aluno_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        sets = ", ".join(f"{k} = %s" for k in data)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE alunos SET {sets}, atualizado_em = now() WHERE id = %s",
                (*data.values(), str(aluno_id)),
            )

    def numero_matricula_em_uso(self, numero: str, exceto_aluno_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT 1 FROM alunos WHERE numero_matricula = %s AND id <> %s LIMIT 1",
                (numero, str(exceto_aluno_id)),
            )
            return cur.fetchone() is not None

    def update_professor_campos(self, professor_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        sets = ", ".join(f"{k} = %s" for k in data)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE professores SET {sets}, atualizado_em = now() WHERE id = %s",
                (*data.values(), str(professor_id)),
            )

    def vinculos_docentes(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT pd.id::text AS professor_disciplina_id, t.id::text AS turma_id, t.nome AS turma_nome,
                       c.nome AS curso_nome, d.id::text AS disciplina_id, d.nome AS disciplina_nome,
                       COALESCE(NULLIF(pd.carga_horaria_total, 0), d.carga_horaria) AS carga_horaria,
                       COALESCE(NULLIF(pd.qtd_aulas_prevista, 0), d.qtd_aulas_prevista) AS aulas_previstas,
                       COALESCE(pd.ativo, true) AS ativo,
                       (SELECT COUNT(*) FROM aulas_ministradas am
                         WHERE am.professor_disciplina_id = pd.id) AS aulas_ministradas,
                       (SELECT COALESCE(SUM(am.horas), 0) FROM aulas_ministradas am
                         WHERE am.professor_disciplina_id = pd.id
                           AND COALESCE(am.tipo, 'prevista') IN ('prevista', 'reposicao')) AS horas_ministradas
                  FROM professor_disciplinas pd
                  LEFT JOIN turmas t ON t.id = pd.turma_id
                  LEFT JOIN cursos c ON c.id = t.curso_id
                  LEFT JOIN disciplinas d ON d.id = pd.disciplina_id
                 WHERE pd.professor_id = %s
                 ORDER BY t.nome NULLS LAST, d.nome
                """,
                (str(professor_id),),
            )
            return [dict(r) for r in cur.fetchall()]

    def aulas_do_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT am.id::text AS id, am.data_aula, am.numero_aula, COALESCE(am.tipo, 'prevista') AS tipo,
                       am.horas, d.nome AS disciplina_nome, t.nome AS turma_nome, t.id::text AS turma_id
                  FROM aulas_ministradas am
                  JOIN professor_disciplinas pd ON pd.id = am.professor_disciplina_id
                  LEFT JOIN disciplinas d ON d.id = pd.disciplina_id
                  LEFT JOIN turmas t ON t.id = pd.turma_id
                 WHERE pd.professor_id = %s
                 ORDER BY am.data_aula DESC, am.numero_aula DESC
                """,
                (str(professor_id),),
            )
            return [dict(r) for r in cur.fetchall()]

    def transferencia_pendente(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT st.id::text AS id, st.tipo, st.criado_em,
                       pd.nome AS polo_destino_nome, ed.nome AS escola_destino_nome
                  FROM solicitacoes_transferencia st
                  LEFT JOIN polos pd ON pd.id = st.polo_destino_id
                  LEFT JOIN escolas ed ON ed.id = st.escola_destino_id
                 WHERE st.aluno_id = %s AND st.status = 'pendente'
                 ORDER BY st.criado_em DESC
                 LIMIT 1
                """,
                (str(aluno_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def revogar_sessoes(self, user_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revogado_em = now(), atualizado_em = now() "
                "WHERE usuario_id = %s AND revogado_em IS NULL",
                (str(user_id),),
            )
            return cur.rowcount or 0

    def historico_existente(
        self, user_id: str, aluno_id: Optional[str], professor_id: Optional[str]
    ) -> List[str]:
        """Uma consulta só (mais a checagem das tabelas, feita uma vez por processo)."""
        ids = {"usuario": str(user_id), "aluno": aluno_id, "professor": professor_id}
        with get_db_cursor() as cur:
            existentes = self._tabelas_historico(cur)
            fontes = [f for f in FONTES_HISTORICO if ids[f[3]] and f[1] in existentes]
            if not fontes:
                return []
            colunas = ", ".join(
                f"EXISTS (SELECT 1 FROM {tabela} WHERE {coluna} = %s) AS c{i}"
                for i, (_, tabela, coluna, _) in enumerate(fontes)
            )
            cur.execute(f"SELECT {colunas}", tuple(ids[dono] for *_, dono in fontes))
            row = cur.fetchone()
        return [rotulo for i, (rotulo, *_) in enumerate(fontes) if row[f"c{i}"]]

    _tabelas_existentes: Optional[frozenset] = None

    @classmethod
    def _tabelas_historico(cls, cur: Any) -> frozenset:
        if cls._tabelas_existentes is None:
            nomes = sorted({f[1] for f in FONTES_HISTORICO})
            colunas = ", ".join(f"to_regclass(%s) IS NOT NULL AS t{i}" for i in range(len(nomes)))
            cur.execute(f"SELECT {colunas}", tuple(nomes))
            row = cur.fetchone()
            cls._tabelas_existentes = frozenset(n for i, n in enumerate(nomes) if row[f"t{i}"])
        return cls._tabelas_existentes

    # ---------- Histórico ----------

    def _listar(self, sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def turmas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT t.id::text AS turma_id, t.nome AS turma_nome, c.nome AS curso_nome,
                   COALESCE(ta.status, 'ativo') AS status, ta.data_matricula,
                   t.data_inicio, t.data_fim, t.concluida_em
              FROM turma_alunos ta
              JOIN turmas t ON t.id = ta.turma_id
              LEFT JOIN cursos c ON c.id = t.curso_id
             WHERE ta.aluno_id = %s
             ORDER BY t.data_inicio DESC NULLS LAST, t.nome
            """,
            (str(aluno_id),),
        )

    def notas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT n.id::text AS id, d.nome AS disciplina_nome, t.nome AS turma_nome, n.valor, n.origem,
                   COALESCE(n.lancado_em, n.criado_em) AS data
              FROM notas n
              LEFT JOIN disciplinas d ON d.id = n.disciplina_id
              LEFT JOIN turmas t ON t.id = n.turma_id
             WHERE n.aluno_id = %s
             ORDER BY data DESC NULLS LAST
            """,
            (str(aluno_id),),
        )

    def certificados_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT ce.id::text AS id, cu.nome AS curso_nome, ce.emitido_em, ce.url_arquivo
              FROM certificados ce
              LEFT JOIN cursos cu ON cu.id = ce.curso_id
             WHERE ce.aluno_id = %s
             ORDER BY ce.emitido_em DESC NULLS LAST
            """,
            (str(aluno_id),),
        )

    def estagios_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT id::text AS id, etapa, status, horas, enviado_em, avaliado_em
              FROM estagio_submissoes
             WHERE aluno_id = %s
             ORDER BY enviado_em DESC NULLS LAST
            """,
            (str(aluno_id),),
        )

    def pagamentos_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT id::text AS id, descricao, valor, status, billing_type, vencimento_em, pago_em, criado_em
              FROM pagamentos
             WHERE aluno_id = %s
             ORDER BY COALESCE(vencimento_em, criado_em::date) DESC
            """,
            (str(aluno_id),),
        )

    def pedidos_do_usuario(self, user_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT id::text AS id, numero, tipo, status, valor_total, criado_em
              FROM pedidos
             WHERE solicitante_id = %s
             ORDER BY criado_em DESC
            """,
            (str(user_id),),
        )

    def licencas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT la.id::text AS id, la.numero_licenca, la.status, la.ativada_em, la.expirada_em,
                   d.nome AS disciplina_nome
              FROM licencas_alunos la
              LEFT JOIN disciplinas d ON d.id = la.materia_id
             WHERE la.aluno_id = %s
             ORDER BY la.ativada_em DESC NULLS LAST
            """,
            (str(aluno_id),),
        )

    def transferencias_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT st.id::text AS id, st.tipo, st.status, st.criado_em, st.resolvido_em,
                   st.observacao, st.motivo_rejeicao,
                   po.nome AS polo_origem_nome, pd.nome AS polo_destino_nome,
                   eo.nome AS escola_origem_nome, ed.nome AS escola_destino_nome
              FROM solicitacoes_transferencia st
              LEFT JOIN polos po ON po.id = st.polo_origem_id
              LEFT JOIN polos pd ON pd.id = st.polo_destino_id
              LEFT JOIN escolas eo ON eo.id = st.escola_origem_id
              LEFT JOIN escolas ed ON ed.id = st.escola_destino_id
             WHERE st.aluno_id = %s
             ORDER BY st.criado_em DESC
            """,
            (str(aluno_id),),
        )

    def desistencias_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._listar(
            """
            SELECT id::text AS id, motivo, data_marcacao, reingresso_em, matricula_anterior
              FROM alunos_desistentes
             WHERE aluno_id = %s
             ORDER BY data_marcacao DESC NULLS LAST
            """,
            (str(aluno_id),),
        )

    def auditoria_de_entidades(
        self, entidade_ids: Sequence[str], acoes: Optional[Sequence[str]], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        filtro = " AND l.acao = ANY(%s)" if acoes else ""
        params: List[Any] = [list(entidade_ids)] + ([list(acoes)] if acoes else [])
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS total FROM logs_auditoria l WHERE l.entidade_id = ANY(%s){filtro}",
                tuple(params),
            )
            total = int(cur.fetchone()["total"] or 0)
            cur.execute(
                f"""
                SELECT l.id::text AS id, l.acao, l.entidade, l.entidade_id, l.dados_antes, l.dados_depois,
                       l.ip, l.criado_em, l.usuario_id::text AS usuario_id,
                       NULLIF(TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)), '') AS usuario_nome
                  FROM logs_auditoria l
                  LEFT JOIN usuarios u ON u.id = l.usuario_id
                 WHERE l.entidade_id = ANY(%s){filtro}
                 ORDER BY l.criado_em DESC
                 LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]


class InMemoryFichaMixin:
    """Paridade em memória. As tabelas extras ficam em `self.tabelas[nome]` (listas de dicts)."""

    def _tab(self, nome: str) -> List[Dict[str, Any]]:
        atributo = getattr(self, nome, None)
        if isinstance(atributo, list):
            return atributo
        if not hasattr(self, "tabelas"):
            self.tabelas: Dict[str, List[Dict[str, Any]]] = {}
        return self.tabelas.setdefault(nome, [])

    def nomes_unidade(self, polo_id: Optional[str], escola_id: Optional[str]) -> Dict[str, Optional[str]]:
        return {
            "polo_nome": (self.polos.get(str(polo_id)) or {}).get("nome") if polo_id else None,
            "escola_nome": (self.escolas.get(str(escola_id)) or {}).get("nome") if escola_id else None,
        }

    def get_dados_cadastrais(self, user_id: str) -> Dict[str, Any]:
        u = self.usuarios.get(str(user_id)) or {}
        dados = {c: u.get(c) for c in CAMPOS_CADASTRAIS}
        por = self.usuarios.get(str(u.get("inativado_por"))) if u.get("inativado_por") else None
        dados["inativado_por_nome"] = (
            f"{por.get('nome') or ''} {por.get('sobrenome') or ''}".strip() if por else None
        )
        return dados

    def update_aluno_campos(self, aluno_id: str, data: Dict[str, Any]) -> None:
        if str(aluno_id) in self.alunos:
            self.alunos[str(aluno_id)].update(data)

    def numero_matricula_em_uso(self, numero: str, exceto_aluno_id: str) -> bool:
        return any(
            a.get("numero_matricula") == numero and str(a.get("id")) != str(exceto_aluno_id)
            for a in self.alunos.values()
        )

    def update_professor_campos(self, professor_id: str, data: Dict[str, Any]) -> None:
        if str(professor_id) in self.professores:
            self.professores[str(professor_id)].update(data)

    def vinculos_docentes(self, professor_id: str) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._tab("professor_disciplinas") if str(v.get("professor_id")) == str(professor_id)]

    def aulas_do_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        return [dict(a) for a in self._tab("aulas_ministradas") if str(a.get("professor_id")) == str(professor_id)]

    def transferencia_pendente(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        for t in self._tab("solicitacoes_transferencia"):
            if str(t.get("aluno_id")) == str(aluno_id) and t.get("status") == "pendente":
                return dict(t)
        return None

    def revogar_sessoes(self, user_id: str) -> int:
        revogados = 0
        for token in self._tab("refresh_tokens"):
            if str(token.get("usuario_id")) == str(user_id) and not token.get("revogado_em"):
                token["revogado_em"] = "agora"
                revogados += 1
        return revogados

    def historico_existente(
        self, user_id: str, aluno_id: Optional[str], professor_id: Optional[str]
    ) -> List[str]:
        ids = {"usuario": str(user_id), "aluno": aluno_id, "professor": professor_id}
        encontrados = []
        for rotulo, tabela, coluna, dono in FONTES_HISTORICO:
            valor = ids[dono]
            if not valor:
                continue
            linhas = self.logs_auditoria if tabela == "logs_auditoria" else self._tab(tabela)
            if any(str(r.get(coluna)) == str(valor) for r in linhas):
                encontrados.append(rotulo)
        return encontrados

    def _do_aluno(self, tabela: str, aluno_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._tab(tabela) if str(r.get("aluno_id")) == str(aluno_id)]

    def turmas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("turma_alunos", aluno_id)

    def notas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("notas", aluno_id)

    def certificados_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("certificados", aluno_id)

    def estagios_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("estagio_submissoes", aluno_id)

    def pagamentos_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("pagamentos", aluno_id)

    def pedidos_do_usuario(self, user_id: str) -> List[Dict[str, Any]]:
        return [dict(p) for p in self._tab("pedidos") if str(p.get("solicitante_id")) == str(user_id)]

    def licencas_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("licencas_alunos", aluno_id)

    def transferencias_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("solicitacoes_transferencia", aluno_id)

    def desistencias_do_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        return self._do_aluno("alunos_desistentes", aluno_id)

    def auditoria_de_entidades(
        self, entidade_ids: Sequence[str], acoes: Optional[Sequence[str]], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        alvo = {str(i) for i in entidade_ids}
        linhas = [
            dict(l) for l in self.logs_auditoria
            if str(l.get("entidade_id")) in alvo and (not acoes or l.get("acao") in acoes)
        ]
        linhas.sort(key=lambda l: str(l.get("criado_em") or ""), reverse=True)
        for l in linhas:
            autor = self.usuarios.get(str(l.get("usuario_id"))) if l.get("usuario_id") else None
            l["usuario_nome"] = f"{autor.get('nome') or ''} {autor.get('sobrenome') or ''}".strip() if autor else None
        return len(linhas), linhas[offset: offset + limit]
