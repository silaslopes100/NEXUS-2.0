-- =============================================================================
-- 026 - Troca de licença/livro (Polo e Escola)
--
-- - pedidos.tipo 'troca': solicitação de troca feita pelo Polo/Escola na tela de
--   licenças. Valor 0; passa pela logística (Pendentes de envio).
-- - pedidos.status 'troca_solicitada' (aguardando o Admin) e 'troca' (efetuada).
--   Recusa = 'cancelado' com motivo_cancelamento.
-- - pedidos.troca_motivo / troca_descricao: dados do formulário de troca.
-- - pedidos_troca_itens: linhas "devolver Disciplina A x qtd -> receber Disciplina B".
-- - estoque_movimentacoes: tipos 'troca_entrada' (livro devolvido volta ao Estoque
--   Central) e 'troca_saida' (livro novo enviado).
--
-- Requer a 025. Idempotente. Se algo falhar, a transação inteira é revertida.
-- =============================================================================
BEGIN;

-- 1) Tipo e status do pedido
ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS ck_pedidos_tipo;
ALTER TABLE pedidos ADD CONSTRAINT ck_pedidos_tipo CHECK (tipo IN ('livro', 'licenca', 'kit', 'troca'));

ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS ck_pedidos_status;
ALTER TABLE pedidos ADD CONSTRAINT ck_pedidos_status CHECK (status IN (
    'aguardando_pagamento', 'pago_aguardando_envio', 'enviado',
    'entregue', 'concluido', 'cancelado', 'troca_solicitada', 'troca'
));

ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS troca_motivo VARCHAR(32);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS troca_descricao TEXT;

-- 2) Itens da troca
CREATE TABLE IF NOT EXISTS pedidos_troca_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    disciplina_devolver_id UUID NOT NULL REFERENCES disciplinas(id),
    disciplina_receber_id UUID NOT NULL REFERENCES disciplinas(id),
    quantidade INT NOT NULL CHECK (quantidade > 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_troca_disciplinas_distintas CHECK (disciplina_devolver_id <> disciplina_receber_id)
);
CREATE INDEX IF NOT EXISTS idx_pedidos_troca_itens_pedido ON pedidos_troca_itens (pedido_id);

-- 3) Movimentações de troca no Estoque Central
ALTER TABLE estoque_movimentacoes DROP CONSTRAINT IF EXISTS estoque_movimentacoes_tipo_check;
ALTER TABLE estoque_movimentacoes DROP CONSTRAINT IF EXISTS ck_estoque_mov_tipo;
ALTER TABLE estoque_movimentacoes ADD CONSTRAINT ck_estoque_mov_tipo
    CHECK (tipo IN ('entrada', 'ajuste', 'baixa_envio', 'troca_entrada', 'troca_saida'));

COMMIT;
