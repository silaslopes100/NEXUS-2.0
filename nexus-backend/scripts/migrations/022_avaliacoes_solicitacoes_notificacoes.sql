-- =============================================================================
-- 022 - Avaliações (questionários por Disciplina), solicitações Escola -> Polo,
--       Nota de Prestação de Contas e notificações
--
-- - avaliacoes / questões / alternativas: questionário da Disciplina, usado na
--   prova online (aluno com licença) e reaproveitável pelo AVA (contexto 'ava').
-- - avaliacao_tentativas: tentativas do aluno; a nota vai para `notas`
--   (origem 'prova' ou 'ava') e o histórico segue a regra da maior nota (>= 6).
-- - solicitacoes_unidade(+itens): Escola pede licenças/livros ao Polo.
-- - notas_prestacao_contas: emitida pelo Polo ao atender; a Escola repassa o valor.
-- - notificacoes: avisos por usuário ou por unidade (Polo/Escola).
--
-- Requer a 021. Idempotente. Se algo falhar, a transação inteira é revertida.
-- =============================================================================
BEGIN;

-- 1) Avaliações -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS avaliacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplina_id UUID NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    instrucoes TEXT,
    tempo_limite_min INT CHECK (tempo_limite_min IS NULL OR tempo_limite_min BETWEEN 1 AND 600),
    tentativas_max INT NOT NULL DEFAULT 2 CHECK (tentativas_max BETWEEN 1 AND 20),
    nota_minima NUMERIC(4,2) NOT NULL DEFAULT 6.0 CHECK (nota_minima BETWEEN 0 AND 10),
    embaralhar BOOLEAN NOT NULL DEFAULT false,
    ativo BOOLEAN NOT NULL DEFAULT false,
    origem VARCHAR(16) NOT NULL DEFAULT 'manual' CHECK (origem IN ('manual', 'demo')),
    criado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_disciplina ON avaliacoes (disciplina_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_avaliacoes_ativa_disciplina ON avaliacoes (disciplina_id) WHERE ativo;

CREATE TABLE IF NOT EXISTS avaliacao_questoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    avaliacao_id UUID NOT NULL REFERENCES avaliacoes(id) ON DELETE CASCADE,
    enunciado TEXT NOT NULL,
    ordem INT NOT NULL DEFAULT 0,
    peso NUMERIC(5,2) NOT NULL DEFAULT 1 CHECK (peso > 0)
);
CREATE INDEX IF NOT EXISTS idx_avaliacao_questoes_avaliacao ON avaliacao_questoes (avaliacao_id, ordem);

CREATE TABLE IF NOT EXISTS avaliacao_alternativas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    questao_id UUID NOT NULL REFERENCES avaliacao_questoes(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    correta BOOLEAN NOT NULL DEFAULT false,
    ordem INT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_avaliacao_alternativas_questao ON avaliacao_alternativas (questao_id, ordem);

CREATE TABLE IF NOT EXISTS avaliacao_tentativas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    avaliacao_id UUID NOT NULL REFERENCES avaliacoes(id) ON DELETE CASCADE,
    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    licenca_id UUID REFERENCES licencas_alunos(id) ON DELETE SET NULL,
    contexto VARCHAR(16) NOT NULL DEFAULT 'prova_licenca' CHECK (contexto IN ('prova_licenca', 'ava')),
    status VARCHAR(16) NOT NULL DEFAULT 'em_andamento' CHECK (status IN ('em_andamento', 'finalizada', 'expirada')),
    ordem_questoes JSONB,
    respostas JSONB NOT NULL DEFAULT '{}'::jsonb,
    nota NUMERIC(4,2),
    nota_id UUID,
    iniciada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em TIMESTAMPTZ,
    finalizada_em TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_avaliacao_tentativas_aluno ON avaliacao_tentativas (aluno_id, avaliacao_id);
-- No máximo uma tentativa em andamento por aluno e avaliação.
CREATE UNIQUE INDEX IF NOT EXISTS uq_avaliacao_tentativa_aberta
    ON avaliacao_tentativas (avaliacao_id, aluno_id) WHERE status = 'em_andamento';

-- 2) Solicitações Escola -> Polo e Nota de Prestação de Contas ---------------
CREATE SEQUENCE IF NOT EXISTS seq_solicitacao_unidade START 1;
CREATE SEQUENCE IF NOT EXISTS seq_nota_prestacao START 1;

