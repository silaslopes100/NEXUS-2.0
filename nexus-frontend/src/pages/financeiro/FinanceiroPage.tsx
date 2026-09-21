'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, CreditCard, Download, FileText, DollarSign, Truck, Calendar, Filter } from 'lucide-react'
import { api } from '@/lib/api'
import { Venda, Boleto, PaginatedResponse, Polo, Escola } from '@/types'
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
import { formatCurrency, formatDate, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const vendaSchema = z.object({
  polo_id: z.string().optional(),
  escola_id: z.string().optional(),
  aluno_id: z.string().optional(),
  modalidade: z.enum(['polo', 'escola', 'ead']),
  valor: z.number().min(0.01, 'Valor deve ser maior que zero'),
  forma_pagamento: z.string().min(1, 'Forma de pagamento obrigatória'),
  status: z.enum(['paga', 'pendente', 'cancelada', 'estornada']).default('paga'),
})

type VendaFormData = z.infer<typeof vendaSchema>

const boletoSchema = z.object({
  venda_id: z.string().optional(),
  valor: z.number().min(0.01, 'Valor deve ser maior que zero'),
  data_vencimento: z.string().min(1, 'Data de vencimento obrigatória'),
  polo_id: z.string().optional(),
})

type BoletoFormData = z.infer<typeof boletoSchema>

export function FinanceiroPage() {
  const queryClient = useQueryClient()
  const [vendasPage, setVendasPage] = useState(1)
  const [boletosPage, setBoletosPage] = useState(1)
  const [pageSize] = useState(10)
  const [isVendaDialogOpen, setIsVendaDialogOpen] = useState(false)
  const [isBoletoDialogOpen, setIsBoletoDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState<'vendas' | 'boletos'>('vendas')

  const { data: vendasData, isLoading: vendasLoading } = useQuery({
    queryKey: ['vendas', vendasPage, pageSize],
    queryFn: () => api.get<any>('/financeiro/vendas', { params: { limit: pageSize, offset: (vendasPage - 1) * pageSize } }).then(r => r.data),
  })

  const { data: boletosData } = useQuery({
    queryKey: ['boletos', boletosPage, pageSize],
    queryFn: () => api.get<any[]>('/financeiro/boletos', { params: { limit: pageSize, offset: (boletosPage - 1) * pageSize } }).then(r => r.data),
  })

  const { data: polosData } = useQuery({ queryKey: ['polos-select'], queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items) })
  const { data: escolasData } = useQuery({ queryKey: ['escolas-select'], queryFn: () => api.get('/escolas', { params: { limit: 1000 } }).then(r => r.data.items) })

  const createVenda = useMutation({ mutationFn: (data: any) => api.post('/financeiro/vendas', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['vendas'] }); toast.success('Venda registrada!'); setIsVendaDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const createBoleto = useMutation({ mutationFn: (data: any) => api.post('/financeiro/boletos', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['boletos'] }); toast.success('Boleto gerado (stub AsaaS)!'); setIsBoletoDialogOpen(false); }, onError: (e) => toast.error(e.message) })

  const vendaForm = useForm<any>({ resolver: zodResolver(vendaSchema), defaultValues: { modalidade: 'polo', status: 'paga', forma_pagamento: 'dinheiro' } })
  const boletoForm = useForm<any>({ resolver: zodResolver(boletoSchema), defaultValues: { status: 'gerado' } })

  const handleVendaSubmit = (data: any) => { setIsSubmitting(true); createVenda.mutate(data) }
  const handleBoletoSubmit = (data: any) => { setIsSubmitting(true); createBoleto.mutate(data) }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Financeiro</h1><p className="text-muted-foreground">Vendas, relatórios PDF, boletos (AsaaS stub)</p></div>
        <div className="flex gap-2">
          <Button onClick={() => { vendaForm.reset({ modalidade: 'polo', status: 'paga', forma_pagamento: 'dinheiro' }); setIsVendaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Venda</Button>
          <Button onClick={() => { boletoForm.reset({ status: 'gerado' }); setIsBoletoDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Gerar Boleto</Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList><TabsTrigger value="vendas">Vendas</TabsTrigger><TabsTrigger value="boletos">Boletos (AsaaS Stub)</TabsTrigger></TabsList>

        <TabsContent value="vendas">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Vendas</CardTitle>
              <Button onClick={() => { vendaForm.reset({ modalidade: 'polo', status: 'paga', forma_pagamento: 'dinheiro' }); setIsVendaDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nova Venda</Button>
            </CardHeader>
            <CardContent>
              {vendasLoading ? <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>Polo/Escola</TableHead><TableHead>Aluno</TableHead><TableHead>Modalidade</TableHead><TableHead>Valor</TableHead><TableHead>Forma Pagamento</TableHead><TableHead>Status</TableHead><TableHead>Data</TableHead><TableHead className="text-right">Ações</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {vendasData?.items.map(v => (
                        <TableRow key={v.id}>
                          <TableCell className="font-mono text-xs">{v.id.slice(0,8)}...</TableCell>
                          <TableCell>{v.polo_nome || v.escola_nome || '—'}</TableCell>
                          <TableCell>{v.aluno_nome || '—'}</TableCell>
                          <TableCell><Badge variant="outline">{v.modalidade}</Badge></TableCell>
                          <TableCell className="font-mono text-right">{formatCurrency(v.valor)}</TableCell>
                          <TableCell>{v.forma_pagamento}</TableCell>
                          <TableCell><Badge className={getStatusColor(v.status)}>{v.status}</Badge></TableCell>
                          <TableCell>{v.criado_em ? formatDate(v.criado_em) : '—'}</TableCell>
                          <TableCell className="text-right"><Button variant="ghost" size="icon" className="text-destructive"><Trash2 className="h-4 w-4" /></Button></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">Total: {formatCurrency(vendasData?.total_valor || 0)}</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setVendasPage(p => Math.max(1, p - 1))} disabled={vendasPage === 1}>Anterior</Button>
                  <Button variant="outline" size="sm" onClick={() => setVendasPage(p => p + 1)}>Próximo</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="boletos">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Boletos (AsaaS Stub)</CardTitle>
              <Button onClick={() => { boletoForm.reset({ status: 'gerado' }); setIsBoletoDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Gerar Boleto</Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>Venda</TableHead><TableHead>Valor</TableHead><TableHead>Vencimento</TableHead><TableHead>Status</TableHead><TableHead>Nosso Número</TableHead><TableHead>Asaas ID</TableHead><TableHead>Link PDF</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {boletosData?.map(b => (
                      <TableRow key={b.id}>
                        <TableCell className="font-mono text-xs">{b.id.slice(0,8)}...</TableCell>
                        <TableCell>{b.venda_id ? b.venda_id.slice(0,8) : '—'}</TableCell>
                        <TableCell className="font-mono text-right">{formatCurrency(b.valor)}</TableCell>
                        <TableCell>{b.data_vencimento ? formatDate(b.data_vencimento) : '—'}</TableCell>
                        <TableCell><Badge variant="outline">{b.status}</Badge></TableCell>
                        <TableCell className="font-mono text-xs">{b.nosso_numero || '—'}</TableCell>
                        <TableCell className="font-mono text-xs">{b.asaas_id || '—'}</TableCell>
                        <TableCell>{b.link_pdf ? <a href={b.link_pdf} target="_blank" className="text-primary underline">PDF</a> : '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isVendaDialogOpen} onOpenChange={setIsVendaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Nova Venda</DialogTitle></DialogHeader>
          <Form {...vendaForm}>
            <form onSubmit={vendaForm.handleSubmit(handleVendaSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={vendaForm.control} name="polo_id" render={({field})=>(<FormItem><FormLabel>Polo</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{polosData?.items.map(p=>(<SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
                <FormField control={vendaForm.control} name="escola_id" render={({field})=>(<FormItem><FormLabel>Escola</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{escolasData?.items.map(e=>(<SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
              </div>
              <FormField control={vendaForm.control} name="modalidade" render={({field})=>(<FormItem><FormLabel>Modalidade *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="polo">Polo</SelectItem><SelectItem value="escola">Escola</SelectItem><SelectItem value="ead">EAD</SelectItem></SelectContent></Select><FormMessage/></FormItem>)} />
              <FormField control={vendaForm.control} name="valor" render={({field})=>(<FormItem><FormLabel>Valor *</FormLabel><FormControl><input type="number" {...field} className="w-full" step="0.01" min="0.01" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={vendaForm.control} name="forma_pagamento" render={({field})=>(<FormItem><FormLabel>Forma de Pagamento *</FormLabel><FormControl><input {...field} className="w-full" placeholder="dinheiro, cartão, pix, boleto" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={vendaForm.control} name="status" render={({field})=>(<FormItem><FormLabel>Status</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="paga">Paga</SelectItem><SelectItem value="pendente">Pendente</SelectItem><SelectItem value="cancelada">Cancelada</SelectItem><SelectItem value="estornada">Estornada</SelectItem></SelectContent></Select></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsVendaDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Salvar'}</Button></DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={isBoletoDialogOpen} onOpenChange={setIsBoletoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Gerar Boleto (AsaaS Stub)</DialogTitle></DialogHeader>
          <Form {...boletoForm}>
            <form onSubmit={boletoForm.handleSubmit(handleBoletoSubmit)} className="space-y-4">
              <FormField control={boletoForm.control} name="valor" render={({field})=>(<FormItem><FormLabel>Valor *</FormLabel><FormControl><input type="number" {...field} className="w-full" step="0.01" min="0.01" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={boletoForm.control} name="data_vencimento" render={({field})=>(<FormItem><FormLabel>Data Vencimento *</FormLabel><FormControl><input type="date" {...field} className="w-full" /></FormControl><FormMessage/></FormItem>)} />
              <FormField control={boletoForm.control} name="polo_id" render={({field})=>(<FormItem><FormLabel>Polo</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent>{polosData?.items.map(p=>(<SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>))}</SelectContent></Select></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsBoletoDialogOpen(false)}>Cancelar</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting?<Loader2 className="mr-2 h-4 w-4 animate-spin"/>:'Gerar Boleto'}</Button></DialogFooter>
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
import { formatDate, formatCurrency, getStatusColor } from '@/lib/utils'
import { Loader2 } from 'lucide-react'