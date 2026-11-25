-- 033 — Ficha cadastral do usuário: dados pessoais, documentos, contato de emergência e inativação.
--  * usuarios.data_nascimento passa a ser a fonte; alunos.data_nascimento continua sendo gravada
--    junto (o login e outras telas leem de lá). Backfill a partir de alunos.
--  * inativado_em / inativado_por / motivo_inativacao: "Excluir" virou "Inativar" (a exclusão
--    definitiva só vale para cadastros sem histórico).
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_nascimento DATE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rg VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rg_orgao_emissor VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rg_uf CHAR(2);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS sexo VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS estado_civil VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS naturalidade_cidade VARCHAR(120);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS naturalidade_uf CHAR(2);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nacionalidade VARCHAR(60) DEFAULT 'brasileira';
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS contato_emergencia_nome VARCHAR(255);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS contato_emergencia_parentesco VARCHAR(60);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS contato_emergencia_telefone VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS inativado_em TIMESTAMPTZ;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS inativado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS motivo_inativacao TEXT;

UPDATE usuarios u
   SET data_nascimento = a.data_nascimento
  FROM alunos a
 WHERE a.usuario_id = u.id
   AND a.data_nascimento IS NOT NULL
   AND u.data_nascimento IS NULL;

COMMIT;
