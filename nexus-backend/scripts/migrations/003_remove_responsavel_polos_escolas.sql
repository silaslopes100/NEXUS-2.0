-- Migração 003 (idempotente): remove as colunas responsavel_* de polos e escolas.
-- A fonte de verdade do responsável passa a ser o usuário vinculado:
--   - Polo  -> polos.coordenador_usuario_id (usuarios)
--   - Escola -> usuarios.escola_id (perfil secretario_escola/escola)
--
-- ANTES do drop, faz o backfill dos vínculos por CPF para preservar
-- coordenadores/secretários que ainda não estavam linkados.

-- 1a. Polos: vincula coordenador por CPF (perfil coordenador_polo)
UPDATE polos p
SET coordenador_usuario_id = u.id
FROM usuarios u
JOIN perfis pf ON pf.id = u.perfil_id
WHERE p.coordenador_usuario_id IS NULL
  AND p.responsavel_cpf IS NOT NULL
  AND u.cpf = p.responsavel_cpf
  AND lower(pf.nome) = 'coordenador_polo';

-- 1b. Escolas: vincula secretário por CPF (vínculo vive em usuarios.escola_id)
-- Obs.: em UPDATE, a tabela alvo (u) não pode ser referenciada dentro do
-- JOIN ... ON do FROM; a condição com u vai para o WHERE.
UPDATE usuarios u
SET escola_id = e.id
FROM escolas e, perfis pf
WHERE pf.id = u.perfil_id
  AND u.escola_id IS NULL
  AND e.responsavel_cpf IS NOT NULL
  AND u.cpf = e.responsavel_cpf
  AND lower(pf.nome) IN ('secretario_escola', 'escola');

-- 2. Drop das colunas redundantes
ALTER TABLE polos DROP COLUMN IF EXISTS responsavel_nome,
                  DROP COLUMN IF EXISTS responsavel_cpf,
                  DROP COLUMN IF EXISTS responsavel_email;

ALTER TABLE escolas DROP COLUMN IF EXISTS responsavel_nome,
                    DROP COLUMN IF EXISTS responsavel_cpf,
                    DROP COLUMN IF EXISTS responsavel_email;
