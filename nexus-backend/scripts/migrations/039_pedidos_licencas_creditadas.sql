-- 039 — Crédito de licenças exatamente uma vez por pedido pago.
-- O crédito do estoque do Polo (licença/kit) rodava depois de o pagamento ser gravado como pago e,
-- se falhasse, o reprocessamento do webhook e o cron não creditavam mais (o pagamento já constava
-- como pago). A coluna marca o crédito na mesma transação do estoque e do extrato: o backend pode
-- repetir o crédito com segurança até ele acontecer.
--
-- APLIQUE ANTES DO DEPLOY do backend que a usa (sem a coluna, todo crédito de licença falha).
-- Idempotente: reaplique logo após o deploy para marcar os pedidos pagos nesse intervalo pelo
-- código antigo (que creditava sem marcar).

BEGIN;

ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS licencas_creditadas_em TIMESTAMPTZ;

-- Pedidos de licença/kit já pagos foram creditados pelo fluxo anterior: marcá-los evita crédito em dobro.
UPDATE pedidos
   SET licencas_creditadas_em = pago_em
 WHERE tipo IN ('licenca', 'kit')
   AND pago_em IS NOT NULL
   AND licencas_creditadas_em IS NULL;

COMMIT;
