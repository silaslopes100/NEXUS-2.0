-- =============================================================================
-- 016 - Financeiro & Logistica (estrutura)
-- Modulo 2.4: vendas, pagamentos/boletos (Asaas, PagBank, Mercado Pago),
-- pedidos (livros e licencas), envios/etiquetas, regras de pagamento,
-- configuracao de gateways (sandbox/producao) e log de webhooks.
--
-- Idempotente: pode ser executada mais de uma vez no SQL Editor.
-- Nao move dados: a unificacao das tabelas antigas fica na 017.
-- =============================================================================
BEGIN;

-- -----------------------------------------------------------------------------
-- Produtos (catalogo de livros e licencas vendidos aos Polos)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(16) NOT NULL,
    sku VARCHAR(64) NOT NULL UNIQUE,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    preco NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (preco >= 0),
    peso_g INT CHECK (peso_g IS NULL OR peso_g >= 0),
    altura_cm NUMERIC(6,1),
    largura_cm NUMERIC(6,1),
    comprimento_cm NUMERIC(6,1),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_produtos_tipo CHECK (tipo IN ('livro', 'licenca'))
);
CREATE INDEX IF NOT EXISTS idx_produtos_tipo_ativo ON produtos (tipo, ativo);
CREATE INDEX IF NOT EXISTS idx_produtos_disciplina ON produtos (disciplina_id);

-- -----------------------------------------------------------------------------
-- Pedidos (tabela unica: substitui pedidos_livros, pedidos_licenca e
-- compras_licencas apos a 017)
-- -----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS seq_pedido START 1;

