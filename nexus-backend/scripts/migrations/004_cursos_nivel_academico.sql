ALTER TABLE cursos
    DROP COLUMN IF EXISTS legacy_table,
    DROP COLUMN IF EXISTS legacy_id,
    ADD COLUMN IF NOT EXISTS nivel_academico VARCHAR(32);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_cursos_nivel_academico'
          AND conrelid = 'cursos'::regclass
    ) THEN
        ALTER TABLE cursos
            ADD CONSTRAINT ck_cursos_nivel_academico
            CHECK (
                nivel_academico IS NULL
                OR nivel_academico IN (
                    'bacharelado',
                    'licenciatura',
                    'tecnologo',
                    'pos_graduacao',
                    'mestrado'
                )
            );
    END IF;
END $$;
