-- =============================================================================
-- 017 - Unificacao Financeiro / Logistica (migracao de dados)
--
-- PRE-REQUISITOS:
--   1. 016_financeiro_logistica_estrutura.sql aplicada.
--   2. Codigo do backend ja apontando para as tabelas novas (Fase 1 do plano):
--      polos_escolas (compras/boletos), admin (estoque), cursos_disciplinas,
--      ETL (pedidos_livros_mapper / schema.py). Rodar esta migration ANTES do
--      deploy do codigo novo quebra as rotas antigas.
--
-- O QUE FAZ:
--   pedidos_livros (+ itens)  -> pedidos (tipo livro)    + pedidos_itens
--   pedidos_licenca (JSONB)   -> pedidos (tipo licenca)  + pedidos_itens
--   compras_licencas          -> pedidos (tipo licenca, concluido)
--   boletos                   -> pagamentos (mesmo id, billing_type BOLETO)
--   pagamentos.pedido_licenca_id -> pagamentos.pedido_id
--   Tabelas antigas sao RENOMEADAS para *_legado (nada e apagado).
--
-- Idempotente: cada etapa verifica se a tabela de origem ainda existe e usa
-- migracao_pedidos_map para nao duplicar registros.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS migracao_pedidos_map (
    origem_tabela VARCHAR(64) NOT NULL,
    origem_id UUID NOT NULL,
    pedido_id UUID NOT NULL,
    migrado_em TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (origem_tabela, origem_id)
);

