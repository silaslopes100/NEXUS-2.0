-- 030 — Remove o fluxo antigo de Calendários Oficiais.
-- O calendário da turma passou a vir do Calendário Acadêmico do curso (migration 029:
-- calendarios_academicos + cursos.calendario_id). A API não lê nem grava mais
-- turmas.calendario_oficial_id nem calendarios_oficiais.
-- Irreversível: os registros de calendarios_oficiais são apagados.
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

ALTER TABLE turmas DROP COLUMN IF EXISTS calendario_oficial_id;
DROP TABLE IF EXISTS calendarios_oficiais;

COMMIT;
