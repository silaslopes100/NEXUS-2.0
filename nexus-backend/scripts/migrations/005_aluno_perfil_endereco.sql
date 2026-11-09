-- Campos de endereço residencial para o perfil self-service do aluno.
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS cep VARCHAR(16),
    ADD COLUMN IF NOT EXISTS logradouro VARCHAR(255),
    ADD COLUMN IF NOT EXISTS numero VARCHAR(32),
    ADD COLUMN IF NOT EXISTS complemento VARCHAR(255),
    ADD COLUMN IF NOT EXISTS bairro VARCHAR(255),
    ADD COLUMN IF NOT EXISTS cidade VARCHAR(255),
    ADD COLUMN IF NOT EXISTS uf VARCHAR(2);
