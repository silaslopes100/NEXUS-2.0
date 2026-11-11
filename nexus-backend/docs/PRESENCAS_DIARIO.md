# Diário de presença docente

Docentes com vínculo ativo e administradores podem registrar chamadas em lote
por vínculo, data e número da aula. A lista inclui todos os alunos com matrícula
ativa na turma e exige uma escolha explícita de presente/ausente para cada
aluno. Administradores podem selecionar qualquer vínculo ativo; docentes veem
somente os próprios vínculos.

## Endpoints

- `GET /presencas/vinculos`: vínculos disponíveis ao usuário autenticado.
- `GET /presencas/vinculos/{vinculo_id}/alunos?data_aula=AAAA-MM-DD&numero_aula=N`:
  alunos matriculados e registros existentes para preencher ou corrigir a
  chamada.
- `PUT /presencas/chamadas`: salva ou corrige em uma transação a chamada completa.
  Reenviar o mesmo vínculo/data/aula atualiza as presenças existentes sem criar
  duplicatas.
- `GET /presencas?aluno_id=...&professor_disciplina_id=...&limit=100&offset=0`:
  consulta paginada (máximo de 500 registros por página), limitada aos vínculos
  ativos do professor.
- `POST /presencas/lancar`: lançamento individual legado; exige vínculo, data,
  matrícula ativa e responde `409` se a presença já existir.

Tentativas docentes de acessar vínculo de outro professor são negadas. Para
ambos os perfis que podem lançar, aluno fora da turma, vínculo inativo e chamada
incompleta são rejeitados pelo servidor.

## Banco de dados

Antes de habilitar a feature, aplique
`scripts/migrations/011_unicidade_chamadas_presenca.sql`. O índice parcial
`uq_presencas_vinculo_aluno_aula` garante um registro por aluno, vínculo, data e
número da aula. Registros históricos sem vínculo/data/número permanecem intactos.
A migração também adiciona colunas ausentes em instalações legadas e torna
`aula_id` nullable, sem apagar seu valor histórico. O esquema SQL do módulo e o
esquema canônico do ETL criam os mesmos campos e índice.

A tabela de presença existente também contém registros legados do ETL. A
migração não altera nem exclui esses dados; os relatórios existentes continuam
consumindo a tabela `presencas`.
