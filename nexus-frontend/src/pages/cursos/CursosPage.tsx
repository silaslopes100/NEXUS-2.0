'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, ChevronRight, BookOpen, ChevronLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { Curso, Modulo, Materia, PaginatedResponse } from '@/types'
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
import { formatCurrency } from '@/lib/utils'
import toast from 'react-hot-toast'

const cursoSchema = z.object({
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  descricao: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horaria minima e 1 hora'),
  grade_curricular: z.string().optional(),
  status: z.enum(['ativo', 'inativo']).default('ativo'),
})

type CursoFormData = z.infer<typeof cursoSchema>

const moduloSchema = z.object({
  curso_id: z.string().min(1, 'Selecione um curso'),
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  ordem: z.number().min(1, 'Ordem minima e 1'),
  conteudo: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horaria minima e 1 hora'),
})

type ModuloFormData = z.infer<typeof moduloSchema>

const materiaSchema = z.object({
  curso_id: z.string().optional(),
  modulo_id: z.string().optional(),
  nome: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  descricao: z.string().optional(),
  carga_horaria: z.number().min(1, 'Carga horaria minima e 1 hora'),
  total_aulas_previstas: z.number().min(1, 'Total de aulas minimo e 1'),
  ordem: z.number().optional(),
  tipo: z.enum(['teoria', 'pratica', 'estagio']).default('teoria'),
})

type MateriaFormData = z.infer<typeof materiaSchema>