CREATE TABLE IF NOT EXISTS solicitacoes_unidade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(32) NOT NULL UNIQUE
        DEFAULT ('SOL-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('seq_solicitacao_unidade')::text, 6, '0')),
    escola_id UUID NOT NULL REFERENCES escolas(id) ON DELETE CASCADE,
    polo_id UUID NOT NULL REFERENCES polos(id) ON DELETE CASCADE,
    solicitante_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'atendida', 'atendida_parcial', 'recusada')),
    observacao TEXT,
    motivo_recusa TEXT,
    resolvido_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    resolvido_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_polo_status ON solicitacoes_unidade (polo_id, status, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_escola ON solicitacoes_unidade (escola_id, criado_em DESC);

CREATE TABLE IF NOT EXISTS solicitacoes_unidade_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solicitacao_id UUID NOT NULL REFERENCES solicitacoes_unidade(id) ON DELETE CASCADE,
    disciplina_id UUID NOT NULL REFERENCES disciplinas(id) ON DELETE RESTRICT,
    quantidade INT NOT NULL CHECK (quantidade > 0),
    quantidade_atendida INT NOT NULL DEFAULT 0 CHECK (quantidade_atendida >= 0),
    valor_unitario NUMERIC(12,2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_itens ON solicitacoes_unidade_itens (solicitacao_id);

CREATE TABLE IF NOT EXISTS notas_prestacao_contas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(32) NOT NULL UNIQUE
        DEFAULT ('NPC-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('seq_nota_prestacao')::text, 6, '0')),
    solicitacao_id UUID NOT NULL REFERENCES solicitacoes_unidade(id) ON DELETE CASCADE,
    polo_id UUID NOT NULL REFERENCES polos(id) ON DELETE CASCADE,
    escola_id UUID NOT NULL REFERENCES escolas(id) ON DELETE CASCADE,
    valor_total NUMERIC(12,2) NOT NULL DEFAULT 0,
    vencimento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'emitida' CHECK (status IN ('emitida', 'repasse_recebido', 'cancelada')),
    emitida_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    repasse_confirmado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    repasse_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prestacoes_polo ON notas_prestacao_contas (polo_id, status);

-- 3) Notificações -----------------------------------------------------------
-- A tabela já pode existir, criada vazia pelo legacy_sync (usuario_id, titulo, mensagem,
-- lida, legacy_*). Ela é COMPLETADA, não recriada: o destino por usuário continua em
-- `usuario_id`; entram destino por Polo/Escola, link e lida_em.
CREATE TABLE IF NOT EXISTS notificacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(255),
    mensagem TEXT,
    lida BOOLEAN DEFAULT false,
    criado_em TIMESTAMPTZ DEFAULT now(),
    atualizado_em TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS destino_polo_id UUID REFERENCES polos(id) ON DELETE CASCADE;
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS destino_escola_id UUID REFERENCES escolas(id) ON DELETE CASCADE;
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS link VARCHAR(500);
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS lida_em TIMESTAMPTZ;
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ DEFAULT now();
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_notificacoes_destino') THEN
        ALTER TABLE notificacoes ADD CONSTRAINT ck_notificacoes_destino CHECK (
            usuario_id IS NOT NULL OR destino_polo_id IS NOT NULL OR destino_escola_id IS NOT NULL) NOT VALID;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes (usuario_id, lida_em, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_notificacoes_polo ON notificacoes (destino_polo_id, lida_em, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_notificacoes_escola ON notificacoes (destino_escola_id, lida_em, criado_em DESC);

COMMENT ON COLUMN notas.origem IS 'manual, ava, prova (avaliação online) ou legado (ETL)';

COMMIT;
