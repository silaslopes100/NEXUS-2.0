import { z } from 'zod';

export const cpfValido = (valor: string): boolean => {
  const d = valor.replace(/\D/g, '');
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (const i of [9, 10]) {
    let soma = 0;
    for (let n = 0; n < i; n++) soma += Number(d[n]) * (i + 1 - n);
    if (((soma * 10) % 11) % 10 !== Number(d[i])) return false;
  }
  return true;
};

export const alunoFormSchema = z
  .object({
    nome: z.string().trim().min(1, 'Informe o nome'),
    sobrenome: z.string().trim().optional(),
    cpf: z.string().refine(cpfValido, 'CPF inválido'),
    email: z.string().trim().email('E-mail inválido'),
    data_nascimento: z
      .string()
      .min(1, 'Informe a data de nascimento')
      .refine((v) => v < new Date().toISOString().slice(0, 10), 'Data deve ser anterior a hoje'),
    modalidade: z.enum(['polo', 'escola', 'ead']),
    escola_id: z.string().optional(),
  })
  .superRefine((v, ctx) => {
    if (v.modalidade === 'escola' && !v.escola_id) {
      ctx.addIssue({ code: 'custom', path: ['escola_id'], message: 'Selecione a escola' });
    }
  });

export type AlunoFormValues = z.infer<typeof alunoFormSchema>;
