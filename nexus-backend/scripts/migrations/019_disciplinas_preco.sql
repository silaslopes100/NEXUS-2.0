-- =============================================================================
-- 019 - Preco informativo da Disciplina
--
-- - disciplinas.preco: valor em R$ exibido e editado no cadastro de Disciplinas.
--   E apenas informativo: pedidos e cobrancas continuam usando o preco do
--   catalogo de Produtos.
--
-- Aplicar ANTES de publicar o backend que lista/grava o preco.
-- Idempotente: pode ser executada mais de uma vez no SQL Editor.
-- =============================================================================
BEGIN;

ALTER TABLE disciplinas ADD COLUMN IF NOT EXISTS preco NUMERIC(12,2);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_disciplinas_preco_nao_negativo'
          AND conrelid = 'disciplinas'::regclass
    ) THEN
        ALTER TABLE disciplinas
            ADD CONSTRAINT ck_disciplinas_preco_nao_negativo CHECK (preco IS NULL OR preco >= 0);
    END IF;
END $$;

COMMENT ON COLUMN disciplinas.preco IS 'Preco informativo (R$); nao usado em pedidos/cobrancas';

COMMIT;
