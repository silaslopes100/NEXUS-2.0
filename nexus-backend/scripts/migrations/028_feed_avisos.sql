-- 028 — Feed de Notícias e Avisos (pop-ups)
-- Feed: publicações da equipe (texto formatado, mídias, links com miniatura), curtidas e comentários moderados.
-- Avisos: pop-ups agendados exibidos ao abrir a plataforma, por público (todos, perfis ou usuários).
-- Chat: mensagens passam a poder referenciar um post do feed (resposta ao autor via chat).
-- Idempotente: pode ser executada mais de uma vez.
-- Obs.: as tabelas legadas feed_posts / feed_noticias / lembretes não são usadas por este módulo.

-- ---------------------------------------------------------------------------
-- Feed
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS feed_publicacoes (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    autor_id                    UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    conteudo_html               TEXT NOT NULL DEFAULT '',
    conteudo_texto              TEXT NOT NULL DEFAULT '',
    publico_perfis              TEXT[],                 -- NULL = todos os perfis
    polo_id                     UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id                   UUID REFERENCES escolas(id) ON DELETE SET NULL,
    fixado                      BOOLEAN NOT NULL DEFAULT false,
    permite_comentarios         BOOLEAN NOT NULL DEFAULT true,
    total_curtidas              INT NOT NULL DEFAULT 0,
    total_comentarios_aprovados INT NOT NULL DEFAULT 0,
    editado                     BOOLEAN NOT NULL DEFAULT false,
    criado_em                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em                 TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_feed_publicacoes_ordem
    ON feed_publicacoes (fixado DESC, criado_em DESC, id DESC) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS idx_feed_publicacoes_autor ON feed_publicacoes (autor_id);

CREATE TABLE IF NOT EXISTS feed_midias (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id      UUID NOT NULL REFERENCES feed_publicacoes(id) ON DELETE CASCADE,
    tipo         VARCHAR(16) NOT NULL,
    url          TEXT NOT NULL,
    storage_key  VARCHAR(200) NOT NULL,
    nome         VARCHAR(255) NOT NULL,
    mime         VARCHAR(127) NOT NULL,
    tamanho      BIGINT NOT NULL,
    ordem        INT NOT NULL DEFAULT 0,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_feed_midia_tipo CHECK (tipo IN ('imagem', 'video', 'arquivo'))
);

CREATE INDEX IF NOT EXISTS idx_feed_midias_post ON feed_midias (post_id, ordem);

CREATE TABLE IF NOT EXISTS feed_links (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     UUID NOT NULL REFERENCES feed_publicacoes(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    titulo      VARCHAR(500),
    descricao   TEXT,
    imagem_url  TEXT,
    site_nome   VARCHAR(255),
    embed_tipo  VARCHAR(16),
    embed_id    VARCHAR(64),
    ordem       INT NOT NULL DEFAULT 0,
    CONSTRAINT ck_feed_link_embed CHECK (embed_tipo IS NULL OR embed_tipo IN ('youtube', 'vimeo'))
);

CREATE INDEX IF NOT EXISTS idx_feed_links_post ON feed_links (post_id, ordem);

CREATE TABLE IF NOT EXISTS feed_link_cache (
    url_hash    VARCHAR(64) PRIMARY KEY,
    url         TEXT NOT NULL,
    dados       JSONB NOT NULL,
    buscado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feed_curtidas (
    post_id     UUID NOT NULL REFERENCES feed_publicacoes(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS feed_comentarios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id          UUID NOT NULL REFERENCES feed_publicacoes(id) ON DELETE CASCADE,
    autor_id         UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    parent_id        UUID REFERENCES feed_comentarios(id) ON DELETE CASCADE,
    texto            VARCHAR(2000) NOT NULL,
    status           VARCHAR(16) NOT NULL DEFAULT 'pendente',
    moderado_por     UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    moderado_em      TIMESTAMPTZ,
    motivo_rejeicao  VARCHAR(500),
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em      TIMESTAMPTZ,
    CONSTRAINT ck_feed_comentario_status CHECK (status IN ('pendente', 'aprovado', 'rejeitado'))
);

CREATE INDEX IF NOT EXISTS idx_feed_comentarios_post ON feed_comentarios (post_id, status, criado_em);
CREATE INDEX IF NOT EXISTS idx_feed_comentarios_pendentes ON feed_comentarios (criado_em)
    WHERE status = 'pendente' AND excluido_em IS NULL;

-- ---------------------------------------------------------------------------
-- Avisos (pop-ups)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS avisos_popup (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo             VARCHAR(200) NOT NULL,
    conteudo_html      TEXT NOT NULL DEFAULT '',
    criado_por         UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    publico_tipo       VARCHAR(16) NOT NULL DEFAULT 'todos',
    perfis             TEXT[],
    polo_id            UUID REFERENCES polos(id) ON DELETE SET NULL,
    escola_id          UUID REFERENCES escolas(id) ON DELETE SET NULL,
    inicio_em          TIMESTAMPTZ NOT NULL,
    fim_em             TIMESTAMPTZ NOT NULL,
    frequencia         VARCHAR(16) NOT NULL DEFAULT 'uma_vez',
    exige_confirmacao  BOOLEAN NOT NULL DEFAULT false,
    prioridade         INT NOT NULL DEFAULT 0,
    ativo              BOOLEAN NOT NULL DEFAULT true,
    cor_destaque       VARCHAR(16),
    largura            VARCHAR(16) NOT NULL DEFAULT 'media',
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em        TIMESTAMPTZ,
    CONSTRAINT ck_aviso_publico CHECK (publico_tipo IN ('todos', 'perfis', 'usuarios')),
    CONSTRAINT ck_aviso_frequencia CHECK (frequencia IN ('uma_vez', 'ate_confirmar', 'toda_sessao')),
    CONSTRAINT ck_aviso_largura CHECK (largura IN ('pequena', 'media', 'grande')),
    CONSTRAINT ck_aviso_periodo CHECK (fim_em > inicio_em)
);

CREATE INDEX IF NOT EXISTS idx_avisos_popup_vigencia ON avisos_popup (ativo, inicio_em, fim_em)
    WHERE excluido_em IS NULL;

CREATE TABLE IF NOT EXISTS avisos_popup_usuarios (
    aviso_id    UUID NOT NULL REFERENCES avisos_popup(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    PRIMARY KEY (aviso_id, usuario_id)
);

CREATE INDEX IF NOT EXISTS idx_avisos_popup_usuarios_usuario ON avisos_popup_usuarios (usuario_id);

CREATE TABLE IF NOT EXISTS avisos_popup_midias (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aviso_id     UUID NOT NULL REFERENCES avisos_popup(id) ON DELETE CASCADE,
    tipo         VARCHAR(16) NOT NULL,
    url          TEXT NOT NULL,
    storage_key  VARCHAR(200),
    nome         VARCHAR(255),
    mime         VARCHAR(127),
    tamanho      BIGINT,
    embed_tipo   VARCHAR(16),
    embed_id     VARCHAR(64),
    ordem        INT NOT NULL DEFAULT 0,
    CONSTRAINT ck_aviso_midia_tipo CHECK (tipo IN ('imagem', 'video', 'arquivo', 'video_link'))
);

CREATE INDEX IF NOT EXISTS idx_avisos_popup_midias_aviso ON avisos_popup_midias (aviso_id, ordem);

CREATE TABLE IF NOT EXISTS avisos_popup_visualizacoes (
    aviso_id         UUID NOT NULL REFERENCES avisos_popup(id) ON DELETE CASCADE,
    usuario_id       UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    primeira_vez_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_vez_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    vezes            INT NOT NULL DEFAULT 1,
    confirmado_em    TIMESTAMPTZ,
    PRIMARY KEY (aviso_id, usuario_id)
);

-- ---------------------------------------------------------------------------
-- Chat: referência a um post do feed
-- ---------------------------------------------------------------------------

ALTER TABLE chat_mensagens ADD COLUMN IF NOT EXISTS ref_tipo VARCHAR(16);
ALTER TABLE chat_mensagens ADD COLUMN IF NOT EXISTS ref_id UUID;
ALTER TABLE chat_mensagens_historico ADD COLUMN IF NOT EXISTS ref_tipo VARCHAR(16);
ALTER TABLE chat_mensagens_historico ADD COLUMN IF NOT EXISTS ref_id UUID;
