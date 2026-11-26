/**
 * Rotas de destino dos indicadores de Polo e Escola.
 *
 * Cada indicador leva para a tela que lista o que ele conta, já filtrada pela
 * unidade. Indicador sem rota (`undefined`) é exibido sem link — o perfil Polo
 * não tem telas de Professores nem de Aulas.
 */

export type AreaIndicadores = 'admin' | 'polo';

export type IndicadorPolo =
  | 'escolas'
  | 'turmas'
  | 'professores'
  | 'alunos'
  | 'aulas'
  | 'licencas_estoque'
  | 'licencas_atribuidas'
  | 'licencas_movimentacoes'
  | 'pedidos_licencas'
  | 'pedidos_livros';

export type IndicadorEscola = Exclude<IndicadorPolo, 'escolas'> | 'licencas_alunos';

export type RotasIndicadores<K extends string> = Partial<Record<K, string>>;

export const areaDoPerfil = (role: string): AreaIndicadores => (role === 'admin' ? 'admin' : 'polo');

const comQuery = (path: string, params: Record<string, string | null | undefined>) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([chave, valor]) => {
    if (valor) query.set(chave, valor);
  });
  const texto = query.toString();
  return texto ? `${path}?${texto}` : path;
};

export const rotasIndicadoresPolo = (area: AreaIndicadores, poloId: string): RotasIndicadores<IndicadorPolo> => {
  if (area === 'admin') {
    const licencas = comQuery('/admin/licencas', { polo_id: poloId });
    return {
      escolas: comQuery('/admin/escolas', { polo_id: poloId }),
      turmas: comQuery('/admin/turmas-calendarios', { polo_id: poloId }),
      professores: comQuery('/admin/professores', { polo_id: poloId }),
      alunos: comQuery('/admin/alunos', { polo_id: poloId }),
      aulas: comQuery('/admin/aulas', { polo: poloId }),
      licencas_estoque: licencas,
      licencas_atribuidas: licencas,
      licencas_movimentacoes: licencas,
      pedidos_licencas: comQuery('/admin/pedidos', { polo_id: poloId, tipo: 'licenca' }),
      pedidos_livros: comQuery('/admin/pedidos', { polo_id: poloId, tipo: 'livro' }),
    };
  }
  return {
    escolas: '/polo/escolas/gestao',
    turmas: '/polo/turmas',
    alunos: '/polo/alunos',
    licencas_estoque: '/polo/licencas',
    licencas_atribuidas: '/polo/licencas',
    licencas_movimentacoes: '/polo/licencas',
    pedidos_licencas: comQuery('/polo/livros', { tipo: 'licenca' }),
    pedidos_livros: comQuery('/polo/livros', { tipo: 'livro' }),
  };
};

export const rotasIndicadoresEscola = (
  area: AreaIndicadores,
  escola: { id: string; polo_id: string | null },
): RotasIndicadores<IndicadorEscola> => {
  const poloId = escola.polo_id || undefined;
  if (area === 'admin') {
    const licencas = `/admin/escolas/${escola.id}/licencas`;
    return {
      turmas: comQuery('/admin/turmas-calendarios', { polo_id: poloId, escola_id: escola.id }),
      professores: comQuery('/admin/professores', { polo_id: poloId, escola_id: escola.id }),
      alunos: comQuery('/admin/alunos', { polo_id: poloId, escola_id: escola.id }),
      // A auditoria de aulas não filtra por escola: abre as aulas do polo.
      aulas: poloId ? comQuery('/admin/aulas', { polo: poloId }) : undefined,
      licencas_estoque: licencas,
      licencas_alunos: licencas,
      licencas_atribuidas: licencas,
      licencas_movimentacoes: licencas,
      pedidos_licencas: comQuery('/admin/pedidos', { polo_id: poloId, escola_id: escola.id, tipo: 'licenca' }),
      pedidos_livros: comQuery('/admin/pedidos', { polo_id: poloId, escola_id: escola.id, tipo: 'livro' }),
    };
  }
  const licencas = `/polo/escolas/${escola.id}/licencas`;
  return {
    turmas: comQuery('/polo/turmas', { escola_id: escola.id }),
    alunos: comQuery('/polo/alunos', { escola_id: escola.id }),
    licencas_estoque: licencas,
    licencas_alunos: licencas,
    licencas_atribuidas: licencas,
    licencas_movimentacoes: licencas,
    pedidos_licencas: comQuery('/polo/livros', { escola_id: escola.id, tipo: 'licenca' }),
    pedidos_livros: comQuery('/polo/livros', { escola_id: escola.id, tipo: 'livro' }),
  };
};

export const formatarEndereco = (endereco?: {
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
} | null): string => {
  if (!endereco) return '';
  const rua = [endereco.logradouro, endereco.numero, endereco.complemento].filter(Boolean).join(', ');
  const cidade = [endereco.cidade, endereco.estado].filter(Boolean).join('/');
  const cep = endereco.cep ? `CEP ${endereco.cep}` : '';
  return [rua, endereco.bairro, cidade, cep].filter(Boolean).join(' · ');
};
