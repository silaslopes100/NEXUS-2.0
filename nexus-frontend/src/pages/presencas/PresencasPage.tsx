'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Calendar, User, Clock, Check, X, FileText, Download, Upload, Eye } from 'lucide-react'
import { api } from '@/lib/api'
import { Aula, Presenca, PaginatedResponse, Aluno, Materia, Professor } from '@/types'
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
import { formatDate, formatDateTime, calculatePresencePercentage, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const aulaSchema = z.object({
  curso_id: z.string().optional(),
  modulo_id: z.string().optional(),
  materia_id: z.string().min(1, 'Selecione uma matéria'),
  professor_id: z.string().min(1, 'Selecione um professor'),
  titulo: z.string().min(1, 'Título obrigatório'),
  data_aula: z.string().min(1, 'Data da aula obrigatória'),
  descricao: z.string().optional(),
})

type AulaFormData = z.infer<typeof aulaSchema>

const presencaSchema = z.object({
  aula_id: z.string().min(1),
  registros: z.array(z.object({ aluno_id: z.string(), presente: z.boolean() })).min(1),
})

export function PresencasPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'aulas' | 'registrar' | 'consultar'>('aulas')
  const [aulasPage, setAulasPage] = useState(1)
  const [pageSize] = useState(10)
  const [isAulaDialogOpen, setIsAulaDialogOpen] = useState(false)
  const [isPresencaDialogOpen, setIsPresencaDialogOpen] = useState(false)
  const [selectedAula, setSelectedAula] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: aulasData, isLoading: aulasLoading } = useQuery({
    queryKey: ['aulas', 1, 100],
    queryFn: () => api.get<any[]>('/operacional/aulas', { params: { limit: 100 } }).then(r => r.data),
  })

  const { data: materiasData } = useQuery({ queryKey: ['materias-select'], queryFn: () => api.get('/materias', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: professoresData } = useQuery({ queryKey: ['professores-select'], queryFn: () => api.get('/professores', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: alunosData } = useQuery({ queryKey: ['alunos-select'], queryFn: () => api.get('/alunos', { params: { limit: 1000 } }).then(r => r.data.items) })

  const aulaForm = useForm<any>({ resolver: zodResolver(z.object({ materia_id: z.string().min(1), professor_id: z.string().min(1), titulo: z.string().min(1), data_aula: z.string().min(1), descricao: z.string().optional() })), defaultValues: {} })

  const createAula = useMutation({ mutationFn: (data: any) => api.post('/operacional/aulas', data), onSuccess: () => { toast.success('Aula criada!'); setIsAulaDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const registrarPresencas = useMutation({ mutationFn: (data: any) => api.post('/operacional/presencas/registrar', data), onSuccess: () => { toast.success('Presenças registradas!'); setSelectedAula(null); }, onError: (e) => toast.error(e.message) })

  const handleAulaSubmit = (data: any) => { createAula.mutate(data) }
  const handlePresencaSubmit = (data: any) => { registrarPresencas.mutate(data) }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Presenças / Aulas / Atas</h1><p className="text-muted-foreground">RN-07: % presença = presenças / total_aulas_previstas * 100</p></div>
        <Button onClick={() => { setSelectedAula(null); aulaForm.reset(); setIsAulaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Aula</Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="aulas">Aulas</TabsTrigger>
          <TabsTrigger value="registrar">Registrar Presença</TabsTrigger>
          <TabsTrigger value="consultar">Consultar Presenças</TabsTrigger>
        </TabsList>

        <TabsContent value="aulas">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Aulas</CardTitle>
              <Button onClick={() => { setSelectedAula(null); aulaForm.reset(); setIsAulaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Aula</Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader><TableRow><TableHead>Título</TableHead><TableHead>Matéria</TableHead><TableHead>Professor</TableHead><TableHead>Data</TableHead><TableHead className="text-right">Ações</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {aulasData?.map(a => (
                      <TableRow key={a.id}>
                        <TableCell className="font-medium">{a.titulo}</TableCell>
                        <TableCell>{a.materia_nome}</TableCell>
                        <TableCell>{a.professor_nome}</TableCell>
                        <TableCell>{a.data_aula ? formatDate(a.data_aula) : '—'}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => { setSelectedAula(a); setIsPresencaDialogOpen(true); }}><Eye className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => { setSelectedAula(a); aulaForm.reset({ materia_id: a.materia_id, professor_id: a.professor_id, titulo: a.titulo, data_aula: a.data_aula?.split('T')[0], descricao: a.descricao }); setIsAulaDialogOpen(true); }}><Edit className="h-4 w-4" /></Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="registrar">
          <Card>
            <CardHeader><CardTitle>Registrar Presença (Lista de Chamada - RN-07)</CardTitle></CardHeader>
            <CardContent>
              <Form {...aulaForm}>
                <form onSubmit={aulaForm.handleSubmit(handlePresencaSubmit)} className="space-y-4">
                  <FormField control={aulaForm.control} name="aula_id" render={({field})=>(<FormItem><FormLabel>Aula *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione a aula"/></SelectTrigger><SelectContent>{aulasData?.map(a => (<SelectItem key={a.id} value={a.id}>{a.titulo} - {a.materia_nome} - {formatDate(a.data_aula)}</SelectItem>))}</SelectContent></Select></FormItem>)} />
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-3">Lista de Chamada</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {alunosData?.items.slice(0, 20).map((aluno, i) => (
                        <div key={aluno.id} className="flex items-center justify-between p-3 border rounded-lg bg-muted/30">
                          <div className="flex items-center gap-3 flex-1"><span className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-medium">{i+1}</span><span className="font-medium">{aluno.nome} {aluno.sobrenome}</span></div>
                          <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" defaultChecked className="h-4 w-4"/><span>Presente</span></label>
                            <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" className="h-4 w-4"/><span>Ausente</span></label>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <Button type="submit" className="w-full">Salvar Presenças</Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="consultar">
          <Card>
            <CardHeader><CardTitle>Consultar Presenças</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3 mb-4">
                <Select placeholder="Aluno"><SelectTrigger><SelectValue placeholder="Filtrar por Aluno"/></SelectTrigger><SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent></Select>
                <Select placeholder="Matéria"><SelectTrigger><SelectValue placeholder="Filtrar por Matéria"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select>
                <Select placeholder="Professor"><SelectTrigger><SelectValue placeholder="Filtrar por Professor"/></SelectTrigger><SelectContent>{professoresData?.items.map(p=>(<SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>))}</SelectContent></Select>
              </div>
              <Card><CardContent><Table><TableHeader><TableRow><TableHead>Aluno</TableHead><TableHead>Matéria</TableHead><TableHead>Total Aulas</TableHead><TableHead>Presenças</TableHead><TableHead>%</TableHead></TableRow></TableHeader><TableBody></TableBody></Table></CardContent></Card>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isAulaDialogOpen} onOpenChange={setIsAulaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{selectedAula ? 'Editar Aula' : 'Nova Aula'}</DialogTitle></DialogHeader>
          <Form {...aulaForm}>
            <form onSubmit={aulaForm.handleSubmit(handleAulaSubmit)} className="space-y-4">
              <FormField control={aulaForm.control} name="materia_id" render={({field})=>(<FormItem><FormLabel>Matéria *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
              <FormField control={aulaForm.control} name="professor_id" render={({field})=>(<FormItem><FormLabel>Professor *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{professoresData?.items.map(p=>(<SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
              <FormField control={aulaForm.control} name="titulo" render={({field})=>(<FormItem><FormLabel>Título *</FormLabel><FormControl><input {...field} className="w-full" placeholder="Título da aula" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={aulaForm.control} name="data_aula" render={({field})=>(<FormItem><FormLabel>Data da Aula *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={aulaForm.control} name="descricao" render={({field})=>(<FormItem><FormLabel>Descrição</FormLabel><FormControl><textarea {...field} className="w-full" rows={3} placeholder="Conteúdo da aula" /></FormControl></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsAulaDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Salvar'}</Button></DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isPresencaDialogOpen} onOpenChange={setIsPresencaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Registrar Presença - {selectedAula?.titulo}</DialogTitle></DialogHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {alunosData?.items.slice(0, 20).map((aluno, i) => (
                <div key={aluno.id} className="flex items-center justify-between p-3 border rounded-lg bg-muted/30">
                  <div className="flex items-center gap-3 flex-1"><span className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-medium">{i+1}</span><span className="font-medium">{aluno.nome} {aluno.sobrenome}</span></div>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" defaultChecked className="h-4 w-4"/><span>Presente</span></label>
                    <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" className="h-4 w-4"/><span>Ausente</span></label>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </DialogContent>
      </Dialog>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate, calculatePresencePercentage, getStatusColor } from '@/lib/utils'