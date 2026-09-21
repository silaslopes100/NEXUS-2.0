"""Schema SQL para o módulo administrativo do NEXUS 2.0."""

-- ==========================================
-- Tabela de Alunos (IF NOT EXISTS — já existe em outros módulos)
-- ==========================================

CREATE TABLE IF NOT EXISTS alunos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    nome VARCHAR(255) NOT NULL,
    sobrenome VARCHAR(255),
    email VARCHAR(255),
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    pais VARCHAR(100),
    estado VARCHAR(100),
    modalidade VARCHAR(20) DEFAULT 'polo',
    numero_matricula VARCHAR(50),
    curso_id UUID,
    semestre SMALLINT,
    ano SMALLINT,
    status VARCHAR(20) DEFAULT 'ativo',
    quantidade_presencas INT DEFAULT 0,
    percentual_presenca FLOAT DEFAULT 0.0,
    ultima_movimentacao_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alunos_polo_id ON alunos(polo_id);
CREATE INDEX IF NOT EXISTS idx_alunos_escola_id ON alunos(escola_id);
CREATE INDEX IF NOT EXISTS idx_alunos_status ON alunos(status);
CREATE INDEX IF NOT EXISTS idx_alunos_cpf ON alunos(cpf);
CREATE INDEX IF NOT EXISTS idx_alunos_ultima_movimentacao ON alunos(ultima_movimentacao_em);

-- ==========================================
-- Polos (RN-01) — FK 1:1 com usuário coordenador
-- ==========================================

CREATE TABLE IF NOT EXISTS polos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    responsavel VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    endereco TEXT NOT NULL,
    logradouro VARCHAR(255),
    numero VARCHAR(50),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    uf VARCHAR(2),
    cep VARCHAR(20),
    usuario_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'ativo',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_polos_status ON polos(status);
CREATE INDEX IF NOT EXISTS idx_polos_email ON polos(email);
CREATE INDEX IF NOT EXISTS idx_polos_cpf ON polos(cpf);
CREATE INDEX IF NOT EXISTS idx_polos_usuario_id ON polos(usuario_id);

-- ==========================================
-- Escolas (RN-01) — FK 1:1 com usuário secretário
-- ==========================================

CREATE TABLE IF NOT EXISTS escolas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    polo_id UUID NOT NULL REFERENCES polos(id) ON DELETE CASCADE,
    responsavel VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    endereco TEXT NOT NULL,
    logradouro VARCHAR(255),
    numero VARCHAR(50),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    uf VARCHAR(2),
    cep VARCHAR(20),
    usuario_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'ativo',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escolas_polo_id ON escolas(polo_id);
CREATE INDEX IF NOT EXISTS idx_escolas_status ON escolas(status);
CREATE INDEX IF NOT EXISTS idx_escolas_email ON escolas(email);
CREATE INDEX IF NOT EXISTS idx_escolas_usuario_id ON escolas(usuario_id);

-- ==========================================
-- Cursos / Módulos / Matérias
-- ==========================================

CREATE TABLE IF NOT EXISTS cursos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    carga_horaria INT,
    grade_curricular JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'ativo',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cursos_nome ON cursos(LOWER(nome));

CREATE TABLE IF NOT EXISTS modulos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id UUID NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    ordem SMALLINT NOT NULL,
    conteudo TEXT,
    carga_horaria INT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(curso_id, ordem)
);

CREATE INDEX IF NOT EXISTS idx_modulos_curso_id ON modulos(curso_id);

