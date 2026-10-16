-- =====================================================================
-- Schema do módulo professores — NEXUS 2.0
-- A tabela `professores` já existe (criada pelo ETL legacy_sync com as
-- colunas usuario_id/polo_id/escola_id/chave_pix/valor_hora_aula/
-- data_inicio_aulas), portanto este script apenas ADICIONA as colunas
-- necessárias à gestão de docentes do painel administrativo.
-- Pressupõe já existentes: usuarios, perfis, polos, escolas
-- =====================================================================

-- Disciplinas/docências do professor (JSONB, mesmo formato esperado pelo
-- módulo polos_escolas: ["Matemática", "Física"])
ALTER TABLE professores ADD COLUMN IF NOT EXISTS materias JSONB NOT NULL DEFAULT '[]';

-- Data de início das aulas (o DDL legado gravava data_inicio_aulas TIMESTAMPTZ)
ALTER TABLE professores ADD COLUMN IF NOT EXISTS data_inicio DATE;

-- Carga horária contratada
ALTER TABLE professores ADD COLUMN IF NOT EXISTS quantidade_aulas INT NOT NULL DEFAULT 0;
ALTER TABLE professores ADD COLUMN IF NOT EXISTS horas_totais INT NOT NULL DEFAULT 0;

-- Conteúdo programático e chave PIX efetiva do docente
ALTER TABLE professores ADD COLUMN IF NOT EXISTS conteudo_programatico TEXT;
ALTER TABLE professores ADD COLUMN IF NOT EXISTS pix VARCHAR(255);

-- Ciclo de vida do cadastro (soft delete grava 'inativo')
ALTER TABLE professores ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ativo';

-- Backfill: aproveita a data de início registrada pelo ETL legado
UPDATE professores
   SET data_inicio = data_inicio_aulas::date
 WHERE data_inicio IS NULL
   AND data_inicio_aulas IS NOT NULL;

-- Índices para os filtros da listagem administrativa
CREATE INDEX IF NOT EXISTS idx_professores_polo_id ON professores (polo_id);
CREATE INDEX IF NOT EXISTS idx_professores_escola_id ON professores (escola_id);
CREATE INDEX IF NOT EXISTS idx_professores_status ON professores (status);