-- -----------------------------------------------------------------------------
-- 1. pedidos_livros -> pedidos (tipo livro)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.pedidos_livros') IS NULL THEN
        RAISE NOTICE '017: pedidos_livros inexistente/ja migrada - etapa ignorada';
        RETURN;
    END IF;

    -- Se o ETL ja gravou o mesmo p_livros direto em `pedidos` (apos a 016),
    -- reaproveita aquele pedido em vez de duplicar (UNIQUE legacy_table/legacy_id).
    INSERT INTO migracao_pedidos_map (origem_tabela, origem_id, pedido_id)
    SELECT 'pedidos_livros', pl.id,
           COALESCE(
               (SELECT x.id FROM pedidos x
                 WHERE pl.legacy_id IS NOT NULL
                   AND x.legacy_table = pl.legacy_table AND x.legacy_id = pl.legacy_id),
               gen_random_uuid())
      FROM pedidos_livros pl
     WHERE NOT EXISTS (SELECT 1 FROM migracao_pedidos_map m
                        WHERE m.origem_tabela = 'pedidos_livros' AND m.origem_id = pl.id);

    INSERT INTO pedidos (
        id, numero, tipo, polo_id, escola_id, status,
        entrega_nome, entrega_cep, entrega_logradouro, entrega_numero, entrega_complemento,
        entrega_bairro, entrega_cidade, entrega_uf,
        enviado_em, legacy_table, legacy_id, synced_at, criado_em, atualizado_em
    )
    SELECT m.pedido_id,
           'PED-' || to_char(COALESCE(pl.criado_em, now()), 'YYYY') || '-' || lpad(nextval('seq_pedido')::text, 6, '0'),
           'livro', pl.polo_id, pl.escola_id,
           CASE lower(COALESCE(pl.status, ''))
                WHEN 'enviado'   THEN 'enviado'
                WHEN 'entregue'  THEN 'entregue'
                WHEN 'cancelado' THEN 'cancelado'
                ELSE 'pago_aguardando_envio'   -- 'pendente' no legado = pendente de envio
           END,
           po.nome, po.cep, po.logradouro, po.numero, po.complemento, po.bairro, po.cidade, po.uf,
           pl.enviado_em, pl.legacy_table, pl.legacy_id, pl.synced_at,
           COALESCE(pl.criado_em, now()), COALESCE(pl.atualizado_em, now())
      FROM pedidos_livros pl
      JOIN migracao_pedidos_map m ON m.origem_tabela = 'pedidos_livros' AND m.origem_id = pl.id
      LEFT JOIN polos po ON po.id = pl.polo_id
     WHERE NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id = m.pedido_id);

    IF to_regclass('public.pedidos_livros_itens') IS NOT NULL THEN
        INSERT INTO pedidos_itens (
            pedido_id, disciplina_id, descricao, quantidade, valor_unitario, valor_total,
            legacy_table, legacy_id, synced_at, criado_em, atualizado_em
        )
        SELECT m.pedido_id, it.disciplina_id, d.nome, GREATEST(COALESCE(it.quantidade, 1), 1), 0, 0,
               it.legacy_table, it.legacy_id, it.synced_at,
               COALESCE(it.criado_em, now()), COALESCE(it.atualizado_em, now())
          FROM pedidos_livros_itens it
          JOIN migracao_pedidos_map m ON m.origem_tabela = 'pedidos_livros' AND m.origem_id = it.pedido_livro_id
          LEFT JOIN disciplinas d ON d.id = it.disciplina_id
         WHERE NOT EXISTS (
               SELECT 1 FROM migracao_pedidos_map mi
                WHERE mi.origem_tabela = 'pedidos_livros_itens' AND mi.origem_id = it.id)
           AND NOT EXISTS (
               SELECT 1 FROM pedidos_itens x
                WHERE it.legacy_id IS NOT NULL
                  AND x.legacy_table = it.legacy_table AND x.legacy_id = it.legacy_id);

        INSERT INTO migracao_pedidos_map (origem_tabela, origem_id, pedido_id)
        SELECT 'pedidos_livros_itens', it.id, m.pedido_id
          FROM pedidos_livros_itens it
          JOIN migracao_pedidos_map m ON m.origem_tabela = 'pedidos_livros' AND m.origem_id = it.pedido_livro_id
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2. pedidos_licenca (itens JSONB) -> pedidos (tipo licenca)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.pedidos_licenca') IS NULL THEN
        RAISE NOTICE '017: pedidos_licenca inexistente/ja migrada - etapa ignorada';
        RETURN;
    END IF;

    INSERT INTO migracao_pedidos_map (origem_tabela, origem_id, pedido_id)
    SELECT 'pedidos_licenca', pl.id, gen_random_uuid()
      FROM pedidos_licenca pl
     WHERE NOT EXISTS (SELECT 1 FROM migracao_pedidos_map m
                        WHERE m.origem_tabela = 'pedidos_licenca' AND m.origem_id = pl.id);

    INSERT INTO pedidos (
        id, numero, tipo, polo_id, escola_id, status, valor_bruto, valor_total,
        legacy_table, legacy_id, synced_at, criado_em, atualizado_em
    )
    SELECT m.pedido_id,
           'PED-' || to_char(COALESCE(pl.criado_em, now()), 'YYYY') || '-' || lpad(nextval('seq_pedido')::text, 6, '0'),
           'licenca', pl.polo_id, pl.escola_id,
           CASE lower(COALESCE(pl.status, ''))
                WHEN 'pago'      THEN 'concluido'
                WHEN 'aprovado'  THEN 'concluido'
                WHEN 'concluido' THEN 'concluido'
                WHEN 'cancelado' THEN 'cancelado'
                ELSE 'aguardando_pagamento'
           END,
           COALESCE(pl.valor_total, 0), COALESCE(pl.valor_total, 0),
           pl.legacy_table, pl.legacy_id, pl.synced_at,
           COALESCE(pl.criado_em, now()), COALESCE(pl.atualizado_em, now())
      FROM pedidos_licenca pl
      JOIN migracao_pedidos_map m ON m.origem_tabela = 'pedidos_licenca' AND m.origem_id = pl.id
     WHERE NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id = m.pedido_id);

    -- Expande itens JSONB (formato livre no legado: tenta chaves usuais)
    INSERT INTO pedidos_itens (pedido_id, disciplina_id, descricao, quantidade, valor_unitario, valor_total)
    SELECT m.pedido_id,
           CASE WHEN (e->>'disciplina_id') ~* '^[0-9a-f-]{36}$' THEN (e->>'disciplina_id')::uuid END,
           left(COALESCE(e->>'descricao', e->>'nome', 'Licença'), 255),
           GREATEST(COALESCE(NULLIF(e->>'quantidade', '')::numeric::int, 1), 1),
           COALESCE(NULLIF(e->>'valor_unitario', '')::numeric, 0),
           COALESCE(NULLIF(e->>'valor_unitario', '')::numeric, 0)
             * GREATEST(COALESCE(NULLIF(e->>'quantidade', '')::numeric::int, 1), 1)
      FROM pedidos_licenca pl
      JOIN migracao_pedidos_map m ON m.origem_tabela = 'pedidos_licenca' AND m.origem_id = pl.id
      CROSS JOIN LATERAL jsonb_array_elements(
           CASE WHEN jsonb_typeof(pl.itens) = 'array' THEN pl.itens ELSE '[]'::jsonb END) AS e
     WHERE NOT EXISTS (SELECT 1 FROM pedidos_itens pi WHERE pi.pedido_id = m.pedido_id);

    -- pagamentos.pedido_licenca_id -> pedido_id
    UPDATE pagamentos pg
       SET pedido_id = m.pedido_id,
           polo_id = COALESCE(pg.polo_id, p.polo_id),
           escola_id = COALESCE(pg.escola_id, p.escola_id)
      FROM migracao_pedidos_map m
      JOIN pedidos p ON p.id = m.pedido_id
     WHERE m.origem_tabela = 'pedidos_licenca'
       AND pg.pedido_licenca_id = m.origem_id
       AND pg.pedido_id IS NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 3. compras_licencas -> pedidos (tipo licenca, concluido)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.compras_licencas') IS NULL THEN
        RAISE NOTICE '017: compras_licencas inexistente/ja migrada - etapa ignorada';
        RETURN;
    END IF;

    INSERT INTO migracao_pedidos_map (origem_tabela, origem_id, pedido_id)
    SELECT 'compras_licencas', c.id, gen_random_uuid()
      FROM compras_licencas c
     WHERE NOT EXISTS (SELECT 1 FROM migracao_pedidos_map m
                        WHERE m.origem_tabela = 'compras_licencas' AND m.origem_id = c.id);

    INSERT INTO pedidos (
        id, numero, tipo, polo_id, status, fornecedor, valor_bruto, valor_total,
        pago_em, criado_em, atualizado_em
    )
    SELECT m.pedido_id,
           'PED-' || to_char(COALESCE(c.data_compra::timestamptz, c.criado_em, now()), 'YYYY') || '-' || lpad(nextval('seq_pedido')::text, 6, '0'),
           'licenca', c.polo_id, 'concluido', c.fornecedor,
           COALESCE(c.valor_total, c.quantidade * COALESCE(c.valor_unitario, 0), 0),
           COALESCE(c.valor_total, c.quantidade * COALESCE(c.valor_unitario, 0), 0),
           COALESCE(c.data_compra::timestamptz, c.criado_em),
           COALESCE(c.data_compra::timestamptz, c.criado_em, now()),
           COALESCE(c.criado_em, now())
      FROM compras_licencas c
      JOIN migracao_pedidos_map m ON m.origem_tabela = 'compras_licencas' AND m.origem_id = c.id
     WHERE NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id = m.pedido_id);

    INSERT INTO pedidos_itens (pedido_id, descricao, quantidade, valor_unitario, valor_total)
    SELECT m.pedido_id, 'Licenças', c.quantidade, COALESCE(c.valor_unitario, 0),
           COALESCE(c.valor_total, c.quantidade * COALESCE(c.valor_unitario, 0), 0)
      FROM compras_licencas c
      JOIN migracao_pedidos_map m ON m.origem_tabela = 'compras_licencas' AND m.origem_id = c.id
     WHERE NOT EXISTS (SELECT 1 FROM pedidos_itens pi WHERE pi.pedido_id = m.pedido_id);
