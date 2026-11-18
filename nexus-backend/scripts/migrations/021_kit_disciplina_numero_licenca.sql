-- =============================================================================
-- 021 - Kit Disciplina (livro + licença) e número da licença do aluno
--
-- - Regra do negócio: ao comprar uma Disciplina, o Polo recebe 1 livro físico
--   (logística) + 1 licença (estoque) por unidade. Novo tipo "kit" em
--   produtos/pedidos; "livro" e "licenca" continuam valendo para o histórico.
-- - disciplinas.peso_livro_g: peso do livro do kit (etiqueta/frete). O preço do
--   kit é disciplinas.preco (fonte única; o produto "kit" é sincronizado pela API).
-- - produtos: no máximo um kit por disciplina.
-- - licencas_alunos.numero_licenca: código de acesso do aluno (NX-XXXX-XXXX),
--   usado no login por licença. Backfill das licenças ativas já existentes.
--
-- Idempotente. Se algo falhar, a transação inteira é revertida.
-- =============================================================================
BEGIN;

-- 1) Tipo "kit"
ALTER TABLE produtos DROP CONSTRAINT IF EXISTS ck_produtos_tipo;
ALTER TABLE produtos ADD CONSTRAINT ck_produtos_tipo CHECK (tipo IN ('livro', 'licenca', 'kit'));
ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS ck_pedidos_tipo;
ALTER TABLE pedidos ADD CONSTRAINT ck_pedidos_tipo CHECK (tipo IN ('livro', 'licenca', 'kit'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_produtos_kit_disciplina
    ON produtos (disciplina_id) WHERE tipo = 'kit';

-- 2) Peso do livro na Disciplina
ALTER TABLE disciplinas ADD COLUMN IF NOT EXISTS peso_livro_g INT;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_disciplinas_peso_livro') THEN
        ALTER TABLE disciplinas
            ADD CONSTRAINT ck_disciplinas_peso_livro CHECK (peso_livro_g IS NULL OR peso_livro_g >= 0);
    END IF;
END $$;

-- 3) Número da licença do aluno
ALTER TABLE licencas_alunos ADD COLUMN IF NOT EXISTS numero_licenca VARCHAR(16);
CREATE UNIQUE INDEX IF NOT EXISTS uq_licencas_alunos_numero ON licencas_alunos (numero_licenca)
    WHERE numero_licenca IS NOT NULL;

-- Backfill: 8 caracteres de um alfabeto sem ambíguos (sem 0/O/1/I/L), formato NX-XXXX-XXXX.
DO $$
DECLARE
    alfabeto CONSTANT TEXT := '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
    r RECORD;
    codigo TEXT;
    bytes BYTEA;
    i INT;
BEGIN
    FOR r IN SELECT id FROM licencas_alunos WHERE numero_licenca IS NULL AND status = 'ativa' LOOP
        LOOP
            -- O número é credencial de login: usa os bytes aleatórios fortes de gen_random_uuid()
            -- (random() do Postgres não é criptográfico).
            bytes := uuid_send(gen_random_uuid());
            codigo := '';
            -- Bytes 6 e 8 do UUID v4 têm bits fixos (versão/variante): usa só posições aleatórias.
            FOREACH i IN ARRAY ARRAY[0, 1, 2, 3, 4, 5, 10, 11] LOOP
                codigo := codigo || substr(alfabeto, 1 + (get_byte(bytes, i) % length(alfabeto)), 1);
            END LOOP;
            codigo := 'NX-' || substr(codigo, 1, 4) || '-' || substr(codigo, 5, 4);
            EXIT WHEN NOT EXISTS (SELECT 1 FROM licencas_alunos WHERE numero_licenca = codigo);
        END LOOP;
        UPDATE licencas_alunos SET numero_licenca = codigo WHERE id = r.id;
    END LOOP;
END $$;

COMMENT ON COLUMN licencas_alunos.numero_licenca IS 'Código de acesso do aluno (login por licença)';
COMMENT ON COLUMN licencas_movimentacoes.tipo IS
    'compra_fornecedor, distribuicao_polo_escola, distribuicao_polo_aluno, venda_aluno, devolucao_escola_polo, '
    'devolucao_aluno_escola, reingresso_churn, reclassificacao, liberacao_admin';

COMMIT;
