-- 035 — Vendas EAD: Turmas EAD na vitrine pública e compra progressiva de disciplinas pelo aluno.
--  * ava_disciplina_config: preço EAD da disciplina (padrão R$ 45,00) e upsell do livro físico
--    (padrão R$ 25,00, sem licença: a avaliação é feita no AVA).
--  * pedidos: pedido do próprio aluno EAD (aluno_id, sem Polo); tipos 'ead' (só a disciplina)
--    e 'ead_livro' (disciplina + livro físico, passa pela logística).
--  * compras_disciplina_ead: ligação com o pedido e a turma; uma compra pendente por disciplina.
--  * gateway_clientes: cliente do gateway também por aluno (pagador pessoa física).
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

-- Preço EAD por disciplina (CRUD "Conteúdo EAD (AVA)")
ALTER TABLE ava_disciplina_config ADD COLUMN IF NOT EXISTS valor_ead NUMERIC(10,2) NOT NULL DEFAULT 45.00;
ALTER TABLE ava_disciplina_config ADD COLUMN IF NOT EXISTS livro_disponivel BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE ava_disciplina_config ADD COLUMN IF NOT EXISTS valor_livro_ead NUMERIC(10,2) NOT NULL DEFAULT 25.00;
ALTER TABLE ava_disciplina_config DROP CONSTRAINT IF EXISTS ck_ava_config_valores;
ALTER TABLE ava_disciplina_config ADD CONSTRAINT ck_ava_config_valores
    CHECK (valor_ead >= 0 AND valor_livro_ead >= 0);

-- Pedido do aluno EAD
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS aluno_id UUID REFERENCES alunos(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_pedidos_aluno_criado ON pedidos (aluno_id, criado_em DESC) WHERE aluno_id IS NOT NULL;
ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS ck_pedidos_tipo;
ALTER TABLE pedidos ADD CONSTRAINT ck_pedidos_tipo
    CHECK (tipo IN ('livro', 'licenca', 'kit', 'troca', 'ead', 'ead_livro'));

-- Compra da disciplina EAD
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS pedido_id UUID REFERENCES pedidos(id) ON DELETE SET NULL;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS com_livro BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_compras_ead_pedido ON compras_disciplina_ead (pedido_id) WHERE pedido_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compras_ead_aluno ON compras_disciplina_ead (aluno_id, disciplina_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_compras_ead_pendente
    ON compras_disciplina_ead (aluno_id, disciplina_id)
    WHERE status_pagamento = 'pendente' AND pedido_id IS NOT NULL;  -- só as da loja (o legado fica de fora)

-- Cliente do gateway por aluno
ALTER TABLE gateway_clientes ALTER COLUMN polo_id DROP NOT NULL;
ALTER TABLE gateway_clientes ADD COLUMN IF NOT EXISTS aluno_id UUID REFERENCES alunos(id) ON DELETE CASCADE;
ALTER TABLE gateway_clientes DROP CONSTRAINT IF EXISTS ck_gateway_clientes_dono;
ALTER TABLE gateway_clientes ADD CONSTRAINT ck_gateway_clientes_dono
    CHECK ((polo_id IS NULL) <> (aluno_id IS NULL));
CREATE UNIQUE INDEX IF NOT EXISTS uq_gateway_clientes_aluno
    ON gateway_clientes (gateway, ambiente, aluno_id) WHERE aluno_id IS NOT NULL;

COMMIT;
