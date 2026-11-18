-- =============================================================================
-- 023 - Disciplina ativa / inativa
--
-- Disciplina inativa sai do catálogo de compra (o kit fica inativo) e não entra no
-- preço do Curso (soma das disciplinas ativas). Pedidos e notas já existentes não mudam.
-- Todas as disciplinas atuais ficam ativas. Idempotente.
-- =============================================================================
BEGIN;

ALTER TABLE disciplinas ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT true;
CREATE INDEX IF NOT EXISTS idx_disciplinas_curso_ativas ON disciplinas (curso_id) WHERE ativo;

COMMIT;