CREATE TABLE IF NOT EXISTS pedidos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(32) NOT NULL UNIQUE
        DEFAULT ('PED-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('seq_pedido')::text, 6, '0')),
    tipo VARCHAR(16) NOT NULL,
    polo_id UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    solicitante_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'aguardando_pagamento',
    valor_bruto NUMERIC(12,2) NOT NULL DEFAULT 0,
    desconto NUMERIC(12,2) NOT NULL DEFAULT 0,
    valor_total NUMERIC(12,2) NOT NULL DEFAULT 0,
    cupom_id UUID REFERENCES cupons(id) ON DELETE SET NULL,
    fornecedor VARCHAR(255),
    -- snapshot do endereco de entrega no momento do pedido
    entrega_nome VARCHAR(255),
    entrega_cep VARCHAR(16),
    entrega_logradouro VARCHAR(255),
    entrega_numero VARCHAR(32),
    entrega_complemento VARCHAR(255),
    entrega_bairro VARCHAR(255),
    entrega_cidade VARCHAR(255),
    entrega_uf VARCHAR(2),
    entrega_telefone VARCHAR(32),
    observacao TEXT,
    pago_em TIMESTAMPTZ,
    cancelado_em TIMESTAMPTZ,
    motivo_cancelamento TEXT,
    enviado_em TIMESTAMPTZ,
    entregue_em TIMESTAMPTZ,
    legacy_table VARCHAR(64),
    legacy_id BIGINT,
    synced_at TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_pedidos_legacy UNIQUE (legacy_table, legacy_id),
    CONSTRAINT ck_pedidos_tipo CHECK (tipo IN ('livro', 'licenca')),
    CONSTRAINT ck_pedidos_status CHECK (status IN (
        'aguardando_pagamento', 'pago_aguardando_envio', 'enviado',
        'entregue', 'concluido', 'cancelado'
    ))
);
CREATE INDEX IF NOT EXISTS idx_pedidos_status_criado ON pedidos (status, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_pedidos_polo_criado ON pedidos (polo_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_pedidos_escola_criado ON pedidos (escola_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_pedidos_tipo_criado ON pedidos (tipo, criado_em DESC);

CREATE TABLE IF NOT EXISTS pedidos_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id UUID REFERENCES produtos(id) ON DELETE SET NULL,
    disciplina_id UUID REFERENCES disciplinas(id) ON DELETE SET NULL,
    descricao VARCHAR(255),
    quantidade INT NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    valor_unitario NUMERIC(12,2) NOT NULL DEFAULT 0,
    valor_total NUMERIC(12,2) NOT NULL DEFAULT 0,
    legacy_table VARCHAR(64),
    legacy_id BIGINT,
    synced_at TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_pedidos_itens_legacy UNIQUE (legacy_table, legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_pedidos_itens_pedido ON pedidos_itens (pedido_id);

CREATE TABLE IF NOT EXISTS pedidos_status_historico (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    status_de VARCHAR(32),
    status_para VARCHAR(32) NOT NULL,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    origem VARCHAR(32) NOT NULL DEFAULT 'usuario', -- usuario | webhook | cron | migracao
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pedidos_hist_pedido ON pedidos_status_historico (pedido_id, criado_em);

-- -----------------------------------------------------------------------------
-- Envios (etiqueta gerada pelo proprio Nexus)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS envios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    transportadora VARCHAR(64),
    codigo_rastreio VARCHAR(64),
    volumes INT NOT NULL DEFAULT 1 CHECK (volumes > 0),
    peso_total_g INT,
    etiqueta_gerada_em TIMESTAMPTZ,
    enviado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    enviado_em TIMESTAMPTZ,
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_envios_pedido ON envios (pedido_id);

-- -----------------------------------------------------------------------------
-- Gateways de pagamento (credenciais criptografadas pela aplicacao - Fernet)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gateways_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway VARCHAR(32) NOT NULL,
    ambiente VARCHAR(16) NOT NULL,
    credenciais_cripto TEXT,
    webhook_token_cripto TEXT,
    ativo BOOLEAN NOT NULL DEFAULT false,
    padrao BOOLEAN NOT NULL DEFAULT false,
    atualizado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    ultimo_teste_em TIMESTAMPTZ,
    ultimo_teste_ok BOOLEAN,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_gateways_config UNIQUE (gateway, ambiente),
    CONSTRAINT ck_gateways_gateway CHECK (gateway IN ('asaas', 'pagbank', 'mercadopago', 'fake')),
    CONSTRAINT ck_gateways_ambiente CHECK (ambiente IN ('sandbox', 'producao'))
);
-- no maximo um gateway padrao por ambiente
CREATE UNIQUE INDEX IF NOT EXISTS uq_gateways_padrao_ambiente
    ON gateways_config (ambiente) WHERE padrao;

INSERT INTO gateways_config (gateway, ambiente)
SELECT g, a
FROM unnest(ARRAY['asaas', 'pagbank', 'mercadopago']) AS g,
     unnest(ARRAY['sandbox', 'producao']) AS a
ON CONFLICT (gateway, ambiente) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Regras de pagamento
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regras_pagamento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(128) NOT NULL,
    aplica_tipo_pedido VARCHAR(16), -- NULL = todos | livro | licenca
    aplica_polo_id UUID REFERENCES polos(id) ON DELETE CASCADE, -- NULL = todos
    meios_permitidos TEXT[] NOT NULL DEFAULT ARRAY['BOLETO', 'PIX']::TEXT[],
    gateway_preferido VARCHAR(32), -- NULL = gateway padrao do ambiente
    max_parcelas INT NOT NULL DEFAULT 1 CHECK (max_parcelas BETWEEN 1 AND 24),
    dias_vencimento INT NOT NULL DEFAULT 3 CHECK (dias_vencimento BETWEEN 0 AND 90),
    multa_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    juros_mes_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    desconto_antecipado_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    valor_minimo NUMERIC(12,2) NOT NULL DEFAULT 0,
    prioridade INT NOT NULL DEFAULT 100, -- menor = avaliada primeiro
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_regras_tipo CHECK (aplica_tipo_pedido IS NULL OR aplica_tipo_pedido IN ('livro', 'licenca')),
    CONSTRAINT ck_regras_meios CHECK (meios_permitidos <@ ARRAY['BOLETO', 'PIX', 'CREDIT_CARD']::TEXT[])
);
CREATE INDEX IF NOT EXISTS idx_regras_pagamento_ativo ON regras_pagamento (ativo, prioridade);

-- Regra padrao (fallback) para nao bloquear o checkout
INSERT INTO regras_pagamento (nome, meios_permitidos, dias_vencimento, prioridade)
SELECT 'Padrão (Boleto e PIX)', ARRAY['BOLETO', 'PIX']::TEXT[], 3, 1000
WHERE NOT EXISTS (SELECT 1 FROM regras_pagamento);

-- -----------------------------------------------------------------------------
-- Webhooks recebidos (auditoria + idempotencia)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS webhook_eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway VARCHAR(32) NOT NULL,
    ambiente VARCHAR(16) NOT NULL,
    evento_id VARCHAR(128) NOT NULL,
    tipo_evento VARCHAR(64),
    gateway_payment_id VARCHAR(128),
    payload JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'recebido',
    tentativas INT NOT NULL DEFAULT 0,
    erro TEXT,
    recebido_em TIMESTAMPTZ DEFAULT now(),
    processado_em TIMESTAMPTZ,
    CONSTRAINT uq_webhook_eventos UNIQUE (gateway, evento_id),
    CONSTRAINT ck_webhook_status CHECK (status IN ('recebido', 'processado', 'erro', 'ignorado'))
);
CREATE INDEX IF NOT EXISTS idx_webhook_eventos_status ON webhook_eventos (status, recebido_em);
CREATE INDEX IF NOT EXISTS idx_webhook_eventos_payment ON webhook_eventos (gateway, gateway_payment_id);

-- -----------------------------------------------------------------------------
-- Pagamentos: passa a ser a tabela canonica (absorve "boletos" na 017)
-- -----------------------------------------------------------------------------
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS pedido_id UUID REFERENCES pedidos(id) ON DELETE SET NULL;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS polo_id UUID REFERENCES polos(id) ON DELETE SET NULL;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS aluno_id UUID REFERENCES alunos(id) ON DELETE SET NULL;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS ambiente VARCHAR(16);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS gateway_customer_id VARCHAR(128);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS gateway_payment_id VARCHAR(128);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS linha_digitavel VARCHAR(128);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS nosso_numero VARCHAR(64);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS pix_copia_cola TEXT;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS pix_qrcode_base64 TEXT;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS invoice_url VARCHAR(500);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS parcelas INT DEFAULT 1;
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS valor_liquido NUMERIC(12,2);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS descricao VARCHAR(255);
ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS cancelado_em TIMESTAMPTZ;

-- Backfill das colunas genericas a partir das colunas Asaas legadas
UPDATE pagamentos
   SET gateway_payment_id = asaas_payment_id
 WHERE gateway_payment_id IS NULL AND asaas_payment_id IS NOT NULL;
UPDATE pagamentos
   SET gateway_customer_id = asaas_customer_id
 WHERE gateway_customer_id IS NULL AND asaas_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pagamentos_status_criado ON pagamentos (status, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_pagamentos_gateway_payment ON pagamentos (gateway, gateway_payment_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_pedido ON pagamentos (pedido_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_polo_criado ON pagamentos (polo_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_pagamentos_vencimento ON pagamentos (vencimento_em) WHERE status = 'pendente';

-- -----------------------------------------------------------------------------
-- Perfis e permissoes do modulo
-- -----------------------------------------------------------------------------
INSERT INTO perfis (nome, descricao) VALUES
    ('financeiro', 'Equipe financeira: vendas, boletos e regras de pagamento'),
    ('logistica', 'Equipe de logística: pedidos, envios e etiquetas')
ON CONFLICT (nome) DO NOTHING;

INSERT INTO permissoes (chave, descricao) VALUES
    ('p_financeiro', 'Financeiro: vendas, boletos, transações e regras de pagamento'),
    ('p_logistica', 'Logística: pedidos de livros, envios e etiquetas')
ON CONFLICT (chave) DO NOTHING;

COMMIT;
