"""DDL do banco de destino (PostgreSQL / NeonDB). Fonte: secao 3 do plano tecnico.

Convencoes:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `criado_em` / `atualizado_em TIMESTAMPTZ DEFAULT now()`
- Rastreabilidade do legado em toda tabela com origem:
  `legacy_table VARCHAR(64)`, `legacy_id BIGINT`, `synced_at TIMESTAMPTZ`
  + UNIQUE (legacy_table, legacy_id) -> habilita o UPSERT idempotente.

Os comandos estao ordenados por dependencia de FK.
"""
from __future__ import annotations

from typing import List

TRACKING = """    legacy_table VARCHAR(64),
    legacy_id BIGINT,
    synced_at TIMESTAMPTZ DEFAULT now(),
"""
UNIQUE_LEGACY = ",\n    UNIQUE (legacy_table, legacy_id)"


def _tbl(name: str, cols: str, *, tracking: bool = True) -> str:
    return (
        f"CREATE TABLE IF NOT EXISTS {name} (\n"
        f"    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
        f"{cols},\n"
        f"{TRACKING if tracking else ''}"
        f"    criado_em TIMESTAMPTZ DEFAULT now(),\n"
        f"    atualizado_em TIMESTAMPTZ DEFAULT now()"
        f"{UNIQUE_LEGACY if tracking else ''}\n"
        f");"
    )


