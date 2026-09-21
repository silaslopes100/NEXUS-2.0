'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Award, FileText, Download, Eye, FileCheck, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { Nota, HistoricoItem, PaginatedResponse, Aluno, Materia } from '@/types'
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
import { formatDate, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const notaSchema = z.object({
  aluno_id: z.string().min(1, 'Selecione um aluno'),
  materia_id: z.string().min(1, 'Selecione uma matéria'),
  nota: z.number().min(0).max(10, 'Nota deve ser entre 0 e 10'),
  tipo: z.enum(['prova', 'trabalho', 'participacao', 'final']),
  semestre: z.number().min(1).max(3),
  ano: z.number().min(2000).max(2100),
})

type NotaFormData = z.infer<typeof notaSchema>

export function NotasPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'lancar' | 'consultar' | 'historico'>('lancar')
  const [alunoFilter, setAlunoFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isNotaDialogOpen, setIsNotaDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: notasData } = useQuery({
    queryKey: ['notas', alunoFilter, page, pageSize],
    queryFn: () => api.get<any>('/operacional/notas', { params: { aluno_id: alunoFilter, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: historicoData } = useQuery({
    queryKey: ['historico', alunoFilter, page, pageSize],
    queryFn: () => api.get<any[]>('/operacional/historico', { params: { aluno_id: alunoFilter, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: alunosData } = useQuery({ queryKey: ['alunos-select'], queryFn: () => api.get('/alunos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: materiasData } = useQuery({ queryKey: ['materias-select'], queryFn: () => api.get('/materias', { params: { limit: 1000 } }).then(r => r.data.items) })

  const createNota = useMutation({ mutationFn: (data: any) => api.post('/operacional/notas', data), onSuccess: () => { toast.success('Nota lançada!'); setIsNotaDialogOpen(false); }, onError: (e) => toast.error(e.message) })

  const notaForm = useForm<any>({ resolver: zodResolver(z.object({ aluno_id: z.string().min(1), materia_id: z.string().min(1), nota: z.number().min(0).max(10), tipo: z.enum(['prova','trabalho','participacao','final']), semestre: z.number().min(1).max(3), ano: z.number().min(2000).max(2100) })), defaultValues: { tipo: 'prova', semestre: 1, ano: new Date().getFullYear() } })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Notas / Histórico</h1><p className="text-muted-foreground">Lançamento de notas e emissão de histórico escolar</p></div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList><TabsTrigger value="lancar">Lançar Nota</TabsTrigger><TabsTrigger value="consultar">Consultar Notas</TabsTrigger><TabsTrigger value="historico">Histórico Escolar</TabsTrigger></TabsList>

        <TabsContent value="lancar">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Lançar Nova Nota</CardTitle></CardHeader>
            <CardContent>
              <Form {...notaForm}>
                <form onSubmit={notaForm.handleSubmit(createNota.mutate)} className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField control={notaForm.control} name="aluno_id" render={({field})=>(<FormItem><FormLabel>Aluno *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
                    <FormField control={notaForm.control} name="materia_id" render={({field})=>(<FormItem><FormLabel>Matéria *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
                  </div>
                  <div className="grid gap-4 md:grid-cols-4">
                    <FormField control={notaForm.control} name="nota" render={({field})=>(<FormItem><FormLabel>Nota (0-10) *</FormLabel><FormControl><input type="number" {...field} className="w-full" step="0.1" min="0" max="10" /></FormControl></FormItem>)} />
                    <FormField control={notaForm.control} name="tipo" render={({field})=>(<FormItem><FormLabel>Tipo</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="prova">Prova</SelectItem><SelectItem value="trabalho">Trabalho</SelectItem><SelectItem value="participacao">Participação</SelectItem><SelectItem value="final">Final</SelectItem></SelectContent></Select></FormItem>)} />
                    <FormField control={notaForm.control} name="semestre" render={({field})=>(<FormItem><FormLabel>Semestre</FormLabel><FormControl><input type="number" {...field} className="w-full" min="1" max="3" /></FormControl></FormItem>)} />
                    <FormField control={notaForm.control} name="ano" render={({field})=>(<FormItem><FormLabel>Ano</FormLabel><FormControl><input type="number" {...field} className="w-full" min="2000" max="2100" /></FormControl></FormItem>)} />
                  </div>
                  <Button type="submit" className="w-full">Lançar Nota</Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="consultar">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Consultar Notas</CardTitle>
              <Select value={alunoFilter} onValueChange={setAlunoFilter}>
                <SelectTrigger className="w-[300px]"><SelectValue placeholder="Filtrar por Aluno"/></SelectTrigger>
                <SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent>
              </Select>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Aluno</TableHead><TableHead>Matéria</TableHead><TableHead>Nota</TableHead><TableHead>Tipo</TableHead><TableHead>Semestre/Ano</TableHead><TableHead>Data</TableHead></TableRow></TableHeader>
              <TableBody>
                {notasData?.items.map(n => (
                  <TableRow key={n.id}>
                    <TableCell>{n.aluno_nome}</TableCell>
                    <TableCell>{n.materia_nome}</TableCell>
                    <TableCell className="font-mono">{n.nota}</TableCell>
                    <TableCell>{n.tipo}</TableCell>
                    <TableCell>{n.semestre}º / {n.ano}</TableCell>
                    <TableCell>{n.criado_em ? formatDate(n.criado_em) : '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody></Table></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="historico">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Histórico Escolar</CardTitle>
              <Select value={alunoFilter} onValueChange={setAlunoFilter}>
                <SelectTrigger className="w-[300px]"><SelectValue placeholder="Selecionar Aluno"/></SelectTrigger>
                <SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent>
              </Select>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 border rounded-lg bg-muted/50"><h4 className="font-medium mb-2">Resumo do Aluno</h4><p className="text-sm text-muted-foreground">Selecione um aluno para ver o histórico completo com notas, presenças e certificados.</p></div>
                <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Data</TableHead><TableHead>Descrição</TableHead><TableHead>Tipo</TableHead><TableHead>Semestre</TableHead><TableHead>Ano</TableHead></TableRow></TableHeader>
                <TableBody>
                  {historicoData?.map(h => (
                    <TableRow key={h.id}>
                      <TableCell>{h.criado_em ? formatDate(h.criado_em) : '—'}</TableCell>
                      <TableCell>{h.descricao}</TableCell>
                      <TableCell>{h.tipo}</TableCell>
                      <TableCell>{h.semestre}</TableCell>
                      <TableCell>{h.ano}</TableCell>
                    </TableRow>
                  ))}
                </TableBody></Table></div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate, getStatusColor } from '@/lib/utils'