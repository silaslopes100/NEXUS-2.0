import { z } from 'zod';

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, { message: 'Informe o seu e-mail' })
    .email({ message: 'Digite um formato de e-mail válido' }),
  senha: z
    .string()
    .min(1, { message: 'Informe a sua senha' })
    .min(4, { message: 'A senha deve conter no mínimo 4 caracteres' }),
  lembrarEmail: z.boolean().optional(),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const esqueciSenhaSchema = z.object({
  email: z
    .string()
    .min(1, { message: 'Informe o seu e-mail' })
    .email({ message: 'Digite um e-mail válido para recuperação' }),
});

export type EsqueciSenhaFormData = z.infer<typeof esqueciSenhaSchema>;

export const redefinirSenhaSchema = z
  .object({
    token: z
      .string()
      .min(1, { message: 'O código ou token de recuperação é obrigatório' }),
    nova_senha: z
      .string()
      .min(6, { message: 'A nova senha deve ter no mínimo 6 caracteres' })
      .max(64, { message: 'A senha não pode exceder 64 caracteres' }),
    confirmar_senha: z
      .string()
      .min(1, { message: 'Confirme a nova senha' }),
  })
  .refine((data) => data.nova_senha === data.confirmar_senha, {
    message: 'As senhas informadas não conferem',
    path: ['confirmar_senha'],
  });

export type RedefinirSenhaFormData = z.infer<typeof redefinirSenhaSchema>;
