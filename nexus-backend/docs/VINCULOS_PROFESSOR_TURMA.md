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

## Detalhe e totais docentes

Na area Corpo Docente, use "Ver detalhe do professor" para consultar disciplinas,
cursos e alunos ativos, agrupados por polo, escola e turma. A lista inclui apenas
turmas com vinculo ativo cuja disciplina tambem esteja no cadastro do professor.
Gestores so recebem turmas de sua propria unidade.

Horas e aulas previstas sao a soma dos valores das disciplinas vinculadas no
cadastro, contando cada disciplina uma vez e tratando valores ausentes como zero.
Vinculos exclusivamente por turma e nomes antigos de materias nao entram na
soma. Esses totais nao sao editaveis; valores enviados por clientes antigos sao
ignorados e o banco recalcula os totais mesmo em outros caminhos de escrita.

Antes de implantar a alteracao, faca backup e aplique, em ordem, as migracoes 008
e 010 (se ainda nao aplicadas) e
`scripts/migrations/013_totais_professores_disciplinas.sql`. A migracao 013
substitui os valores manuais existentes, inclusive por zero quando nao ha
disciplinas cadastradas. Suas triggers mantem os totais atualizados ao alterar
vinculos ou disciplinas; nao desative as triggers durante operacoes normais.
Para validar a migracao, configure `NEXUS_TEST_POSTGRES_DSN` para um banco de
teste isolado e execute `pytest tests/test_professores_totais_postgres.py`.
