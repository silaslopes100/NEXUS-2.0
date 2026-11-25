/** Formatação e rótulos da ficha cadastral do usuário. */

export function formatarData(iso?: string | null, comHora = false): string {
  if (!iso) return '—';
  // 'AAAA-MM-DD' sem hora: formata sem passar por Date para não deslocar o dia pelo fuso.
  const soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (soData && !comHora) return `${soData[3]}/${soData[2]}/${soData[1]}`;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return comHora
    ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('pt-BR');
}

export function mensagemErro(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item: { msg?: string; loc?: unknown[] }) => {
        const campo = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
        const msg = (item.msg || '').replace(/^Value error, /, '');
        return campo && typeof campo === 'string' ? `${ROTULO_CAMPO[campo] ?? campo}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }
  return fallback;
}

export function formatarTelefone(value?: string | null): string {
  if (!value) return '—';
  const digits = value.replace(/\D/g, '');
  if (digits.length === 11) return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  if (digits.length === 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return value;
}

export function formatarCpf(value?: string | null): string {
  const d = (value || '').replace(/\D/g, '');
  if (d.length !== 11) return value || '—';
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

export function formatarCep(value?: string | null): string {
  const d = (value || '').replace(/\D/g, '');
  return d.length === 8 ? `${d.slice(0, 5)}-${d.slice(5)}` : value || '—';
}

export const fmtBRL = (v?: number | null) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const fmtNum = (v?: number | null, casas = 0) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: casas, minimumFractionDigits: 0 });

export const vazio = (v?: string | null) => (v && v.trim() ? v : '—');

export const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
  'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

export const SEXO: Record<string, string> = {
  feminino: 'Feminino',
  masculino: 'Masculino',
  outro: 'Outro',
  nao_informado: 'Prefere não informar',
};

export const ESTADO_CIVIL: Record<string, string> = {
  solteiro: 'Solteiro(a)',
  casado: 'Casado(a)',
  uniao_estavel: 'União estável',
  separado: 'Separado(a)',
  divorciado: 'Divorciado(a)',
  viuvo: 'Viúvo(a)',
};

export const MODALIDADE: Record<string, string> = { polo: 'Polo', escola: 'Escola', ead: 'EAD' };

export const ROTULO_CAMPO: Record<string, string> = {
  nome: 'Nome', sobrenome: 'Sobrenome', email: 'E-mail', cpf: 'CPF', telefone: 'Telefone', celular: 'Celular',
  data_nascimento: 'Nascimento', rg: 'RG', rg_orgao_emissor: 'Órgão emissor', rg_uf: 'UF do RG', sexo: 'Sexo',
  estado_civil: 'Estado civil', naturalidade_cidade: 'Naturalidade', naturalidade_uf: 'UF de naturalidade',
  nacionalidade: 'Nacionalidade', cep: 'CEP', logradouro: 'Logradouro', numero: 'Número',
  complemento: 'Complemento', bairro: 'Bairro', cidade: 'Cidade', uf: 'UF',
  contato_emergencia_nome: 'Nome do contato', contato_emergencia_parentesco: 'Parentesco',
  contato_emergencia_telefone: 'Telefone do contato', numero_matricula: 'Matrícula',
  valor_hora_aula: 'Valor da hora-aula', chave_pix: 'Chave PIX', motivo: 'Motivo',
  perfil_id: 'Perfil', perfil_nome: 'Perfil', polo_id: 'Polo', escola_id: 'Escola', status: 'Status',
};

/** Rótulos legíveis para os status que aparecem no histórico. */
export const ROTULO_STATUS: Record<string, string> = {
  ativo: 'Ativo', inativo: 'Inativo', bloqueado: 'Bloqueado', concluida: 'Concluída', desistente: 'Desistente',
  pendente: 'Pendente', aprovada: 'Aprovada', rejeitada: 'Rejeitada', churn: 'Churn', reingresso: 'Reingresso',
  pago: 'Pago', vencido: 'Vencido', cancelado: 'Cancelado', emitido: 'Emitido',
  pago_aguardando_envio: 'Pago — aguardando envio', aguardando_pagamento: 'Aguardando pagamento',
  enviado: 'Enviado', entregue: 'Entregue', concluido: 'Concluído', troca: 'Troca',
  ativa: 'Ativa', expirada: 'Expirada', cancelada: 'Cancelada',
  aprovado: 'Aprovado', rejeitado: 'Rejeitado', em_analise: 'Em análise',
  prevista: 'Prevista', reposicao: 'Reposição', extra: 'Extra', reforco: 'Reforço',
  complemento: 'Complemento', revisao: 'Revisão',
};

/** Ações da auditoria em português (o que foi feito com o usuário). */
export const ROTULO_ACAO: Record<string, string> = {
  usuario_criado: 'Cadastro criado',
  usuario_atualizado: 'Cadastro atualizado (lista de usuários)',
  usuario_identificacao_atualizada: 'Identificação alterada',
  usuario_dados_pessoais_atualizados: 'Dados pessoais alterados',
  usuario_endereco_atualizado: 'Endereço alterado',
  usuario_contato_emergencia_atualizado: 'Contato de emergência alterado',
  usuario_permissoes_atualizadas: 'Permissões alteradas',
  usuario_inativado: 'Usuário inativado',
  usuario_reativado: 'Usuário reativado',
  usuario_excluido: 'Usuário excluído',
  senha_alterada_admin: 'Senha redefinida pelo admin',
  aluno_vinculo_atualizado: 'Vínculo de aluno alterado',
  professor_vinculo_atualizado: 'Vínculo de professor alterado',
  professor_cadastrado: 'Entrou no Corpo Docente',
  professor_reativado: 'Reativado no Corpo Docente',
  professor_desativado: 'Saiu do Corpo Docente',
  foto_atualizada: 'Foto alterada',
};

export const rotuloAcao = (acao: string) => ROTULO_ACAO[acao] ?? acao.replace(/_/g, ' ');
export const rotuloStatus = (s?: string | null) => (s ? ROTULO_STATUS[s] ?? s.replace(/_/g, ' ') : '—');

export const statusBadge = (status?: string | null) => {
  switch (status) {
    case 'ativo':
    case 'pago':
    case 'aprovada':
    case 'aprovado':
    case 'emitido':
    case 'entregue':
    case 'concluido':
    case 'concluida':
    case 'ativa':
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    case 'pendente':
    case 'aguardando_pagamento':
    case 'pago_aguardando_envio':
    case 'em_analise':
    case 'enviado':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    case 'bloqueado':
    case 'vencido':
    case 'rejeitada':
    case 'rejeitado':
    case 'desistente':
    case 'churn':
      return 'bg-red-500/15 text-red-300 border-red-500/30';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
};

export const inputCls =
  'w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow transition-colors disabled:opacity-60';

/** Campo vazio vira null no payload. */
export const ouNull = (v?: string | null) => (v && v.trim() ? v.trim() : null);
