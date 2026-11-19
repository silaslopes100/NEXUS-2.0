-- 027 — Central de Estágio ETADEMP
-- Etapa 1: Teologia do Ministério (50h iniciais) · Etapa 2: Homilética (50h finais, liberada após aprovar a 1).
-- Uma submissão por aluno e etapa; o reenvio (após "negado") reaproveita a linha e o histórico fica em estagio_eventos.
-- Idempotente: pode ser executada mais de uma vez.

CREATE TABLE IF NOT EXISTS estagio_submissoes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id             UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    etapa                VARCHAR(32) NOT NULL,
    status               VARCHAR(16) NOT NULL DEFAULT 'em_analise',
    horas                INT NOT NULL DEFAULT 50,
    comentario_feedback  TEXT,
    avaliado_por         UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    avaliado_em          TIMESTAMPTZ,
    visto_pelo_aluno     BOOLEAN NOT NULL DEFAULT true,
    codigo_comprovante   VARCHAR(20) UNIQUE,
    enviado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_estagio_etapa CHECK (etapa IN ('teologia_ministerio', 'homiletica')),
    CONSTRAINT ck_estagio_status CHECK (status IN ('em_analise', 'aprovado', 'negado')),
    CONSTRAINT uq_estagio_aluno_etapa UNIQUE (aluno_id, etapa)
);

CREATE INDEX IF NOT EXISTS idx_estagio_submissoes_status ON estagio_submissoes (status);
CREATE INDEX IF NOT EXISTS idx_estagio_submissoes_aluno ON estagio_submissoes (aluno_id);
CREATE INDEX IF NOT EXISTS idx_estagio_submissoes_enviado ON estagio_submissoes (enviado_em);

CREATE TABLE IF NOT EXISTS estagio_arquivos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submissao_id  UUID NOT NULL REFERENCES estagio_submissoes(id) ON DELETE CASCADE,
    tipo          VARCHAR(16) NOT NULL,
    nome          VARCHAR(255) NOT NULL,
    mime          VARCHAR(127) NOT NULL,
    tamanho       BIGINT NOT NULL,
    url           TEXT NOT NULL,
    storage_key   VARCHAR(200) NOT NULL,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_estagio_arquivo_tipo CHECK (tipo IN ('carta', 'relatorio', 'foto'))
);

CREATE INDEX IF NOT EXISTS idx_estagio_arquivos_submissao ON estagio_arquivos (submissao_id);

CREATE TABLE IF NOT EXISTS estagio_eventos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submissao_id  UUID NOT NULL REFERENCES estagio_submissoes(id) ON DELETE CASCADE,
    acao          VARCHAR(16) NOT NULL,
    comentario    TEXT,
    usuario_id    UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_estagio_evento_acao CHECK (acao IN ('enviado', 'reenviado', 'aprovado', 'negado'))
);

CREATE INDEX IF NOT EXISTS idx_estagio_eventos_submissao ON estagio_eventos (submissao_id, criado_em);

-- Arquivos-base que o aluno baixa (o Admin substitui pela Gestão de Arquivos).
CREATE TABLE IF NOT EXISTS estagio_arquivos_base (
    chave           VARCHAR(32) PRIMARY KEY,
    nome            VARCHAR(255) NOT NULL,
    mime            VARCHAR(127) NOT NULL,
    tamanho         BIGINT NOT NULL,
    url             TEXT NOT NULL,
    storage_key     VARCHAR(200) NOT NULL,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_por  UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT ck_estagio_base_chave CHECK (chave IN ('manual', 'carta_modelo', 'relatorio_modelo'))
);

-- Configuração única (link do vídeo explicativo do manual).
CREATE TABLE IF NOT EXISTS estagio_config (
    id             SMALLINT PRIMARY KEY DEFAULT 1,
    video_url      TEXT,
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_estagio_config_unica CHECK (id = 1)
);

INSERT INTO estagio_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
