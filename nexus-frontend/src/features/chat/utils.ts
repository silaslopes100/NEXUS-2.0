import { Mensagem } from './api';

const PERFIL_ROTULO: Record<string, string> = {
  admin: 'Admin',
  polo: 'Polo',
  coordenador_polo: 'Polo',
  escola: 'Escola',
  secretario_escola: 'Escola',
  professor: 'Professor',
  aluno: 'Aluno',
  financeiro: 'Financeiro',
  logistica: 'Logística',
  secretario_geral: 'Secretaria Geral',
  coordenador_ead: 'Coord. EAD',
  monitor: 'Monitor',
};

export const rotuloPerfil = (perfil?: string | null) =>
  perfil ? PERFIL_ROTULO[perfil.toLowerCase()] ?? perfil : '';

export const iniciais = (nome?: string | null) =>
  (nome || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('') || '?';

export const horaCurta = (v?: string | null) => {
  if (!v) return '';
  const d = new Date(v);
  const hoje = new Date();
  if (d.toDateString() === hoje.toDateString()) {
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  if (d.toDateString() === ontem.toDateString()) return 'ontem';
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
};

export const rotuloDia = (v: string) => {
  const d = new Date(v);
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  if (d.toDateString() === hoje.toDateString()) return 'Hoje';
  if (d.toDateString() === ontem.toDateString()) return 'Ontem';
  return d.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' });
};

export const tamanhoLegivel = (bytes?: number | null) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/** Junta mensagens sem duplicar (polling + envio otimista) e mantém a ordem cronológica. */
export const mesclarMensagens = (atuais: Mensagem[], novas: Mensagem[]) => {
  if (!novas.length) return atuais;
  const mapa = new Map(atuais.map((m) => [m.id, m]));
  novas.forEach((m) => mapa.set(m.id, m));
  return Array.from(mapa.values()).sort(
    (a, b) => new Date(a.criado_em).getTime() - new Date(b.criado_em).getTime() || a.id.localeCompare(b.id),
  );
};
