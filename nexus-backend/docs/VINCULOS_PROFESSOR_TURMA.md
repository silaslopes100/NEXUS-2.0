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

## Unificacao dos vinculos administrativos

A migracao `scripts/migrations/014_unificar_professor_disciplinas.sql` copia
os pares de `professor_disciplina_vinculos` para `professor_disciplinas`, com
`turma_id` nulo. Ela nao exclui nem altera linhas preexistentes nessas tabelas;
mantem os IDs do destino e copia as datas da origem apenas para linhas novas.
Pares ja existentes sem turma nao sao duplicados. Um par com turma nao substitui
o registro administrativo. A tabela antiga permanece como copia historica e
nao deve mais receber escritas nem ser usada como fonte pela aplicacao.
As chaves estrangeiras antigas ainda podem apagar registros em cascata quando
um professor ou uma disciplina for excluido; preserve o backup para uma copia
historica imutavel.

Todas as linhas preexistentes sem turma passam a ser administrativas, inclusive
as inativas e as que nao constavam na tabela antiga. Elas entram nas listagens,
autorizacao por disciplina e totais, portanto os totais podem mudar. O campo
`ativo` continua determinando a atividade dos vinculos de turma. A edicao do
cadastro nao remove vinculos de turma e recusa a remocao de uma linha
administrativa que tenha dependencias.

Antes do corte:

1. Confirme no banco real os nomes, colunas, restricoes, triggers, referencias
   e todos os processos externos que usam as duas tabelas. Aplique antes as
   migracoes 008, 010 e 013 de totais, se ainda nao estiverem aplicadas; a
   migracao 013 de lotacoes tambem e necessaria para a versao atual da
   aplicacao. Nao execute novamente a 013 de totais apos a 014.
2. Em homologacao com copia protegida, confira pares da origem, registros
   existentes sem turma, dados associados e totais. A migracao interrompe a
   transacao se encontrar pares duplicados sem turma ou referencias invalidas;
   investigue e decida como corrigir esses casos antes de prosseguir.
3. Ensaie a restauracao do backup e a migracao. Configure
   `NEXUS_TEST_POSTGRES_DSN` apontando para um PostgreSQL **de teste isolado**
   e execute `pytest tests/test_unificar_professor_disciplinas_postgres.py
   tests/test_professores_totais_postgres.py`.
4. Em janela de manutencao, interrompa todos os leitores e escritores antigos,
   inclusive ETL e integracoes, e produza backup verificavel. Execute a 014 em
   uma unica sessao; ela bloqueia as tabelas durante a transacao e falhas
   revertem toda a migracao. Implante a versao atualizada da aplicacao antes
   de liberar os acessos. Nao execute versoes antigas apos o corte.
5. Antes de liberar, confira que cada par de origem tem uma linha sem turma no
   destino, compare as linhas preexistentes com o backup e valide totais,
   permissoes, turmas, materiais, aulas, presencas e notas. A tabela
   `migracao_professor_disciplinas` registra a conclusao para impedir que uma
   nova execucao recrie vinculos removidos posteriormente.

Se a validacao falhar, mantenha a manutencao e restaure banco e aplicacao a
partir do backup testado. Se ja houver escritas posteriores ao corte, preserve e
concilie essas alteracoes antes da restauracao para nao perde-las.
