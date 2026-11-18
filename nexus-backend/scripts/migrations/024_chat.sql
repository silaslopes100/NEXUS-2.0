-- =============================================================================
-- 024 - Chat Interno Moderado
--
-- Tabelas próprias do chat (não usa nem altera as tabelas legadas
-- `conversas`, `conversa_membros` e `mensagens`, alimentadas pelo ETL).
--
-- - chat_conversas: uma linha por chat. `chave` é única e determinística:
--     individual  -> 'ind:<uuidA>_<uuidB>' (IDs dos usuários em ordem)
--     grupo turma -> 'turma:<turma_id>'
--     grupo livre -> 'grupo:<uuid>'
--   O `id` é uuid5(namespace, chave), gerado pela aplicação.
-- - chat_membros: participantes, leitura por membro e ocultação ("some só para mim").
-- - chat_mensagens: mensagens ativas (até 48h).
-- - chat_mensagens_historico: mensagens movidas após 48h; mantém 90 dias.
--   A rotação é feita pelo cron GET /chat/cron/rotacionar.
--
-- Idempotente. Se algo falhar, a transação inteira é revertida.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS chat_conversas (
    id UUID PRIMARY KEY,
    chave VARCHAR(200) NOT NULL UNIQUE,
    tipo VARCHAR(16) NOT NULL CHECK (tipo IN ('individual', 'grupo')),
    titulo VARCHAR(255),
    turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL,
    criado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'encerrada')),
    encerrada_em TIMESTAMPTZ,
    encerrada_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    ultima_mensagem_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_conversas_ultima ON chat_conversas (ultima_mensagem_em DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_chat_conversas_turma ON chat_conversas (turma_id) WHERE turma_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS chat_membros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    papel VARCHAR(16) NOT NULL DEFAULT 'membro' CHECK (papel IN ('membro', 'moderador')),
    ultima_leitura_em TIMESTAMPTZ,
    oculta_em TIMESTAMPTZ,
    entrou_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversa_id, usuario_id)
);
CREATE INDEX IF NOT EXISTS idx_chat_membros_usuario ON chat_membros (usuario_id);

CREATE TABLE IF NOT EXISTS chat_mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    remetente_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo VARCHAR(16) NOT NULL DEFAULT 'texto' CHECK (tipo IN ('texto', 'anexo', 'sistema')),
    texto TEXT,
    anexo_url VARCHAR(1000),
    anexo_storage_key VARCHAR(500),
    anexo_nome VARCHAR(255),
    anexo_mime VARCHAR(127),
    anexo_tamanho BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_mensagens_conversa ON chat_mensagens (conversa_id, criado_em);
CREATE INDEX IF NOT EXISTS idx_chat_mensagens_criado ON chat_mensagens (criado_em);

CREATE TABLE IF NOT EXISTS chat_mensagens_historico (
    id UUID PRIMARY KEY,
    conversa_id UUID NOT NULL REFERENCES chat_conversas(id) ON DELETE CASCADE,
    remetente_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo VARCHAR(16) NOT NULL DEFAULT 'texto',
    texto TEXT,
    anexo_url VARCHAR(1000),
    anexo_storage_key VARCHAR(500),
    anexo_nome VARCHAR(255),
    anexo_mime VARCHAR(127),
    anexo_tamanho BIGINT,
    criado_em TIMESTAMPTZ NOT NULL,
    arquivada_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_historico_conversa ON chat_mensagens_historico (conversa_id, criado_em);
CREATE INDEX IF NOT EXISTS idx_chat_historico_criado ON chat_mensagens_historico (criado_em);

COMMIT;
