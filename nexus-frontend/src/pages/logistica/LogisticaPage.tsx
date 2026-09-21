'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Truck, Package, Calendar, Filter, Download, Eye, Edit as EditIcon, Trash2 as TrashIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { PedidoLivro, PaginatedResponse, Polo, Escola, Materia } from '@/types'
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

const pedidoSchema = z.object({
  polo_id: z.string().optional(),
  escola_id: z.string().optional(),
  materia_id: z.string().optional(),
  quantidade: z.number().int().min(1, 'Quantidade mínima é 1'),
  observacao: z.string().optional(),
})

type PedidoFormData = z.infer<typeof pedidoSchema>

const statusSchema = z.object({
  status: z.enum(['pendente', 'enviado', 'entregue', 'cancelado']),
  observacao: z.string().optional(),
})

type StatusFormData = z.infer<typeof statusSchema>

export function LogisticaPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false)
  const [editingPedido, setEditingPedido] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: pedidosData, isLoading } = useQuery({
    queryKey: ['pedidos', search, statusFilter, page, pageSize],
    queryFn: () => api.get<any>('/logistica/pedidos', { params: { filtros: { status: statusFilter }, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: polosData } = useQuery({ queryKey: ['polos-select'], queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: escolasData } = useQuery({ queryKey: ['escolas-select'], queryFn: () => api.get('/escolas', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: materiasData } = useQuery({ queryKey: ['materias-select'], queryFn: () => api.get('/materias', { params: { limit: 1000 } }).then(r => r.data.items) })

  const createMutation = useMutation({ mutationFn: (data: any) => api.post('/operacional/logistica/pedidos', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pedidos'] }); toast.success('Pedido criado!'); setIsDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const updateMutation = useMutation({ mutationFn: ({ id, data }: { id: string; data: any }) => api.put(`/operacional/logistica/pedidos/${id}`, data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pedidos'] }); toast.success('Pedido atualizado!'); setIsDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const statusMutation = useMutation({ mutationFn: ({ id, data }: { id: string; data: any }) => api.put(`/operacional/logistica/pedidos/${id}`, data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pedidos'] }); toast.success('Status atualizado!'); setIsStatusDialogOpen(false); }, onError: (e) => toast.error(e.message) })

  const form = useForm<any>({ resolver: zodResolver(pedidoSchema), defaultValues: { quantidade: 1, status: 'pendente' } })
  const statusForm = useForm<any>({ resolver: zodResolver(statusSchema) })

  const handleSubmit = (data: any) => { setIsSubmitting(true); if (editingPedido) updateMutation.mutate({ id: editingPedido.id, data }); else createMutation.mutate(data) }
  const handleStatusSubmit = (data: any) => { setIsSubmitting(true); statusMutation.mutate({ id: editingPedido?.id, data }) }

  const openCreateDialog = () => { setEditingPedido(null); form.reset({ quantidade: 1, status: 'pendente' }); setIsDialogOpen(true); }
  const openEditDialog = (pedido: any) => { setEditingPedido(pedido); form.reset({ polo_id: pedido.polo_id, escola_id: pedido.escola_id, materia_id: pedido.materia_id, quantidade: pedido.quantidade, observacao: pedido.observacao }); setIsDialogOpen(true); }
  const openStatusDialog = (pedido: any) => { setEditingPedido(pedido); statusForm.reset({ status: pedido.status, observacao: '' }); setIsStatusDialogOpen(true); }
  const handleDelete = (id: string) => { if (confirm('Cancelar pedido?')) { toast.success('Pedido cancelado!'); } }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Logística - Pedidos de Livros</h1><p className="text-muted-foreground">Gerenciamento de pedidos de livros dos polos</p></div>
        <Button onClick={openCreateDialog}><Plus className="mr-2 h-4 w-4" />Novo Pedido</Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Pedidos de Livros</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="pendente">Pendente</SelectItem>
                  <SelectItem value="enviado">Enviado</SelectItem>
                  <SelectItem value="entregue">Entregue</SelectItem>
                  <SelectItem value="cancelado">Cancelado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>Polo</TableHead><TableHead>Escola</TableHead><TableHead>Matéria</TableHead><TableHead>Qtd</TableHead><TableHead>Status</TableHead><TableHead>Solicitado por</TableHead><TableHead>Data</TableHead><TableHead className="text-right">Ações</TableHead></TableRow></TableHeader>
                <TableBody>
                  {pedidosData?.items.map(pedido => (
                    <TableRow key={pedido.id}>
                      <TableCell className="font-mono text-xs">{pedido.id.slice(0,8)}...</TableCell>
                      <TableCell>{pedido.polo_nome || '—'}</TableCell>
                      <TableCell>{pedido.escola_nome || '—'}</TableCell>
                      <TableCell>{pedido.materia_nome || '—'}</TableCell>
                      <TableCell className="font-mono">{pedido.quantidade}</TableCell>
                      <TableCell><Badge variant={getStatusColor(pedido.status) as any}>{pedido.status}</Badge></TableCell>
                      <TableCell>{pedido.solicitado_por_nome || '—'}</TableCell>
                      <TableCell>{pedido.criado_em ? formatDate(pedido.criado_em) : '—'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => openEditDialog(pedido)}><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => openStatusDialog(pedido)}><Truck className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(pedido.id)}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-muted-foreground">Paginação...</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)}>Próximo</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingPedido ? 'Editar Pedido' : 'Novo Pedido'}</DialogTitle></DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <FormField control={form.control} name="polo_id" render={({field})=>(<FormItem><FormLabel>Polo</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{polosData?.items.map(p=>(<SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
              <FormField control={form.control} name="escola_id" render={({field})=>(<FormItem><FormLabel>Escola</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{escolasData?.items.map(e=>(<SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
              <FormField control={form.control} name="materia_id" render={({field})=>(<FormItem><FormLabel>Matéria</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{materiasData?.items.map(m=>(<SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
              <FormField control={form.control} name="quantidade" render={({field})=>(<FormItem><FormLabel>Quantidade *</FormLabel><FormControl><input type="number" {...field} className="w-full" min="1" /></FormControl></FormItem>)} />
              <FormField control={form.control} name="observacao" render={({field})=>(<FormItem><FormLabel>Observação</FormLabel><FormControl><textarea {...field} className="w-full" rows={3} /></FormControl></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Salvar'}</Button></DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isStatusDialogOpen} onOpenChange={setIsStatusDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Atualizar Status</DialogTitle></DialogHeader>
          <Form {...statusForm}>
            <form onSubmit={statusForm.handleSubmit(handleStatusSubmit)} className="space-y-4">
              <FormField control={statusForm.control} name="status" render={({field})=>(<FormItem><FormLabel>Status *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="pendente">Pendente</SelectItem><SelectItem value="enviado">Enviado</SelectItem><SelectItem value="entregue">Entregue</SelectItem><SelectItem value="cancelado">Cancelado</SelectItem></SelectContent></Select><FormMessage/></FormItem>)} />
              <FormField control={statusForm.control} name="observacao" render={({field})=>(<FormItem><FormLabel>Observação</FormLabel><FormControl><textarea {...field} className="w-full" rows={3} /></FormControl></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsStatusDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Atualizar'}</Button></DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate, getStatusColor } from '@/lib/utils'
import { Loader2 } from 'lucide-react'