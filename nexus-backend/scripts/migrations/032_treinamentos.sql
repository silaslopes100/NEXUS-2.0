-- 032 — AVA: Treinamentos, workshops e capacitações para Polos, Escolas e Professores
-- O conteúdo usa o mesmo motor do AVA (ava_capitulos.treinamento_id >> ava_aulas >> ava_aula_itens).
-- Público: perfis-alvo e, opcionalmente, polos/escolas específicos (sem unidades = todas).
-- Tabelas com prefixo ava_: a tabela legada `treinamentos` (polos_escolas/schema.sql) não é usada aqui.
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

CREATE TABLE IF NOT EXISTS ava_treinamentos (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo             VARCHAR(255) NOT NULL,
    descricao          TEXT,
    capa_url           TEXT,
    categoria          VARCHAR(16) NOT NULL DEFAULT 'treinamento',
    carga_horaria      INT,
    perfis_alvo        TEXT[] NOT NULL DEFAULT ARRAY['polo', 'escola', 'professor'],
    certificado_ativo  BOOLEAN NOT NULL DEFAULT true,
    sequencial         BOOLEAN NOT NULL DEFAULT false,
    data_inicio        DATE,
    data_fim           DATE,
    publicado          BOOLEAN NOT NULL DEFAULT false,
    criado_por         UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_ava_treinamento_categoria CHECK (categoria IN ('treinamento', 'workshop', 'capacitacao'))
);

CREATE INDEX IF NOT EXISTS idx_ava_treinamentos_publicados ON ava_treinamentos (publicado, criado_em DESC);

CREATE TABLE IF NOT EXISTS ava_treinamento_unidades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treinamento_id  UUID NOT NULL REFERENCES ava_treinamentos(id) ON DELETE CASCADE,
    polo_id         UUID REFERENCES polos(id) ON DELETE CASCADE,
    escola_id       UUID REFERENCES escolas(id) ON DELETE CASCADE,
    CONSTRAINT ck_ava_treinamento_unidade CHECK ((polo_id IS NULL) <> (escola_id IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_ava_treinamento_unidades ON ava_treinamento_unidades (treinamento_id);

CREATE TABLE IF NOT EXISTS ava_treinamento_conclusoes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treinamento_id    UUID NOT NULL REFERENCES ava_treinamentos(id) ON DELETE CASCADE,
    usuario_id        UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    concluido_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    codigo_validacao  VARCHAR(16) NOT NULL UNIQUE,
    CONSTRAINT uq_ava_treinamento_conclusao UNIQUE (treinamento_id, usuario_id)
);

-- O motor de conteúdo criado na 030 passa a apontar para os treinamentos.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ava_capitulos_treinamento') THEN
        ALTER TABLE ava_capitulos
            ADD CONSTRAINT fk_ava_capitulos_treinamento
            FOREIGN KEY (treinamento_id) REFERENCES ava_treinamentos(id) ON DELETE CASCADE;
    END IF;
END $$;

COMMIT;
