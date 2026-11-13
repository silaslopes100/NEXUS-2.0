-- =============================================================================
-- 018 - Dados fiscais do Polo + cache de clientes nos gateways (Fase 2)
--
-- - polos: CPF/CNPJ, razao social, e-mail e telefone financeiros (pagador das
--   cobrancas nos gateways). Documento gravado so com digitos.
-- - gateway_clientes: id do cliente criado em cada gateway/ambiente por Polo,
--   para nao duplicar clientes (o Asaas permite duplicados).
-- - indice parcial para o cron reprocessar webhooks com erro.
--
-- Idempotente: pode ser executada mais de uma vez no SQL Editor.
-- =============================================================================
BEGIN;

ALTER TABLE polos ADD COLUMN IF NOT EXISTS documento_fiscal VARCHAR(18);
ALTER TABLE polos ADD COLUMN IF NOT EXISTS razao_social VARCHAR(255);
ALTER TABLE polos ADD COLUMN IF NOT EXISTS email_financeiro VARCHAR(255);
ALTER TABLE polos ADD COLUMN IF NOT EXISTS telefone_financeiro VARCHAR(32);

CREATE TABLE IF NOT EXISTS gateway_clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway VARCHAR(32) NOT NULL,
    ambiente VARCHAR(16) NOT NULL,
    polo_id UUID NOT NULL REFERENCES polos(id) ON DELETE CASCADE,
    customer_id VARCHAR(128) NOT NULL,
    documento_fiscal VARCHAR(18),
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_gateway_clientes UNIQUE (gateway, ambiente, polo_id)
);

CREATE INDEX IF NOT EXISTS idx_webhook_eventos_erro
    ON webhook_eventos (recebido_em) WHERE status = 'erro';

COMMIT;
