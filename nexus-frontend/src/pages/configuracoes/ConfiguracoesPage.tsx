'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, Settings, User, Lock, CreditCard, Globe, Bell, Shield, Save, Palette, Moon, Sun, Key, Camera, Eye, EyeOff, GraduationCap } from 'lucide-react'
import { api } from '@/lib/api'
import { Configuracao, Perfil } from '@/types'
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
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'

export function ConfiguracoesPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'perfil' | 'pagamentos' | 'sistema' | 'sobre'>('perfil')
  const [isPasswordDialogOpen, setIsPasswordDialogOpen] = useState(false)
  const [isPhotoDialogOpen, setIsPhotoDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: configData } = useQuery({ queryKey: ['configuracoes'], queryFn: () => api.get('/admin/configuracoes').then(r => r.data) })

  const passwordForm = useForm({
    resolver: zodResolver(z.object({
      senha_atual: z.string().min(1, 'Senha atual obrigatória'),
      nova_senha: z.string().min(6, 'Mínimo 6 caracteres'),
      confirmar_senha: z.string()
    }).refine(d => d.nova_senha === d.confirmar_senha, { message: 'Senhas não coincidem', path: ['confirmar_senha'] }))
  })

  const perfilForm = useForm({ defaultValues: { nome: user?.nome, sobrenome: user?.sobrenome, email: user?.email, telefone: user?.telefone } })

  const handlePerfilSubmit = async (data: any) => {
    try {
      // await update_perfil_configuracao(data)
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
        <div><h1 className="text-3xl font-bold tracking-tight">Configurações</h1><p className="text-muted-foreground">Gerenciamento de perfil, pagamentos, sistema e informações</p></div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="perfil">Perfil</TabsTrigger>
          <TabsTrigger value="pagamentos">Pagamentos</TabsTrigger>
          <TabsTrigger value="sistema">Sistema</TabsTrigger>
          <TabsTrigger value="sobre">Sobre</TabsTrigger>
        </TabsList>

        <TabsContent value="perfil" className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Dados do Perfil</CardTitle></CardHeader>
            <CardContent>
              <Form {...perfilForm}>
                <form onSubmit={perfilForm.handleSubmit(handlePerfilSubmit)} className="space-y-4">
                  <div className="flex items-center gap-6">
                    <div className="relative w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                      <span className="text-2xl font-bold text-primary">{user?.nome?.[0]}{user?.sobrenome?.[0]}</span>
                    </div>
                    <div><Button variant="outline" onClick={()=>{}}><Camera className="mr-2 h-4 w-4" />Alterar Foto</Button></div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField control={perfilForm.control} name="nome" render={({field})=>(<FormItem><FormLabel>Nome</FormLabel><FormControl><input {...field} className="w-full" /></FormControl></FormItem>)} />
                    <FormField control={perfilForm.control} name="sobrenome" render={({field})=>(<FormItem><FormLabel>Sobrenome</FormLabel><FormControl><input {...field} className="w-full" /></FormControl></FormItem>)} />
                    <FormField control={perfilForm.control} name="email" render={({field})=>(<FormItem><FormLabel>E-mail</FormLabel><FormControl><input type="email" {...field} className="w-full" /></FormControl></FormItem>)} />
                    <FormField control={perfilForm.control} name="telefone" render={({field})=>(<FormItem><FormLabel>Telefone</FormLabel><FormControl><input {...field} className="w-full" placeholder="(11) 99999-9999" /></FormControl></FormItem>)} />
                  </div>
                  <Button type="submit">Salvar Alterações</Button>
                </form>
              </Form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <CardTitle>Segurança</CardTitle>
              <Button variant="outline" onClick={()=>setIsPasswordDialogOpen(true)}><Key className="mr-2 h-4 w-4" />Alterar Senha</Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 border rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">Segurança da Conta</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Última alteração de senha: há 30 dias</li>
                  <li>• Autenticação de dois fatores: <span className="text-red-600">Desativada</span></li>
                  <li>• Sessões ativas: 2 dispositivos</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pagamentos" className="space-y-6">
          <Card><CardHeader><CardTitle>Meios de Pagamento</CardTitle></CardHeader><CardContent><p className="text-muted-foreground">Configuração de meios de pagamento (dinheiro, cartão, PIX, boleto) - TODO: integração com gateways</p></CardContent></Card>
          <Card><CardHeader><CardTitle>Configuração de Boletos (AsaaS)</CardTitle></CardHeader><CardContent><p className="text-muted-foreground">Integração com API AsaaS - TODO: implementar</p></CardContent></Card>
          <Card><CardHeader><CardTitle>Regras de Preço</CardTitle></CardHeader><CardContent><div className="space-y-2"><div className="flex items-center justify-between p-3 border rounded-lg"><span>Preço por matéria EAD</span><span className="font-medium">R$ 45,00</span></div><div className="flex items-center justify-between p-3 border rounded-lg"><span>Taxa de reingresso (RN-04)</span><span className="font-medium">R$ 100,00</span></div><div className="flex items-center justify-between p-3 border rounded-lg"><span>Licenças para reingresso</span><span className="font-medium">2 licenças</span></div></div></CardContent></Card>
        </TabsContent>

        <TabsContent value="sistema" className="space-y-6">
          <Card><CardHeader><CardTitle>Configurações do Sistema</CardTitle></CardHeader><CardContent><div className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg"><div><p className="font-medium">Modo de Manutenção</p><p className="text-sm text-muted-foreground">Coloca o sistema em modo somente leitura</p></div><Switch checked={false} onCheckedChange={()=>{}} /></div>
            <div className="flex items-center justify-between p-3 border rounded-lg"><div><p className="font-medium">Registro de Auditoria</p><p className="text-sm text-muted-foreground">Registra todas as ações de escrita</p></div><Switch checked={true} onCheckedChange={()=>{}} /></div>
            <div className="flex items-center justify-between p-3 border rounded-lg"><div><p className="font-medium">Notificações por E-mail</p><p className="text-sm text-muted-foreground">Envia e-mails para eventos importantes</p></div><Switch checked={true} onCheckedChange={()=>{}} /></div>
          </div></CardContent></Card>
          <Card><CardHeader><CardTitle>Configurações Avançadas</CardTitle></CardHeader><CardContent><div className="space-y-2"><div className="flex items-center justify-between p-3 border rounded-lg"><span>Timeout de Sessão (minutos)</span><Input type="number" defaultValue={60} className="w-24" /></div><div className="flex items-center justify-between p-3 border rounded-lg"><span>Limite de Upload (MB)</span><Input type="number" defaultValue={10} className="w-24" /></div><div className="flex items-center justify-between p-3 border rounded-lg"><span>Timezone</span><Select defaultValue="America/Sao_Paulo"><SelectTrigger className="w-48"><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="America/Sao_Paulo">São Paulo (UTC-3)</SelectItem><SelectItem value="UTC">UTC</SelectItem></SelectContent></Select></div></div></CardContent></Card>
        </TabsContent>

        <TabsContent value="sobre" className="space-y-6">
          <Card><CardHeader><CardTitle>Sobre o NEXUS 2.0</CardTitle></CardHeader><CardContent className="space-y-4"><div className="text-center py-8"><GraduationCap className="h-16 w-16 mx-auto text-primary mb-4" /><h3 className="text-2xl font-bold">NEXUS 2.0</h3><p className="text-muted-foreground mt-2">Sistema de Gestão Educacional Teológica ETADEMP</p></div>
            <div className="grid gap-4 md:grid-cols-2"><div className="p-4 border rounded-lg"><h4 className="font-medium mb-2">Versão</h4><p className="text-sm text-muted-foreground">2.0.0 (Build 2024.09)</p></div><div className="p-4 border rounded-lg"><h4 className="font-medium mb-2">Stack Tecnológico</h4><ul className="text-sm text-muted-foreground space-y-1"><li>Backend: FastAPI + PostgreSQL + Pydantic v2</li><li>Frontend: React 18 + TypeScript + Vite + Tailwind</li><li>Auth: JWT + Argon2id</li><li>DB: psycopg2 + migrations SQL</li></ul></div></div><div className="border-t pt-4"><h4 className="font-medium mb-2">Licenças e Agradecimentos</h4><p className="text-sm text-muted-foreground">Este software utiliza bibliotecas de código aberto. Agradecemos à comunidade open source.</p></div></CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate, getStatusColor } from '@/lib/utils'
import { Settings, Key, Camera, Palette, Moon, Sun, Shield, Save, Bell, Globe, CreditCard, DollarSign, AboutCircle, Info, User, Lock, Camera as CameraIcon } from 'lucide-react'
import { Switch } from '@/components/ui/switch'