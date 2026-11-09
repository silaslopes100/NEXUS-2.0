import { z } from 'zod';

export const perfilAlunoSchema = z.object({
  email: z.string().trim().min(1, 'Informe o e-mail').email('Informe um e-mail válido'),
  telefone: z.string().max(64, 'O telefone deve ter no máximo 64 caracteres'),
  celular: z.string().max(64, 'O celular deve ter no máximo 64 caracteres'),
  cep: z.string().max(16, 'O CEP deve ter no máximo 16 caracteres'),
  logradouro: z.string().max(255, 'O logradouro deve ter no máximo 255 caracteres'),
  numero: z.string().max(32, 'O número deve ter no máximo 32 caracteres'),
  complemento: z.string().max(255, 'O complemento deve ter no máximo 255 caracteres'),
  bairro: z.string().max(255, 'O bairro deve ter no máximo 255 caracteres'),
  cidade: z.string().max(255, 'A cidade deve ter no máximo 255 caracteres'),
  uf: z.string().max(2, 'Informe a UF com até 2 caracteres'),
});

export type PerfilAlunoForm = z.infer<typeof perfilAlunoSchema>;
