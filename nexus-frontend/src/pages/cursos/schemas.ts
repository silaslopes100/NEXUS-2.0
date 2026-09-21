import { z } from 'zod'

export const cursoSchema = z.object({
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  descricao: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horária mínima é 1 hora'),
  grade_curricular: z.string().optional(),
  status: z.enum(['ativo', 'inativo']).default('ativo'),
})

export type CursoFormData = z.infer<typeof cursoSchema>

export const moduloSchema = z.object({
  curso_id: z.string().min(1, 'Selecione um curso'),
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  ordem: z.number().min(1, 'Ordem mínima é 1'),
  conteudo: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horária mínima é 1 hora'),
})

export type ModuloFormData = z.infer<typeof moduloSchema>

export const materiaSchema = z.object({
  curso_id: z.string().optional(),
  modulo_id: z.string().optional(),
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  descricao: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horária mínima é 1 hora'),
  total_aulas_previstas: z.number().min(1, 'Total de aulas mínimo é 1'),
  ordem: z.number().optional(),
  tipo: z.enum(['teoria', 'pratica', 'estagio']).default('teoria'),
})

export type MateriaFormData = z.infer<typeof materiaSchema>