END $$;

-- -----------------------------------------------------------------------------
-- 4. boletos -> pagamentos (preserva o id para manter URLs de 2a via)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.boletos') IS NULL THEN
        RAISE NOTICE '017: boletos inexistente/ja migrada - etapa ignorada';
        RETURN;
    END IF;

    INSERT INTO pagamentos (
        id, pedido_id, polo_id, gateway, ambiente, billing_type, valor, status,
        gateway_payment_id, asaas_payment_id, boleto_url, vencimento_em,
        descricao, criado_em, atualizado_em
    )
    SELECT b.id, m.pedido_id, b.polo_id, 'asaas', NULL, 'BOLETO', b.valor,
           COALESCE(NULLIF(lower(b.status), ''), 'pendente'),
           b.asaas_id, b.asaas_id, b.url_pdf, b.data_vencimento,
           'Boleto migrado (tabela boletos)', COALESCE(b.criado_em, now()), COALESCE(b.criado_em, now())
      FROM boletos b
      LEFT JOIN migracao_pedidos_map m ON m.origem_tabela = 'compras_licencas' AND m.origem_id = b.compra_id
     WHERE NOT EXISTS (SELECT 1 FROM pagamentos pg WHERE pg.id = b.id);

    -- compras com boleto_id mas sem compra_id no boleto
    IF to_regclass('public.compras_licencas') IS NOT NULL THEN
        UPDATE pagamentos pg
           SET pedido_id = m.pedido_id
          FROM compras_licencas c
          JOIN migracao_pedidos_map m ON m.origem_tabela = 'compras_licencas' AND m.origem_id = c.id
         WHERE c.boleto_id = pg.id AND pg.pedido_id IS NULL;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 5. Historico inicial dos pedidos migrados
