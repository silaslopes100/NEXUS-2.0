import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, AlertTriangle, ChevronLeft, ChevronRight, ExternalLink, Inbox, Loader2, RefreshCw } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { AbaHistorico, HistoricoItem, HistoricoResponse } from '@/types/admin';
import {
  ROTULO_CAMPO, fmtBRL, fmtNum, formatarData, mensagemErro, rotuloAcao, rotuloStatus, statusBadge,
} from './fichaUtils';

type Valor = 'moeda' | 'nota' | 'pct' | 'horas' | null;

interface Grupo {
  titulo: string;
  colunaTitulo: string;
  colunaDetalhe?: string;
  valor: Valor;
  colunaValor?: string;
  semData?: boolean;
}

const GRUPOS: Record<string, Grupo> = {
  turmas: { titulo: 'Turmas', colunaTitulo: 'Turma', colunaDetalhe: 'Curso', valor: 'pct', colunaValor: 'Frequência (RN07)' },
  notas: { titulo: 'Notas', colunaTitulo: 'Disciplina', colunaDetalhe: 'Turma', valor: 'nota', colunaValor: 'Nota' },
  certificados: { titulo: 'Certificados', colunaTitulo: 'Curso', valor: null },
  estagios: { titulo: 'Estágios', colunaTitulo: 'Etapa', valor: 'horas', colunaValor: 'Horas' },
  vinculos: { titulo: 'Disciplinas lecionadas', colunaTitulo: 'Disciplina', colunaDetalhe: 'Turma · curso', valor: 'horas', colunaValor: 'Horas ministradas', semData: true },
  aulas: { titulo: 'Aulas ministradas', colunaTitulo: 'Disciplina', colunaDetalhe: 'Turma · aula', valor: 'horas', colunaValor: 'Horas' },
  pagamentos: { titulo: 'Cobranças', colunaTitulo: 'Descrição', colunaDetalhe: 'Forma', valor: 'moeda', colunaValor: 'Valor' },
  pedidos: { titulo: 'Pedidos', colunaTitulo: 'Pedido', colunaDetalhe: 'Tipo', valor: 'moeda', colunaValor: 'Total' },
  licencas: { titulo: 'Licenças', colunaTitulo: 'Disciplina', colunaDetalhe: 'Nº da licença', valor: null },
  transferencias: { titulo: 'Transferências', colunaTitulo: 'Tipo', colunaDetalhe: 'Origem → destino', valor: null },
  desistencias: { titulo: 'Desistências e reingressos', colunaTitulo: 'Evento', colunaDetalhe: 'Motivo', valor: null },
  status: { titulo: 'Mudanças de status e perfil', colunaTitulo: 'Ação', colunaDetalhe: 'Feita por', valor: null },
};

const ORDEM_GRUPOS: Record<Exclude<AbaHistorico, 'auditoria'>, string[]> = {
  academico: ['turmas', 'notas', 'certificados', 'estagios', 'vinculos', 'aulas'],
  financeiro: ['pagamentos', 'pedidos', 'licencas'],
  movimentacoes: ['transferencias', 'desistencias', 'status'],
};

const VAZIO: Record<AbaHistorico, string> = {
  academico: 'Nenhum registro acadêmico (turmas, notas, certificados, estágios ou aulas).',
  financeiro: 'Nenhuma cobrança, pedido ou licença.',
  movimentacoes: 'Nenhuma transferência, desistência ou mudança de status.',
  auditoria: 'Nenhuma alteração registrada para este usuário.',
};

const PAGINA_AUDITORIA = 20;

function formatarValor(tipo: Valor, v?: number | null): string {
  if (v == null) return '—';
  if (tipo === 'moeda') return fmtBRL(v);
  if (tipo === 'pct') return `${fmtNum(v, 1)}%`;
  if (tipo === 'horas') return `${fmtNum(v, 1)}h`;
  if (tipo === 'nota') return fmtNum(v, 2);
  return String(v);
}

const Status: React.FC<{ s?: string | null }> = ({ s }) =>
  s ? <span className={`px-2 py-0.5 rounded-full text-[11px] border whitespace-nowrap ${statusBadge(s)}`}>{rotuloStatus(s)}</span> : <>—</>;

