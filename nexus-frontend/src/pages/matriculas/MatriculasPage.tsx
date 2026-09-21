'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Eye, Download, FileText, Calendar, GraduationCap, Building2, Package, ChevronRight, Filter } from 'lucide-react'
import { api } from '@/lib/api'
import { Matricula, PaginatedResponse, Aluno, Curso, Polo, Escola } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Form, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage, useForm } from '@/components/ui/form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Table, TableHeader, TableBody, TableRow, TableCell, TableHead } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatCPF, formatDate, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'

const matriculaSchema = z.object({
  aluno_id: z.string().min(1, 'Selecione um aluno'),
  polo_id: z.string().optional(),
  escola_id: z.string().optional(),
  curso_id: z.string().min(1, 'Selecione um curso'),
  semestre: z.number().min(1).max(3, 'Semestre deve ser entre 1 e 3'),
  ano: z.number().min(2000).max(2100, 'Ano invalido'),
  status: z.enum(['ativa', 'trancada', 'cancelada', 'concluida']).default('ativa'),
})

type MatriculaFormData = z.infer<typeof matriculaSchema>

export function MatriculasPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [poloFilter, setPoloFilter] = useState('')
  const [escolaFilter, setEscolaFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingMatricula, setEditingMatricula] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: matriculasData, isLoading } = useQuery({
    queryKey: ['matriculas', search, statusFilter, poloFilter, escolaFilter, page, pageSize],
    queryFn: () => {
      const params: Record<string, any> = { limit: pageSize, offset: (page - 1) * pageSize }
      if (search) params.q = search
      if (statusFilter) params.status = statusFilter
      if (poloFilter) params.polo_id = poloFilter
      if (escolaFilter) params.escola_id = escolaFilter
      return api.get<PaginatedResponse<any>>('/matriculas', { params }).then(r => r.data)
    },
  })

  const { data: alunosData } = useQuery({ queryKey: ['alunos-select'], queryFn: () => api.get('/alunos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: cursosData } = useQuery({ queryKey: ['cursos-select'], queryFn: () => api.get('/cursos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: polosData } = useQuery({ queryKey: ['polos-select'], queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: escolasData } = useQuery({ queryKey: ['escolas-select'], queryFn: () => api.get('/escolas', { params: { limit: 1000 } }).then(r => r.data.items) })

  const createMutation = useMutation({
    mutationFn: (data: MatriculaFormData) => api.post<Matricula>('/operacional/matriculas', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matriculas'] })
      toast.success('Matricula criada!')
      setIsDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MatriculaFormData> }) => api.put<Matricula>(`/operacional/matriculas/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matriculas'] })
      toast.success('Matricula atualizada!')
      setIsDialogOpen(false)
      setEditingMatricula(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/matriculas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matriculas'] })
      toast.success('Matricula desativada!')
    },
    onError: (e) => toast.error(e.message),
  })

  const form = useForm<MatriculaFormData>({ resolver: zodResolver(matriculaSchema), defaultValues: { status: 'ativa', semestre: 1, ano: new Date().getFullYear() } })

  const handleSubmit = (data: MatriculaFormData) => {
    setIsSubmitting(true)
    if (editingMatricula) updateMutation.mutate({ id: editingMatricula.id, data })
    else createMutation.mutate(data)
  }

  const openCreateDialog = () => {
    setEditingMatricula(null)
    form.reset({ status: 'ativa', semestre: 1, ano: new Date().getFullYear() })
    setIsDialogOpen(true)
  }

  const openEditDialog = (matricula: any) => {
    setEditingMatricula(matricula)
    form.reset({
      aluno_id: matricula.aluno_id,
      polo_id: matricula.polo_id,
      escola_id: matricula.escola_id,
      curso_id: matricula.curso_id,
      semestre: matricula.semestre,
      ano: matricula.ano,
      status: matricula.status,
    })
    setIsDialogOpen(true)
  }

  const handleDelete = (id: string) => {
    if (confirm('Desativar matricula?')) deleteMutation.mutate(id)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Matriculas</h1><p className="text-muted-foreground">Gerenciamento de matriculas ativas e historicas</p></div>
        <Button onClick={openCreateDialog}><Plus className="mr-2 h-4 w-4" />Nova Matricula</Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Lista de Matriculas</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent><SelectItem value="">Todos</SelectItem><SelectItem value="ativa">Ativa</SelectItem><SelectItem value="trancada">Trancada</SelectItem><SelectItem value="cancelada">Cancelada</SelectItem><SelectItem value="concluida">Concluida</SelectItem></SelectContent>
              </Select>
              <Select value={poloFilter} onValueChange={setPoloFilter}>
                <SelectTrigger className="w-[200px]"><SelectValue placeholder="Filtrar por Polo" /></SelectTrigger>
                <SelectContent><SelectItem value="">Todos os Polos</SelectItem>{polosData?.items.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={escolaFilter} onValueChange={setEscolaFilter}>
                <SelectTrigger className="w-[200px]"><SelectValue placeholder="Filtrar por Escola" /></SelectTrigger>
                <SelectContent><SelectItem value="">Todas as Escolas</SelectItem>{escolasData?.items.map(e => <SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Aluno</TableHead>
                    <TableHead>Polo</TableHead>
                    <TableHead>Escola</TableHead>
                    <TableHead>Curso</TableHead>
                    <TableHead>Semestre/Ano</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {matriculasData?.items.length === 0 ? (
                    <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">Nenhuma matricula</TableCell></TableRow>
                  ) : (
                    matriculasData?.items.map(m => (
                      <TableRow key={m.id}>
                        <TableCell className="font-medium">{m.aluno_nome}</TableCell>
                        <TableCell>{m.polo_nome || '---'}</TableCell>
                        <TableCell>{m.escola_nome || '---'}</TableCell>
                        <TableCell>{m.curso_nome}</TableCell>
                        <TableCell>{m.semestre} / {m.ano}</TableCell>
                        <TableCell><Badge variant={getStatusColor(m.status)}>{m.status}</Badge></TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(m)} aria-label="Editar"><Edit className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDelete(m.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
          {matriculasData && matriculasData.total > pageSize && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">Mostrando {((page - 1) * pageSize) + 1} a {Math.min(page * pageSize, matriculasData.total)} de {matriculasData.total}</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (matriculasData?.total || 0)}>Proximo</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingMatricula ? 'Editar Matricula' : 'Nova Matricula'}</DialogTitle></DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <FormField control={form.control} name="aluno_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Aluno *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                    <SelectContent>
                      {alunosData?.items.map(a => <SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome} - {a.cpf ? formatCPF(a.cpf) : ''}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={form.control} name="polo_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Polo</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent>{polosData?.items.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}</SelectContent>
                    </Select>
                  </FormItem>
                )} />
                <FormField control={form.control} name="escola_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Escola</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent>{escolasData?.items.map(e => <SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>)}</SelectContent>
                    </Select>
                  </FormItem>
                )} />
              </div>
              <FormField control={form.control} name="curso_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Curso *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                    <SelectContent>{cursosData?.items.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <div className="grid gap-4 md:grid-cols-3">
                <FormField control={form.control} name="semestre" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Semestre *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" max="3" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="ano" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ano *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="2000" max="2100" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="status" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent><SelectItem value="ativa">Ativa</SelectItem><SelectItem value="trancada">Trancada</SelectItem><SelectItem value="cancelada">Cancelada</SelectItem><SelectItem value="concluida">Concluida</SelectItem></SelectContent>
                    </Select>
                  </FormItem>
                )} />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { MatriculaFormData } from './schemas'