export function CursosPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isCursoDialogOpen, setIsCursoDialogOpen] = useState(false)
  const [isModuloDialogOpen, setIsModuloDialogOpen] = useState(false)
  const [isMateriaDialogOpen, setIsMateriaDialogOpen] = useState(false)
  const [editingCurso, setEditingCurso] = useState<Curso | null>(null)
  const [editingModulo, setEditingModulo] = useState<Modulo | null>(null)
  const [editingMateria, setEditingMateria] = useState<Materia | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState<'cursos' | 'modulos' | 'materias'>('cursos')
  const [selectedCurso, setSelectedCurso] = useState<Curso | null>(null)
  const [selectedModulo, setSelectedModulo] = useState<Modulo | null>(null)

  const { data: cursosData, isLoading: cursosLoading } = useQuery({
    queryKey: ['cursos', search, statusFilter, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<Curso>>('/cursos', {
      params: { q: search, status: statusFilter, limit: pageSize, offset: (page - 1) * pageSize }
    }).then(r => r.data),
  })

  const { data: modulosData, isLoading: modulosLoading } = useQuery({
    queryKey: ['modulos', selectedCurso?.id, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<Modulo>>('/modulos', {
      params: { curso_id: selectedCurso?.id, limit: pageSize, offset: (page - 1) * pageSize }
    }).then(r => r.data),
    enabled: !!selectedCurso,
  })

  const { data: materiasData, isLoading: materiasLoading } = useQuery({
    queryKey: ['materias', selectedCurso?.id, selectedModulo?.id, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<Materia>>('/materias', {
      params: { curso_id: selectedCurso?.id, modulo_id: selectedModulo?.id, limit: pageSize, offset: (page - 1) * pageSize }
    }).then(r => r.data),
    enabled: !!selectedCurso,
  })

  const { data: cursosSelect } = useQuery({
    queryKey: ['cursos-select'],
    queryFn: () => api.get('/cursos', { params: { limit: 1000 } }).then(r => r.data.items),
  })

  const { data: modulosSelect } = useQuery({
    queryKey: ['modulos-select', selectedCurso?.id],
    queryFn: () => api.get('/modulos', { params: { curso_id: selectedCurso?.id, limit: 1000 } }).then(r => r.data.items),
    enabled: !!selectedCurso,
  })

  const createCursoMutation = useMutation({
    mutationFn: (data: CursoFormData) => api.post<Curso>('/operacional/cursos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cursos'] })
      toast.success('Curso criado!')
      setIsCursoDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const updateCursoMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CursoFormData> }) => api.put<Curso>(`/operacional/cursos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cursos'] })
      toast.success('Curso atualizado!')
      setIsCursoDialogOpen(false)
      setEditingCurso(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const deleteCursoMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/cursos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cursos'] })
      toast.success('Curso desativado!')
    },
    onError: (e) => toast.error(e.message),
  })

  const createModuloMutation = useMutation({
    mutationFn: (data: ModuloFormData) => api.post<Modulo>('/operacional/modulos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modulos'] })
      toast.success('Modulo criado!')
      setIsModuloDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const updateModuloMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ModuloFormData> }) => api.put<Modulo>(`/operacional/modulos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modulos'] })
      toast.success('Modulo atualizado!')
      setIsModuloDialogOpen(false)
      setEditingModulo(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const deleteModuloMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/modulos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modulos'] })
      toast.success('Modulo desativado!')
    },
    onError: (e) => toast.error(e.message),
  })

  const createMateriaMutation = useMutation({
    mutationFn: (data: MateriaFormData) => api.post<Materia>('/operacional/materias', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materias'] })
      toast.success('Materia criada!')
      setIsMateriaDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const updateMateriaMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MateriaFormData> }) => api.put<Materia>(`/operacional/materias/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materias'] })
      toast.success('Materia atualizada!')
      setIsMateriaDialogOpen(false)
      setEditingMateria(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const deleteMateriaMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/materias/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materias'] })
      toast.success('Materia desativada!')
    },
    onError: (e) => toast.error(e.message),
  })

  const cursoForm = useForm<CursoFormData>({ resolver: zodResolver(cursoSchema), defaultValues: { status: 'ativo' } })
  const moduloForm = useForm<ModuloFormData>({ resolver: zodResolver(moduloSchema), defaultValues: { ordem: 1, carga_horaria: 10 } })
  const materiaForm = useForm<MateriaFormData>({ resolver: zodResolver(materiaSchema), defaultValues: { tipo: 'teoria', carga_horaria: 20, total_aulas_previstas: 10 } })

  const handleCursoSubmit = (data: CursoFormData) => {
    setIsSubmitting(true)
    if (editingCurso) updateCursoMutation.mutate({ id: editingCurso.id, data })
    else createCursoMutation.mutate(data)
  }

  const handleModuloSubmit = (data: ModuloFormData) => {
    setIsSubmitting(true)
    if (editingModulo) updateModuloMutation.mutate({ id: editingModulo.id, data })
    else createModuloMutation.mutate(data)
  }

  const handleMateriaSubmit = (data: MateriaFormData) => {
    setIsSubmitting(true)
    if (editingMateria) updateMateriaMutation.mutate({ id: editingMateria.id, data })
    else createMateriaMutation.mutate(data)
  }

  const openCursoCreate = () => { setEditingCurso(null); cursoForm.reset({ status: 'ativo' }); setIsCursoDialogOpen(true); }
  const openCursoEdit = (curso: Curso) => { setEditingCurso(curso); cursoForm.reset({ nome: curso.nome, descricao: curso.descricao || '', carga_horaria: curso.carga_horaria, grade_curricular: curso.grade_curricular || '', status: curso.status }); setIsCursoDialogOpen(true); }
  const openModuloCreate = () => { setEditingModulo(null); moduloForm.reset({ curso_id: selectedCurso?.id || '', ordem: 1, carga_horaria: 10 }); setIsModuloDialogOpen(true); }
  const openModuloEdit = (modulo: Modulo) => { setEditingModulo(modulo); moduloForm.reset({ curso_id: modulo.curso_id, nome: modulo.nome, ordem: modulo.ordem, conteudo: modulo.conteudo || '', carga_horaria: modulo.carga_horaria }); setIsModuloDialogOpen(true); }
  const openMateriaCreate = () => { setEditingMateria(null); materiaForm.reset({ curso_id: selectedCurso?.id, modulo_id: selectedModulo?.id, tipo: 'teoria', carga_horaria: 20, total_aulas_previstas: 10 }); setIsMateriaDialogOpen(true); }
  const openMateriaEdit = (materia: Materia) => { setEditingMateria(materia); materiaForm.reset({ curso_id: materia.curso_id, modulo_id: materia.modulo_id, nome: materia.nome, descricao: materia.descricao || '', carga_horaria: materia.carga_horaria, total_aulas_previstas: materia.total_aulas_previstas, ordem: materia.ordem, tipo: materia.tipo || 'teoria' }); setIsMateriaDialogOpen(true); }

  const handleDeleteCurso = (id: string) => { if (confirm('Desativar curso?')) deleteCursoMutation.mutate(id); }
  const handleDeleteModulo = (id: string) => { if (confirm('Desativar modulo?')) deleteModuloMutation.mutate(id); }
  const handleDeleteMateria = (id: string) => { if (confirm('Desativar materia?')) deleteMateriaMutation.mutate(id); }

  const isLoading = cursosLoading || modulosLoading || materiasLoading

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cursos, Modulos e Materias</h1>
          <p className="text-muted-foreground">Gerenciamento hierarquico da grade curricular</p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'cursos' && <Button onClick={openCursoCreate}><Plus className="mr-2 h-4 w-4" />Novo Curso</Button>}
          {activeTab === 'modulos' && selectedCurso && <Button onClick={openModuloCreate}><Plus className="mr-2 h-4 w-4" />Novo Modulo</Button>}
          {activeTab === 'materias' && selectedCurso && <Button onClick={openMateriaCreate}><Plus className="mr-2 h-4 w-4" />Nova Materia</Button>}
        </div>
      </div>

      <div className="flex gap-4 border-b mb-4">
        <button onClick={() => setActiveTab('cursos')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'cursos' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          Cursos
        </button>
        <button onClick={() => setActiveTab('modulos')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'modulos' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`} disabled={!selectedCurso}>
          Modulos {selectedCurso && `(${selectedCurso.nome})`}
        </button>
        <button onClick={() => setActiveTab('materias')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'materias' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`} disabled={!selectedCurso}>
          Materias {selectedCurso && `(${selectedCurso.nome})`}
        </button>
      </div>

      {activeTab === 'cursos' && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle>Cursos</CardTitle>
              <div className="flex flex-wrap gap-2">
                <Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[180px]"><SelectValue placeholder="Status" /></SelectTrigger>
                  <SelectContent><SelectItem value="">Todos</SelectItem><SelectItem value="ativo">Ativo</SelectItem><SelectItem value="inativo">Inativo</SelectItem></SelectContent>
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
                      <TableHead>Nome</TableHead>
                      <TableHead>Carga Horaria</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cursosData?.items.length === 0 ? (
                      <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">Nenhum curso</TableCell></TableRow>
                    ) : (
                      cursosData?.items.map(curso => (
                        <TableRow key={curso.id}>
                          <TableCell className="font-medium">{curso.nome}</TableCell>
                          <TableCell>{curso.carga_horaria}h</TableCell>
                          <TableCell><Badge variant={curso.status === 'ativo' ? 'default' : 'secondary'}>{curso.status}</Badge></TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="icon" onClick={() => { setSelectedCurso(curso); setActiveTab('modulos'); }}><ChevronRight className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="icon" onClick={() => openCursoEdit(curso)}><Edit className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="icon" onClick={() => handleDeleteCurso(curso.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
            {cursosData && cursosData.total > pageSize && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">Mostrando {((page - 1) * pageSize) + 1} a {Math.min(page * pageSize, cursosData.total)} de {cursosData.total}</p>
                <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button><Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (cursosData?.total || 0)}>Proximo</Button></div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'modulos' && selectedCurso && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle>Modulos do Curso: {selectedCurso.nome}</CardTitle>
              <Button onClick={() => { setSelectedCurso(null); setActiveTab('cursos'); }} variant="ghost" size="sm"><ChevronLeft className="mr-1 h-4 w-4" />Voltar</Button>
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
                      <TableHead>Ordem</TableHead>
                      <TableHead>Nome</TableHead>
                      <TableHead>Carga Horaria</TableHead>
                      <TableHead className="text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {modulosData?.items.length === 0 ? (
                      <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">Nenhum modulo</TableCell></TableRow>
                    ) : (
                      modulosData?.items.map(modulo => (
                        <TableRow key={modulo.id}>
                          <TableCell>{modulo.ordem}</TableCell>
                          <TableCell className="font-medium">{modulo.nome}</TableCell>
                          <TableCell>{modulo.carga_horaria}h</TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="icon" onClick={() => { setSelectedModulo(modulo); setActiveTab('materias'); }}><ChevronRight className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="icon" onClick={() => openModuloEdit(modulo)}><Edit className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="icon" onClick={() => handleDeleteModulo(modulo.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
            {modulosData && modulosData.total > pageSize && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">Paginacao...</p>
                <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button><Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (modulosData?.total || 0)}>Proximo</Button></div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'materias' && selectedCurso && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <CardTitle>Materias {selectedModulo ? `do Modulo: ${selectedModulo.nome}` : `do Curso: ${selectedCurso.nome}`}</CardTitle>
              <div className="flex gap-2">
                {selectedModulo && <Button onClick={() => { setSelectedModulo(null); setActiveTab('modulos'); }} variant="ghost" size="sm"><ChevronLeft className="mr-1 h-4 w-4" />Modulos</Button>}
                <Button onClick={() => { setSelectedCurso(null); setActiveTab('cursos'); }} variant="ghost" size="sm"><ChevronLeft className="mr-1 h-4 w-4" />Cursos</Button>
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
                      <TableHead>Ordem</TableHead>
                      <TableHead>Nome</TableHead>
                      <TableHead>Carga Horaria</TableHead>
                      <TableHead>Total Aulas</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {materiasData?.items.length === 0 ? (
                      <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">Nenhuma materia</TableCell></TableRow>
                    ) : (
                      materiasData?.items.map(materia => (
                        <TableRow key={materia.id}>
                          <TableCell>{materia.ordem || '---'}</TableCell>
                          <TableCell className="font-medium">{materia.nome}</TableCell>
                          <TableCell>{materia.carga_horaria}h</TableCell>
                          <TableCell>{materia.total_aulas_previstas}</TableCell>
                          <TableCell><Badge variant="outline">{materia.tipo}</Badge></TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="icon" onClick={() => openMateriaEdit(materia)}><Edit className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteMateria(materia.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
            {materiasData && materiasData.total > pageSize && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">Paginacao...</p>
                <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button><Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (materiasData?.total || 0)}>Proximo</Button></div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog open={isCursoDialogOpen} onOpenChange={setIsCursoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingCurso ? 'Editar Curso' : 'Novo Curso'}</DialogTitle></DialogHeader>
          <Form {...cursoForm}>
            <form onSubmit={cursoForm.handleSubmit(handleCursoSubmit)} className="space-y-4">
              <FormField control={cursoForm.control} name="nome" render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome *</FormLabel>
                  <FormControl><input {...field} className="w-full" placeholder="Nome do Curso" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={cursoForm.control} name="descricao" render={({ field }) => (
                <FormItem>
                  <FormLabel>Descricao</FormLabel>
                  <FormControl><textarea {...field} className="w-full" rows={3} placeholder="Descricao do curso" /></FormControl>
                </FormItem>
              )} />
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={cursoForm.control} name="carga_horaria" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Carga Horaria (h) *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={cursoForm.control} name="status" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent><SelectItem value="ativo">Ativo</SelectItem><SelectItem value="inativo">Inativo</SelectItem></SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
              <FormField control={cursoForm.control} name="grade_curricular" render={({ field }) => (
                <FormItem>
                  <FormLabel>Grade Curricular (JSON)</FormLabel>
                  <FormControl><textarea {...field} className="w-full" rows={4} placeholder='[{"modulo":"Modulo 1","materias":["Materia 1","Materia 2"]}]' /></FormControl>
                </FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsCursoDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isModuloDialogOpen} onOpenChange={setIsModuloDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingModulo ? 'Editar Modulo' : 'Novo Modulo'}</DialogTitle></DialogHeader>
          <Form {...moduloForm}>
            <form onSubmit={moduloForm.handleSubmit(handleModuloSubmit)} className="space-y-4">
              <FormField control={moduloForm.control} name="curso_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Curso *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                    <SelectContent>{cursosSelect?.items.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={moduloForm.control} name="nome" render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome *</FormLabel>
                  <FormControl><input {...field} className="w-full" placeholder="Nome do Modulo" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <div className="grid gap-4 md:grid-cols-3">
                <FormField control={moduloForm.control} name="ordem" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ordem *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={moduloForm.control} name="carga_horaria" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Carga Horaria (h) *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
              <FormField control={moduloForm.control} name="conteudo" render={({ field }) => (
                <FormItem>
                  <FormLabel>Conteudo</FormLabel>
                  <FormControl><textarea {...field} className="w-full" rows={3} placeholder="Conteudo programatico" /></FormControl>
                </FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsModuloDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isMateriaDialogOpen} onOpenChange={setIsMateriaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingMateria ? 'Editar Materia' : 'Nova Materia'}</DialogTitle></DialogHeader>
          <Form {...materiaForm}>
            <form onSubmit={materiaForm.handleSubmit(handleMateriaSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={materiaForm.control} name="curso_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Curso</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent>{cursosSelect?.items.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent>
                    </Select>
                  </FormItem>
                )} />
                <FormField control={materiaForm.control} name="modulo_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Modulo</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent>{modulosSelect?.items.map(m => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}</SelectContent>
                    </Select>
                  </FormItem>
                )} />
              </div>
              <FormField control={materiaForm.control} name="nome" render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome *</FormLabel>
                  <FormControl><input {...field} className="w-full" placeholder="Nome da Materia" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={materiaForm.control} name="descricao" render={({ field }) => (
                <FormItem>
                  <FormLabel>Descricao</FormLabel>
                  <FormControl><textarea {...field} className="w-full" rows={3} placeholder="Descricao da materia" /></FormControl>
                </FormItem>
              )} />
              <div className="grid gap-4 md:grid-cols-4">
                <FormField control={materiaForm.control} name="carga_horaria" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Carga Horaria (h) *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={materiaForm.control} name="total_aulas_previstas" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Total Aulas Previstas *</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={materiaForm.control} name="ordem" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ordem</FormLabel>
                    <FormControl><input type="number" {...field} className="w-full" min="0" /></FormControl>
                  </FormItem>
                )} />
                <FormField control={materiaForm.control} name="tipo" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tipo</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                      <SelectContent><SelectItem value="teoria">Teoria</SelectItem><SelectItem value="pratica">Pratica</SelectItem><SelectItem value="estagio">Estagio</SelectItem></SelectContent>
                    </Select>
                  </FormItem>
                )} />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsMateriaDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}