const TabelaGrupo: React.FC<{ chave: string; itens: HistoricoItem[] }> = ({ chave, itens }) => {
  const g = GRUPOS[chave] ?? { titulo: chave, colunaTitulo: 'Item', valor: null };
  const comDetalhe = Boolean(g.colunaDetalhe);
  const titulo = (i: HistoricoItem) => (chave === 'status' ? rotuloAcao(i.titulo) : i.titulo);
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
        {g.titulo} <span className="text-slate-500 font-semibold normal-case">({itens.length})</span>
      </h3>
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-xs">
          <thead className="bg-slate-950/80 text-slate-400 text-left">
            <tr>
              {!g.semData && <th className="px-3 py-2 font-semibold">Data</th>}
              <th className="px-3 py-2 font-semibold">{g.colunaTitulo}</th>
              {comDetalhe && <th className="px-3 py-2 font-semibold">{g.colunaDetalhe}</th>}
              <th className="px-3 py-2 font-semibold">Situação</th>
              {g.valor && <th className="px-3 py-2 font-semibold text-right">{g.colunaValor}</th>}
              <th className="px-3 py-2"><span className="sr-only">Abrir</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {itens.map((i, idx) => (
              <tr key={`${i.id ?? idx}-${idx}`}>
                {!g.semData && <td className="px-3 py-2 text-slate-400 whitespace-nowrap tabular-nums">{formatarData(i.data, chave === 'status')}</td>}
                <td className="px-3 py-2 text-white font-semibold">{titulo(i)}</td>
                {comDetalhe && <td className="px-3 py-2 text-slate-300">{i.detalhe || '—'}</td>}
                <td className="px-3 py-2"><Status s={i.status} /></td>
                {g.valor && (
                  <td className="px-3 py-2 text-right text-slate-200 tabular-nums whitespace-nowrap">
                    {formatarValor(g.valor, i.valor)}
                    {chave === 'turmas' && i.extra?.em_risco && (
                      <span className="ml-2 inline-flex items-center gap-1 text-[10px] font-bold text-red-300">
                        <AlertTriangle className="w-3 h-3" aria-hidden /> em risco
                      </span>
                    )}
                  </td>
                )}
                <td className="px-3 py-2 text-right">
                  {i.link && (
                    <Link to={i.link} className="inline-flex text-slate-500 hover:text-nexus-yellow" title="Abrir a tela de origem">
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span className="sr-only">Abrir {titulo(i)}</span>
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

function valorLegivel(v: unknown): string {
  if (v == null || v === '') return '—';
  if (Array.isArray(v)) return v.join(', ') || '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

const ListaAuditoria: React.FC<{ itens: HistoricoItem[] }> = ({ itens }) => (
  <ol className="space-y-2">
    {itens.map((i, idx) => {
      const antes = (i.extra?.dados_antes ?? {}) as Record<string, unknown>;
      const depois = (i.extra?.dados_depois ?? {}) as Record<string, unknown>;
      const campos = Array.from(new Set([...Object.keys(antes), ...Object.keys(depois)]));
      return (
        <li key={i.id ?? idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-xs font-bold text-white">{rotuloAcao(i.titulo)}</p>
            <p className="text-[11px] text-slate-500 tabular-nums">
              {formatarData(i.data, true)} · {i.detalhe}
              {i.extra?.ip ? ` · IP ${i.extra.ip}` : ''}
            </p>
          </div>
          {campos.length > 0 && (
            <dl className="mt-2 grid grid-cols-1 sm:grid-cols-[minmax(0,10rem)_1fr] gap-x-3 gap-y-1 text-[11px]">
              {campos.map((c) => (
                <React.Fragment key={c}>
                  <dt className="text-slate-500">{ROTULO_CAMPO[c] ?? c.replace(/_/g, ' ')}</dt>
                  <dd className="text-slate-300 break-words">
                    {c in antes && <span className="line-through text-slate-500 mr-2">{valorLegivel(antes[c])}</span>}
                    {c in depois && <span>{valorLegivel(depois[c])}</span>}
                  </dd>
                </React.Fragment>
              ))}
            </dl>
          )}
        </li>
      );
    })}
  </ol>
);

/** Aba de histórico da ficha: carrega só quando aberta. */
export const HistoricoTab: React.FC<{ usuarioId: string; aba: AbaHistorico; versao: number }> = ({ usuarioId, aba, versao }) => {
  const [dados, setDados] = useState<HistoricoResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const auditoria = aba === 'auditoria';

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await adminApi.historicoUsuario(usuarioId, aba, auditoria ? { limit: PAGINA_AUDITORIA, offset } : { limit: 500 }));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar o histórico.'));
    } finally {
      setCarregando(false);
    }
  }, [usuarioId, aba, auditoria, offset]);

  useEffect(() => {
    setOffset(0);
  }, [aba]);

  useEffect(() => {
    void carregar();
  }, [carregar, versao]);

  if (carregando && !dados) {
    return (
      <div className="flex items-center gap-2 py-12 justify-center text-sm text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin text-nexus-yellow" /> Carregando histórico...
      </div>
    );
  }
  if (erro) {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-sm text-red-200">
        <AlertCircle className="w-5 h-5" /> {erro}
        <button type="button" onClick={() => void carregar()} className="ml-auto px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 text-xs font-semibold flex items-center gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" /> Tentar de novo
        </button>
      </div>
    );
  }
  const itens = dados?.items ?? [];
  if (!itens.length) {
    return (
      <div className="flex flex-col items-center gap-2 py-12 text-center text-sm text-slate-500">
        <Inbox className="w-8 h-8 text-slate-600" aria-hidden />
        {VAZIO[aba]}
      </div>
    );
  }

  if (auditoria) {
    const total = dados?.total ?? 0;
    const pagina = Math.floor(offset / PAGINA_AUDITORIA) + 1;
    const paginas = Math.max(1, Math.ceil(total / PAGINA_AUDITORIA));
    return (
      <div className={`space-y-4 ${carregando ? 'opacity-60' : ''}`}>
        <ListaAuditoria itens={itens} />
        {paginas > 1 && (
          <nav className="flex items-center justify-end gap-2 text-xs text-slate-400" aria-label="Páginas da auditoria">
            <span>Página {pagina} de {paginas} · {total} registro(s)</span>
            <button type="button" aria-label="Página anterior" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGINA_AUDITORIA))}
              className="p-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 disabled:opacity-40">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button type="button" aria-label="Próxima página" disabled={pagina >= paginas}
              onClick={() => setOffset(offset + PAGINA_AUDITORIA)}
              className="p-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 disabled:opacity-40">
              <ChevronRight className="w-4 h-4" />
            </button>
          </nav>
        )}
      </div>
    );
  }

  const porGrupo = new Map<string, HistoricoItem[]>();
  for (const i of itens) porGrupo.set(i.grupo, [...(porGrupo.get(i.grupo) ?? []), i]);
  const ordem = ORDEM_GRUPOS[aba];
  const grupos = [...porGrupo.keys()].sort((a, b) => ordem.indexOf(a) - ordem.indexOf(b));
  return (
    <div className={`space-y-6 ${carregando ? 'opacity-60' : ''}`}>
      {grupos.map((g) => <TabelaGrupo key={g} chave={g} itens={porGrupo.get(g)!} />)}
    </div>
  );
};
