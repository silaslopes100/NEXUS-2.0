'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Award, FileText, Download, Eye, Calendar, Clock, AlertCircle, CheckCircle, XCircle, Shield, Eye as EyeIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { Certificado, PaginatedResponse, Aluno } from '@/types'
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

const emitirSchema = z.object({
  aluno_id: z.string().min(1, 'Selecione um aluno'),
  titulo: z.string().min(1, 'Titulo obrigatorio'),
  estagio1_data: z.string().min(1, 'Data entrega Teologia do Ministerio obrigatoria'),
  estagio2_data: z.string().min(1, 'Data entrega Homiletica obrigatoria'),
})

type EmitirFormData = z.infer<typeof emitirSchema>

export function CertificadosPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isEmitirDialogOpen, setIsEmitirDialogOpen] = useState(false)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [detailCertificado, setDetailCertificado] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: certificadosData, isLoading } = useQuery({
    queryKey: ['certificados', search, statusFilter, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/certificados', { params: { query: search, status: statusFilter, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: alunosData } = useQuery({ queryKey: ['alunos-select'], queryFn: () => api.get('/alunos', { params: { limit: 1000 } }).then(r => r.data.items) })

  const emitMutation = useMutation({ mutationFn: (data: any) => api.post('/operacional/certificados/emitir', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificados'] }); toast.success('Certificado emitido!'); setIsEmitirDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const deleteMutation = useMutation({ mutationFn: (id: string) => api.delete(`/operacional/certificados/${id}`), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificados'] }); toast.success('Certificado cancelado!'); }, onError: (e) => toast.error(e.message) })

  const emitForm = useForm<any>({ resolver: zodResolver(emitirSchema), defaultValues: {} })

  const handleEmitSubmit = (data: any) => { setIsSubmitting(true); emitMutation.mutate(data) }

  const openEmitDialog = () => { emitForm.reset(); setIsEmitirDialogOpen(true); }
  const openDetailDialog = async (cert: any) => { try { const detail = await api.get<any>(`/certificados/${cert.id}`).then(r => r.data); setDetailCertificado(detail); setIsDetailDialogOpen(true); } catch { toast.error('Erro ao carregar'); } }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Certificados</h1><p className="text-muted-foreground">RN-05: Emissao exige 2 estagios (Teologia + Homiletica) + historico completo</p></div>
        <Button onClick={openEmitDialog}><Plus className="mr-2 h-4 w-4" />Emitir Certificado</Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Certificados</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="pendente">Pendente</SelectItem>
                  <SelectItem value="emitido">Emitido</SelectItem>
                  <SelectItem value="cancelado">Cancelado</SelectItem>
                </SelectContent>
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
                    <TableHead>Titulo</TableHead>
                    <TableHead>Estagios</TableHead>
                    <TableHead>Historico Completo</TableHead>
                    <TableHead>Emissao</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {certificadosData?.items.map(c => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium">{c.aluno_nome || '---'}</TableCell>
                      <TableCell>{c.titulo}</TableCell>
                      <TableCell>{c.estagios_entregues?.map(e => `${e.nome}: ${e.data_entrega ? formatDate(e.data_entrega) : '---'}`).join(', ') || '---'}</TableCell>
                      <TableCell><Badge variant={c.historico_completo ? 'success' : 'destructive'}>{c.historico_completo ? 'Completo' : 'Incompleto'}</Badge></TableCell>
                      <TableCell>{c.data_emissao ? formatDate(c.data_emissao) : '---'}</TableCell>
                      <TableCell><Badge className={getStatusColor(c.status)}>{c.status}</Badge></TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => openDetailDialog(c)} aria-label="Ver"><EyeIcon className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={() => { if(confirm('Cancelar?')) deleteMutation.mutate(c.id) }} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-muted-foreground">Paginacao...</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)}>Proximo</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isEmitirDialogOpen} onOpenChange={setIsEmitirDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Emitir Certificado (RN-05)</DialogTitle></DialogHeader>
          <Form {...emitForm}>
            <form onSubmit={emitForm.handleSubmit(handleEmitSubmit)} className="space-y-4">
              <FormField control={emitForm.control} name="aluno_id" render={({field})=>(<FormItem><FormLabel>Aluno *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{alunosData?.items.map(a=>(<SelectItem key={a.id} value={a.id}>{a.nome} {a.sobrenome}</SelectItem>))}</SelectContent></Select><FormMessage/></FormItem>)} />
              <FormField control={emitForm.control} name="titulo" render={({field})=>(<FormItem><FormLabel>Titulo *</FormLabel><FormControl><input {...field} className="w-full" placeholder="Certificado de Conclusao" /></FormControl></FormItem>)} />
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={emitForm.control} name="estagio1_data" render={({field})=>(<FormItem><FormLabel>Entrega: Teologia do Ministerio *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl></FormItem>)} />
                <FormField control={emitForm.control} name="estagio2_data" render={({field})=>(<FormItem><FormLabel>Entrega: Homiletica *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl></FormItem>)} />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={()=>setIsEmitirDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Emitir'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}