CREATE TABLE IF NOT EXISTS materias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    modulo_id UUID REFERENCES modulos(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    carga_horaria INT,
    total_aulas_previstas INT DEFAULT 0,
    ordem SMALLINT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_materias_curso_id ON materias(curso_id);
CREATE INDEX IF NOT EXISTS idx_materias_modulo_id ON materias(modulo_id);

-- ==========================================
-- Matrículas
-- ==========================================

CREATE TABLE IF NOT EXISTS matriculas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    aluno_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    semestre SMALLINT,
    ano SMALLINT,
    status VARCHAR(20) DEFAULT 'ativa',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matriculas_polo_id ON matriculas(polo_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_escola_id ON matriculas(escola_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_aluno_id ON matriculas(aluno_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_status ON matriculas(status);
CREATE INDEX IF NOT EXISTS idx_matriculas_ano_semestre ON matriculas(ano, semestre);

-- ==========================================
-- Matrículas EAD
-- ==========================================

CREATE TABLE IF NOT EXISTS matriculas_ead (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'ativa',
    progresso FLOAT DEFAULT 0.0,
    ultimo_acesso_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matriculas_ead_aluno_id ON matriculas_ead(aluno_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_ead_status ON matriculas_ead(status);

-- ==========================================
-- Licenças / Estoque
-- ==========================================

CREATE TABLE IF NOT EXISTS licencas_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'licenca',
    quantidade INT NOT NULL DEFAULT 0,
    polo_destino_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(materia_id, tipo, polo_destino_id)
);

CREATE INDEX IF NOT EXISTS idx_licencas_estoque_materia ON licencas_estoque(materia_id);
CREATE INDEX IF NOT EXISTS idx_licencas_estoque_tipo ON licencas_estoque(tipo);

CREATE TABLE IF NOT EXISTS licencas_movimentacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    estoque_id UUID REFERENCES licencas_estoque(id) ON DELETE SET NULL,
    tipo_movimento VARCHAR(20) NOT NULL,
    quantidade INT NOT NULL,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_licencas_mov_tipo ON licencas_movimentacoes(tipo_movimento);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_polo ON licencas_movimentacoes(polo_id);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_criado ON licencas_movimentacoes(criado_em);

-- ==========================================
-- EAD — Calendário, Feed, Lembretes
-- ==========================================

CREATE TABLE IF NOT EXISTS ead_calendario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    titulo VARCHAR(255) NOT NULL,
    data_inicio TIMESTAMPTZ NOT NULL,
    data_fim TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'programado',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ead_cal_curso ON ead_calendario(curso_id);
CREATE INDEX IF NOT EXISTS idx_ead_cal_data ON ead_calendario(data_inicio);

CREATE TABLE IF NOT EXISTS feed_noticias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    autor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lembretes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT NOT NULL,
    data_exibicao TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- Aulas / Presenças / Anexos / Atas
-- ==========================================

CREATE TABLE IF NOT EXISTS aulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id UUID REFERENCES cursos(id) ON DELETE SET NULL,
    modulo_id UUID REFERENCES modulos(id) ON DELETE SET NULL,
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    professor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo VARCHAR(255) NOT NULL,
    data_aula TIMESTAMPTZ,
    descricao TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aulas_materia ON aulas(materia_id);
CREATE INDEX IF NOT EXISTS idx_aulas_professor ON aulas(professor_id);
CREATE INDEX IF NOT EXISTS idx_aulas_data ON aulas(data_aula);

CREATE TABLE IF NOT EXISTS presencas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID NOT NULL REFERENCES aulas(id) ON DELETE CASCADE,
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    presente BOOLEAN DEFAULT FALSE,
    registrado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(aula_id, aluno_id)
);

CREATE INDEX IF NOT EXISTS idx_presencas_aula ON presencas(aula_id);
CREATE INDEX IF NOT EXISTS idx_presencas_aluno ON presencas(aluno_id);

CREATE TABLE IF NOT EXISTS anexos_aula (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID REFERENCES aulas(id) ON DELETE CASCADE,
    professor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    nome_arquivo VARCHAR(255) NOT NULL,
    url TEXT,
    descricao TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anexos_aula ON anexos_aula(aula_id);

CREATE TABLE IF NOT EXISTS atas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID REFERENCES aulas(id) ON DELETE SET NULL,
    professor_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    conteudo TEXT NOT NULL,
    data_ata TIMESTAMPTZ DEFAULT NOW(),
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_atas_aula ON atas(aula_id);

-- ==========================================
-- Certificados (RN-05)
-- ==========================================

CREATE TABLE IF NOT EXISTS certificados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    estagios_entregues JSONB DEFAULT '[]'::jsonb,
    historico_completo BOOLEAN DEFAULT FALSE,
    data_emissao TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pendente',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_certificados_aluno ON certificados(aluno_id);
CREATE INDEX IF NOT EXISTS idx_certificados_status ON certificados(status);

-- ==========================================
-- Chat (RN-06)
-- ==========================================

CREATE TABLE IF NOT EXISTS chat_conversas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(20) NOT NULL DEFAULT 'individual',
    criado_por UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome VARCHAR(255),
    status VARCHAR(20) DEFAULT 'ativa',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_conv_tipo ON chat_conversas(tipo);
CREATE INDEX IF NOT EXISTS idx_chat_conv_status ON chat_conversas(status);

CREATE TABLE IF NOT EXISTS chat_mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    remetente_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    conteudo TEXT NOT NULL,
    lida BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_msg_conversa ON chat_mensagens(conversa_id);
CREATE INDEX IF NOT EXISTS idx_chat_msg_criado ON chat_mensagens(criado_em);

CREATE TABLE IF NOT EXISTS chat_grupos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID UNIQUE NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    criado_por UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_participantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    perfil VARCHAR(20) NOT NULL,
    entrou_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(conversa_id, usuario_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_part_conv ON chat_participantes(conversa_id);
CREATE INDEX IF NOT EXISTS idx_chat_part_usuario ON chat_participantes(usuario_id);

-- ==========================================
-- Vendas / Boletos / Pedidos de Livros
-- ==========================================

CREATE TABLE IF NOT EXISTS vendas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    aluno_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    modalidade VARCHAR(20),
    valor NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    forma_pagamento VARCHAR(50),
    status VARCHAR(20) DEFAULT 'paga',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendas_polo ON vendas(polo_id);
CREATE INDEX IF NOT EXISTS idx_vendas_escola ON vendas(escola_id);
CREATE INDEX IF NOT EXISTS idx_vendas_criado ON vendas(criado_em);

CREATE TABLE IF NOT EXISTS boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venda_id UUID REFERENCES vendas(id) ON DELETE SET NULL,
    valor NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    data_vencimento DATE,
    status VARCHAR(20) DEFAULT 'gerado',
    nosso_numero VARCHAR(50),
    asaas_id VARCHAR(100),
    link_pdf TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_boletos_venda ON boletos(venda_id);
CREATE INDEX IF NOT EXISTS idx_boletos_asaas ON boletos(asaas_id);

CREATE TABLE IF NOT EXISTS pedidos_livros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    quantidade INT NOT NULL DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pendente',
    solicitado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos_livros(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_polo ON pedidos_livros(polo_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_escola ON pedidos_livros(escola_id);

-- ==========================================
-- Churn (RN-04) / Requisições de Troca
-- ==========================================

CREATE TABLE IF NOT EXISTS alunos_churn (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID UNIQUE NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    ultima_movimentacao_em TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ativo',
    reingresso_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_churn_status ON alunos_churn(status);
CREATE INDEX IF NOT EXISTS idx_churn_ultima_mov ON alunos_churn(ultima_movimentacao_em);

CREATE TABLE IF NOT EXISTS requisicoes_troca (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    polo_origem_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_origem_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    polo_destino_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_destino_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    tipo_troca VARCHAR(30) NOT NULL,
    justificativa TEXT,
    status VARCHAR(20) DEFAULT 'pendente',
    solicitado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_req_troca_aluno ON requisicoes_troca(aluno_id);
CREATE INDEX IF NOT EXISTS idx_req_troca_status ON requisicoes_troca(status);
CREATE INDEX IF NOT EXISTS idx_req_troca_criado ON requisicoes_troca(criado_em);

-- ==========================================
-- Notas / Histórico de Alunos
-- ==========================================

CREATE TABLE IF NOT EXISTS notas_alunos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    nota NUMERIC(5, 2),
    tipo VARCHAR(30),
    semestre SMALLINT,
    ano SMALLINT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notas_aluno ON notas_alunos(aluno_id);
CREATE INDEX IF NOT EXISTS idx_notas_materia ON notas_alunos(materia_id);

CREATE TABLE IF NOT EXISTS historico_alunos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    materia_id UUID REFERENCES materias(id) ON DELETE SET NULL,
    descricao TEXT NOT NULL,
    tipo VARCHAR(30),
    semestre SMALLINT,
    ano SMALLINT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_historico_aluno ON historico_alunos(aluno_id);
