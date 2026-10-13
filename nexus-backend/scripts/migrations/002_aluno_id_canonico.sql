-- Migração 002 (idempotente): id canônico do aluno = alunos.id.
-- licencas_alunos, licencas_movimentacoes e requisicoes_troca passam a referenciar alunos(id)
-- em vez de usuarios(id). Linhas existentes são convertidas (usuarios.id -> alunos.id).

DO $$
DECLARE
    t TEXT;
    c TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['licencas_alunos', 'licencas_movimentacoes', 'requisicoes_troca'] LOOP
        c := t || '_aluno_id_fkey';
        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = c AND conrelid = t::regclass AND confrelid = 'usuarios'::regclass
        ) THEN
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', t, c);
            EXECUTE format(
                'UPDATE %I x SET aluno_id = a.id FROM alunos a WHERE a.usuario_id = x.aluno_id', t
            );
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (aluno_id) REFERENCES alunos(id)', t, c
            );
        END IF;
    END LOOP;
END $$;
