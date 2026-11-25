import { apiClient } from '@/api/client';
import { Tentativa } from '@/features/avaliacoes/api';
import { ItemAula, TipoAula } from './api';

export type SituacaoDisciplina =
  | 'liberada'
  | 'concluida'
  | 'em_breve'
  | 'bloqueada'
  | 'pagamento_pendente'
  | 'prazo_expirado';
export type StatusAula = 'bloqueada' | 'disponivel' | 'em_andamento' | 'concluida';
export type MotivoBloqueio = 'drip' | 'sequencial' | 'pre_requisito';

export interface DisciplinaAluno {
  id: string;
  nome: string;
  curso_id?: string | null;
  curso_nome?: string | null;
  semestre?: number | null;
  capa_url?: string | null;
  descricao?: string | null;
  situacao: SituacaoDisciplina;
  total_aulas: number;
  aulas_concluidas: number;
  progresso_pct: number;
  duracao_min: number;
  prazo_conclusao?: string | null;
  ultimo_acesso_em?: string | null;
}

export interface Continuar {
  disciplina_id: string;
  disciplina_nome: string;
  capa_url?: string | null;
  aula_id: string;
  aula_titulo: string;
  capitulo_titulo: string;
  progresso_pct: number;
  ultimo_acesso_em?: string | null;
}

export interface HomeAva {
  nome: string;
  continuar?: Continuar | null;
  disciplinas: DisciplinaAluno[];
  resumo: {
    aulas_concluidas: number;
    disciplinas_concluidas: number;
    disciplinas_liberadas: number;
    minutos_estudados: number;
  };
}

export interface AulaResumoAluno {
  id: string;
  titulo: string;
  tipo: TipoAula;
  duracao_min?: number | null;
  obrigatoria: boolean;
  status: StatusAula;
  motivo_bloqueio?: MotivoBloqueio | null;
  libera_em?: string | null;
  tipos_itens: string[];
}

export interface CapituloAluno {
  id: string;
  titulo: string;
  descricao?: string | null;
  total_aulas: number;
  aulas_concluidas: number;
  aulas: AulaResumoAluno[];
}

export interface DisciplinaPlayer {
  disciplina: DisciplinaAluno;
  sequencial: boolean;
  previa: boolean;
  /** Treinamentos: certificado pronto para baixar. */
  certificado_disponivel?: boolean;
  proxima_aula_id?: string | null;
  capitulos: CapituloAluno[];
}

export interface AvaliacaoAula {
  avaliacao_id: string;
  titulo: string;
  instrucoes?: string | null;
  ativa: boolean;
  tempo_limite_min?: number | null;
  total_questoes: number;
  tentativas_max: number;
  tentativas_usadas: number;
  tentativas_restantes: number;
  melhor_nota?: number | null;
  nota_minima: number;
  aprovado: boolean;
  tentativa_aberta_id?: string | null;
  pode_realizar: boolean;
}

export interface Anotacao {
  id: string;
  texto: string;
  posicao_seg?: number | null;
  criado_em: string;
  atualizado_em?: string | null;
}

export interface AulaAluno {
  id: string;
  disciplina_id: string;
  capitulo_id: string;
  capitulo_titulo: string;
  titulo: string;
  descricao?: string | null;
  tipo: TipoAula;
  duracao_min?: number | null;
  status: StatusAula;
  percentual: number;
  posicao_seg?: number | null;
  itens: ItemAula[];
  avaliacao?: AvaliacaoAula | null;
  anotacoes: Anotacao[];
  minha_nota?: number | null;
  anterior_id?: string | null;
  proxima_id?: string | null;
  numero: number;
  total_aulas: number;
}

export interface Conclusao {
  aula_id: string;
  concluida: boolean;
  ja_estava_concluida: boolean;
  capitulo_concluido: boolean;
  disciplina_concluida: boolean;
  progresso_pct: number;
  proxima_aula_id?: string | null;
  recompensa?: Recompensa | null;
}

// ---------------------------------------------------------------------------
// Gamificação
// ---------------------------------------------------------------------------

export interface Conquista {
  codigo: string;
  nome: string;
  descricao: string;
  icone: string;
  cor: string;
  xp_bonus: number;
  obtida_em?: string | null;
}

export interface EventoXp {
  tipo: string;
  rotulo: string;
  xp: number;
  descricao?: string | null;
  criado_em?: string | null;
}

export interface Nivel {
  nivel: number;
  nome: string;
  xp_total: number;
  xp_inicio: number;
  xp_proximo: number;
  progresso_pct: number;
}

export interface Recompensa {
  xp_ganho: number;
  eventos: EventoXp[];
  conquistas: Conquista[];
  subiu_nivel: boolean;
  nivel?: Nivel | null;
  streak_atual: number;
}

