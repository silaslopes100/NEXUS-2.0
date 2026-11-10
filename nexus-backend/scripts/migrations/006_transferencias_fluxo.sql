BEGIN;

ALTER TABLE solicitacoes_transferencia
    ADD COLUMN IF NOT EXISTS modalidade_origem VARCHAR(16),
    ADD COLUMN IF NOT EXISTS modalidade_destino VARCHAR(16),
    ADD COLUMN IF NOT EXISTS escola_origem_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS escola_destino_id UUID REFERENCES escolas(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS observacao TEXT,
    ADD COLUMN IF NOT EXISTS motivo_rejeicao TEXT,
    ADD COLUMN IF NOT EXISTS resolvido_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;

-- Cada aluno pode ter apenas uma solicitação aguardando análise.
CREATE UNIQUE INDEX IF NOT EXISTS uq_solicitacoes_transferencia_aluno_pendente
    ON solicitacoes_transferencia (aluno_id)
    WHERE status = 'pendente';

COMMIT;
