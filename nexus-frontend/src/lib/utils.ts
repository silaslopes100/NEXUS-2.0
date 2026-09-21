import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(date))
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatCPF(cpf: string): string {
  const cleaned = cpf.replace(/\D/g, '')
  if (cleaned.length !== 11) return cpf
  return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function calculatePresencePercentage(presences: number, totalClasses: number): number {
  if (totalClasses === 0) return 0
  return Math.round((presences / totalClasses) * 100)
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ativo: 'bg-green-100 text-green-800',
    inativo: 'bg-gray-100 text-gray-800',
    bloqueado: 'bg-red-100 text-red-800',
    pendente: 'bg-yellow-100 text-yellow-800',
    aprovado: 'bg-green-100 text-green-800',
    reprovado: 'bg-red-100 text-red-800',
    concluido: 'bg-blue-100 text-blue-800',
    em_andamento: 'bg-blue-100 text-blue-800',
    cancelado: 'bg-gray-100 text-gray-800',
    desistente: 'bg-red-100 text-red-800',
    revalidado: 'bg-purple-100 text-purple-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

export function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    admin: 'Administrador',
    secretario_geral: 'Secretário Geral',
    coordenador_ead: 'Coordenador EAD',
    coordenador_polo: 'Coordenador de Polo',
    secretario_escola: 'Secretário de Escola',
    professor: 'Professor',
    monitor: 'Monitor',
    aluno: 'Aluno',
    financeiro: 'Financeiro',
    logistica: 'Logística',
  }
  return labels[role] || role
}

export function getPermissionLabel(permission: string): string {
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

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}