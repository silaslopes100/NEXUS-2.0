import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { User, Permission, Profile } from '@/types'

interface AuthContextType {
  user: User | null
  permissions: Permission[]
  profiles: Profile[]
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hasPermission: (permission: string, allowRoles?: string[]) => boolean
  isGlobalView: () => boolean
  getActorContext: () => { user_id: string; perfil: string; global_view: boolean; polo_id?: string; escola_id?: string }
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('access_token')
    const storedUser = localStorage.getItem('user')
    
    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setUser(parsedUser)
        // Permissions would be loaded from API in a real app
        // For now, we'll use a simplified version
        const role = parsedUser.perfil_nome || 'aluno'
        const userPermissions = getPermissionsForRole(role)
        setPermissions(userPermissions)
      } catch (error) {
        console.error('Failed to load user:', error)
        logout()
      }
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = async (email: string, password: string) => {
    // In a real app, this would call the auth API
    // For now, we'll simulate
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    
    if (!response.ok) {
      throw new Error('Credenciais inválidas')
    }
    
    const data = await response.json()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    
    setUser(data.user)
    setPermissions(getPermissionsForRole(data.user.perfil_nome))
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    setUser(null)
    setPermissions([])
    window.location.href = '/login'
  }

  const hasPermission = (permission: string, allowRoles: string[] = []) => {
    if (!user) return false
    const role = user.perfil_nome || ''
    if (role === 'admin' || role === 'secretario_geral') return true
    if (allowRoles.includes(role)) return true
    return permissions.some(p => p.chave === permission)
  }

  const isGlobalView = () => {
    if (!user) return false
    const role = user.perfil_nome || ''
    return role === 'admin' || role === 'secretario_geral'
  }

  const getActorContext = () => {
    if (!user) throw new Error('User not authenticated')
    const perfil = user.perfil_nome || ''
    return {
      user_id: user.id,
      perfil,
      global_view: perfil === 'admin' || perfil === 'secretario_geral',
      polo_id: user.polo_id,
      escola_id: user.escola_id,
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      permissions,
      profiles,
      isLoading,
      login,
      logout,
      hasPermission,
      isGlobalView,
      getActorContext,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

function getPermissionsForRole(role: string): Permission[] {
  const allPermissions: Record<string, string[]> = {
    admin: [
      'p_dashboard', 'p_alunos', 'p_polos', 'p_escolas', 'p_cursos', 'p_modulos',
      'p_licencas', 'p_ead', 'p_financeiro', 'p_logistica', 'p_chat', 'p_certificados',
      'p_config', 'p_auditoria', 'p_usuarios', 'p_relatorios'
    ],
    secretario_geral: [
      'p_dashboard', 'p_alunos', 'p_polos', 'p_escolas', 'p_cursos', 'p_modulos',
      'p_licencas', 'p_ead', 'p_financeiro', 'p_logistica', 'p_chat', 'p_certificados',
      'p_config', 'p_auditoria', 'p_usuarios', 'p_relatorios'
    ],
    coordenador_ead: [
      'p_dashboard', 'p_alunos', 'p_ead', 'p_cursos', 'p_modulos', 'p_licencas',
      'p_certificados', 'p_chat', 'p_relatorios'
    ],
    coordenador_polo: [
      'p_dashboard', 'p_alunos', 'p_polos', 'p_escolas', 'p_cursos', 'p_modulos',
      'p_licencas', 'p_ead', 'p_financeiro', 'p_logistica', 'p_chat', 'p_certificados',
      'p_config', 'p_auditoria', 'p_usuarios', 'p_relatorios'
    ],
    secretario_escola: [
      'p_dashboard', 'p_alunos', 'p_polos', 'p_escolas', 'p_cursos', 'p_modulos',
      'p_licencas', 'p_ead', 'p_financeiro', 'p_logistica', 'p_chat', 'p_certificados',
      'p_config', 'p_auditoria', 'p_usuarios', 'p_relatorios'
    ],
    professor: [
      'p_dashboard', 'p_alunos', 'p_cursos', 'p_modulos', 'p_chat', 'p_certificados',
      'p_relatorios'
    ],
    monitor: [
      'p_dashboard', 'p_alunos', 'p_chat'
    ],
    aluno: [
      'p_dashboard'
    ],
    financeiro: [
      'p_dashboard', 'p_financeiro', 'p_relatorios'
    ],
    logistica: [
      'p_dashboard', 'p_logistica', 'p_relatorios'
    ],
  }
  
  return (allPermissions[role] || []).map(chave => ({
    id: chave,
    chave,
    descricao: getPermissionLabel(chave),
    modulo: chave.split('_')[1] || 'geral'
  }))
}

function getPermissionLabel(permission: string): string {
  const labels: Record<string, string> = {
    p_dashboard: 'Dashboard',
    p_alunos: 'Alunos',
    p_polos: 'Polos',
    p_escolas: 'Escolas',
    p_cursos: 'Cursos',
    p_modulos: 'Módulos',
    p_licencas: 'Licenças',
    p_ead: 'EAD',
    p_financeiro: 'Financeiro',
    p_logistica: 'Logística',
    p_chat: 'Chat',
    p_certificados: 'Certificados',
    p_config: 'Configurações',
    p_auditoria: 'Auditoria',
    p_usuarios: 'Usuários',
    p_relatorios: 'Relatórios',
  }
  return labels[permission] || permission
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}