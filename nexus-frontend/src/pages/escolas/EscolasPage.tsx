'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Building2, MapPin, Download, GraduationCap, Filter, Package, ChevronRight, Eye } from 'lucide-react'
import { api } from '@/lib/api'
import { Escola, PaginatedResponse, Polo } from '@/types'
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
import { formatCurrency, formatCPF, formatDate, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'

const escolaSchema = z.object({
  nome: z.string().min(2, 'Nome da escola deve ter pelo menos 2 caracteres'),
  polo_id: z.string().min(1, 'Selecione um polo'),
  responsavel: z.string().min(2, 'Nome do responsavel/secretario e obrigatorio'),
  cpf: z.string().min(11, 'CPF invalido').max(14),
  email: z.string().email('E-mail invalido'),
  endereco: z.string().min(1, 'Endereco completo e obrigatorio'),
  senha: z.string().min(6, 'Senha deve ter pelo menos 6 caracteres'),
  logradouro: z.string().optional(),
  numero: z.string().optional(),
  bairro: z.string().optional(),
  cidade: z.string().optional(),
  uf: z.string().optional(),
  cep: z.string().optional(),
  status: z.enum(['ativo', 'inativo']).default('ativo'),
})

type EscolaFormData = z.infer<typeof escolaSchema>

export function EscolasPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [poloFilter, setPoloFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingEscola, setEditingEscola] = useState<any | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: escolasData, isLoading } = useQuery({
    queryKey: ['escolas', search, statusFilter, poloFilter, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<any>>('/operacional/escolas', {
      params: { q: search, status: statusFilter, polo_id: poloFilter, limit: pageSize, offset: (page - 1) * pageSize }
    }).then(r => r.data),
  })

  const { data: polosData } = useQuery({
    queryKey: ['polos-select'],
    queryFn: () => api.get('/polos', { params: { limit: 1000 } }).then(r => r.data.items),
  })

  const createMutation = useMutation({
    mutationFn: (data: EscolaFormData) => api.post<any>('/operacional/escolas', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escolas'] })
      toast.success('Escola criada com sucesso!')
      setIsDialogOpen(false)
    },
    onError: (error) => toast.error(error.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EscolaFormData> }) => api.put<any>(`/operacional/escolas/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escolas'] })
      toast.success('Escola atualizada com sucesso!')
      setIsDialogOpen(false)
      setEditingEscola(null)
    },
    onError: (error) => toast.error(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/escolas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escolas'] })
      toast.success('Escola desativada com sucesso')
    },
    onError: (error) => toast.error(error.message),
  })

  const form = useForm<EscolaFormData>({
    resolver: zodResolver(escolaSchema),
    defaultValues: {
      status: 'ativo',
    },
  })

  const handleSubmit = (data: EscolaFormData) => {
    setIsSubmitting(true)
    if (editingEscola) {
      updateMutation.mutate({ id: editingEscola.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const openCreateDialog = () => {
    setEditingEscola(null)
    form.reset({ status: 'ativo' })
    setIsDialogOpen(true)
  }

  const openEditDialog = (escola: any) => {
    setEditingEscola(escola)
    form.reset({
      nome: escola.nome,
      polo_id: escola.polo_id,
      responsavel: escola.responsavel,
      cpf: formatCPF(escola.cpf),
      email: escola.email,
      endereco: escola.endereco,
      logradouro: escola.logradouro || '',
      numero: escola.numero || '',
      bairro: escola.bairro || '',
      cidade: escola.cidade || '',
      uf: escola.uf || '',
      cep: escola.cep || '',
      status: escola.status,
      senha: '',
    })
    setIsDialogOpen(true)
  }

  const handleDelete = (id: string) => {
    if (confirm('Tem certeza que deseja desativar esta escola? O secretario vinculado tambem sera desativado.')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Escolas</h1>
          <p className="text-muted-foreground">Gerenciamento de escolas e secretarios (RN-01)</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Nova Escola
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Lista de Escolas</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input placeholder="Buscar por nome, responsavel, CPF ou e-mail..." value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="inativo">Inativo</SelectItem>
                </SelectContent>
              </Select>
              <Select value={poloFilter} onValueChange={setPoloFilter}>
                <SelectTrigger className="w-[200px]"><SelectValue placeholder="Filtrar por Polo" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos os Polos</SelectItem>
                  {polosData?.items.map((polo) => <SelectItem key={polo.id} value={polo.id}>{polo.nome}</SelectItem>)}
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
                    <TableHead>Nome</TableHead>
                    <TableHead>Polo</TableHead>
                    <TableHead>Responsavel/Secretario</TableHead>
                    <TableHead>CPF</TableHead>
                    <TableHead>E-mail</TableHead>
                    <TableHead>Cidade/UF</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {escolasData?.items.length === 0 ? (
                    <TableRow><TableCell colSpan={8} className="text-center py-8 text-muted-foreground">Nenhuma escola encontrada</TableCell></TableRow>
                  ) : (
                    escolasData?.items.map((escola) => (
                      <TableRow key={escola.id}>
                        <TableCell className="font-medium">{escola.nome}</TableCell>
                        <TableCell>{escola.polo_nome || '---'}</TableCell>
                        <TableCell>{escola.responsavel}</TableCell>
                        <TableCell>{formatCPF(escola.cpf)}</TableCell>
                        <TableCell>{escola.email}</TableCell>
                        <TableCell>{escola.cidade} - {escola.uf}</TableCell>
                        <TableCell><Badge variant={escola.status === 'ativo' ? 'default' : 'secondary'}>{escola.status}</Badge></TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(escola)} aria-label="Editar"><Edit className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDelete(escola.id)} aria-label="Excluir" className="text-destructive hover:text-destructive"><Trash2 className="h-4 w-4" /></Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}

          {escolasData && escolasData.total > pageSize && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">Mostrando {((page - 1) * pageSize) + 1} a {Math.min(page * pageSize, escolasData.total)} de {escolasData.total} escolas</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (escolasData?.total || 0)}>Proximo</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editingEscola ? 'Editar Escola' : 'Nova Escola'}</DialogTitle></DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField control={form.control} name="nome" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome da Escola *</FormLabel>
                    <FormControl><input {...field} className="w-full" placeholder="Nome da Escola" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="polo_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Polo Vinculado *</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <SelectTrigger><SelectValue placeholder="Selecione o polo" /></SelectTrigger>
                      <SelectContent>{polosData?.items.map((polo) => <SelectItem key={polo.id} value={polo.id}>{polo.nome}</SelectItem>)}</SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="responsavel" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Responsavel/Secretario *</FormLabel>
                    <FormControl><input {...field} className="w-full" placeholder="Nome completo do secretario" /></FormControl>
                    <FormDescription>Este sera o nome do usuario secretario criado automaticamente (RN-01)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="cpf" render={({ field }) => (
                  <FormItem>
                    <FormLabel>CPF *</FormLabel>
                    <FormControl><input {...field} placeholder="000.000.000-00" className="w-full" maxLength={14} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="email" render={({ field }) => (
                  <FormItem>
                    <FormLabel>E-mail *</FormLabel>
                    <FormControl><input type="email" {...field} className="w-full" placeholder="secretario@email.com" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="senha" render={({ field }) => (
                  <FormItem>
                    <FormLabel>{editingEscola ? 'Nova Senha (deixe em branco para manter)' : 'Senha *'} </FormLabel>
                    <FormControl><input type="password" {...field} className="w-full" placeholder={editingEscola ? 'Deixe em branco para manter a senha atual' : 'Minimo 6 caracteres'} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="status" render={({ field }) => (
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

              <div className="border-t pt-4">
                <h4 className="font-medium mb-3">Endereco da Escola</h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <FormField control={form.control} name="endereco" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Endereco Completo *</FormLabel>
                      <FormControl><input {...field} className="w-full" placeholder="Rua, numero, bairro" /></FormControl>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <div className="md:col-span-2">
                    <FormField control={form.control} name="logradouro" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Logradouro</FormLabel>
                        <FormControl><input {...field} className="w-full" placeholder="Rua/Avenida" /></FormControl>
                      </FormItem>
                    )} />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-4">
                  <FormField control={form.control} name="numero" render={({ field }) => (
                    <FormItem><FormLabel>Numero</FormLabel><FormControl><input {...field} className="w-full" placeholder="123" /></FormControl></FormItem>
                  )} />
                  <FormField control={form.control} name="bairro" render={({ field }) => (
                    <FormItem><FormLabel>Bairro</FormLabel><FormControl><input {...field} className="w-full" placeholder="Centro" /></FormControl></FormItem>
                  )} />
                  <FormField control={form.control} name="cidade" render={({ field }) => (
                    <FormItem><FormLabel>Cidade</FormLabel><FormControl><input {...field} className="w-full" placeholder="Sao Paulo" /></FormControl></FormItem>
                  )} />
                  <FormField control={form.control} name="uf" render={({ field }) => (
                    <FormItem><FormLabel>UF</FormLabel><FormControl><input {...field} className="w-full" placeholder="SP" maxLength={2} /></FormControl></FormItem>
                  )} />
                </div>
                <FormField control={form.control} name="cep" render={({ field }) => (
                  <FormItem><FormLabel>CEP</FormLabel><FormControl><input {...field} className="w-full" placeholder="00000-000" maxLength={9} /></FormControl></FormItem>
                )} />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancelar</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}