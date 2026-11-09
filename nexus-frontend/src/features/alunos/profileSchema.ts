import { z } from 'zod';

export const onlyDigits = (value: string): string => value.replace(/\D/g, '');

export const formatPhone = (value: string): string => {
  const digits = onlyDigits(value).slice(0, 11);
  if (digits.length <= 2) {
    if (!digits.length) return '';
    return digits.length === 2 ? `(${digits}) ` : `(${digits}`;
  }
  if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
};

export const formatCep = (value: string): string => {
  const digits = onlyDigits(value).slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
};

const optionalDigitsWithLength = (length: number, label: string) =>
  z.string().refine(
    (value) => {
      const digits = onlyDigits(value);
      return digits.length === 0 || digits.length === length;
    },
    `${label} deve conter ${length} dígitos`
  );

export const perfilAlunoSchema = z.object({
  email: z.string().trim().min(1, 'Informe o e-mail').email('Informe um e-mail válido'),
  telefone: optionalDigitsWithLength(11, 'O telefone'),
  celular: optionalDigitsWithLength(11, 'O celular'),
  cep: optionalDigitsWithLength(8, 'O CEP'),
  logradouro: z.string().max(255, 'O logradouro deve ter no máximo 255 caracteres'),
  numero: z.string().max(32, 'O número deve ter no máximo 32 caracteres'),
  complemento: z.string().max(255, 'O complemento deve ter no máximo 255 caracteres'),
  bairro: z.string().max(255, 'O bairro deve ter no máximo 255 caracteres'),
  cidade: z.string().max(255, 'A cidade deve ter no máximo 255 caracteres'),
  uf: z.string().max(2, 'Informe a UF com até 2 caracteres'),
});

export type PerfilAlunoForm = z.infer<typeof perfilAlunoSchema>;
