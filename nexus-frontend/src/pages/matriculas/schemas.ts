import { z } from 'zod'

export const matriculaSchema = z.object({
  aluno_id: z.string().min(1, 'Selecione um aluno'),
  polo_id: z.string().optional(),
  escola_id: z.string().optional(),
  curso_id: z.string().min(1, 'Selecione um curso'),
  semestre: z.number().min(1).max(3, 'Semestre deve ser entre 1 e 3'),
  ano: z.number().min(2000).max(2100, 'Ano inválido'),
  status: z.enum(['ativa', 'trancada', 'cancelada', 'concluida']).default('ativa'),
})

export type MatriculaFormData = z.infer<typeof matriculaSchema>