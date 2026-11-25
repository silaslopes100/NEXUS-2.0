-- 030 — AVA: motor de conteúdo (Capítulo >> Aula >> Itens)
-- O conteúdo EAD é sempre preso a uma disciplina existente; o mesmo motor atende os Treinamentos
-- (treinamento_id — a FK é criada na migração dos treinamentos).
-- Vídeos são somente embed (YouTube, Vimeo, Panda, iframe); arquivos vão pelo upload direto (prefixo "ava").
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

CREATE TABLE IF NOT EXISTS ava_disciplina_config (
    disciplina_id  UUID PRIMARY KEY REFERENCES disciplinas(id) ON DELETE CASCADE,
    capa_url       TEXT,
    descricao_ava  TEXT,
    sequencial     BOOLEAN NOT NULL DEFAULT false,
    publicado      BOOLEAN NOT NULL DEFAULT false,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ava_capitulos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplina_id   UUID REFERENCES disciplinas(id) ON DELETE CASCADE,
    treinamento_id  UUID,
    titulo          VARCHAR(255) NOT NULL,
    descricao       TEXT,
    ordem           INT NOT NULL DEFAULT 0,
    publicado       BOOLEAN NOT NULL DEFAULT true,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_ava_capitulo_dono CHECK ((disciplina_id IS NULL) <> (treinamento_id IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_ava_capitulos_disciplina ON ava_capitulos (disciplina_id, ordem);
CREATE INDEX IF NOT EXISTS idx_ava_capitulos_treinamento ON ava_capitulos (treinamento_id, ordem);

CREATE TABLE IF NOT EXISTS ava_aulas (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capitulo_id        UUID NOT NULL REFERENCES ava_capitulos(id) ON DELETE CASCADE,
    titulo             VARCHAR(255) NOT NULL,
    descricao          TEXT,
    tipo               VARCHAR(16) NOT NULL DEFAULT 'conteudo',
    avaliacao_id       UUID REFERENCES avaliacoes(id) ON DELETE SET NULL,
    duracao_min        INT,
    ordem              INT NOT NULL DEFAULT 0,
    publicado          BOOLEAN NOT NULL DEFAULT true,
    obrigatoria        BOOLEAN NOT NULL DEFAULT true,
    liberar_apos_dias  INT,
    capa_url           TEXT,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_ava_aula_tipo CHECK (tipo IN ('conteudo', 'avaliacao'))
);

CREATE INDEX IF NOT EXISTS idx_ava_aulas_capitulo ON ava_aulas (capitulo_id, ordem);

CREATE TABLE IF NOT EXISTS ava_aula_itens (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id           UUID NOT NULL REFERENCES ava_aulas(id) ON DELETE CASCADE,
    tipo              VARCHAR(16) NOT NULL,
    titulo            VARCHAR(255),
    url               TEXT,
    provedor          VARCHAR(16),
    embed_id          VARCHAR(128),
    conteudo_html     TEXT,
    arquivo_pathname  VARCHAR(200),
    arquivo_nome      VARCHAR(255),
    arquivo_mime      VARCHAR(127),
    arquivo_tamanho   BIGINT,
    permite_download  BOOLEAN NOT NULL DEFAULT true,
    ordem             INT NOT NULL DEFAULT 0,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_ava_item_tipo CHECK (tipo IN ('video_embed', 'arquivo', 'imagem', 'link', 'texto'))
);

CREATE INDEX IF NOT EXISTS idx_ava_aula_itens_aula ON ava_aula_itens (aula_id, ordem);

CREATE TABLE IF NOT EXISTS ava_progresso (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id        UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    aula_id           UUID NOT NULL REFERENCES ava_aulas(id) ON DELETE CASCADE,
    status            VARCHAR(16) NOT NULL DEFAULT 'iniciada',
    percentual        INT NOT NULL DEFAULT 0,
    posicao_seg       INT,
    ultimo_acesso_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em      TIMESTAMPTZ,
    CONSTRAINT uq_ava_progresso UNIQUE (usuario_id, aula_id),
    CONSTRAINT ck_ava_progresso_status CHECK (status IN ('iniciada', 'concluida'))
);

CREATE INDEX IF NOT EXISTS idx_ava_progresso_recente ON ava_progresso (usuario_id, ultimo_acesso_em DESC);
CREATE INDEX IF NOT EXISTS idx_ava_progresso_aula ON ava_progresso (aula_id);

CREATE TABLE IF NOT EXISTS ava_anotacoes (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    aula_id        UUID NOT NULL REFERENCES ava_aulas(id) ON DELETE CASCADE,
    texto          TEXT NOT NULL,
    posicao_seg    INT,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ava_anotacoes_usuario_aula ON ava_anotacoes (usuario_id, aula_id);

CREATE TABLE IF NOT EXISTS ava_aula_avaliacoes (
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    aula_id     UUID NOT NULL REFERENCES ava_aulas(id) ON DELETE CASCADE,
    nota        SMALLINT NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (usuario_id, aula_id),
    CONSTRAINT ck_ava_aula_avaliacao_nota CHECK (nota BETWEEN 1 AND 5)
);

COMMIT;
