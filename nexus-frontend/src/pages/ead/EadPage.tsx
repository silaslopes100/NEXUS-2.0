'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Calendar, Bell, MessageSquare, Package, Download, Upload } from 'lucide-react'
import { api } from '@/lib/api'
import { EADMatricula, EADCalendario, FeedNoticia, Lembrete, PaginatedResponse, Aluno, Curso, Materia } from '@/types'
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
import { formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const matriculaEadSchema = z.object({
  aluno_id: z.string().min(1, 'Selecione um aluno'),
  curso_id: z.string().min(1, 'Selecione um curso'),
  materia_id: z.string().min(1, 'Selecione uma matéria'),
  data_inicio: z.string().min(1, 'Data de início obrigatória'),
  status: z.enum(['ativa', 'concluida', 'reprovada', 'cancelada']).default('ativa'),
})

type MatriculaEadFormData = z.infer<typeof matriculaEadSchema>

const calendarioSchema = z.object({
  curso_id: z.string().optional(),
  materia_id: z.string().optional(),
  titulo: z.string().min(1, 'Título obrigatório'),
  data_inicio: z.string().min(1, 'Data de início obrigatória'),
  data_fim: z.string().min(1, 'Data de fim obrigatória'),
  status: z.enum(['programado', 'aberto', 'fechado']).default('programado'),
})

type CalendarioFormData = z.infer<typeof calendarioSchema>

const feedSchema = z.object({
  titulo: z.string().min(1, 'Título obrigatório'),
  conteudo: z.string().min(1, 'Conteúdo obrigatório'),
})

type FeedFormData = z.infer<typeof feedSchema>

const lembreteSchema = z.object({
  titulo: z.string().min(1, 'Título obrigatório'),
  mensagem: z.string().min(1, 'Mensagem obrigatória'),
  data_exibicao: z.string().optional(),
})

type LembreteFormData = z.infer<typeof lembreteSchema>

export function EadPage() {
  const queryClient = useQueryClient()
  const [matriculasPage, setMatriculasPage] = useState(1)
  const [calendarioPage, setCalendarioPage] = useState(1)
  const [pageSize] = useState(10)
  const [activeTab, setActiveTab] = useState<'matriculas' | 'calendario' | 'feed' | 'lembretes'>('matriculas')
  const [isMatriculaDialogOpen, setIsMatriculaDialogOpen] = useState(false)
  const [isCalendarioDialogOpen, setIsCalendarioDialogOpen] = useState(false)
  const [isFeedDialogOpen, setIsFeedDialogOpen] = useState(false)
  const [isLembreteDialogOpen, setIsLembreteDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: matriculasData, isLoading: matriculasLoading } = useQuery({
    queryKey: ['matriculas-ead', matriculasPage, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/operacional/ead/matriculas', { params: { limit: pageSize, offset: (matriculasPage - 1) * pageSize } }).then(r => r.data),
  })

  const { data: calendarioData } = useQuery({
    queryKey: ['ead-calendario', calendarioPage, pageSize],
    queryFn: () => api.get<any[]>('/operacional/ead/calendario', { params: { limit: pageSize, offset: (calendarioPage - 1) * pageSize } }).then(r => r.data),
  })

  const { data: feedData } = useQuery({
    queryKey: ['ead-feed'],
    queryFn: () => api.get<any[]>('/operacional/ead/feed', { params: { limit: 50 } }).then(r => r.data),
  })

  const { data: lembretesData } = useQuery({
    queryKey: ['ead-lembretes'],
    queryFn: () => api.get<any[]>('/operacional/ead/lembretes', { params: { limit: 50 } }).then(r => r.data),
  })

  const { data: alunosData } = useQuery({ queryKey: ['alunos-select'], queryFn: () => api.get('/alunos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: cursosData } = useQuery({ queryKey: ['cursos-select'], queryFn: () => api.get('/cursos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: materiasData } = useQuery({ queryKey: ['materias-select'], queryFn: () => api.get('/materias', { params: { limit: 1000 } }).then(r => r.data.items) })

  const matriculaForm = useForm<MatriculaEadFormData>({ resolver: zodResolver(matriculaEadSchema), defaultValues: { status: 'ativa' } })
  const calendarioForm = useForm<CalendarioFormData>({ resolver: zodResolver(calendarioSchema), defaultValues: { status: 'programado' } })
  const feedForm = useForm<FeedFormData>({ resolver: zodResolver(feedSchema) })
  const lembreteForm = useForm<LembreteFormData>({ resolver: zodResolver(lembreteSchema), defaultValues: { data_exibicao: new Date().toISOString().split('T')[0] } })

  const createMatricula = useMutation({ mutationFn: (data: MatriculaEadFormData) => api.post('/operacional/ead/matricula', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['matriculas-ead'] }); toast.success('Matrícula EAD criada!'); setIsMatriculaDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const createCalendario = useMutation({ mutationFn: (data: CalendarioFormData) => api.post('/operacional/ead/calendario', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ead-calendario'] }); toast.success('Evento criado!'); setIsCalendarioDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const createFeed = useMutation({ mutationFn: (data: FeedFormData) => api.post('/operacional/feed', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ead-feed'] }); toast.success('Notícia publicada!'); setIsFeedDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const createLembrete = useMutation({ mutationFn: (data: LembreteFormData) => api.post('/operacional/lembretes', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ead-lembretes'] }); toast.success('Lembrete criado!'); setIsLembreteDialogOpen(false); }, onError: (e) => toast.error(e.message) })

  const handleMatriculaSubmit = (data: MatriculaEadFormData) => { setIsSubmitting(true); createMatricula.mutate(data) }
  const handleCalendarioSubmit = (data: CalendarioFormData) => { setIsSubmitting(true); createCalendario.mutate(data) }
  const handleFeedSubmit = (data: FeedFormData) => { setIsSubmitting(true); createFeed.mutate(data) }
  const handleLembreteSubmit = (data: LembreteFormData) => { createLembrete.mutate(data) }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">EAD - Gestão Pedagógica</h1><p className="text-muted-foreground">RN-03: 2 matérias/mês, calendário, feed, lembretes</p></div>
        <div className="flex gap-2">
          {activeTab === 'matriculas' && <Button onClick={() => { matriculaForm.reset({ status: 'ativa' }); setIsMatriculaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Matrícula</Button>}
          {activeTab === 'calendario' && <Button onClick={() => { calendarioForm.reset({ status: 'programado' }); setIsCalendarioDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Novo Evento</Button>}
          {activeTab === 'feed' && <Button onClick={() => { feedForm.reset(); setIsFeedDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Notícia</Button>}
          {activeTab === 'lembretes' && <Button onClick={() => { lembreteForm.reset({ data_exibicao: new Date().toISOString().split('T')[0] }); setIsLembreteDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Novo Lembrete</Button>}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="matriculas">Matrículas EAD</TabsTrigger>
          <TabsTrigger value="calendario">Calendário de Liberação</TabsTrigger>
          <TabsTrigger value="feed">Feed de Notícias</TabsTrigger>
          <TabsTrigger value="lembretes">Lembretes</TabsTrigger>
        </TabsList>

        <TabsContent value="matriculas">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Matrículas EAD</CardTitle><Button onClick={() => { matriculaForm.reset({ status: 'ativa' }); setIsMatriculaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Matrícula</Button></CardHeader>
            <CardContent>
              {matriculasLoading ? <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : (
                <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Aluno</TableHead><TableHead>Curso</TableHead><TableHead>Matéria</TableHead><TableHead>Início</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Ações</TableHead></TableRow></TableHeader>
                <TableBody>{matriculasData?.items.map(m => (<TableRow key={m.id}><TableCell className="font-medium">{m.aluno_nome || '—'}</TableCell><TableCell>{m.curso_nome || '—'}</TableCell><TableCell>{m.materia_nome || '—'}</TableCell><TableCell>{m.data_inicio ? formatDate(m.data_inicio) : '—'}</TableCell><TableCell><Badge variant="outline">{m.status}</Badge></TableCell><TableCell className="text-right"><Button variant="ghost" size="icon" className="text-destructive"><Trash2 className="h-4 w-4" /></Button></TableCell></TableRow>))}</TableBody></Table></div>
              )}</CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="calendario">
          <Card><CardHeader className="flex flex-row items-center justify-between"><CardTitle>Calendário de Liberação</CardTitle><Button onClick={() => { calendarioForm.reset({ status: 'programado' }); setIsCalendarioDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Novo Evento</Button></CardHeader>
          <CardContent><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Título</TableHead><TableHead>Curso</TableHead><TableHead>Matéria</TableHead><TableHead>Início</TableHead><TableHead>Fim</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Ações</TableHead></TableRow></TableHeader><TableBody>{calendarioData?.map(c => (<TableRow key={c.id}><TableCell className="font-medium">{c.titulo}</TableCell><TableCell>{c.curso_nome || '—'}</TableCell><TableCell>{c.materia_nome || '—'}</TableCell><TableCell>{c.data_inicio ? formatDate(c.data_inicio) : '—'}</TableCell><TableCell>{c.data_fim ? formatDate(c.data_fim) : '—'}</TableCell><TableCell><Badge variant="outline">{c.status}</Badge></TableCell><TableCell className="text-right"><Button variant="ghost" size="icon" className="text-destructive"><Trash2 className="h-4 w-4" /></Button></TableCell></TableRow>))}</TableBody></Table></div></CardContent></Card>
        </TabsContent>

        <TabsContent value="feed">
          <Card><CardHeader className="flex flex-row items-center justify-between"><CardTitle>Feed de Notícias</CardTitle><Button onClick={() => { feedForm.reset(); setIsFeedDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Notícia</Button></CardHeader>
          <CardContent><div className="space-y-4">{feedData?.map(f => (<Card key={f.id} className="p-4"><div className="flex items-start justify-between gap-4"><div><h4 className="font-medium">{f.titulo}</h4><p className="text-sm text-muted-foreground">{f.conteudo}</p><p className="text-xs text-muted-foreground mt-1">Por {f.autor_nome} ({f.autor_perfil}) • {formatDate(f.criado_em)}</p></div><Button variant="ghost" size="icon" className="text-destructive"><Trash2 className="h-4 w-4" /></Button></div></Card>))}</div></CardContent></Card>
        </TabsContent>

        <TabsContent value="lembretes">
          <Card><CardHeader className="flex flex-row items-center justify-between"><CardTitle>Lembretes</CardTitle><Button onClick={() => { lembreteForm.reset({ data_exibicao: new Date().toISOString().split('T')[0] }); setIsLembreteDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Novo Lembrete</Button></CardHeader>
          <CardContent><div className="space-y-4">{lembretesData?.map(l => (<Card key={l.id} className="p-4"><div className="flex items-center justify-between"><div><h4 className="font-medium">{l.titulo}</h4><p className="text-sm text-muted-foreground">{l.mensagem}</p></div><Badge variant="outline">{l.data_exibicao ? formatDate(l.data_exibicao) : 'Sem data'}</Badge></div></Card>)) || <p className="text-muted-foreground text-center py-8">Nenhum lembrete</p>}</div></CardContent></Card>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <Dialog open={isMatriculaDialogOpen} onOpenChange={setIsMatriculaDialogOpen}>
        <DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Nova Matrícula EAD</DialogTitle></DialogHeader>
        <Form {...matriculaForm}><form onSubmit={matriculaForm.handleSubmit(handleMatriculaSubmit)} className="space-y-4">
          <FormField control={matriculaForm.control} name="aluno_id" render={({field})=>(<FormItem><FormLabel>Aluno *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
          <FormField control={matriculaForm.control} name="curso_id" render={({field})=>(<FormItem><FormLabel>Curso *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{cursosData?.items.map(c=>(<SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
          <FormField control={matriculaForm.control} name="materia_id" render={({field})=>(<FormItem><FormLabel>Matéria *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
          <FormField control={matriculaForm.control} name="data_inicio" render={({field})=>(<FormItem><FormLabel>Data Início *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl><FormMessage/></FormItem>)} />
          <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsMatriculaDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Salvar'}</Button></DialogFooter>
        </form></Form></DialogContent></Dialog>

      <Dialog open={isCalendarioDialogOpen} onOpenChange={setIsCalendarioDialogOpen}>
        <DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Novo Evento no Calendário</DialogTitle></DialogHeader>
        <Form {...calendarioForm}><form onSubmit={calendarioForm.handleSubmit(handleCalendarioSubmit)} className="space-y-4">
          <FormField control={calendarioForm.control} name="titulo" render={({field})=>(<FormItem><FormLabel>Título *</FormLabel><FormControl><input {...field} className="w-full" placeholder="Título do evento" /></FormControl><FormMessage/></FormItem>)} />
          <FormField control={calendarioForm.control} name="curso_id" render={({field})=>(<FormItem><FormLabel>Curso</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{cursosData?.items.map(c=>(<SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
          <FormField control={calendarioForm.control} name="materia_id" render={({field})=>(<FormItem><FormLabel>Matéria</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
          <div className="grid gap-4 md:grid-cols-2"><FormField control={calendarioForm.control} name="data_inicio" render={({field})=>(<FormItem><FormLabel>Início *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl><FormMessage/></FormItem>)} /><FormField control={calendarioForm.control} name="data_fim" render={({field})=>(<FormItem><FormLabel>Fim *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl><FormMessage/></FormItem>)} /></div>
          <FormField control={calendarioForm.control} name="status" render={({field})=>(<FormItem><FormLabel>Status</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="programado">Programado</SelectItem><SelectItem value="aberto">Aberto</SelectItem><SelectItem value="fechado">Fechado</SelectItem></SelectContent></Select></FormItem>)} />
          <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsCalendarioDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Salvar'}</Button></DialogFooter>
        </form></Form></DialogContent></Dialog>

      <Dialog open={isFeedDialogOpen} onOpenChange={setIsFeedDialogOpen}>
        <DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Nova Notícia</DialogTitle></DialogHeader>
        <Form {...feedForm}><form onSubmit={feedForm.handleSubmit(handleFeedSubmit)} className="space-y-4">
          <FormField control={feedForm.control} name="titulo" render={({field})=>(<FormItem><FormLabel>Título *</FormLabel><FormControl><input {...field} className="w-full" placeholder="Título da notícia" /></FormControl><FormMessage/></FormItem>)} />
          <FormField control={feedForm.control} name="conteudo" render={({field})=>(<FormItem><FormLabel>Conteúdo *</FormLabel><FormControl><textarea {...field} className="w-full" rows={4} placeholder="Conteúdo da notícia" /></FormControl><FormMessage/></FormItem>)} />
          <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsFeedDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Publicar'}</Button></DialogFooter>
        </form></Form></DialogContent></Dialog>

      <Dialog open={isLembreteDialogOpen} onOpenChange={setIsLembreteDialogOpen}>
        <DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Novo Lembrete</DialogTitle></DialogHeader>
        <Form {...lembreteForm}><form onSubmit={lembreteForm.handleSubmit(handleLembreteSubmit)} className="space-y-4">
          <FormField control={lembreteForm.control} name="titulo" render={({field})=>(<FormItem><FormLabel>Título *</FormLabel><FormControl><input {...field} className="w-full" placeholder="Título do lembrete" /></FormControl></FormItem>)} />
          <FormField control={lembreteForm.control} name="mensagem" render={({field})=>(<FormItem><FormLabel>Mensagem *</FormLabel><FormControl><textarea {...field} className="w-full" rows={3} placeholder="Mensagem do lembrete" /></FormControl></FormItem>)} />
          <FormField control={lembreteForm.control} name="data_exibicao" render={({field})=>(<FormItem><FormLabel>Data de Exibição</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl></FormItem>)} />
          <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsLembreteDialogOpen(false)}>Cancelar</Button><Button type="submit">Criar</Button></DialogFooter>
        </form></Form></DialogContent></Dialog>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate } from '@/lib/utils'
import { Loader2 } from 'lucide-react'