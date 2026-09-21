import { NavLink, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, Users, Building2, GraduationCap, BookOpen, 
  Briefcase, CreditCard, Truck, MessageSquare, Award, 
  Settings, LogOut, Menu, X, ChevronDown, ChevronRight,
  Package, FileText, Calendar, Bell, ShoppingBag
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { cn, getRoleLabel } from '@/lib/utils'
import { useState } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, permission: 'p_dashboard' },
  { name: 'Alunos', href: '/alunos', icon: Users, permission: 'p_alunos' },
  { name: 'Matrículas', href: '/matriculas', icon: BookOpen, permission: 'p_alunos' },
  { name: 'Polos', href: '/polos', icon: Building2, permission: 'p_polos' },
  { name: 'Escolas', href: '/escolas', icon: GraduationCap, permission: 'p_escolas' },
  { name: 'Cursos', href: '/cursos', icon: BookOpen, permission: 'p_cursos' },
  { name: 'EAD', href: '/ead', icon: Package, permission: 'p_ead' },
  { name: 'Licenças', href: '/licencas', icon: Package, permission: 'p_licencas' },
  { name: 'Financeiro', href: '/financeiro', icon: CreditCard, permission: 'p_financeiro' },
  { name: 'Logística', href: '/logistica', icon: Truck, permission: 'p_logistica' },
  { name: 'Certificados', href: '/certificados', icon: Award, permission: 'p_certificados' },
  { name: 'Chat', href: '/chat', icon: MessageSquare, permission: 'p_chat' },
  { name: 'Configurações', href: '/configuracoes', icon: Settings, permission: 'p_config' },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation()
  const { user, hasPermission, logout } = useAuth()
  const [expandedSections, setExpandedSections] = useState<string[]>([])

  const toggleSection = (section: string) => {
    setExpandedSections(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section) 
        : [...prev, section]
    )
  }

  const filteredNavigation = navigation.filter(item => hasPermission(item.permission))

  return (
    <>
      <div 
        className={cn(
          'fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-card border-r border-border',
          'transform transition-transform duration-300 ease-in-out',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          'flex flex-col'
        )}
        aria-label="Menu principal"
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-border lg:justify-center">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-bold text-lg text-primary">
            <GraduationCap className="h-6 w-6" />
            <span>NEXUS 2.0</span>
          </NavLink>
          <button
            className="lg:hidden p-2 rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            onClick={onClose}
            aria-label="Fechar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1" aria-label="Navegação principal">
          {filteredNavigation.map((item) => {
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/')
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={({ isActive: active }) => cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                {item.name}
              </NavLink>
            )
          })}
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.nome} {user?.sobrenome}</p>
              <p className="text-xs text-muted-foreground truncate">{getRoleLabel(user?.perfil_nome || '')}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors mt-2"
          >
            <LogOut className="h-5 w-5" aria-hidden="true" />
            Sair
          </button>
        </div>
      </aside>
    </>
  )
}