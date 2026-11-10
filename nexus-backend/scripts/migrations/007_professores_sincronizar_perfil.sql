-- Sincroniza "Corpo Docente" (tabela professores) com "Usuários" (perfil professor).
-- Idempotente: pode ser executada mais de uma vez.
BEGIN;

-- 1. Quem tem registro docente ativo passa a ter perfil `professor`.
WITH alterados AS (
    UPDATE usuarios u
       SET perfil_id = pp.id,
           atualizado_em = now()
      FROM professores pr, perfis pp
     WHERE pr.usuario_id = u.id
       AND pr.status = 'ativo'
       AND lower(pp.nome) = 'professor'
       AND u.perfil_id IS DISTINCT FROM pp.id
    RETURNING u.id
)
INSERT INTO logs_auditoria (usuario_id, acao, entidade, entidade_id, dados_depois, criado_em, atualizado_em)
SELECT NULL, 'usuario_perfil_alterado', 'usuarios', id::text,
       '{"perfil": "professor", "origem": "migracao_007"}'::jsonb, now(), now()
  FROM alterados;

-- 2. Usuário com perfil `professor` sem registro docente ganha um registro mínimo.
INSERT INTO professores (id, usuario_id, polo_id, escola_id, status, criado_em, atualizado_em)
SELECT gen_random_uuid(), u.id, u.polo_id, u.escola_id, 'ativo', now(), now()
  FROM usuarios u
  JOIN perfis p ON p.id = u.perfil_id
 WHERE lower(p.nome) = 'professor'
   AND NOT EXISTS (SELECT 1 FROM professores pr WHERE pr.usuario_id = u.id)
ON CONFLICT (usuario_id) DO NOTHING;

-- 3. Registro docente inativo de usuário com perfil professor volta a ficar ativo.
UPDATE professores pr
   SET status = 'ativo', atualizado_em = now()
  FROM usuarios u
  JOIN perfis p ON p.id = u.perfil_id
 WHERE pr.usuario_id = u.id
   AND lower(p.nome) = 'professor'
   AND pr.status <> 'ativo';

COMMIT;
