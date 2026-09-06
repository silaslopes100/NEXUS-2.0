import {
  LayoutDashboard,
  Users,
  Shield,
  Building2,
  GraduationCap,
  BookOpen,
  FolderKanban,
  CalendarDays,
  UserCheck,
  Laptop,
  Award,
  FileCheck2,
  Clock,
  Key,
  CreditCard,
  TicketPercent,
  Truck,
  ArrowLeftRight,
  MessageSquare,
  BellRing,
  ScrollText,
  BookMarked,
  Sliders,
  Database,
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
          title: 'Usuários & Staff',
          path: '/admin/usuarios',
          icon: Users,
        },
        {
          title: 'Perfis & Permissões',
          path: '/admin/perfis-permissoes',
          icon: Shield,
          isPlaceholder: true,
        },
        {
          title: 'Polos & Escolas',
          path: '/admin/polos-escolas',
          icon: Building2,
          isPlaceholder: true,
        },
        {
          title: 'Professores & Docentes',
          path: '/admin/professores',
          icon: GraduationCap,
          isPlaceholder: true,
        },
      ],
    },
    {
      groupTitle: 'Acadêmico & AVA',
      items: [
        {
          title: 'Cursos & Matrizes',
          path: '/admin/cursos',
          icon: BookOpen,
          isPlaceholder: true,
        },
        {
          title: 'Disciplinas & AVA',
          path: '/admin/disciplinas',
          icon: FolderKanban,
          isPlaceholder: true,
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
          title: 'Matrículas EAD',
          path: '/admin/ead',
          icon: Laptop,
          isPlaceholder: true,
        },
        {
          title: 'Notas & Histórico Unificado',
          path: '/admin/notas-historico',
          icon: Award,
          isPlaceholder: true,
        },
        {
          title: 'Presenças & Frequência',
          path: '/admin/presencas',
          icon: Clock,
          isPlaceholder: true,
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
          badge: 'Vendas',
          badgeColor: 'yellow',
          isPlaceholder: true,
        },
        {
          title: 'Vendas & Asaas',
          path: '/admin/financeiro',
          icon: CreditCard,
          badge: 'Gateway',
          badgeColor: 'blue',
          isPlaceholder: true,
        },
        {
          title: 'Cupons de Desconto',
          path: '/admin/cupons',
          icon: TicketPercent,
          isPlaceholder: true,
        },
        {
          title: 'Logística & Livros',
          path: '/admin/pedidos-livros',
          icon: Truck,
          isPlaceholder: true,
        },
        {
          title: 'Transferências',
          path: '/admin/transferencias',
          icon: ArrowLeftRight,
          isPlaceholder: true,
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
          badge: 'Online',
          badgeColor: 'emerald',
          isPlaceholder: true,
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
          isPlaceholder: true,
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
          isPlaceholder: true,
        },
        {
          title: 'Comprar Licenças',
          path: '/polo/comprar-licencas',
          icon: CreditCard,
          isPlaceholder: true,
        },
        {
          title: 'Pedidos de Livros Didáticos',
          path: '/polo/livros',
          icon: BookMarked,
          isPlaceholder: true,
        },
      ],
    },
    {
      groupTitle: 'Comunicação',
      items: [
        {
          title: 'Chat com Central',
          path: '/chat',
          icon: MessageSquare,
          isPlaceholder: true,
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
          title: 'Pedidos de Livros',
          path: '/escola/livros',
          icon: BookMarked,
          isPlaceholder: true,
        },
        {
          title: 'Chat Interno',
          path: '/chat',
          icon: MessageSquare,
          isPlaceholder: true,
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
          title: 'Conteúdos AVA & Aulas',
          path: '/professor/conteudos',
          icon: FolderKanban,
          isPlaceholder: true,
        },
        {
          title: 'Lançamento de Notas',
          path: '/professor/notas',
          icon: Award,
          isPlaceholder: true,
        },
        {
          title: 'Diário de Presença',
          path: '/professor/presencas',
          icon: Clock,
          isPlaceholder: true,
        },
        {
          title: 'Atas de Aula',
          path: '/professor/atas',
          icon: ScrollText,
          isPlaceholder: true,
        },
        {
          title: 'Chat com Alunos',
          path: '/chat',
          icon: MessageSquare,
          isPlaceholder: true,
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
          isPlaceholder: true,
        },
        {
          title: 'Notas & Histórico Unificado',
          path: '/aluno/historico',
          icon: Award,
          isPlaceholder: true,
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
          title: 'Chat com Professores',
          path: '/chat',
          icon: MessageSquare,
          isPlaceholder: true,
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
