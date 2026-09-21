'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Edit, Trash2, Loader2, MessageSquare, Send, Paperclip, Download, X, Check, ChevronDown, MoreVertical, User as UserIcon, Bell, Shield } from 'lucide-react'
import { api } from '@/lib/api'
import { Conversa, ChatMensagem, PaginatedResponse } from '@/types'
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
import { formatDate, formatDateTime, getInitials } from '@/lib/utils'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'

const conversaSchema = z.object({
  tipo: z.enum(['individual', 'grupo']),
  nome: z.string().optional(),
  participantes: z.array(z.string()).min(1, 'Selecione pelo menos um participante'),
})

type ConversaFormData = z.infer<typeof conversaSchema>

const mensagemSchema = z.object({
  conteudo: z.string().min(1, 'Mensagem não pode ser vazia'),
})

type MensagemFormData = z.infer<typeof mensagemSchema>

export function ChatPage() {
  const { user, hasPermission } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [tipoFilter, setTipoFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [selectedConversa, setSelectedConversa] = useState<any | null>(null)
  const [mensagemInput, setMensagemInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: conversasData, isLoading } = useQuery({
    queryKey: ['chat-conversas', search, tipoFilter, page, pageSize],
    queryFn: () => api.get<any>('/operacional/chat/conversas', { params: { q: search, tipo: tipoFilter, limit: 50, offset: (page - 1) * 50 } }).then(r => r.data),
  })

  const { data: usuariosData } = useQuery({ queryKey: ['usuarios-select'], queryFn: () => api.get('/usuarios', { params: { limit: 1000 } }).then(r => r.data.items) })

  const { data: mensagensData } = useQuery({
    queryKey: ['chat-mensagens', selectedConversa?.id],
    queryFn: () => selectedConversa ? api.get<any[]>('/operacional/chat/mensagens', { params: { conversa_id: selectedConversa.id, limit: 200 } }).then(r => r.data) : [],
    enabled: !!selectedConversa,
    refetchInterval: 5000,
  })

  const createConversa = useMutation({ mutationFn: (data: any) => api.post('/operacional/chat/conversas', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['chat-conversas'] }); toast.success('Conversa criada!'); setIsCreateDialogOpen(false); }, onError: (e) => toast.error(e.message) })
  const sendMensagem = useMutation({ mutationFn: (data: { conversa_id: string; conteudo: string }) => api.post('/operacional/chat/mensagens', data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['chat-mensagens', selectedConversa?.id] }); setMensagemInput(''); }, onError: (e) => toast.error(e.message) })
  const marcarLida = useMutation({ mutationFn: (id: string) => api.post(`/operacional/chat/mensagens/${id}/marcar-lida`), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-mensagens', selectedConversa?.id] }) })
  const excluirChat = useMutation({ mutationFn: (id: string) => api.delete(`/operacional/chat/admin/excluir/${id}`), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['chat-conversas'] }); toast.success('Chat excluído!'); setSelectedConversa(null); }, onError: (e) => toast.error(e.message) })
  const baixarChat = useMutation({ mutationFn: (id: string) => api.get(`/operacional/chat/admin/baixar/${id}`).then(r => r.data), onSuccess: (data) => { toast.success('Conversa baixada!'); }, onError: (e) => toast.error(e.message) })

  const conversaForm = useForm<any>({ resolver: zodResolver(z.object({ tipo: z.enum(['individual', 'grupo']), nome: z.string().optional(), participantes: z.array(z.string()).min(1) })), defaultValues: { tipo: 'individual', participantes: [] } })

  const handleCreate = (data: any) => { setIsSubmitting(true); createConversa.mutate(data) }

  const handleSend = (conversaId: string, conteudo: string) => {
    if (!conteudo.trim()) return
    sendMensagem.mutate({ conversa_id: conversaId, conteudo })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-3xl font-bold tracking-tight">Chat Interno</h1><p className="text-muted-foreground">RN-06: Proibido aluno↔aluno, Admin pode baixar conversas</p></div>
        <Button onClick={() => setIsCreateDialogOpen(true)} disabled={!hasPermission('p_chat') || !hasPermission('p_chat', ['coordenador_polo', 'secretario_escola', 'professor', 'monitor', 'aluno'])}><Plus className="mr-2 h-4 w-4" />Nova Conversa</Button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 h-[calc(100vh-200px)] flex flex-col">
          <CardHeader className="flex items-center justify-between"><CardTitle>Conversas</CardTitle><Button onClick={() => setIsCreateDialogOpen(true)} variant="ghost" size="sm"><Plus className="h-4 w-4" /></Button></CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            {isLoading ? <div className="flex justify-center py-8"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> : (
              <div className="space-y-2">
                {conversasData?.items?.length === 0 ? <p className="text-center text-muted-foreground py-8">Nenhuma conversa</p> : (
                  conversasData?.items.map(conv => (
                    <Button key={conv.id} variant={selectedConversa?.id === conv.id ? 'default' : 'ghost'} className="w-full justify-start gap-3 p-3 rounded-lg" onClick={() => setSelectedConversa(conv)}>
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center"><MessageSquare className="h-5 w-5 text-primary" /></div>
                      <div className="flex-1 min-w-0 text-left">
                        <p className="font-medium truncate">{conv.nome || (conv.tipo === 'individual' ? (conv.participantes?.find((p: any) => p.usuario_id !== user?.id)?.usuario_nome || 'Conversa') : 'Grupo')}</p>
                        <p className="text-xs text-muted-foreground truncate">{conv.ultima_mensagem?.conteudo || 'Sem mensagens'}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="text-xs text-muted-foreground">{conv.ultima_mensagem?.criado_em ? formatDateTime(conv.ultima_mensagem.criado_em) : ''}</span>
                        {conv.nao_lidas > 0 && <Badge variant="success" className="text-xs">{conv.nao_lidas}</Badge>}
                      </div>
                    </Button>
                  ))
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {selectedConversa && (
          <Card className="lg:col-span-2 h-[calc(100vh-200px)] flex flex-col">
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center"><MessageSquare className="h-5 w-5 text-primary" /></div>
                <div>
                  <p className="font-medium">{selectedConversa.nome || selectedConversa.tipo}</p>
                  <p className="text-xs text-muted-foreground">{selectedConversa.participantes?.map((p: any) => p.usuario_nome).join(', ') || 'Sem participantes'}</p>
                </div>
              </div>
              <div className="flex gap-1">
                {hasPermission('p_chat') && <Button variant="ghost" size="icon" onClick={() => baixarChat.mutate(selectedConversa.id)} aria-label="Baixar"><Download className="h-4 w-4" /></Button>}
                {hasPermission('p_chat') && user?.perfil_nome === 'admin' && <Button variant="ghost" size="icon" onClick={() => { if(confirm('Excluir chat?')) excluirChat.mutate(selectedConversa.id) }} className="text-destructive" aria-label="Excluir"><Trash2 className="h-4 w-4" /></Button>}
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto space-y-4">
              {mensagensData?.map(msg => (
                <div key={msg.id} className={`flex ${msg.remetente_id === user?.id ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] ${msg.remetente_id === user?.id ? 'bg-primary text-primary-foreground rounded-2xl rounded-tr-sm' : 'bg-secondary rounded-2xl rounded-tl-sm'} p-3`}>
                    <p className="text-sm">{msg.conteudo}</p>
                    <p className={`text-xs mt-1 ${msg.remetente_id === user?.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>{msg.remetente_nome} • {formatDateTime(msg.criado_em)}</p>
                  </div>
                </div>
              ))}
              <div ref={(el) => el?.scrollIntoView()} />
            </CardContent>
            <CardFooter>
              <form onSubmit={(e) => { e.preventDefault(); handleSend(selectedConversa.id, mensagemInput); }} className="flex gap-2">
                <Input value={mensagemInput} onChange={e => setMensagemInput(e.target.value)} placeholder="Digite sua mensagem..." className="flex-1" disabled={isSubmitting} />
                <Button type="submit" disabled={!mensagemInput.trim() || isSubmitting}><Send className="h-4 w-4" /></Button>
              </form>
            </CardFooter>
          </Card>
        )}
      </div>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Nova Conversa</DialogTitle></DialogHeader>
          <Form {...conversaForm}>
            <form onSubmit={conversaForm.handleSubmit(handleCreate)} className="space-y-4">
              <FormField control={conversaForm.control} name="tipo" render={({field})=>(<FormItem><FormLabel>Tipo</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value}><SelectTrigger><SelectValue placeholder="Selecione"/></SelectTrigger><SelectContent><SelectItem value="individual">Individual</SelectItem><SelectItem value="grupo">Grupo</SelectItem></SelectContent></Select></FormItem>)} />
              <FormField control={conversaForm.control} name="nome" render={({field})=>(<FormItem><FormLabel>Nome (para grupos)</FormLabel><FormControl><input {...field} className="w-full" placeholder="Nome do grupo" /></FormControl></FormItem>)} />
              <FormField control={conversaForm.control} name="participantes" render={({field})=>(<FormItem><FormLabel>Participantes *</FormLabel><Select onValueChange={field.onChange} defaultValue={field.value} multiple><SelectTrigger><SelectValue placeholder="Selecione participantes"/></SelectTrigger><SelectContent>{usuariosData?.items?.map(u => <SelectItem key={u.id} value={u.id}>{u.nome} {u.sobrenome} ({u.perfil_nome})</SelectItem>)}</SelectContent></Select></FormItem>)} />
              <DialogFooter><Button type="button" variant="outline" onClick={()=>setIsCreateDialogOpen(false)}>Cancelar</Button><Button type="submit">Criar</Button></DialogFooter>
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
import { formatDate, formatDateTime, getInitials } from '@/lib/utils'
import { Loader2 } from 'lucide-react'