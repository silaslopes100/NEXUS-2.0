-- 038 — Corrige a chave estrangeira dos capítulos de treinamento.
-- Uma versão antiga da 032 criou fk_ava_capitulos_treinamento apontando para a tabela LEGADA
-- "treinamentos" (módulo polos_escolas), em vez de "ava_treinamentos". Como a 032 só cria a chave
-- quando ela não existe, reaplicá-la não corrigia: todo capítulo novo de treinamento falhava (500).
-- Idempotente.

BEGIN;

ALTER TABLE ava_capitulos DROP CONSTRAINT IF EXISTS fk_ava_capitulos_treinamento;
ALTER TABLE ava_capitulos
    ADD CONSTRAINT fk_ava_capitulos_treinamento
    FOREIGN KEY (treinamento_id) REFERENCES ava_treinamentos(id) ON DELETE CASCADE;

COMMIT;