DDL: List[str] = [
    # ---------- 3.1 Autenticacao & Usuarios ----------
    _tbl(
        "perfis",
        """    nome VARCHAR(32) NOT NULL UNIQUE,
    descricao TEXT""",
    ),
    _tbl(
        "permissoes",
        """    chave VARCHAR(64) NOT NULL UNIQUE,
    descricao TEXT""",
    ),
    # ---------- 3.2 Polos / Escolas ----------
    _tbl(
        "polos",
        """    nome VARCHAR(255) NOT NULL,
    responsavel_nome VARCHAR(255),
    responsavel_cpf VARCHAR(20),
    responsavel_email VARCHAR(255),
    cep VARCHAR(16),
    logradouro VARCHAR(255),
    numero VARCHAR(32),
    bairro VARCHAR(255),
    cidade VARCHAR(255),
    uf VARCHAR(2),
    complemento VARCHAR(255),
    status VARCHAR(16) DEFAULT 'ativo'""",
    ),
    _tbl(
        "escolas",
        """    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    nome VARCHAR(255) NOT NULL,
    responsavel_nome VARCHAR(255),
    responsavel_cpf VARCHAR(20),
    responsavel_email VARCHAR(255),
    cep VARCHAR(16),
    logradouro VARCHAR(255),
    numero VARCHAR(32),
    bairro VARCHAR(255),
    cidade VARCHAR(255),
    uf VARCHAR(2),
    complemento VARCHAR(255),
    status VARCHAR(16) DEFAULT 'ativo'""",
    ),
    _tbl(
        "usuarios",
        """    nome VARCHAR(255) NOT NULL DEFAULT '',
    sobrenome VARCHAR(255) DEFAULT '',
    email VARCHAR(255),
    cpf VARCHAR(20),
    senha_hash VARCHAR(255),
    senha_algoritmo VARCHAR(16) DEFAULT 'legacy_bcrypt',
    telefone VARCHAR(64),
    celular VARCHAR(64),
    foto_url VARCHAR(500),
    perfil_id UUID REFERENCES perfis(id) ON DELETE SET NULL,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    status VARCHAR(16) DEFAULT 'ativo',
    ultimo_login_em TIMESTAMPTZ""",
    ),
    "ALTER TABLE polos ADD COLUMN IF NOT EXISTS coordenador_usuario_id UUID REFERENCES usuarios(id);",
    _tbl(
        "usuario_permissoes",
        """    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permissao_id UUID NOT NULL REFERENCES permissoes(id) ON DELETE CASCADE,
    UNIQUE (usuario_id, permissao_id)""",
        tracking=False,
    ),
    # ---------- 3.3 Professores ----------
    _tbl(
        "professores",
        """    usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    chave_pix VARCHAR(255),
    valor_hora_aula NUMERIC(10,2),
    data_inicio_aulas TIMESTAMPTZ""",
    ),
    # ---------- 3.5/3.6 Cursos / Disciplinas / Turmas (criadas antes dos filhos) ----------
    _tbl(
        "cursos",
        """    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    modalidade VARCHAR(16) DEFAULT 'hibrido',
    carga_horaria_total INT,
    semestres INT DEFAULT 3,
    status VARCHAR(16) DEFAULT 'ativo'""",
    ),
    _tbl(
        "disciplinas",
        """    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    semestre INT,
    nome VARCHAR(255) NOT NULL,
    ordem INT DEFAULT 0,
    carga_horaria INT,
    qtd_aulas_prevista INT,
    tipo VARCHAR(16) DEFAULT 'presencial',
    eh_extra_grade BOOLEAN DEFAULT false""",
    ),
    _tbl(
        "calendarios_oficiais",
        """    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    data_liberacao DATE,
    data_encerramento DATE""",
    ),
    _tbl(
        "turmas",
        """    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    nome VARCHAR(255) NOT NULL,
    data_inicio DATE,
    data_fim DATE,
    calendario_oficial_id UUID REFERENCES calendarios_oficiais(id) ON DELETE SET NULL""",
    ),
    _tbl(
        "disciplina_conteudos",
        """    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE CASCADE,
    titulo VARCHAR(255),
    tipo_midia VARCHAR(32),
    url_arquivo VARCHAR(500),
    ordem INT DEFAULT 0""",
    ),
    _tbl(
        "professor_disciplinas",
        """    professor_id UUID REFERENCES professores(id) ON DELETE CASCADE,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE CASCADE,
    turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL,
    qtd_aulas_prevista INT,
    carga_horaria_total INT,
    conteudo_programatico TEXT""",
    ),
    _tbl(
        "professor_materiais",
        """    professor_disciplina_id UUID REFERENCES professor_disciplinas(id) ON DELETE CASCADE,
    arquivo_url VARCHAR(500),
    data_aula DATE,
    descricao TEXT,
    expira_em TIMESTAMPTZ""",
    ),
    _tbl(
        "atas_aula",
        """    professor_disciplina_id UUID REFERENCES professor_disciplinas(id) ON DELETE CASCADE,
    numero_aula INT,
    data_aula DATE,
    conteudo_ata TEXT""",
    ),
    # ---------- 3.4 Alunos ----------
    _tbl(
        "alunos",
        """    usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    modalidade VARCHAR(16) DEFAULT 'polo',
    numero_matricula VARCHAR(32) UNIQUE,
    data_nascimento DATE,
    status VARCHAR(16) DEFAULT 'ativo',
    ultima_movimentacao_em TIMESTAMPTZ""",
    ),
    _tbl(
        "alunos_desistentes",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    motivo TEXT,
    data_marcacao TIMESTAMPTZ DEFAULT now(),
    taxa_regularizacao_paga BOOLEAN DEFAULT false""",
    ),
    # ---------- 3.7 EAD ----------
    _tbl(
        "matriculas_ead",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    ativa_automaticamente BOOLEAN DEFAULT false,
    data_matricula TIMESTAMPTZ""",
    ),
    _tbl(
        "compras_disciplina_ead",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    valor_pago NUMERIC(10,2),
    status_pagamento VARCHAR(32) DEFAULT 'pendente',
    liberada_em TIMESTAMPTZ,
    prazo_conclusao TIMESTAMPTZ,
    reprovado_por_prazo BOOLEAN DEFAULT false""",
    ),
    _tbl(
        "avisos_liberacao_ead",
        """    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE CASCADE,
    data_liberacao DATE,
    notificado_em TIMESTAMPTZ""",
    ),
    _tbl(
        "turma_alunos",
        """    turma_id UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    data_matricula TIMESTAMPTZ,
    status VARCHAR(16) DEFAULT 'ativo',
    UNIQUE (turma_id, aluno_id)""",
        tracking=False,
    ),
    # ---------- 3.8 Grades (Notas) & Historico ----------
    _tbl(
        "notas",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL,
    origem VARCHAR(16) DEFAULT 'ava',
    valor NUMERIC(4,2),
    lancado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    lancado_em TIMESTAMPTZ""",
    ),
    _tbl(
        "historico_unificado",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    nota_final NUMERIC(4,2),
    status VARCHAR(16) DEFAULT 'cursando',
    eh_extra_grade BOOLEAN DEFAULT false,
    UNIQUE (aluno_id, disciplina_id)""",
        tracking=False,
    ),
    _tbl(
        "certificados",
        """    aluno_id UUID REFERENCES alunos(id) ON DELETE SET NULL,
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    data_estagio_teologia_ministerio DATE,
    data_estagio_homiletica DATE,
    emitido_em TIMESTAMPTZ,
    url_arquivo VARCHAR(500)""",
    ),
    # ---------- 3.9 Presenca ----------
    _tbl(
        "presencas",
        """    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    professor_disciplina_id UUID REFERENCES professor_disciplinas(id) ON DELETE SET NULL,
    numero_aula INT,
    data_aula DATE,
    presente BOOLEAN DEFAULT false""",
    ),
    # ---------- 3.10 Licencas ----------
    _tbl(
        "estoque_licencas",
        """    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    quantidade_total INT DEFAULT 0,
    quantidade_disponivel INT DEFAULT 0""",
        tracking=False,
    ),
    _tbl(
        "licencas_atribuidas",
        """    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    aluno_id UUID REFERENCES alunos(id) ON DELETE SET NULL,
    quantidade INT DEFAULT 0,
    atribuido_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    atribuido_em TIMESTAMPTZ""",
    ),
    # ---------- 3.11 Vendas / Financeiro ----------
    _tbl(
        "pedidos_licenca",
        """    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    itens JSONB,
    valor_total NUMERIC(12,2),
    status VARCHAR(16) DEFAULT 'pendente'""",
    ),
    _tbl(
        "pagamentos",
        """    pedido_licenca_id UUID REFERENCES pedidos_licenca(id) ON DELETE SET NULL,
    compra_disciplina_ead_id UUID REFERENCES compras_disciplina_ead(id) ON DELETE SET NULL,
    gateway VARCHAR(32) DEFAULT 'legado',
    asaas_customer_id VARCHAR(64),
    asaas_payment_id VARCHAR(64),
    billing_type VARCHAR(32),
    valor NUMERIC(12,2),
    status VARCHAR(32),
    boleto_url VARCHAR(500),
    vencimento_em DATE,
    pago_em TIMESTAMPTZ""",
    ),
    _tbl(
        "cupons",
        """    codigo VARCHAR(64) UNIQUE,
    percentual_desconto NUMERIC(5,2),
    valido_de DATE,
    valido_ate DATE""",
    ),
    # ---------- 3.12 Orders (Logistica) ----------
    _tbl(
        "pedidos_livros",
        """    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    status VARCHAR(16) DEFAULT 'pendente',
    enviado_em TIMESTAMPTZ""",
    ),
    _tbl(
        "pedidos_livros_itens",
        """    pedido_livro_id UUID NOT NULL REFERENCES pedidos_livros(id) ON DELETE CASCADE,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    quantidade INT DEFAULT 1""",
    ),
    # ---------- 3.13 Transferencias ----------
    _tbl(
        "solicitacoes_transferencia",
        """    aluno_id UUID REFERENCES alunos(id) ON DELETE SET NULL,
    tipo VARCHAR(32) NOT NULL,
    polo_origem_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    polo_destino_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    solicitado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    status VARCHAR(16) DEFAULT 'pendente',
    resolvido_em TIMESTAMPTZ""",
    ),
    # ---------- 3.14 Chat ----------
    _tbl(
        "conversas",
        """    tipo VARCHAR(16) DEFAULT 'individual',
    criada_em TIMESTAMPTZ DEFAULT now(),
    encerrada_em TIMESTAMPTZ""",
    ),
    _tbl(
        "conversa_membros",
        """    conversa_id UUID NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE (conversa_id, usuario_id)""",
        tracking=False,
    ),
    _tbl(
        "mensagens",
        """    conversa_id UUID NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
    remetente_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    texto TEXT,
    lida_em TIMESTAMPTZ""",
    ),
    # ---------- 3.15 Notificacoes / Feed ----------
    _tbl(
        "feed_posts",
        """    autor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo VARCHAR(255),
    conteudo TEXT""",
    ),
    _tbl(
        "lembretes",
        """    usuario_destino_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    perfil_destino UUID REFERENCES perfis(id) ON DELETE SET NULL,
    titulo VARCHAR(255),
    mensagem TEXT,
    exibir_de DATE,
    exibir_ate DATE""",
    ),
    _tbl(
        "notificacoes",
        """    usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(255),
    mensagem TEXT,
    lida BOOLEAN DEFAULT false""",
    ),
    # ---------- 3.16 Admin / Auditoria ----------
    _tbl(
        "configuracoes",
        """    chave VARCHAR(255) NOT NULL UNIQUE,
    valor JSONB""",
    ),
    _tbl(
        "logs_auditoria",
        """    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    acao VARCHAR(64) NOT NULL,
    entidade VARCHAR(64),
    entidade_id VARCHAR(64),
    dados_antes JSONB,
    dados_depois JSONB,
    ip INET""",
        tracking=False,
    ),
    # ---------- Sessoes / Recuperacao (runtime, sem origem legado) ----------
    _tbl(
        "refresh_tokens",
        """    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expira_em TIMESTAMPTZ NOT NULL,
    revogado_em TIMESTAMPTZ,
    criado_por_ip INET""",
        tracking=False,
    ),
    _tbl(
        "password_reset",
        """    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expira_em TIMESTAMPTZ NOT NULL,
    usado_em TIMESTAMPTZ""",
        tracking=False,
    ),
    _tbl(
        "login_tentativas",
        """    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    email VARCHAR(255),
    ip VARCHAR(64),
    sucesso BOOLEAN DEFAULT false""",
        tracking=False,
    ),
    # ---------- Controle do ETL ----------
    """
CREATE TABLE IF NOT EXISTS etl_sync_runs (
    id BIGSERIAL PRIMARY KEY,
    modo VARCHAR(16) NOT NULL,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ,
    total_lido BIGINT DEFAULT 0,
    total_inserido BIGINT DEFAULT 0,
    total_atualizado BIGINT DEFAULT 0,
    total_erro BIGINT DEFAULT 0,
    status VARCHAR(16) DEFAULT 'rodando'
);
""",
    """
CREATE TABLE IF NOT EXISTS etl_erros (
    id BIGSERIAL PRIMARY KEY,
    execucao_id BIGINT REFERENCES etl_sync_runs(id) ON DELETE CASCADE,
    tabela_origem VARCHAR(64),
    id_origem VARCHAR(255),
    erro TEXT,
    linha_raw JSONB,
    criado_em TIMESTAMPTZ DEFAULT now()
);
""",
    # ---------- Indices complementares (unicidade de e-mail/cpf) ----------
    """
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_email ON usuarios (email) WHERE email IS NOT NULL;
""",
    """
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_cpf ON usuarios (cpf) WHERE cpf IS NOT NULL;
""",
]