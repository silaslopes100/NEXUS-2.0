'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, User, Mail, Lock, Camera, Save, Eye, EyeOff, Calendar, MapPin, Phone, GraduationCap, Building2, Award, FileText, Clock, AlertCircle, CheckCircle, XCircle, Shield, Key, Camera as CameraIcon, Settings } from 'lucide-react'
import { api } from '@/lib/api'
import { User as UserType, AlunoDetalheResponse } from '@/types'
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
import { Switch } from '@/components/ui/switch'
import { formatDate, formatDateTime, getInitials, getStatusColor } from '@/lib/utils'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'

export function PerfilPage() {
  const { user, update_perfil_configuracao } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'dados' | 'seguranca' | 'atividade' | 'preferencias'>('dados')
  const [isPasswordDialogOpen, setIsPasswordDialogOpen] = useState(false)
  const [isPhotoDialogOpen, setIsPhotoDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const passwordForm = useForm<any>({
    resolver: zodResolver(z.object({
      senha_atual: z.string().min(1, 'Senha atual obrigatoria'),
      nova_senha: z.string().min(6, 'Minimo 6 caracteres'),
      confirmar_senha: z.string()
    }).refine(d => d.nova_senha === d.confirmar_senha, { message: 'Senhas nao coincidem', path: ['confirmar_senha'] }))
  })

  const perfilForm = useForm<any>({
    defaultValues: { nome: user?.nome, sobrenome: user?.sobrenome, email: user?.email, telefone: user?.telefone, foto_url: user?.foto_url }
  })

  const handlePerfilSubmit = async (data: any) => {
    try {
      await update_perfil_configuracao(data)
      toast.success('Perfil atualizado!')
    } catch (e: any) {
      toast.error(e.message || 'Erro ao atualizar')
    }
  }

  const handleSenhaSubmit = (data: any) => {
    toast.success('Senha alterada!')
    setIsPasswordDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Meu Perfil</h1>
          <p className="text-muted-foreground">Gerencie seus dados, seguranca e preferencias</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="dados"><User className="mr-2 h-4 w-4" />Dados Pessoais</TabsTrigger>
          <TabsTrigger value="seguranca"><Shield className="mr-2 h-4 w-4" />Seguranca</TabsTrigger>
          <TabsTrigger value="atividade"><Clock className="mr-2 h-4 w-4" />Atividade</TabsTrigger>
          <TabsTrigger value="preferencias"><Settings className="mr-2 h-4 w-4" />Preferencias</TabsTrigger>
        </TabsList>

        <TabsContent value="dados" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                    {user?.foto_url ? (
                      <img src={user.foto_url} alt={user.nome} className="w-full h-full object-cover rounded-full" />
                    ) : (
                      <span className="text-3xl font-bold text-primary">{getInitials(user?.nome || '')}</span>
                    )}
                  </div>
                  <Button variant="outline" size="sm" onClick={() => {}} className="absolute bottom-0 right-0 -translate-y-1/2 translate-x-1/2">
                    <CameraIcon className="mr-1 h-4 w-4" /> Alterar
                  </Button>
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold">{user?.nome} {user?.sobrenome}</h2>
                  <p className="text-muted-foreground">{user?.email}</p>
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                    <span><Badge variant="outline">{user?.perfil_nome}</Badge></span>
                    {user?.polo_nome && <span><Building2 className="mr-1 h-3 w-3 inline" /> {user.polo_nome}</span>}
                    {user?.escola_nome && <span><GraduationCap className="mr-1 h-3 w-3 inline" /> {user.escola_nome}</span>}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Form {...perfilForm}>
                <form onSubmit={perfilForm.handleSubmit(handlePerfilSubmit)} className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField control={perfilForm.control} name="nome" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nome</FormLabel>
                        <FormControl><input {...field} className="w-full" /></FormControl>
                      </FormItem>
                    )} />
                    <FormField control={perfilForm.control} name="sobrenome" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Sobrenome</FormLabel>
                        <FormControl><input {...field} className="w-full" /></FormControl>
                      </FormItem>
                    )} />
                    <FormField control={perfilForm.control} name="email" render={({ field }) => (
                      <FormItem>
                        <FormLabel>E-mail</FormLabel>
                        <FormControl><input type="email" {...field} className="w-full" disabled /></FormControl>
                        <FormDescription>Nao e possivel alterar o e-mail</FormDescription>
                      </FormItem>
                    )} />
                    <FormField control={perfilForm.control} name="telefone" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Telefone</FormLabel>
                        <FormControl><input {...field} className="w-full" placeholder="(11) 99999-9999" /></FormControl>
                      </FormItem>
                    )} />
                  </div>
                  <Button type="submit">Salvar Alteracoes</Button>
                </form>
              </Form>
            </CardContent>
          </Card>

          <Card className="mt-6">
            <CardHeader><CardTitle>Informacoes do Sistema</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">ID do Usuario</label><p className="font-mono text-sm">{user?.id}</p></div>
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">Perfil</label><p className="font-medium">{user?.perfil_nome}</p></div>
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">Status</label><p><Badge variant={user?.status === 'ativo' ? 'success' : 'secondary'}>{user?.status}</Badge></p></div>
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">Ultimo Login</label><p className="text-sm text-muted-foreground">{user?.ultimo_login_em ? formatDateTime(user.ultimo_login_em) : 'Nunca'}</p></div>
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">Criado em</label><p className="text-sm text-muted-foreground">{user?.criado_em ? formatDate(user.criado_em) : '---'}</p></div>
                <div className="p-4 border rounded-lg"><label className="text-sm text-muted-foreground block mb-1">Atualizado em</label><p className="text-sm text-muted-foreground">{user?.atualizado_em ? formatDate(user.atualizado_em) : '---'}</p></div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="seguranca" className="space-y-6">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <CardTitle>Alterar Senha</CardTitle>
              <Button variant="outline" onClick={() => setIsPasswordDialogOpen(true)}><Key className="mr-2 h-4 w-4" />Alterar Senha</Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 border rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">Seguranca da Conta</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>Ultima alteracao de senha: ha 45 dias</li>
                  <li>Autenticacao de dois fatores: <span className="text-red-600">Desativada</span></li>
                  <li>Sessoes ativas: 2 dispositivos</li>
                  <li>Ultimo login: {user?.ultimo_login_em ? formatDateTime(user.ultimo_login_em) : 'Nunca'}</li>
                </ul>
              </div>
              <Button variant="outline" onClick={() => setIsPasswordDialogOpen(true)}><Key className="mr-2 h-4 w-4" />Alterar Senha</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Sessoes Ativas</CardTitle></CardHeader>
            <CardContent><div className="space-y-2"><p className="text-sm text-muted-foreground">Gerenciamento de sessoes - TODO: implementar listagem e revogacao</p></div></CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Autenticacao de Dois Fatores (2FA)</CardTitle></CardHeader>
            <CardContent>
              <div className="p-4 border rounded-lg bg-amber-50 border-amber-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-amber-800">2FA Desativado</h4>
                    <p className="text-sm text-amber-700">Ative a autenticacao de dois fatores para maior seguranca</p>
                  </div>
                  <Button variant="outline" disabled>Ativar 2FA</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="atividade" className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Historico de Atividade</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg"><Lock className="h-4 w-4 text-blue-600" /></div>
                    <div><p className="font-medium">Login realizado</p><p className="text-sm text-muted-foreground">IP: 192.168.1.100 - Chrome 119 - Windows 10</p></div>
                  </div>
                  <span className="text-sm text-muted-foreground">{formatDateTime(new Date())}</span>
                </div>
                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 rounded-lg"><Shield className="h-4 w-4 text-green-600" /></div>
                    <div><p className="font-medium">Senha alterada</p><p className="text-sm text-muted-foreground">Alteracao de senha bem-sucedida</p></div>
                  </div>
                  <span className="text-sm text-muted-foreground">2 dias atras</span>
                </div>
                <div className="p-4 border rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-100 rounded-lg"><Settings className="h-4 w-4 text-amber-600" /></div>
                    <div><p className="font-medium">Perfil atualizado</p><p className="text-sm text-muted-foreground">Nome e telefone alterados</p></div>
                  </div>
                  <span className="text-sm text-muted-foreground">5 dias atras</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferencias" className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Preferencias de Interface</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Tema Escuro</p><p className="text-sm text-muted-foreground">Alterna entre modo claro e escuro</p></div>
                <Switch checked={false} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Notificacoes por E-mail</p><p className="text-sm text-muted-foreground">Receber avisos por e-mail</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Notificacoes no Sistema</p><p className="text-sm text-muted-foreground">Alertas e avisos no painel</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Idioma</p><p className="text-sm text-muted-foreground">Portugues (Brasil)</p></div>
                <Select defaultValue="pt-BR">
                  <SelectTrigger className="w-48"><SelectValue placeholder="Selecione" /></SelectTrigger>
                  <SelectContent><SelectItem value="pt-BR">Portugues (Brasil)</SelectItem><SelectItem value="en-US">English (US)</SelectItem><SelectItem value="es-ES">Espanol</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Timezone</p><p className="text-sm text-muted-foreground">Horario local</p></div>
                <Select defaultValue="America/Sao_Paulo">
                  <SelectTrigger className="w-48"><SelectValue placeholder="Selecione" /></SelectTrigger>
                  <SelectContent><SelectItem value="America/Sao_Paulo">Sao Paulo (UTC-3)</SelectItem><SelectItem value="UTC">UTC</SelectItem></SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Notificacoes</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Novas Mensagens no Chat</p><p className="text-sm text-muted-foreground">Notificar quando receber mensagens</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Alertas de Presenca Baixa</p><p className="text-sm text-muted-foreground">Avisar quando presenca < 75%</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Lembretes de Liberacao EAD</p><p className="text-sm text-muted-foreground">RN-03: Avisos de novas materias</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div><p className="font-medium">Certificados Prontos</p><p className="text-sm text-muted-foreground">Avisar quando certificado for emitido</p></div>
                <Switch checked={true} onCheckedChange={() => {}} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}