-- -----------------------------------------------------------------------------
INSERT INTO pedidos_status_historico (pedido_id, status_de, status_para, origem, observacao, criado_em)
SELECT p.id, NULL, p.status, 'migracao', 'Migrado de ' || m.origem_tabela, p.criado_em
  FROM migracao_pedidos_map m
  JOIN pedidos p ON p.id = m.pedido_id
 WHERE m.origem_tabela IN ('pedidos_livros', 'pedidos_licenca', 'compras_licencas')
   AND NOT EXISTS (SELECT 1 FROM pedidos_status_historico h WHERE h.pedido_id = p.id);

-- -----------------------------------------------------------------------------
-- 6. Renomeia tabelas antigas para *_legado (rollback = renomear de volta)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'pedidos_livros_itens', 'pedidos_livros', 'pedidos_licenca',
        'boletos', 'compras_licencas', 'estoque_licencas'
    ] LOOP
        IF to_regclass('public.' || t) IS NOT NULL AND to_regclass('public.' || t || '_legado') IS NULL THEN
            EXECUTE format('ALTER TABLE %I RENAME TO %I', t, t || '_legado');
            RAISE NOTICE '017: % -> %_legado', t, t;
        END IF;
    END LOOP;
END $$;

COMMIT;

-- -----------------------------------------------------------------------------
-- Conferencia (rodar manualmente apos o COMMIT):
-- SELECT origem_tabela, count(*) FROM migracao_pedidos_map GROUP BY 1;
-- SELECT tipo, status, count(*), sum(valor_total) FROM pedidos GROUP BY 1, 2 ORDER BY 1, 2;
-- SELECT count(*) FROM pagamentos WHERE descricao = 'Boleto migrado (tabela boletos)';
-- SELECT (SELECT count(*) FROM pedidos_livros_legado) AS livros,
--        (SELECT count(*) FROM pedidos_licenca_legado) AS licenca,
--        (SELECT count(*) FROM compras_licencas_legado) AS compras,
--        (SELECT count(*) FROM pedidos) AS pedidos_total;
-- -----------------------------------------------------------------------------
