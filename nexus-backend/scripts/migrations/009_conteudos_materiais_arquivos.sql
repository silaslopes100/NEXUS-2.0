-- Metadados de anexos mantidos em armazenamento privado.
BEGIN;

ALTER TABLE disciplina_conteudos
    ADD COLUMN IF NOT EXISTS arquivo_storage_key VARCHAR(500),
    ADD COLUMN IF NOT EXISTS arquivo_nome VARCHAR(255),
    ADD COLUMN IF NOT EXISTS arquivo_mime_type VARCHAR(127),
    ADD COLUMN IF NOT EXISTS arquivo_tamanho_bytes BIGINT;

ALTER TABLE professor_materiais
    ADD COLUMN IF NOT EXISTS arquivo_storage_key VARCHAR(500),
    ADD COLUMN IF NOT EXISTS arquivo_nome VARCHAR(255),
    ADD COLUMN IF NOT EXISTS arquivo_mime_type VARCHAR(127),
    ADD COLUMN IF NOT EXISTS arquivo_tamanho_bytes BIGINT;

COMMIT;
