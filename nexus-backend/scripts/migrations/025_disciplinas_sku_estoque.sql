-- =============================================================================
-- 025 - SKU da Disciplina e Estoque Central de livros
--
-- - disciplinas.sku: o SKU passa a ser cadastrado na própria Disciplina (o CRUD
--   "Produtos e Preços" foi removido). Backfill com o SKU que o produto "kit" de
--   cada disciplina já tinha; disciplinas sem kit recebem o mesmo formato
--   (KIT-<id sem hífens>). O produto "kit" continua existindo internamente
--   (pedidos/cobranças) e é sincronizado pela API a partir da Disciplina.
-- - estoque_livros: saldo de livros por Disciplina no Estoque Central. Pode ficar
--   negativo (envio sem estoque suficiente não é bloqueado).
-- - estoque_movimentacoes: entradas, ajustes e baixas automáticas ao marcar um
--   pedido como enviado (no máximo uma baixa por pedido/disciplina).
--
-- Aplicar ANTES de publicar o backend.
-- Idempotente. Se algo falhar, a transação inteira é revertida.
-- =============================================================================
BEGIN;

-- 1) SKU da Disciplina
ALTER TABLE disciplinas ADD COLUMN IF NOT EXISTS sku VARCHAR(64);

UPDATE disciplinas d
   SET sku = p.sku
  FROM produtos p
 WHERE p.disciplina_id = d.id
   AND p.tipo = 'kit'
   AND d.sku IS NULL;

UPDATE disciplinas
   SET sku = 'KIT-' || upper(replace(id::text, '-', ''))
 WHERE sku IS NULL;

ALTER TABLE disciplinas ALTER COLUMN sku SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_disciplinas_sku ON disciplinas (sku);

COMMENT ON COLUMN disciplinas.sku IS 'SKU do kit da disciplina (livro + licença); espelhado em produtos.sku';

-- 2) Estoque Central de livros
CREATE TABLE IF NOT EXISTS estoque_livros (
    disciplina_id UUID PRIMARY KEY REFERENCES disciplinas(id) ON DELETE CASCADE,
    quantidade INT NOT NULL DEFAULT 0,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

COMMENT ON COLUMN estoque_livros.quantidade IS 'Saldo de livros no Estoque Central; negativo = enviado sem estoque';

CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplina_id UUID NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    tipo VARCHAR(16) NOT NULL CHECK (tipo IN ('entrada', 'ajuste', 'baixa_envio')),
    quantidade INT NOT NULL,
    saldo_apos INT NOT NULL,
    pedido_id UUID REFERENCES pedidos(id) ON DELETE SET NULL,
    usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN estoque_movimentacoes.quantidade IS 'Variação com sinal (+entrada, -baixa; ajuste = novo saldo - saldo anterior)';

CREATE INDEX IF NOT EXISTS ix_estoque_mov_disciplina
    ON estoque_movimentacoes (disciplina_id, criado_em DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_estoque_baixa_pedido
    ON estoque_movimentacoes (pedido_id, disciplina_id) WHERE tipo = 'baixa_envio';

COMMIT;
