import {
  LayoutDashboard,
  Users,
  Building2,
  GraduationCap,
  BookOpen,
  FolderKanban,
  CalendarDays,
  UserCheck,
  UserRound,
  Laptop,
  Award,
  FileCheck2,
  Clock,
  Key,
  CreditCard,
  Ticket,
  Truck,
  ShieldCheck,
  ArrowLeftRight,
  MessageSquare,
  BellRing,
  ScrollText,
  BookMarked,
  Sliders,
  Database,
  ClipboardList,
  History,
  Scale,
  TrendingUp,
  Inbox,
  LucideIcon,
} from 'lucide-react';
import { UserRole } from '@/types/auth';

export interface MenuItem {
  title: string;
  path: string;
  icon: LucideIcon;
  badge?: string;
  badgeColor?: 'yellow' | 'blue' | 'emerald' | 'purple' | 'slate';
  permission?: string;
  isPlaceholder?: boolean;
}

export interface MenuGroup {
  groupTitle?: string;
  items: MenuItem[];
}

export const menuByRole: Record<UserRole, MenuGroup[]> = {
  admin: [
    {
      groupTitle: 'Visão Geral',
      items: [
        {
          title: 'Dashboard Executivo',
          path: '/admin/dashboard',
          icon: LayoutDashboard,
        },
      ],
    },
    {
      groupTitle: 'Gestão de Acesso & Rede',
      items: [
        {
          title: 'Usuários',
          path: '/admin/usuarios',
          icon: Users,
        },
        {
          title: 'Polos',
          path: '/admin/polos-escolas',
          icon: Building2,
          isPlaceholder: true,
        },
        {
          title: 'Escolas',
          path: '/admin/escolas',
          icon: Building2,
        },
        {
          title: 'Corpo Docentes',
          path: '/admin/professores',
          icon: GraduationCap,
        },
      ],
    },
    {
      groupTitle: 'Acadêmico',
      items: [
        {
          title: 'Cursos & Matrizes',
          path: '/admin/cursos',
          icon: BookOpen,
        },
        {
          title: 'Disciplinas',
          path: '/admin/disciplinas',
          icon: FolderKanban,
        },
        {
          title: 'Auditoria de Aulas',
          path: '/admin/aulas',
          icon: ClipboardList,
        },
        {
          title: 'Turmas & Calendários',
          path: '/admin/turmas-calendarios',
          icon: CalendarDays,
          isPlaceholder: true,
        },
        {
          title: 'Alunos & Matrículas',
          path: '/admin/alunos',
          icon: UserCheck,
          isPlaceholder: true,
        },
        {
          title: 'EAD',
          path: '/admin/ead',
          icon: Laptop,
          isPlaceholder: true,
        },
        {
          title: 'Notas & Histórico Unificado',
          path: '/admin/notas-historico',
          icon: Award,
        },
        {
          title: 'Presenças & Frequência',
          path: '/admin/presencas',
          icon: Clock,
        },
        {
          title: 'Certificados & Diplomas',
          path: '/admin/certificados',
          icon: FileCheck2,
          isPlaceholder: true,
        },
      ],
    },
    {
      groupTitle: 'Comercial & Licenças',
      items: [
        {
          title: 'Estoque de Licenças',
          path: '/admin/licencas',
          icon: Key,
        },
        {
          title: 'Vendas',
          path: '/admin/vendas',
          icon: TrendingUp,
        },
        {
          title: 'Boletos & Pagamentos',
          path: '/admin/financeiro',
          icon: CreditCard,
          badge: 'Gateway',
          badgeColor: 'blue',
        },
        {
          title: 'Pedidos',
          path: '/admin/pedidos',
          icon: ClipboardList,
        },
        {
          title: 'Regras de Pagamento',
          path: '/admin/regras-pagamento',
          icon: Scale,
        },
        {
          title: 'Gateways de Pagamento',
          path: '/admin/gateways',
          icon: ShieldCheck,
        },
        {
          title: 'Cupons de Desconto',
          path: '/admin/cupons',
          icon: Ticket,
          isPlaceholder: true,
        },
        {
          title: 'Transferências',
          path: '/admin/transferencias',
          icon: ArrowLeftRight,
        },
      ],
    },
    {
      groupTitle: 'Logística & Livros',
      items: [
        {
          title: 'Pendentes de envio',
          path: '/admin/logistica/pendentes',
          icon: Truck,
        },
        {
          title: 'Histórico de pedidos',
          path: '/admin/logistica/historico',
          icon: History,
        },
      ],
    },
    {
      groupTitle: 'Governança & Auditoria',
      items: [
        {
          title: 'Auditoria & Logs',
          path: '/admin/auditoria',
          icon: ScrollText,
        },
        {
          title: 'Parâmetros & Configurações',
          path: '/admin/configuracoes',
          icon: Sliders,
        },
        {
          title: 'Execuções do ETL',
          path: '/admin/execucoes-batch',
          icon: Database,
          badge: 'NeonDB',
          badgeColor: 'blue',
        },
        {
          title: 'Chat & Mensagens',
          path: '/chat',
          icon: MessageSquare,
        },
        {
          title: 'Gestão do Chat',
          path: '/admin/chat',
          icon: ShieldCheck,
        },
        {
          title: 'Feed & Notificações',
          path: '/feed',
          icon: BellRing,
          isPlaceholder: true,
        },
      ],
    },
  ],

  // Perfis do módulo 2.4: usam as mesmas telas do admin (caminhos /admin/...),
  // liberadas por RequireRole e restritas no backend por require_area.
  financeiro: [
    {
      groupTitle: 'Financeiro',
      items: [
        { title: 'Dashboard Financeiro', path: '/financeiro/dashboard', icon: LayoutDashboard },
        { title: 'Vendas', path: '/admin/vendas', icon: TrendingUp },
        { title: 'Boletos & Pagamentos', path: '/admin/financeiro', icon: CreditCard },
        { title: 'Pedidos', path: '/admin/pedidos', icon: ClipboardList },
        { title: 'Regras de Pagamento', path: '/admin/regras-pagamento', icon: Scale },
        { title: 'Gateways de Pagamento', path: '/admin/gateways', icon: ShieldCheck },
      ],
    },
    {
      groupTitle: 'Comunicação',
      items: [{ title: 'Chat', path: '/chat', icon: MessageSquare }],
    },
  ],

  logistica: [
    {
      groupTitle: 'Logística & Livros',
      items: [
        { title: 'Dashboard Logística', path: '/logistica/dashboard', icon: LayoutDashboard },
        { title: 'Pendentes de envio', path: '/admin/logistica/pendentes', icon: Truck },
        { title: 'Histórico de pedidos', path: '/admin/logistica/historico', icon: History },
      ],
    },
    {
      groupTitle: 'Comunicação',
      items: [{ title: 'Chat', path: '/chat', icon: MessageSquare }],
    },
  ],

  polo: [
    {
      groupTitle: 'Visão do Polo',
      items: [
        {
          title: 'Dashboard do Polo',
          path: '/polo/dashboard',
          icon: LayoutDashboard,
        },
        {
          title: 'Escolas Vinculadas',
          path: '/polo/escolas',
          icon: Building2,
          isPlaceholder: true,
        },
        {
          title: 'Gestão de Escolas',
          path: '/polo/escolas/gestao',
          icon: Building2,
        },
        {
          title: 'Cursos',
          path: '/polo/cursos',
          icon: BookOpen,
        },
      ],
    },
    {
      groupTitle: 'Alunos & Turmas',
      items: [
        {
          title: 'Alunos do Polo',
          path: '/polo/alunos',
          icon: UserCheck,
          isPlaceholder: true,
        },
        {
          title: 'Turmas & Horários',
          path: '/polo/turmas',
          icon: CalendarDays,
          isPlaceholder: true,
        },
        {
          title: 'Certificados Emitidos',
          path: '/polo/certificados',
          icon: FileCheck2,
          isPlaceholder: true,
        },
        {
          title: 'Transferências',
          path: '/polo/transferencias',
          icon: ArrowLeftRight,
        },
      ],
    },
    {
      groupTitle: 'Licenças & Pedidos',
      items: [
        {
          title: 'Minhas Licenças',
          path: '/polo/licencas',
          icon: Key,
        },
        {
          title: 'Comprar Disciplinas',
          path: '/polo/comprar-licencas',
          icon: CreditCard,
        },
        {
          title: 'Meus Pedidos',
          path: '/polo/livros',
          icon: BookMarked,
        },
        {
          title: 'Solicitações das Escolas',
          path: '/polo/solicitacoes',
          icon: Inbox,
        },
      ],
    },
    {
      groupTitle: 'Comunicação',
      items: [
        {
          title: 'Chat',
          path: '/chat',
          icon: MessageSquare,
        },
        {
          title: 'Mural de Avisos',
          path: '/feed',
          icon: BellRing,
          isPlaceholder: true,
        },
      ],
    },
  ],

  escola: [
    {
      groupTitle: 'Unidade Escolar',
      items: [
        {
          title: 'Dashboard da Escola',
          path: '/escola/dashboard',
          icon: LayoutDashboard,
        },
        {
          title: 'Cursos',
          path: '/escola/cursos',
          icon: BookOpen,
        },
        {
          title: 'Meus Alunos',
          path: '/escola/alunos',
          icon: UserCheck,
          isPlaceholder: true,
        },
        {
          title: 'Turmas & Horários',
          path: '/escola/turmas',
          icon: CalendarDays,
          isPlaceholder: true,
        },
        {
          title: 'Transferências',
          path: '/escola/transferencias',
          icon: ArrowLeftRight,
        },
        {
          title: 'Presenças & Frequência',
          path: '/escola/presencas',
          icon: Clock,
          isPlaceholder: true,
        },
        {
          title: 'Licenças Atribuídas',
          path: '/escola/licencas',
          icon: Key,
          isPlaceholder: true,
        },
        {
          title: 'Solicitar ao Polo',
          path: '/escola/solicitacoes',
          icon: Inbox,
        },
        {
          title: 'Meus Pedidos',
          path: '/escola/livros',
          icon: BookMarked,
        },
        {
          title: 'Chat Interno',
          path: '/chat',
          icon: MessageSquare,
        },
        {
          title: 'Mural de Notificações',
          path: '/feed',
          icon: BellRing,
          isPlaceholder: true,
        },
      ],
    },
  ],

  professor: [
    {
      groupTitle: 'Espaço do Docente',
      items: [
        {
          title: 'Painel do Professor',
          path: '/professor/dashboard',
          icon: LayoutDashboard,
        },
        {
          title: 'Minhas Disciplinas & Turmas',
          path: '/professor/disciplinas',
          icon: BookOpen,
          isPlaceholder: true,
        },
        {
          title: 'Diário de Aulas',
          path: '/professor/aulas',
          icon: ClipboardList,
          badge: 'Novo',
          badgeColor: 'emerald',
        },
        {
          title: 'Conteúdos AVA',
          path: '/professor/conteudos',
          icon: FolderKanban,
        },
        {
          title: 'Lançamento de Notas',
          path: '/professor/notas',
          icon: Award,
        },
        {
          title: 'Chat',
          path: '/chat',
          icon: MessageSquare,
        },
        {
          title: 'Avisos & Feed',
          path: '/feed',
          icon: BellRing,
          isPlaceholder: true,
        },
      ],
    },
  ],

  aluno: [
    {
      groupTitle: 'Ambiente do Aluno',
      items: [
        {
          title: 'Meu Perfil',
          path: '/aluno/perfil',
          icon: UserRound,
        },
        {
          title: 'Meu Aprendizado (Dashboard)',
          path: '/aluno/dashboard',
          icon: LayoutDashboard,
        },
        {
          title: 'Sala de Aula Virtual (AVA)',
          path: '/aluno/ava',
          icon: Laptop,
          badge: 'Aulas',
          badgeColor: 'emerald',
          isPlaceholder: true,
        },
        {
          title: 'Minhas Disciplinas',
          path: '/aluno/disciplinas',
          icon: BookOpen,
        },
        {
          title: 'Notas & Histórico Unificado',
          path: '/aluno/historico',
          icon: Award,
        },
        {
          title: 'Frequência & Presença',
          path: '/aluno/presenca',
          icon: Clock,
          isPlaceholder: true,
        },
        {
          title: 'Meus Certificados',
          path: '/aluno/certificados',
          icon: FileCheck2,
          isPlaceholder: true,
        },
        {
          title: 'Material Didático & Livros',
          path: '/aluno/livros',
          icon: BookMarked,
          isPlaceholder: true,
        },
        {
          title: 'Cursos & Matrículas EAD',
          path: '/aluno/compras',
          icon: CreditCard,
          isPlaceholder: true,
        },
        {
          title: 'Minhas Transferências',
          path: '/aluno/transferencias',
          icon: ArrowLeftRight,
        },
        {
          title: 'Chat',
          path: '/chat',
          icon: MessageSquare,
        },
        {
          title: 'Notificações & Mural',
          path: '/feed',
          icon: BellRing,
          isPlaceholder: true,
        },
      ],
    },
  ],
};
