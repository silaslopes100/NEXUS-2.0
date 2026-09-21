'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Eye, Download, FileText, Calendar, GraduationCap, Building2, Package, ChevronRight, MapPin, User } from 'lucide-react'
import { api } from '@/lib/api'
import { Aluno, AlunoDetalheResponse, PaginatedResponse } from '@/types'
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
import { formatCurrency, formatCPF, formatDate, calculatePresencePercentage, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const alunoSchema = z.object({
  nome: z.string().min(1, 'Nome e obrigatorio'),
  sobrenome: z.string().min(1, 'Sobrenome e obrigatorio'),
  cpf: z.string().optional(),
  email: z.string().email('E-mail invalido').optional().or(z.literal('')),
  data_nascimento: z.string().optional(),
  eh_aluno_polo: z.boolean().default(false),
  polo_id: z.string().optional(),
  pertence_escola: z.string().optional(),
  eh_aluno_ead: z.boolean().default(false),
  curso_id: z.string().optional(),
  semestre: z.number().min(1).max(3).optional(),
  ano: z.number().min(2000).max(2100).optional(),
  senha: z.string().min(6, 'Senha deve ter pelo menos 6 caracteres'),
})

type AlunoFormData = z.infer<typeof alunoSchema>

const alunoUpdateSchema = z.object({
  nome: z.string().optional(),
  sobrenome: z.string().optional(),
  cpf: z.string().optional(),
  email: z.string().email('E-mail invalido').optional().or(z.literal('')),
  data_nascimento: z.string().optional(),
  polo_id: z.string().optional(),
  escola_id: z.string().optional(),
  modalidade: z.enum(['polo', 'escola', 'ead']).optional(),
  status: z.enum(['ativo', 'inativo', 'bloqueado', 'desistente']).optional(),
})

type AlunoUpdateFormData = z.infer<typeof alunoUpdateSchema>

export function AlunosPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [poloFilter, setPoloFilter] = useState('')
  const [escolaFilter, setEscolaFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [editingAluno, setEditingAluno] = useState<any | null>(null)
  const [detailAluno, setDetailAluno] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: alunosData, isLoading } = useQuery({
    queryKey: ['alunos', search, statusFilter, poloFilter, escolaFilter, page, pageSize],
    queryFn: () => {
      const params: Record<string, any> = { limit: pageSize, offset: (page - 1) * pageSize }
      if (search) params.q = search
      if (statusFilter) params.status = statusFilter
      if (poloFilter) params.polo_id = poloFilter
      if (escolaFilter) params.escola_id = escolaFilter
      return api.get<PaginatedResponse<any>>('/alunos', { params }).then(r => r.data)
    },
  })

  const { data: polosData } = useQuery({
    queryKey: ['polos-select'],
    queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items),
  })

  const { data: escolasData } = useQuery({
    queryKey: ['escolas-select'],
    queryFn: () => api.get('/escolas', { params: { limit: 1000 } }).then(r => r.data.items),
  })

  const { data: cursosData } = useQuery({
    queryKey: ['cursos-select'],
    queryFn: () => api.get('/cursos', { params: { limit: 1000 } }).then(r => r.data.items),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post<Aluno>('/operacional/alunos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alunos'] })
      toast.success('Aluno criado!')
      setIsDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlunoUpdateFormData }) => api.put<Aluno>(`/operacional/alunos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alunos'] })
      toast.success('Aluno atualizado!')
      setIsDialogOpen(false)
      setEditingAluno(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/alunos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alunos'] })
      toast.success('Aluno desativado!')
    },
    onError: (e) => toast.error(e.message),
  })

  const form = useForm<AlunoFormData>({
    resolver: zodResolver(alunoSchema),
    defaultValues: {
      eh_aluno_polo: false,
      eh_aluno_ead: false,
      semestre: 1,
      ano: new Date().getFullYear(),
    },
  })

  const updateForm = useForm<AlunoUpdateFormData>({ resolver: zodResolver(alunoUpdateSchema) })

  const handleSubmit = (data: AlunoFormData) => {
    setIsSubmitting(true)
    if (editingAluno) {
      updateMutation.mutate({ id: editingAluno.id, data: data as AlunoUpdateFormData })
    } else {
      createMutation.mutate(data)
    }
  }

  const openCreateDialog = () => {
    setEditingAluno(null)
    form.reset({ eh_aluno_polo: false, eh_aluno_ead: false, semestre: 1, ano: new Date().getFullYear() })
    setIsDialogOpen(true)
  }

  const openEditDialog = (aluno: any) => {
    setEditingAluno(aluno)
    updateForm.reset({
      nome: aluno.nome,
      sobrenome: aluno.sobrenome,
      cpf: aluno.cpf,
      email: aluno.email,
      data_nascimento: aluno.data_nascimento?.split('T')[0],
      polo_id: aluno.polo_id,
      escola_id: aluno.escola_id,
      modalidade: aluno.modalidade,
      status: aluno.status,
    })
    setIsDialogOpen(true)
  }

  const openDetailDialog = async (aluno: any) => {
    try {
      const detail = await api.get<any>(`/alunos/${aluno.id}`).then(r => r.data)
      setDetailAluno(detail)
      setIsDetailDialogOpen(true)
    } catch (e) {
      toast.error('Erro ao carregar detalhes')
    }
  }

  const handleDelete = (id: string) => {
    if (confirm('Desativar aluno?')) deleteMutation.mutate(id)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Alunos</h1>
          <p className="text-muted-foreground">Gestao de alunos, matriculas, historico e presencas</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Novo Aluno
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Lista de Alunos</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Buscar por nome, CPF, e-mail..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="inativo">Inativo</SelectItem>
                  <SelectItem value="bloqueado">Bloqueado</SelectItem>
                  <SelectItem value="desistente">Desistente</SelectItem>
                </SelectContent>
              </Select>
              <Select value={poloFilter} onValueChange={setPoloFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Filtrar por Polo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos os Polos</SelectItem>
                  {polosData?.items.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={escolaFilter} onValueChange={setEscolaFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Filtrar por Escola" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todas as Escolas</SelectItem>
                  {escolasData?.items.map(e => <SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>CPF</TableHead>
                    <TableHead>E-mail</TableHead>
                    <TableHead>Polo/Escola</TableHead>
                    <TableHead>Modalidade</TableHead>
                    <TableHead>Curso</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alunosData?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">Nenhum aluno encontrado</TableCell>
                    </TableRow>
                  ) : (
                    alunosData?.items.map(aluno => (
                      <TableRow key={aluno.id}>
                        <TableCell className="font-medium">{aluno.nome} {aluno.sobrenome}</TableCell>
                        <TableCell>{aluno.cpf ? formatCPF(aluno.cpf) : '---'}</TableCell>
                        <TableCell>{aluno.email || '---'}</TableCell>
                        <TableCell>
                          {aluno.polo_nome && <span className="text-blue-600"><Building2 className="inline h-3 w-3 mr-1" />{aluno.polo_nome}</span>}
                          {aluno.escola_nome && <span className="text-green-600 ml-2"><GraduationCap className="inline h-3 w-3 mr-1" />{aluno.escola_nome}</span>}
                          {aluno.modalidade === 'ead' && <span className="text-purple-600"><Package className="inline h-3 w-3 mr-1" />EAD</span>}
                        </TableCell>
                        <TableCell>{aluno.modalidade === 'ead' ? 'EAD' : aluno.modalidade === 'polo' ? 'Polo' : 'Escola'}</TableCell>
                        <TableCell>{aluno.curso_nome || '---'}</TableCell>
                        <TableCell><Badge className={getStatusColor(aluno.status)}>{aluno.status}</Badge></TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openDetailDialog(aluno)} aria-label="Ver detalhes"><Eye className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(aluno)} aria-label="Editar"><Edit className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDelete(aluno.id)} aria-label="Desativar" className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}

          {alunosData && alunosData.total > pageSize && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">Mostrando {((page - 1) * pageSize) + 1} a {Math.min(page * pageSize, alunosData.total)} de {alunosData.total} alunos</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (alunosData?.total || 0)}>Proximo</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingAluno ? 'Editar Aluno' : 'Novo Aluno'}</DialogTitle>
          </DialogHeader>
          <Form {...(editingAluno ? updateForm : form)}>
            <form onSubmit={(editingAluno ? updateForm : form).handleSubmit(handleSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={editingAluno ? updateForm.control : form.control} name="nome" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome *</FormLabel>
                    <FormControl>
                      <input {...field} className="w-full" placeholder="Nome" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editingAluno ? updateForm.control : form.control} name="sobrenome" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sobrenome *</FormLabel>
                    <FormControl>
                      <input {...field} className="w-full" placeholder="Sobrenome" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editingAluno ? updateForm.control : form.control} name="cpf" render={({ field }) => (
                  <FormItem>
                    <FormLabel>CPF</FormLabel>
                    <FormControl>
                      <input {...field} placeholder="000.000.000-00" className="w-full" maxLength={14} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editingAluno ? updateForm.control : form.control} name="email" render={({ field }) => (
                  <FormItem>
                    <FormLabel>E-mail</FormLabel>
                    <FormControl>
                      <input type="email" {...field} className="w-full" placeholder="aluno@email.com" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editingAluno ? updateForm.control : form.control} name="data_nascimento" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data de Nascimento</FormLabel>
                    <FormControl>
                      <input type="date" {...field} className="w-full" />
                    </FormControl>
                  </FormItem>
                )} />
              </div>

              {!editingAluno && (
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Tipo de Matricula</h4>
                  <div className="grid gap-4 md:grid-cols-3">
                    <FormField control={form.control} name="eh_aluno_polo" render={({ field }) => (
                      <FormItem className="flex items-center gap-2">
                        <FormControl>
                          <input type="checkbox" {...field} className="h-4 w-4" />
                        </FormControl>
                        <FormLabel>Aluno de Polo</FormLabel>
                      </FormItem>
                    )} />
                    <FormField control={form.control} name="eh_aluno_ead" render={({ field }) => (
                      <FormItem className="flex items-center gap-2">
                        <FormControl>
                          <input type="checkbox" {...field} className="h-4 w-4" />
                        </FormControl>
                        <FormLabel>Aluno EAD</FormLabel>
                      </FormItem>
                    )} />
                    <FormField control={form.control} name="pertence_escola" render={({ field }) => (
                      <FormItem className="flex items-center gap-2">
                        <FormControl>
                          <input type="checkbox" {...field} className="h-4 w-4" />
                        </FormControl>
                        <FormLabel>Pertence a Escola</FormLabel>
                      </FormItem>
                    )} />
                  </div>
                </div>
              )}

              {editingAluno ? (
                <FormField control={updateForm.control} name="modalidade" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Modalidade</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="polo">Polo</SelectItem>
                        <SelectItem value="escola">Escola</SelectItem>
                        <SelectItem value="ead">EAD</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
              ) : (
                <div className="grid gap-4 md:grid-cols-3">
                  <FormField control={form.control} name="polo_id" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Polo</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Selecione</SelectItem>
                          {polosData?.items.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="escola_id" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Escola</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Selecione</SelectItem>
                          {escolasData?.items.map(e => <SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="curso_id" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Curso</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Selecione</SelectItem>
                          {cursosData?.items.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )} />
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-3">
                <FormField control={editingAluno ? updateForm.control : form.control} name="semestre" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Semestre</FormLabel>
                    <FormControl>
                      <input type="number" {...field} className="w-full" min="1" max="3" />
                    </FormControl>
                  </FormItem>
                )} />
                <FormField control={editingAluno ? updateForm.control : form.control} name="ano" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ano</FormLabel>
                    <FormControl>
                      <input type="number" {...field} className="w-full" min="2000" max="2100" />
                    </FormControl>
                  </FormItem>
                )} />
                {editingAluno && <FormField control={updateForm.control} name="status" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ativo">Ativo</SelectItem>
                        <SelectItem value="inativo">Inativo</SelectItem>
                        <SelectItem value="bloqueado">Bloqueado</SelectItem>
                        <SelectItem value="desistente">Desistente</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />}
              </div>

              {!editingAluno && (
                <FormField control={form.control} name="senha" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Senha *</FormLabel>
                    <FormControl>
                      <input type="password" {...field} className="w-full" placeholder="Minimo 6 caracteres" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              )}

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{detailAluno?.nome} {detailAluno?.sobrenome} - Detalhes</DialogTitle>
          </DialogHeader>
          <DialogContent>
            {detailAluno && (
              <Tabs defaultValue="perfil">
                <TabsList>
                  <TabsTrigger value="perfil">Perfil</TabsTrigger>
                  <TabsTrigger value="historico">Historico</TabsTrigger>
                  <TabsTrigger value="presencas">Presencas</TabsTrigger>
                  <TabsTrigger value="notas">Notas</TabsTrigger>
                  <TabsTrigger value="certificados">Certificados</TabsTrigger>
                </TabsList>

                <TabsContent value="perfil" className="space-y-4 pt-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div><label className="text-sm text-muted-foreground">Nome</label><p className="font-medium">{detailAluno.nome} {detailAluno.sobrenome}</p></div>
                    <div><label className="text-sm text-muted-foreground">CPF</label><p>{detailAluno.cpf ? formatCPF(detailAluno.cpf) : '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">E-mail</label><p>{detailAluno.email || '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Data Nascimento</label><p>{detailAluno.data_nascimento ? formatDate(detailAluno.data_nascimento) : '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Modalidade</label><p><Badge variant={detailAluno.modalidade === 'ead' ? 'default' : detailAluno.modalidade === 'polo' ? 'secondary' : 'outline'}>{detailAluno.modalidade}</Badge></p></div>
                    <div><label className="text-sm text-muted-foreground">Polo</label><p>{detailAluno.polo_nome || '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Escola</label><p>{detailAluno.escola_nome || '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Curso</label><p>{detailAluno.curso_nome || '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Semestre/Ano</label><p>{detailAluno.semestre ? detailAluno.semestre + ' semestre / ' + detailAluno.ano : '---'}</p></div>
                    <div><label className="text-sm text-muted-foreground">Status</label><p><Badge className={getStatusColor(detailAluno.status)}>{detailAluno.status}</Badge></p></div>
                    <div><label className="text-sm text-muted-foreground">Matricula</label><p>{detailAluno.numero_matricula || '---'}</p></div>
                  </div>
                  <div className="border-t pt-4">
                    <h4 className="font-medium mb-2">Presencas por Materia</h4>
                    {detailAluno.presencas_por_materia?.length ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Materia</TableHead>
                            <TableHead>Aulas Previstas</TableHead>
                            <TableHead>Presencas</TableHead>
                            <TableHead>%</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {detailAluno.presencas_por_materia.map(p => (
                            <TableRow key={p.materia_id}>
                              <TableCell>{p.materia_nome}</TableCell>
                              <TableCell>{p.total_aulas_previstas}</TableCell>
                              <TableCell>{p.presencas}</TableCell>
                              <TableCell>
                                <Badge variant={p.percentual >= 75 ? 'success' : p.percentual >= 50 ? 'warning' : 'destructive'}>
                                  {p.percentual}%
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : <p className="text-muted-foreground">Nenhuma presenca registrada</p>}
                  </div>
                </TabsContent>

                <TabsContent value="historico" className="pt-4">
                  {detailAluno.notas?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Materia</TableHead>
                          <TableHead>Nota</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Semestre</TableHead>
                          <TableHead>Ano</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailAluno.notas.map(n => (
                          <TableRow key={n.id}>
                            <TableCell>{n.materia_nome || '-'}</TableCell>
                            <TableCell>{n.nota}</TableCell>
                            <TableCell>{n.tipo}</TableCell>
                            <TableCell>{n.semestre}</TableCell>
                            <TableCell>{n.ano}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : <p className="text-muted-foreground">Nenhuma nota registrada</p>}
                </TabsContent>

                <TabsContent value="presencas" className="pt-4">
                  <p className="text-muted-foreground">Detalhes de presencas por aula disponiveis no modulo de Presencas</p>
                </TabsContent>

                <TabsContent value="notas" className="pt-4">
                  {detailAluno.notas?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Materia</TableHead>
                          <TableHead>Nota</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Semestre</TableHead>
                          <TableHead>Ano</TableHead>
                          <TableHead>Data</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailAluno.notas.map(n => (
                          <TableRow key={n.id}>
                            <TableCell>{n.materia_nome || '-'}</TableCell>
                            <TableCell>{n.nota}</TableCell>
                            <TableCell>{n.tipo}</TableCell>
                            <TableCell>{n.semestre}</TableCell>
                            <TableCell>{n.ano}</TableCell>
                            <TableCell>{n.criado_em ? formatDate(n.criado_em) : '---'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : <p className="text-muted-foreground">Nenhuma nota registrada</p>}
                </TabsContent>

                <TabsContent value="certificados" className="pt-4">
                  {detailAluno.certificados?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Titulo</TableHead>
                          <TableHead>Estagios</TableHead>
                          <TableHead>Historico Completo</TableHead>
                          <TableHead>Data Emissao</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailAluno.certificados.map(c => (
                          <TableRow key={c.id}>
                            <TableCell>{c.titulo}</TableCell>
                            <TableCell>{c.estagios_entregues.map(e => e.nome).join(', ')}</TableCell>
                            <TableCell>{c.historico_completo ? 'Sim' : 'Nao'}</TableCell>
                            <TableCell>{c.data_emissao ? formatDate(c.data_emissao) : '---'}</TableCell>
                            <TableCell>
                              <Badge variant={c.status === 'emitido' ? 'success' : c.status === 'pendente' ? 'warning' : 'destructive'}>
                                {c.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : <p className="text-muted-foreground">Nenhum certificado emitido</p>}
                </TabsContent>
              </Tabs>
            )}
          </DialogContent>
        </DialogContent>
      </Dialog>
    </div>
  )
}