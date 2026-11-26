"""Vendas EAD: vitrine pública das Turmas EAD, inscrição gratuita e loja de disciplinas do aluno.

Fluxo: o visitante escolhe uma Turma EAD na vitrine e se inscreve (cria a conta de aluno EAD,
a matrícula no curso e a vaga na turma). Na loja, compra cada disciplina quando ela é liberada
pelo calendário da turma e publicada pelo admin no AVA (R$ 45 + livro físico opcional).
O pagamento confirmado (webhook/cron do financeiro) libera a disciplina no AVA.
"""
