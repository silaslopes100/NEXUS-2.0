'use client'

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Building2, User, Mail, Calendar, MapPin, GraduationCap, Award, FileText, Clock, AlertCircle, Shield, Users, TrendingUp } from 'lucide-react'
import { api } from '@/lib/api'
import { Escola, PaginatedResponse, Aluno } from '@/types'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatDate, formatDateTime, formatCPF, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'

export function EscolaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'perfil' | 'alunos' | 'historico'>('perfil')

  const { data: escola, isLoading, error } = useQuery({
    queryKey: ['escola', id],
    queryFn: () => api.get<any>(`/operacional/escolas/${id}`).then(r => r.data),
    enabled: !!id,
  })

  const { data: alunosData } = useQuery({
    queryKey: ['alunos', 'escola', id],
    queryFn: () => api.get<PaginatedResponse<any>>('/alunos', { params: { escola_id: id, limit: 100 } }).then(r => r.data),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !escola) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Escola não encontrada</h2>
        <p className="text-muted-foreground">A escola solicitada não foi encontrada.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Building2 className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{escola.nome}</h1>
            <p className="text-muted-foreground">{escola.email}</p>
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span><Badge variant={escola.status === 'ativo' ? 'success' : 'secondary'}>{escola.status}</Badge></span>
              {escola.polo_nome && <span><Building2 className="mr-1 h-3 w-3 inline" /> {escola.polo_nome}</span>}
            </div>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="perfil"><Building2 className="mr-2 h-4 w-4" />Perfil</TabsTrigger>
          <TabsTrigger value="alunos"><Users className="mr-2 h-4 w-4" />Alunos ({alunosData?.total || 0})</TabsTrigger>
          <TabsTrigger value="historico"><FileText className="mr-2 h-4 w-4" />Histórico</TabsTrigger>
        </TabsList>

        <TabsContent value="perfil" className="space-y-4 pt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div><label className="text-sm text-muted-foreground">Nome</label><p className="font-medium">{escola.nome}</p></div>
            <div><label className="text-sm text-muted-foreground">Responsável/Secretário</label><p>{escola.responsavel}</p></div>
            <div><label className="text-sm text-muted-foreground">CPF</label><p>{escola.cpf ? formatCPF(escola.cpf) : '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">E-mail</label><p>{escola.email || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Polo</label><p>{escola.polo_nome || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Usuário do Secretário</label><p>{escola.usuario_nome || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">E-mail do Usuário</label><p>{escola.usuario_email || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Status</label><p><Badge className={getStatusColor(escola.status)}>{escola.status}</Badge></p></div>
            <div><label className="text-sm text-muted-foreground">Total de Alunos</label><p>{escola.total_alunos || 0}</p></div>
            <div><label className="text-sm text-muted-foreground">Criado em</label><p>{escola.criado_em ? formatDate(escola.criado_em) : '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Atualizado em</label><p>{escola.atualizado_em ? formatDate(escola.atualizado_em) : '—'}</p></div>
          </div>
          <div className="border-t pt-4">
            <h4 className="font-medium mb-3">Endereço</h4>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="text-sm text-muted-foreground">Endereço Completo</label><p>{escola.endereco || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">Logradouro</label><p>{escola.logradouro || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">Número</label><p>{escola.numero || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">Bairro</label><p>{escola.bairro || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">Cidade</label><p>{escola.cidade || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">UF</label><p>{escola.uf || '—'}</p></div>
              <div><label className="text-sm text-muted-foreground">CEP</label><p>{escola.cep || '—'}</p></div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="alunos" className="pt-4">
          {alunosData?.items?.length ? (
            <Card>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nome</TableHead>
                        <TableHead>CPF</TableHead>
                        <TableHead>E-mail</TableHead>
                        <TableHead>Modalidade</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {alunosData.items.map(aluno => (
                        <TableRow key={aluno.id}>
                          <TableCell className="font-medium">{aluno.nome} {aluno.sobrenome}</TableCell>
                          <TableCell>{aluno.cpf ? formatCPF(aluno.cpf) : '—'}</TableCell>
                          <TableCell>{aluno.email || '—'}</TableCell>
                          <TableCell>
                            <Badge variant={aluno.modalidade === 'ead' ? 'default' : aluno.modalidade === 'polo' ? 'secondary' : 'outline'}>
                              {aluno.modalidade}
                            </Badge>
                          </TableCell>
                          <TableCell><Badge className={getStatusColor(aluno.status)}>{aluno.status}</Badge></TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="icon" aria-label="Ver aluno">
                              <FileText className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-8">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-1">Nenhum aluno encontrado</h3>
              <p className="text-muted-foreground">Esta escola ainda não possui alunos vinculados.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="historico" className="pt-4">
          <div className="p-4 border rounded-lg bg-muted/50">
            <h4 className="font-medium mb-2">Histórico de Alterações</h4>
            <p className="text-sm text-muted-foreground">Auditoria de alterações desta escola - TODO: implementar busca de logs de auditoria filtrados por escola</p>
            <div className="mt-4 space-y-2 text-sm text-muted-foreground">
              <p>• Criado em: {escola.criado_em ? formatDateTime(escola.criado_em) : '—'}</p>
              <p>• Última atualização: {escola.atualizado_em ? formatDateTime(escola.atualizado_em) : '—'}</p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { formatDate, formatDateTime, formatCPF, getStatusColor } from '@/lib/utils'