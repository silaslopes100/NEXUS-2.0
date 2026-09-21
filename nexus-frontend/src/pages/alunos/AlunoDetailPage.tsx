'use client'

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, User, Mail, Lock, Calendar, MapPin, GraduationCap, Building2, Award, FileText, Clock, AlertCircle, CheckCircle, XCircle, Shield, Key, Camera, Eye, EyeOff, Package, FileText as FileTextIcon, Clock as ClockIcon, GraduationCap as GradCap } from 'lucide-react'
import { api } from '@/lib/api'
import { AlunoDetalheResponse } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Form, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage, useForm } from '@/components/ui/form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatDate, formatDateTime, formatCPF, getInitials, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'

export function AlunoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'perfil' | 'historico' | 'presencas' | 'notas' | 'certificados'>('perfil')

  const { data: aluno, isLoading, error } = useQuery({
    queryKey: ['aluno', id],
    queryFn: () => api.get<any>(`/alunos/${id}`).then(r => r.data),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !aluno) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Aluno não encontrado</h2>
        <p className="text-muted-foreground">O aluno solicitado não foi encontrado.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            {aluno.foto_url ? (
              <img src={aluno.foto_url} alt={aluno.nome} className="w-full h-full object-cover rounded-full" />
            ) : (
              <span className="text-2xl font-bold text-primary">{getInitials(aluno.nome)}</span>
            )}
          </div>
          <div>
            <h1 className="text-3xl font-bold">{aluno.nome} {aluno.sobrenome}</h1>
            <p className="text-muted-foreground">{aluno.email}</p>
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span><Badge variant="outline">{aluno.modalidade}</Badge></span>
              {aluno.polo_nome && <span><Building2 className="mr-1 h-3 w-3 inline" /> {aluno.polo_nome}</span>}
              {aluno.escola_nome && <span><GraduationCap className="mr-1 h-3 w-3 inline" /> {aluno.escola_nome}</span>}
            </div>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="perfil"><User className="mr-2 h-4 w-4" />Perfil</TabsTrigger>
          <TabsTrigger value="historico"><FileTextIcon className="mr-2 h-4 w-4" />Histórico</TabsTrigger>
          <TabsTrigger value="presencas"><ClockIcon className="mr-2 h-4 w-4" />Presenças</TabsTrigger>
          <TabsTrigger value="notas"><GradCap className="mr-2 h-4 w-4" />Notas</TabsTrigger>
          <TabsTrigger value="certificados"><Award className="mr-2 h-4 w-4" />Certificados</TabsTrigger>
        </TabsList>

        <TabsContent value="perfil" className="space-y-4 pt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div><label className="text-sm text-muted-foreground">Nome</label><p className="font-medium">{aluno.nome} {aluno.sobrenome}</p></div>
            <div><label className="text-sm text-muted-foreground">CPF</label><p>{aluno.cpf ? aluno.cpf : '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">E-mail</label><p>{aluno.email || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Data Nascimento</label><p>{aluno.data_nascimento ? aluno.data_nascimento : '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Modalidade</label><p><Badge variant={aluno.modalidade === 'ead' ? 'default' : aluno.modalidade === 'polo' ? 'secondary' : 'outline'}>{aluno.modalidade}</Badge></p></div>
            <div><label className="text-sm text-muted-foreground">Polo</label><p>{aluno.polo_nome || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Escola</label><p>{aluno.escola_nome || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Curso</label><p>{aluno.curso_nome || '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Semestre/Ano</label><p>{aluno.semestre ? `${aluno.semestre}º semestre / ${aluno.ano}` : '—'}</p></div>
            <div><label className="text-sm text-muted-foreground">Status</label><p><Badge className={getStatusColor(aluno.status)}>{aluno.status}</Badge></p></div>
            <div><label className="text-sm text-muted-foreground">Matrícula</label><p>{aluno.numero_matricula || '—'}</p></div>
          </div>
          <div className="border-t pt-4">
            <h4 className="font-medium mb-2">Presenças por Matéria</h4>
            {aluno.presencas_por_materia?.length ? (
              <Table>
                <TableHeader><TableRow><TableHead>Matéria</TableHead><TableHead>Aulas Previstas</TableHead><TableHead>Presenças</TableHead><TableHead>%</TableHead></TableRow></TableHeader>
                <TableBody>
                  {aluno.presencas_por_materia.map(p => (
                    <TableRow key={p.materia_id}><TableCell>{p.materia_nome}</TableCell><TableCell>{p.total_aulas_previstas}</TableCell><TableCell>{p.presencas}</TableCell><TableCell><Badge variant={p.percentual >= 75 ? 'success' : p.percentual >= 50 ? 'warning' : 'destructive'}>{p.percentual}%</Badge></TableCell></TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : <p className="text-muted-foreground">Nenhuma presença registrada</p>}
          </div>
        </TabsContent>

        <TabsContent value="historico" className="pt-4">
          {aluno.notas?.length ? (
            <Table>
              <TableHeader><TableRow><TableHead>Matéria</TableHead><TableHead>Nota</TableHead><TableHead>Tipo</TableHead><TableHead>Semestre</TableHead><TableHead>Ano</TableHead></TableRow></TableHeader>
              <TableBody>{aluno.notas.map(n => (<TableRow key={n.id}><TableCell>{n.materia_nome || '-'}</TableCell><TableCell>{n.nota}</TableCell><TableCell>{n.tipo}</TableCell><TableCell>{n.semestre}</TableCell><TableCell>{n.ano}</TableCell></TableRow>))}</TableBody>
            </Table>
          ) : <p className="text-muted-foreground">Nenhuma nota registrada</p>}
        </TabsContent>

        <TabsContent value="presencas" className="pt-4">
          {aluno.presencas_por_materia?.length ? (
            <Table>
              <TableHeader><TableRow><TableHead>Matéria</TableHead><TableHead>Aulas Previstas</TableHead><TableHead>Presenças</TableHead><TableHead>%</TableHead></TableRow></TableHeader>
              <TableBody>
                {aluno.presencas_por_materia.map(p => (
                  <TableRow key={p.materia_id}><TableCell>{p.materia_nome}</TableCell><TableCell>{p.total_aulas_previstas}</TableCell><TableCell>{p.presencas}</TableCell><TableCell><Badge variant={p.percentual >= 75 ? 'success' : p.percentual >= 50 ? 'warning' : 'destructive'}>{p.percentual}%</Badge></TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <p className="text-muted-foreground">Nenhuma presença registrada</p>}
        </TabsContent>

        <TabsContent value="notas" className="pt-4">
          {aluno.notas?.length ? (
            <Table>
              <TableHeader><TableRow><TableHead>Matéria</TableHead><TableHead>Nota</TableHead><TableHead>Tipo</TableHead><TableHead>Semestre</TableHead><TableHead>Ano</TableHead><TableHead>Data</TableHead></TableRow></TableHeader>
              <TableBody>{aluno.notas.map(n => (<TableRow key={n.id}><TableCell>{n.materia_nome || '-'}</TableCell><TableCell>{n.nota}</TableCell><TableCell>{n.tipo}</TableCell><TableCell>{n.semestre}</TableCell><TableCell>{n.ano}</TableCell><TableCell>{n.criado_em ? n.criado_em : '—'}</TableCell></TableRow>))}</TableBody>
            </Table>
          ) : <p className="text-muted-foreground">Nenhuma nota registrada</p>}
        </TabsContent>

        <TabsContent value="certificados" className="pt-4">
          {aluno.certificados?.length ? (
            <Table>
              <TableHeader><TableRow><TableHead>Título</TableHead><TableHead>Estágios</TableHead><TableHead>Histórico Completo</TableHead><TableHead>Data Emissão</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
              <TableBody>{aluno.certificados.map(c => (<TableRow key={c.id}><TableCell>{c.titulo}</TableCell><TableCell>{c.estagios_entregues.map(e => e.nome).join(', ')}</TableCell><TableCell>{c.historico_completo ? 'Sim' : 'Não'}</TableCell><TableCell>{c.data_emissao ? formatDate(c.data_emissao) : '—'}</TableCell><TableCell><Badge variant={c.status === 'emitido' ? 'success' : c.status === 'pendente' ? 'warning' : 'destructive'}>{c.status}</Badge></TableCell></TableRow>))}</TableBody>
            </Table>
          ) : <p className="text-muted-foreground">Nenhum certificado emitido</p>}
        </TabsContent>
      </Tabs>
    </div>
  )
}

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { formatDate, formatDateTime, formatCPF, getInitials, getStatusColor } from '@/lib/utils'
import { Settings } from 'lucide-react'