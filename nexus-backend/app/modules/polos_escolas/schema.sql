-- =====================================================================
-- Schema do módulo polos_escolas — NEXUS 2.0
-- Pressupõe já existentes: usuarios, perfis, permissoes, usuario_permissoes,
-- logs_auditoria, configuracoes, polos, escolas
-- =====================================================================

-- RN-01: vínculo 1:1 entre Polo/Escola e o usuário coordenador/secretário
ALTER TABLE polos ADD COLUMN IF NOT EXISTS coordenador_usuario_id UUID REFERENCES usuarios(id);
ALTER TABLE escolas ADD COLUMN IF NOT EXISTS secretario_usuario_id UUID REFERENCES usuarios(id);

-- Estoque de licenças por local (polo OU escola)
CREATE TABLE IF NOT EXISTS licencas_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    materia_id UUID,
    quantidade_disponivel INT NOT NULL DEFAULT 0 CHECK (quantidade_disponivel >= 0),
    quantidade_vendida INT NOT NULL DEFAULT 0 CHECK (quantidade_vendida >= 0),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CHECK (polo_id IS NOT NULL OR escola_id IS NOT NULL),
    CHECK ((polo_id IS NULL) <> (escola_id IS NULL))
);

-- Movimentações de licenças (extrato — fonte de verdade do fluxo RN-02)
CREATE TABLE IF NOT EXISTS licencas_movimentacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(30) NOT NULL, -- compra_fornecedor, distribuicao_polo_escola, venda_aluno, devolucao_escola_polo, devolucao_aluno_escola
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    aluno_id UUID REFERENCES usuarios(id),
    materia_id UUID,
    quantidade INT NOT NULL CHECK (quantidade > 0),
    valor_unitario DECIMAL(10,2),
    status VARCHAR(30) NOT NULL DEFAULT 'ativa',
    actor_id UUID REFERENCES usuarios(id),
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Licenças vinculadas a alunos (1 licença ativa = 1 vínculo)
CREATE TABLE IF NOT EXISTS licencas_alunos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id),
    escola_id UUID REFERENCES escolas(id),
    polo_id UUID REFERENCES polos(id),
    materia_id UUID,
    movimentacao_id UUID REFERENCES licencas_movimentacoes(id),
    status VARCHAR(30) NOT NULL DEFAULT 'ativa', -- ativa, devolvida, cancelada
    ativada_em TIMESTAMPTZ DEFAULT now(),
    expirada_em TIMESTAMPTZ,
    cancelada_em TIMESTAMPTZ
);

-- Compras de licenças (financeiro)
CREATE TABLE IF NOT EXISTS compras_licencas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID NOT NULL REFERENCES polos(id),
    fornecedor VARCHAR(255),
    quantidade INT NOT NULL CHECK (quantidade > 0),
    valor_unitario DECIMAL(10,2),
    valor_total DECIMAL(10,2),
    data_compra DATE NOT NULL,
    boleto_id UUID,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Boletos
CREATE TABLE IF NOT EXISTS boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID NOT NULL REFERENCES polos(id),
    compra_id UUID REFERENCES compras_licencas(id),
    valor DECIMAL(10,2),
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    data_vencimento DATE,
    asaas_id VARCHAR(255),
    url_pdf TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Professores (vínculo com polo/escola)
CREATE TABLE IF NOT EXISTS professores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id),
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    materias JSONB DEFAULT '[]',
    data_inicio DATE,
    quantidade_aulas INT DEFAULT 0,
    horas_totais INT DEFAULT 0,
    valor_hora_aula DECIMAL(10,2),
    pix VARCHAR(255),
    conteudo_programatico TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Aulas
CREATE TABLE IF NOT EXISTS aulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_id UUID NOT NULL REFERENCES professores(id),
    materia_id UUID,
    escola_id UUID REFERENCES escolas(id),
    polo_id UUID REFERENCES polos(id),
    data_aula DATE NOT NULL,
    conteudo TEXT,
    total_aulas_previstas INT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Anexos de aula
