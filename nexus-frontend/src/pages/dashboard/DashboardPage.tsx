import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  Users, Building2, GraduationCap, BookOpen, Award, 
  TrendingUp, ArrowUpRight, ArrowDownRight, Package
} from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { DashboardResumo, ContagemResponse } from '@/types'

const statCards = [
  { 
    title: 'Alunos Ativos', 
    key: 'alunos_ativos', 
    icon: Users, 
    color: 'bg-blue-500',
    href: '/alunos'
  },
  { 
    title: 'Matrículas', 
    key: 'matriculas', 
    icon: BookOpen, 
    color: 'bg-green-500',
    href: '/matriculas'
  },
  { 
    title: 'Polos Ativos', 
    key: 'polos_ativos', 
    icon: Building2, 
    color: 'bg-purple-500',
    href: '/polos'
  },
  { 
    title: 'Escolas Ativas', 
    key: 'escolas_ativas', 
    icon: GraduationCap, 
    color: 'bg-orange-500',
    href: '/escolas'
  },
  { 
    title: 'Professores', 
    key: 'professores_ativos', 
    icon: Users, 
    color: 'bg-teal-500',
    href: '/professores'
  },
  { 
    title: 'Certificados', 
    key: 'certificados_emitidos', 
    icon: Award, 
    color: 'bg-pink-500',
    href: '/certificados'
  },
]

export function DashboardPage() {
  const { data: resumo } = useQuery({
    queryKey: ['dashboard-resumo'],
    queryFn: () => api.get<DashboardResumo>('/dashboard/resumo').then(r => r.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Visão geral do sistema</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((stat) => {
          const value = resumo?.[stat.key as keyof DashboardResumo] || 0
          return (
            <Card key={stat.key} className="cursor-pointer hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                    <p className="text-3xl font-bold mt-1">{value.toLocaleString('pt-BR')}</p>
                  </div>
                  <div className={cn('p-3 rounded-full', stat.color)}>
                    <stat.icon className="h-6 w-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Ações Rápidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a href="/alunos/novo" className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors">
              <Users className="h-5 w-5 text-primary" />
              <span className="font-medium">Novo Aluno</span>
            </a>
            <a href="/polos/novo" className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors">
              <Building2 className="h-5 w-5 text-purple-500" />
              <span className="font-medium">Novo Polo</span>
            </a>
            <a href="/escolas/novo" className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors">
              <GraduationCap className="h-5 w-5 text-orange-500" />
              <span className="font-medium">Nova Escola</span>
            </a>
            <a href="/certificados/emitir" className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent transition-colors">
              <Award className="h-5 w-5 text-pink-500" />
              <span className="font-medium">Emitir Certificado</span>
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Ranking de Polos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Top 5 por licenças/livros</p>
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((pos) => (
                  <div key={pos} className="flex items-center justify-between text-sm">
                    <span>{pos}º Polo Exemplo</span>
                    <span className="font-medium">125</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Vendas do Mês</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold">R$ 45.230</span>
                <span className="text-sm text-green-600">+12%</span>
              </div>
              <p className="text-sm text-muted-foreground">vs mês anterior</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Alertas do Sistema</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
              <p className="text-sm text-yellow-800">5 alunos com presença abaixo de 75%</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm text-blue-800">3 certificados pendentes de emissão</p>
            </div>
            <div className="p-3 rounded-lg bg-red-50 border border-red-200">
              <p className="text-sm text-red-800">2 polos com estoque crítico</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}