'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Eye, Building2, MapPin, Download, GraduationCap, Package } from 'lucide-react'
import { api } from '@/lib/api'
import { Polo, PaginatedResponse, PoloDetalheResponse } from '@/types'
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
import { formatCurrency, formatCPF } from '@/lib/utils'
import toast from 'react-hot-toast'

const poloSchema = z.object({
  nome: z.string().min(2, 'Nome do polo deve ter pelo menos 2 caracteres'),
  responsavel: z.string().min(1, 'Nome do responsável/coordenador é obrigatório'),
  cpf: z.string().min(11, 'CPF inválido').max(14),
  email: z.string().email('E-mail inválido'),
  endereco: z.string().min(1, 'Endereço completo é obrigatório'),
  senha: z.string().min(6, 'Senha deve ter pelo menos 6 caracteres'),
  logradouro: z.string().optional(),
  numero: z.string().optional(),
  bairro: z.string().optional(),
  cidade: z.string().optional(),
  uf: z.string().optional(),
  cep: z.string().optional(),
  status: z.enum(['ativo', 'inativo']).default('ativo'),
})

type PoloFormData = z.infer<typeof poloSchema>

export function PolosPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [poloFilter, setPoloFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingPolo, setEditingPolo] = useState<Polo | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: polosData, isLoading } = useQuery({
    queryKey: ['polos', search, statusFilter, poloFilter, page, pageSize],
    queryFn: () => api.get<PaginatedResponse<Polo>>('/operacional/polos', {
      params: { q: search, status: statusFilter, polo_id: poloFilter, limit: pageSize, offset: (page - 1) * pageSize }
    }).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: PoloFormData) => api.post<Polo>('/operacional/polos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['polos'] })
      toast.success('Polo criado com sucesso!')
      setIsDialogOpen(false)
    },
    onError: (error) => toast.error(error.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PoloFormData> }) => api.put<Polo>(`/operacional/polos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['polos'] })
      toast.success('Polo atualizado com sucesso!')
      setIsDialogOpen(false)
      setEditingPolo(null)
    },
    onError: (error) => toast.error(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/operacional/polos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['polos'] })
      toast.success('Polo desativado com sucesso')
    },
    onError: (error) => toast.error(error.message),
  })

  const form = useForm<PoloFormData>({
    resolver: zodResolver(poloSchema),
    defaultValues: {
      status: 'ativo',
    },
  })

  const handleSubmit = (data: PoloFormData) => {
    setIsSubmitting(true)
    if (editingPolo) {
      updateMutation.mutate({ id: editingPolo.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const openCreateDialog = () => {
    setEditingPolo(null)
    form.reset({ status: 'ativo' })
    setIsDialogOpen(true)
  }

  const openEditDialog = (polo: Polo) => {
    setEditingPolo(polo)
    form.reset({
      nome: polo.nome,
      responsavel: polo.responsavel,
      cpf: formatCPF(polo.cpf),
      email: polo.email,
      endereco: polo.endereco,
      logradouro: polo.logradouro || '',
      numero: polo.numero || '',
      bairro: polo.bairro || '',
      cidade: polo.cidade || '',
      uf: polo.uf || '',
      cep: polo.cep || '',
      status: polo.status,
      senha: '',
    })
    setIsDialogOpen(true)
  }

  const handleDelete = (id: string) => {
    if (confirm('Tem certeza que deseja desativar este polo? O coordenador vinculado também será desativado.')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Polos</h1>
          <p className="text-muted-foreground">Gerenciamento de polos e coordenadores (RN-01)</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Novo Polo
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle>Lista de Polos</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Input
                placeholder="Buscar por nome, responsável, CPF ou e-mail..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-64"
              />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="inativo">Inativo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>Responsável/Coordenador</TableHead>
                    <TableHead>CPF</TableHead>
                    <TableHead>E-mail</TableHead>
                    <TableHead>Cidade/UF</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {polosData?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        Nenhum polo encontrado
                      </TableCell>
                    </TableRow>
                  ) : (
                    polosData?.items.map((polo) => (
                      <TableRow key={polo.id}>
                        <TableCell className="font-medium">{polo.nome}</TableCell>
                        <TableCell>{polo.responsavel}</TableCell>
                        <TableCell>{formatCPF(polo.cpf)}</TableCell>
                        <TableCell>{polo.email}</TableCell>
                        <TableCell>
                          {polo.cidade} - {polo.uf}
                        </TableCell>
                        <TableCell>
                          <Badge variant={polo.status === 'ativo' ? 'default' : 'secondary'}>
                            {polo.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(polo)} aria-label="Editar">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDelete(polo.id)} aria-label="Excluir" className="text-destructive hover:text-destructive">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}

          {polosData && polosData.total > pageSize && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Mostrando {((page - 1) * pageSize) + 1} a {Math.min(page * pageSize, polosData.total)} de {polosData.total} polos
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                  Anterior
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= (polosData?.total || 0)}>
                  Próximo
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingPolo ? 'Editar Polo' : 'Novo Polo'}</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="nome"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nome do Polo *</FormLabel>
                      <FormControl>
                        <input {...field} className="w-full" placeholder="Nome do polo" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="responsavel"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Responsável/Coordenador *</FormLabel>
                      <FormControl>
                        <input {...field} className="w-full" placeholder="Nome completo do coordenador" />
                      </FormControl>
                      <FormDescription>Este será o nome do usuário coordenador criado automaticamente (RN-01)</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="cpf"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>CPF *</FormLabel>
                      <FormControl>
                        <input {...field} placeholder="000.000.000-00" className="w-full" maxLength={14} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>E-mail *</FormLabel>
                      <FormControl>
                        <input type="email" {...field} className="w-full" placeholder="coordenador@email.com" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="senha"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{editingPolo ? 'Nova Senha (deixe em branco para manter)' : 'Senha *'} </FormLabel>
                      <FormControl>
                        <input type="password" {...field} className="w-full" placeholder={editingPolo ? 'Deixe em branco para manter a senha atual' : 'Mínimo 6 caracteres'} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ativo">Ativo</SelectItem>
                          <SelectItem value="inativo">Inativo</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="border-t pt-4">
                <h4 className="font-medium mb-3">Endereço do Polo</h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="endereco"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Endereço Completo *</FormLabel>
                        <FormControl>
                          <input {...field} className="w-full" placeholder="Rua, número, bairro" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="md:col-span-2">
                    <FormField
                      control={form.control}
                      name="logradouro"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Logradouro</FormLabel>
                          <FormControl>
                            <input {...field} className="w-full" placeholder="Rua/Avenida" />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-4">
                  <FormField
                    control={form.control}
                    name="numero"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Número</FormLabel>
                        <FormControl>
                          <input {...field} className="w-full" placeholder="123" />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="bairro"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Bairro</FormLabel>
                        <FormControl>
                          <input {...field} className="w-full" placeholder="Centro" />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="cidade"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Cidade</FormLabel>
                        <FormControl>
                          <input {...field} className="w-full" placeholder="São Paulo" />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="uf"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>UF</FormLabel>
                        <FormControl>
                          <input {...field} className="w-full" placeholder="SP" maxLength={2} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="cep"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>CEP</FormLabel>
                      <FormControl>
                        <input {...field} className="w-full" placeholder="00000-000" maxLength={9} />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Salvar'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}