CREATE TABLE IF NOT EXISTS anexos_aula (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID NOT NULL REFERENCES aulas(id),
    nome VARCHAR(255),
    url TEXT NOT NULL,
    tipo VARCHAR(50),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Atas oficiais
CREATE TABLE IF NOT EXISTS atas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID NOT NULL REFERENCES aulas(id),
    professor_id UUID NOT NULL REFERENCES professores(id),
    conteudo TEXT,
    url_pdf TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Presenças (RN-07)
CREATE TABLE IF NOT EXISTS presencas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id),
    aula_id UUID NOT NULL REFERENCES aulas(id),
    materia_id UUID,
    presente BOOLEAN NOT NULL DEFAULT false,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Requisições de troca de polo / migração de modalidade (RN-05, RN-06)
CREATE TABLE IF NOT EXISTS requisicoes_troca (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES usuarios(id),
    tipo VARCHAR(30) NOT NULL, -- troca_polo, migracao_modalidade
    polo_origem_id UUID REFERENCES polos(id),
    polo_destino_id UUID REFERENCES polos(id),
    modalidade_destino VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    solicitado_por UUID REFERENCES usuarios(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Feed de notícias (RN-08)
CREATE TABLE IF NOT EXISTS feed_noticias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    autor_id UUID NOT NULL REFERENCES usuarios(id),
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    tags JSONB DEFAULT '[]',
    polo_id UUID REFERENCES polos(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Lembretes (RN-08)
CREATE TABLE IF NOT EXISTS lembretes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id),
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT NOT NULL,
    data_expiracao DATE,
    lido BOOLEAN NOT NULL DEFAULT false,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Calendário EAD (RN-08)
CREATE TABLE IF NOT EXISTS calendario_ead (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    materia_id UUID NOT NULL,
    data_liberacao DATE NOT NULL,
    semestre INT,
    ano INT,
    criado_por UUID REFERENCES usuarios(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Treinamentos de docentes
CREATE TABLE IF NOT EXISTS treinamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    url_conteudo TEXT,
    carga_horaria INT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS treinamentos_inscricoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treinamento_id UUID NOT NULL REFERENCES treinamentos(id),
    professor_id UUID NOT NULL REFERENCES professores(id),
    status VARCHAR(20) NOT NULL DEFAULT 'inscrito',
    concluido_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- =====================================================================
-- Índices de performance
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_licencas_estoque_polo ON licencas_estoque(polo_id);
CREATE INDEX IF NOT EXISTS idx_licencas_estoque_escola ON licencas_estoque(escola_id);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_polo ON licencas_movimentacoes(polo_id);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_escola ON licencas_movimentacoes(escola_id);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_tipo ON licencas_movimentacoes(tipo);
CREATE INDEX IF NOT EXISTS idx_licencas_mov_criado_em ON licencas_movimentacoes(criado_em);
CREATE INDEX IF NOT EXISTS idx_licencas_alunos_aluno ON licencas_alunos(aluno_id);
CREATE INDEX IF NOT EXISTS idx_licencas_alunos_escola ON licencas_alunos(escola_id);
CREATE INDEX IF NOT EXISTS idx_licencas_alunos_status ON licencas_alunos(status);
CREATE INDEX IF NOT EXISTS idx_compras_licencas_polo ON compras_licencas(polo_id);
CREATE INDEX IF NOT EXISTS idx_boletos_polo ON boletos(polo_id);
CREATE INDEX IF NOT EXISTS idx_professores_polo ON professores(polo_id);
CREATE INDEX IF NOT EXISTS idx_professores_escola ON professores(escola_id);
CREATE INDEX IF NOT EXISTS idx_aulas_professor ON aulas(professor_id);
CREATE INDEX IF NOT EXISTS idx_aulas_data ON aulas(data_aula);
CREATE INDEX IF NOT EXISTS idx_presencas_aluno ON presencas(aluno_id);
CREATE INDEX IF NOT EXISTS idx_presencas_aula ON presencas(aula_id);
CREATE INDEX IF NOT EXISTS idx_requisicoes_aluno ON requisicoes_troca(aluno_id);
CREATE INDEX IF NOT EXISTS idx_requisicoes_status ON requisicoes_troca(status);
CREATE INDEX IF NOT EXISTS idx_feed_polo ON feed_noticias(polo_id);
CREATE INDEX IF NOT EXISTS idx_lembretes_usuario ON lembretes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_calendario_ead_materia ON calendario_ead(materia_id);
CREATE INDEX IF NOT EXISTS idx_treinamentos_inscricoes_professor ON treinamentos_inscricoes(professor_id);
