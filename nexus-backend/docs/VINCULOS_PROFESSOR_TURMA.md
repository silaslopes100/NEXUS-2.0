# Vinculos de professores a turmas

Administradores, gestores de polo e gestores de escola podem abrir a acao de
docentes em uma turma e associar um professor a uma disciplina do curso daquela
turma. A API valida novamente o escopo do gestor, o status ativo do professor e
se a disciplina pertence ao curso; os dados enviados pelo navegador nao sao
considerados autorizacao.

No aplicativo, abra Turmas (`/admin/turmas`, `/polo/turmas` ou `/escola/turmas`)
e use o botao de docentes na linha da turma.

Um mesmo professor pode ter vinculos para disciplinas diferentes na mesma turma.
O mesmo par professor-disciplina-turma nao pode ser duplicado. Se um vinculo
arquivado for criado novamente, o registro existente e reativado.

Arquivar desativa o vinculo sem excluir a linha de `professor_disciplinas`, para
preservar materiais e atas associados. Vinculos inativos deixam de aparecer na
area docente e nao autorizam acesso a materiais, presencas ou notas.

Antes da implantacao, aplique
`scripts/migrations/010_arquivamento_vinculos_professor_turma.sql`.
