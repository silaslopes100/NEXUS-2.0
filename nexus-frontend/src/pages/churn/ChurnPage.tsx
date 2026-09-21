'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, AlertCircle, RotateCcw, DollarSign, CreditCard, UserCheck, AlertTriangle, Mail, Phone, MapPin, Calendar, Shield, Eye, RotateCcw as Rotate } from 'lucide-react'
import { api } from '@/lib/api'
import { AlunoDesistente, PaginatedResponse, ReingressoRequest } from '@/types'
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
import { formatDate, formatCurrency, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const reingressoSchema = z.object({
  aluno_id: z.string().min(1),
  pagamento_taxa: z.boolean().default(true),
  polo_destino_id: z.string().optional(),
})

type ReingressoFormData = z.infer<typeof reingressoSchema>

export function ChurnPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isReingressoDialogOpen, setIsReingressoDialogOpen] = useState(false)
  const [editingAluno, setEditingAluno] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: churnData, isLoading } = useQuery({
    queryKey: ['churn', search, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/operacional/churn', { params: { q: search, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: alunosData } = useQuery({ queryKey: ['alunos-select-churn'], queryFn: () => api.get('/alunos', { params: { limit: 1000, status: 'desistente' } }).then(r => r.data.items) })
  const { data: polosData } = useQuery({ queryKey: ['polos-select'], queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items) })

  const reativarMutation = useMutation({
    mutationFn: (data: any) => api.post('/operacional/churn/reativar', data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['churn'] }); toast.success('Reingresso processado!'); setIsReingressoDialogOpen(false); },
    onError: (e) => toast.error(e.message),
  })

  const reingressoForm = useForm<any>({ resolver: zodResolver(z.object({ aluno_id: z.string().min(1), pagamento_taxa: z.boolean().default(true), polo_destino_id: z.string().optional() })), defaultValues: { pagamento_taxa: true } })

  const handleReingressoSubmit = (data: any) => { reativarMutation.mutate(data) }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Churn / Alunos Desistentes</h1><p className="text-muted-foreground">RN-04: mais de 1 ano sem movimentacao vira desistente. Reingresso: R$ 100,00 ou 2 licencas</p></div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-red-100 rounded-lg"><AlertCircle className="h-6 w-6 text-red-600" /></div><div><p className="text-sm text-muted-foreground">Total Desistentes</p><p className="text-2xl font-bold text-red-600">{churnData?.total || 0}</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-green-100 rounded-lg"><Rotate className="h-6 w-6 text-green-600" /></div><div><p className="text-sm text-muted-foreground">Reingressos Processados</p><p className="text-2xl font-bold text-green-600">0</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-yellow-100 rounded-lg"><DollarSign className="h-6 w-6 text-yellow-600" /></div><div><p className="text-sm text-muted-foreground">Taxas Arrecadadas</p><p className="text-2xl font-bold text-yellow-600">R$ 0,00</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-blue-100 rounded-lg"><CreditCard className="h-6 w-6 text-blue-600" /></div><div><p className="text-sm text-muted-foreground">Licencas Cobradas</p><p className="text-2xl font-bold text-blue-600">0</p></div></div></CardContent></Card>
      </div>

      <Tabs defaultValue="lista" className="space-y-4">
        <TabsList><TabsTrigger value="lista">Alunos Desistentes</TabsTrigger><TabsTrigger value="reativar">Processar Reingresso</TabsTrigger></TabsList>

        <TabsContent value="lista">
          <Card><CardHeader><div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"><CardTitle>Alunos Desistentes (mais de 1 ano sem movimentacao)</CardTitle><div className="flex flex-wrap gap-2"><Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" /></div></div></CardHeader>
          <CardContent>{isLoading ? <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : (<div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Aluno</TableHead><TableHead>CPF</TableHead><TableHead>Polo/Escola</TableHead><TableHead>Ultima Movimentacao</TableHead><TableHead>Dias Inativos</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Acoes</TableHead></TableRow></TableHeader><TableBody>{churnData?.items.map(a => (<TableRow key={a.id}><TableCell className="font-medium">{a.nome} {a.sobrenome}</TableCell><TableCell>{a.cpf ? formatDate(a.cpf) : '---'}</TableCell><TableCell>{a.polo_nome || a.escola_nome || '---'}</TableCell><TableCell>{a.ultima_movimentacao ? formatDate(a.ultima_movimentacao) : '---'}</TableCell><TableCell>{a.dias_inativos || 0}</TableCell><TableCell><Badge className={getStatusColor(a.status)}>{a.status}</Badge></TableCell><TableCell className="text-right"><Button variant="ghost" size="icon" onClick={() => { setEditingAluno(a); setIsReingressoDialogOpen(true); }} aria-label="Reingresso"><Rotate className="h-4 w-4" /></Button></TableCell></TableRow>))}</TableBody></Table></div>)}<div className="flex items-center justify-between mt-4"><p className="text-sm text-muted-foreground">Paginacao...</p><div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button><Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)}>Proximo</Button></div></div></CardContent></Card>
        </TabsContent>

        <TabsContent value="reativar">
          <Card><CardHeader><CardTitle>Processar Reingresso (RN-04)</CardTitle></CardHeader><CardContent>
            <div className="max-w-lg mx-auto space-y-6">
              <div className="p-4 border rounded-lg bg-amber-50 border-amber-200"><h4 className="font-medium mb-2">Regras de Reingresso (RN-04)</h4><ul className="text-sm text-amber-800 space-y-1"><li>Taxa de matricula: <strong>R$ 100,00</strong></li><li>OU 2 licencas cobradas do polo de destino</li><li>Etiqueta "aluno revalidado" aplicada automaticamente</li><li>So entra em turmas que comecem do zero</li><li>EAD: Pop-up "Voce ja tem cadastro, regularize pelo WhatsApp (11) 1936-6880"</li></ul></div>

              <div className="border-t pt-6"><h4 className="font-medium mb-4">Processar Reingresso</h4>
                <Form {...reingressoForm}><form onSubmit={reingressoForm.handleSubmit(handleReingressoSubmit)} className="space-y-4">
                  <FormField control={reingressoForm.control} name="aluno_id" render={({field})=>(<FormItem><FormLabel>Aluno Desistente *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{alunosData?.items.map(a => <SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>)}</SelectContent></Select><FormMessage/></FormItem>)} />
                  <FormField control={reingressoForm.control} name="pagamento_taxa" render={({field})=>(<FormItem className="flex items-center gap-2"><FormControl><input type="checkbox" {...field} className="h-4 w-4" /></FormControl><FormLabel>Pagar taxa de R$ 100,00 (desmarcar = 2 licencas do polo destino)</FormLabel></FormItem>)} />
                  <FormField control={reingressoForm.control} name="polo_destino_id" render={({field})=>(<FormItem><FormLabel>Polo de Destino (se 2 licencas)</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{polosData?.items.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}</SelectContent></Select></FormItem>)} />
                  <Button type="submit">Processar Reingresso</Button>
                </form></Form>
              </div>
            </div>
          </CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}