export interface PerfilGamificacao {
  nivel: Nivel;
  xp_semana: number;
  streak_atual: number;
  streak_recorde: number;
  estudou_hoje: boolean;
  ultimo_dia?: string | null;
  ranking_visivel: boolean;
  conquistas: Conquista[];
  historico: EventoXp[];
}

export interface RankingItem {
  posicao: number;
  usuario_id: string;
  nome: string;
  foto_url?: string | null;
  xp: number;
  nivel: number;
  eu: boolean;
}

export interface Ranking {
  periodo: 'semana' | 'geral';
  curso?: { id: string; nome: string } | null;
  cursos: { id: string; nome: string }[];
  itens: RankingItem[];
  minha_posicao?: RankingItem | null;
  total_participantes: number;
  ranking_visivel: boolean;
}

const G = '/ava/gamificacao';

export const gamificacaoApi = {
  perfil: () => apiClient.get<PerfilGamificacao>(`${G}/perfil`).then((r) => r.data),
  ranking: (periodo: 'semana' | 'geral', cursoId?: string | null, limite = 10) =>
    apiClient.get<Ranking>(`${G}/ranking`, { params: { periodo, curso_id: cursoId || undefined, limite } }).then((r) => r.data),
  definirRankingVisivel: (ranking_visivel: boolean) => apiClient.put(`${G}/preferencias`, { ranking_visivel }),
};

/** Operações que o player usa (disciplina EAD ou treinamento). */
export interface PlayerApi {
  disciplina: (id: string) => Promise<DisciplinaPlayer>;
  aula: (id: string) => Promise<AulaAluno>;
  progresso: (id: string, percentual: number, posicao_seg?: number | null) => Promise<Conclusao | null>;
  concluir: (id: string) => Promise<Conclusao>;
  iniciarAvaliacao?: (aulaId: string) => Promise<Tentativa>;
  avaliarAula: (id: string, nota: number) => Promise<unknown>;
  criarAnotacao: (aulaId: string, texto: string, posicao_seg?: number | null) => Promise<Anotacao>;
  atualizarAnotacao: (id: string, texto: string) => Promise<Anotacao>;
  excluirAnotacao: (id: string) => Promise<unknown>;
}

const A = '/ava/aluno';

export const avaAlunoApi = {
  home: () => apiClient.get<HomeAva>(`${A}/home`).then((r) => r.data),
  disciplina: (id: string) => apiClient.get<DisciplinaPlayer>(`${A}/disciplinas/${id}`).then((r) => r.data),
  aula: (id: string) => apiClient.get<AulaAluno>(`${A}/aulas/${id}`).then((r) => r.data),
  progresso: (id: string, percentual: number, posicao_seg?: number | null) =>
    apiClient.post<Conclusao | null>(`${A}/aulas/${id}/progresso`, { percentual, posicao_seg }).then((r) => r.data),
  concluir: (id: string) => apiClient.post<Conclusao>(`${A}/aulas/${id}/concluir`).then((r) => r.data),
  iniciarAvaliacao: (aulaId: string) =>
    apiClient.post<Tentativa>(`${A}/aulas/${aulaId}/avaliacao/iniciar`).then((r) => r.data),
  avaliarAula: (id: string, nota: number) => apiClient.put(`${A}/aulas/${id}/minha-nota`, { nota }),
  criarAnotacao: (aulaId: string, texto: string, posicao_seg?: number | null) =>
    apiClient.post<Anotacao>(`${A}/aulas/${aulaId}/anotacoes`, { texto, posicao_seg }).then((r) => r.data),
  atualizarAnotacao: (id: string, texto: string) =>
    apiClient.put<Anotacao>(`${A}/anotacoes/${id}`, { texto }).then((r) => r.data),
  excluirAnotacao: (id: string) => apiClient.delete(`${A}/anotacoes/${id}`),
};

export const SITUACAO: Record<SituacaoDisciplina, { rotulo: string; classe: string }> = {
  liberada: { rotulo: 'Em andamento', classe: 'bg-blue-500/90 text-white' },
  concluida: { rotulo: 'Concluída', classe: 'bg-emerald-500/90 text-white' },
  em_breve: { rotulo: 'Em breve', classe: 'bg-slate-700/90 text-slate-100' },
  bloqueada: { rotulo: 'Bloqueada', classe: 'bg-slate-800/90 text-slate-300' },
  pagamento_pendente: { rotulo: 'Pagamento pendente', classe: 'bg-amber-500/90 text-ink' },
  prazo_expirado: { rotulo: 'Prazo encerrado', classe: 'bg-red-500/90 text-white' },
};

/** Saudação conforme o horário. */
export const saudacao = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite';
};

/** "mm:ss" ou "h:mm:ss" a partir de segundos. */
export const tempoVideo = (seg: number) => {
  const s = Math.max(0, Math.floor(seg));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`;
};
