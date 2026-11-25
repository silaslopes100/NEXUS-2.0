-- 031 — AVA: gamificação (XP, níveis, sequência de dias, conquistas e ranking semanal por curso)
-- Cada crédito de XP é um evento único por (usuário, tipo, referência): concluir de novo não duplica.
-- O "dia" da sequência segue o horário de Brasília.
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

CREATE TABLE IF NOT EXISTS gam_eventos_xp (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo           VARCHAR(32) NOT NULL,
    referencia_id  VARCHAR(64) NOT NULL,
    xp             INT NOT NULL,
    curso_id       UUID REFERENCES cursos(id) ON DELETE SET NULL,
    descricao      VARCHAR(255),
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gam_evento UNIQUE (usuario_id, tipo, referencia_id)
);

CREATE INDEX IF NOT EXISTS idx_gam_eventos_usuario ON gam_eventos_xp (usuario_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_gam_eventos_ranking ON gam_eventos_xp (curso_id, criado_em);

-- Catálogo de conquistas. regra: {"contador": <tipo de evento>, "minimo": n} | {"streak": n}
--                                 | {"nota": n} | {"ranking_semanal": posição}
CREATE TABLE IF NOT EXISTS gam_conquistas (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo     VARCHAR(48) NOT NULL UNIQUE,
    nome       VARCHAR(120) NOT NULL,
    descricao  VARCHAR(255) NOT NULL,
    icone      VARCHAR(32) NOT NULL DEFAULT 'medal',
    cor        VARCHAR(16) NOT NULL DEFAULT '#FFB800',
    regra      JSONB NOT NULL,
    xp_bonus   INT NOT NULL DEFAULT 0,
    ordem      INT NOT NULL DEFAULT 0,
    ativo      BOOLEAN NOT NULL DEFAULT true,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gam_conquistas_usuario (
    usuario_id    UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    conquista_id  UUID NOT NULL REFERENCES gam_conquistas(id) ON DELETE CASCADE,
    obtida_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (usuario_id, conquista_id)
);

CREATE TABLE IF NOT EXISTS gam_streak (
    usuario_id  UUID PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    atual       INT NOT NULL DEFAULT 0,
    recorde     INT NOT NULL DEFAULT 0,
    ultimo_dia  DATE
);

-- Privacidade: o aluno pode sair do ranking.
ALTER TABLE alunos ADD COLUMN IF NOT EXISTS ranking_visivel BOOLEAN NOT NULL DEFAULT true;

INSERT INTO gam_conquistas (codigo, nome, descricao, icone, cor, regra, xp_bonus, ordem) VALUES
    ('primeira_aula',       'Primeiro passo',       'Concluiu a primeira aula.',                     'play',       '#22C55E', '{"contador": "aula_concluida", "minimo": 1}',     10, 10),
    ('dez_aulas',           'Embalado',             'Concluiu 10 aulas.',                            'rocket',     '#3B82F6', '{"contador": "aula_concluida", "minimo": 10}',    30, 20),
    ('cinquenta_aulas',     'Maratonista',          'Concluiu 50 aulas.',                            'zap',        '#8B5CF6', '{"contador": "aula_concluida", "minimo": 50}',   100, 30),
    ('primeiro_capitulo',   'Capítulo fechado',     'Concluiu o primeiro capítulo.',                 'book',       '#06B6D4', '{"contador": "capitulo_concluido", "minimo": 1}', 20, 40),
    ('primeira_aprovacao',  'Aprovado!',            'Foi aprovado na primeira avaliação.',           'check',      '#10B981', '{"contador": "avaliacao_aprovada", "minimo": 1}', 30, 50),
    ('nota_dez',            'Nota 10',              'Tirou nota 10 em uma avaliação.',               'star',       '#FFB800', '{"nota": 10}',                                    50, 60),
    ('primeira_disciplina', 'Disciplina concluída', 'Concluiu a primeira disciplina.',               'graduation', '#F59E0B', '{"contador": "disciplina_concluida", "minimo": 1}', 50, 70),
    ('cinco_disciplinas',   'Rumo ao diploma',      'Concluiu 5 disciplinas.',                       'trophy',     '#EAB308', '{"contador": "disciplina_concluida", "minimo": 5}', 150, 80),
    ('streak_7',            'Uma semana em chamas', 'Estudou 7 dias seguidos.',                      'flame',      '#F97316', '{"streak": 7}',                                   50, 90),
    ('streak_30',           'Imparável',            'Estudou 30 dias seguidos.',                     'flame',      '#EF4444', '{"streak": 30}',                                 200, 100),
    ('podio_semanal',       'No pódio',             'Ficou entre os 3 primeiros do ranking da semana.', 'crown',   '#FACC15', '{"ranking_semanal": 3}',                          50, 110)
ON CONFLICT (codigo) DO NOTHING;

COMMIT;
