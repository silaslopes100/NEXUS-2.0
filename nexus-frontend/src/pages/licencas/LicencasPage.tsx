'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Package, ArrowUp, ArrowDown, Minus, DollarSign, Download } from 'lucide-react'
import { api } from '@/lib/api'
import { LicencaEstoque, Movimentacao, PaginatedResponse, Materia } from '@/types'
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

const ajusteSchema = z.object({
  materia_id: z.string().min(1, 'Selecione uma materia'),
  tipo: z.enum(['licenca', 'livro']),
  delta: z.number().int().min(-10000).max(10000).refine(v => v !== 0, 'Delta deve ser diferente de zero'),
  observacao: z.string().optional(),
})

type AjusteFormData = z.infer<typeof ajusteSchema>

export function LicencasPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isAjusteDialogOpen, setIsAjusteDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState<'estoque' | 'movimentacoes'>('estoque')

  const { data: estoqueData, isLoading: estoqueLoading } = useQuery({
    queryKey: ['licencas-estoque', search, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/licencas/estoque', { params: { query: search, limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: movimentacoesData } = useQuery({
    queryKey: ['licencas-movimentacoes', page, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/licencas/movimentacoes', { params: { limit: pageSize, offset: (page - 1) * pageSize } }).then(r => r.data),
  })

  const { data: materiasData } = useQuery({ queryKey: ['materias-select'], queryFn: () => api.get('/materias', { params: { limit: 1000 } }).then(r => r.data.items) })

  const ajusteSchema = z.object({
    materia_id: z.string().min(1, 'Selecione uma materia'),
    tipo: z.enum(['licenca', 'livro']),
    delta: z.number().int().min(-10000).max(10000).refine(v => v !== 0, 'Quantidade deve ser diferente de zero'),
    observacao: z.string().optional(),
  })

  type AjusteFormData = z.infer<typeof ajusteSchema>

  const createAjuste = useMutation({
    mutationFn: (data: AjusteFormData) => api.post('/operacional/licencas/ajustar', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['licencas-estoque'] })
      queryClient.invalidateQueries({ queryKey: ['licencas-movimentacoes'] })
      toast.success('Ajuste realizado com auditoria!')
      setIsAjusteDialogOpen(false)
    },
    onError: (e) => toast.error(e.message),
  })

  const ajusteForm = useForm<AjusteFormData>({ resolver: zodResolver(ajusteSchema), defaultValues: { tipo: 'licenca', delta: 1 } })

  const handleSubmit = (data: AjusteFormData) => {
    setIsSubmitting(true)
    createAjuste.mutate(data)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Licencas / Estoque</h1>
          <p className="text-muted-foreground">Dashboard de licencas/livros por materia, ajuste manual auditado (RN-04)</p>
        </div>
        <Button onClick={() => setIsAjusteDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Ajuste Manual (Auditoria)
        </Button>
      </div>

      <div className="flex gap-4 border-b mb-4">
        <button onClick={() => setActiveTab('estoque')} className={`px-4 py-2 text-sm font-medium border-b-2 ${activeTab === 'estoque' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          Estoque
        </button>
        <button onClick={() => setActiveTab('movimentacoes')} className={`px-4 py-2 text-sm font-medium border-b-2 ${activeTab === 'movimentacoes' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          Movimentacoes
        </button>
      </div>

      {activeTab === 'estoque' && (
        <Card>
          <CardHeader>
            <CardTitle>Estoque de Licencas e Livros</CardTitle>
          </CardHeader>
          <CardContent>
            {estoqueLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Materia</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Licencas</TableHead>
                      <TableHead className="text-right">Livros</TableHead>
                      <TableHead>Polo Destino</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {estoqueData?.items.map(e => (
                      <TableRow key={e.id}>
                        <TableCell className="font-medium">{e.materia_nome}</TableCell>
                        <TableCell><Badge variant="outline">{e.tipo}</Badge></TableCell>
                        <TableCell className="text-right font-mono">{e.quantidade}</TableCell>
                        <TableCell className="text-right font-mono">{e.quantidade}</TableCell>
                        <TableCell>{e.polo_destino_nome || '---'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            {estoqueData && estoqueData.total > pageSize && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">Paginacao...</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
                  <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (estoqueData?.total || 0)}>Proximo</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'movimentacoes' && (
        <Card>
          <CardHeader>
            <CardTitle>Historico de Movimentacoes (Auditoria)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Materia</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Tipo Movimento</TableHead>
                    <TableHead className="text-right">Quantidade</TableHead>
                    <TableHead>Polo</TableHead>
                    <TableHead>Usuario</TableHead>
                    <TableHead>Observacao</TableHead>
                    <TableHead>Data</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movimentacoesData?.items.map(m => (
                    <TableRow key={m.id}>
                      <TableCell>{m.materia_nome || '---'}</TableCell>
                      <TableCell><Badge variant="outline">{m.tipo}</Badge></TableCell>
                      <TableCell>
                        <Badge variant={m.tipo_movimento === 'entrada' ? 'success' : m.tipo_movimento === 'saida' ? 'destructive' : 'warning'}>
                          {m.tipo_movimento}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">{m.quantidade > 0 ? '+' : ''}{m.quantidade}</TableCell>
                      <TableCell>{m.polo_nome || '---'}</TableCell>
                      <TableCell>{m.usuario_nome || '---'}</TableCell>
                      <TableCell className="max-w-xs truncate">{m.observacao || '---'}</TableCell>
                      <TableCell>{m.criado_em ? formatDate(m.criado_em) : '---'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={isAjusteDialogOpen} onOpenChange={setIsAjusteDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Ajuste Manual de Estoque (Auditoria)</DialogTitle>
          </DialogHeader>
          <Form {...ajusteForm}>
            <form onSubmit={ajusteForm.handleSubmit(handleSubmit)} className="space-y-4">
              <FormField control={ajusteForm.control} name="materia_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Materia *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione" />
                    </SelectTrigger>
                    <SelectContent>
                      {materiasData?.items.map(m => (
                        <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={ajusteForm.control} name="tipo" render={({ field }) => (
                <FormItem>
                  <FormLabel>Tipo *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="licenca">Licenca</SelectItem>
                      <SelectItem value="livro">Livro</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )} />
              <FormField control={ajusteForm.control} name="delta" render={({ field }) => (
                <FormItem>
                  <FormLabel>Quantidade (positivo=entrada, negativo=saida) *</FormLabel>
                  <FormControl>
                    <input type="number" {...field} className="w-full" step="1" min="-10000" max="10000" />
                  </FormControl>
                  <FormDescription>Use numeros negativos para saidas, positivos para entradas</FormDescription>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={ajusteForm.control} name="observacao" render={({ field }) => (
                <FormItem>
                  <FormLabel>Observacao (obrigatoria para auditoria)</FormLabel>
                  <FormControl>
                    <textarea {...field} className="w-full" rows={3} placeholder="Motivo do ajuste..." />
                  </FormControl>
                </FormItem>
              )} />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsAjusteDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Registrar Ajuste'}
                </Button>
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
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate } from '@/lib/utils'
import { Loader2 } from 'lucide-react'