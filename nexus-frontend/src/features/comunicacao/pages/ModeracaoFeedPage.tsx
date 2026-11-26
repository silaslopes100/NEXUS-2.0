import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Check, CheckCheck, ExternalLink, Loader2, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { Avatar } from '@/features/chat/components/Avatar';
import { rotuloPerfil } from '@/features/chat/utils';
import {
  ItemModeracao,
  StatusComentario,
  atualizarContadoresMenu,
  feedApi,
  mensagemErro,
  tempoRelativo,
} from '../api';
import { usePerfilAtual } from '../usePerfilAtual';

const ABAS: { valor: StatusComentario; rotulo: string }[] = [
  { valor: 'pendente', rotulo: 'Pendentes' },
  { valor: 'aprovado', rotulo: 'Aprovados' },
  { valor: 'rejeitado', rotulo: 'Rejeitados' },
];
const POR_PAGINA = 30;

/** Moderação dos comentários: o admin vê todos; os demais publicadores, só os das próprias publicações. */
export const ModeracaoFeedPage: React.FC = () => {
  const { admin } = usePerfilAtual();
  const [aba, setAba] = useState<StatusComentario>('pendente');
  const [itens, setItens] = useState<ItemModeracao[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = useCallback(async (status: StatusComentario, desde: number) => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await feedApi.moderacao(status, desde, POR_PAGINA);
      setItens(r.itens);
      setTotal(r.total);
      setSelecionados([]);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar a moderação.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar(aba, offset);
  }, [aba, offset, carregar]);

  const moderar = async (ids: string[], acao: 'aprovar' | 'rejeitar') => {
    let motivo: string | undefined;
    if (acao === 'rejeitar' && ids.length === 1) {
      const m = window.prompt('Motivo da rejeição (opcional — fica só no registro da moderação):', '');
      if (m === null) return;
      motivo = m;
    }
    setOcupado(ids.length === 1 ? ids[0] : 'lote');
    try {
      if (ids.length === 1) {
        await (acao === 'aprovar' ? feedApi.aprovar(ids[0]) : feedApi.rejeitar(ids[0], motivo));
      } else {
        await feedApi.moderarLote(ids, acao);
      }
      setItens((atuais) => atuais.filter((i) => !ids.includes(i.id)));
      setTotal((t) => Math.max(0, t - ids.length));
      setSelecionados([]);
      atualizarContadoresMenu();
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setOcupado(null);
    }
  };

  const todosMarcados = itens.length > 0 && selecionados.length === itens.length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-300">
            <ShieldCheck size={24} />
          </span>
          <div>
            <h1 className="text-2xl font-extrabold text-white">Moderação do Feed</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              {admin
                ? 'Comentários aguardando aprovação em todas as publicações. Quem comentou vê o próprio comentário normalmente; os demais só depois de aprovado.'
                : 'Comentários feitos nas suas publicações. Aprove para que todos vejam.'}
            </p>
          </div>
        </div>
        <button type="button" onClick={() => void carregar(aba, offset)}
          className="inline-flex items-center gap-1.5 self-start rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">
          <RefreshCw size={14} /> Atualizar
        </button>
      </header>

      <nav className="rolagem-sem-barra flex gap-1 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 p-1 [&>*]:shrink-0" aria-label="Situação">
        {ABAS.map((a) => (
          <button key={a.valor} type="button" onClick={() => { setAba(a.valor); setOffset(0); }}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
              aba === a.valor ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
            {a.rotulo}
            {aba === a.valor && !carregando && <span className="ml-1.5 rounded-full bg-white/25 px-1.5 text-[11px]">{total}</span>}
          </button>
        ))}
      </nav>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {aba === 'pendente' && itens.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2 text-slate-300">
            <input type="checkbox" checked={todosMarcados}
              onChange={(e) => setSelecionados(e.target.checked ? itens.map((i) => i.id) : [])} />
            Selecionar todos
          </label>
          {selecionados.length > 0 && (
            <>
              <button type="button" disabled={ocupado === 'lote'} onClick={() => void moderar(selecionados, 'aprovar')}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
                <CheckCheck size={14} /> Aprovar {selecionados.length}
              </button>
              <button type="button" disabled={ocupado === 'lote'} onClick={() => void moderar(selecionados, 'rejeitar')}
                className="inline-flex items-center gap-1.5 rounded-xl bg-red-600/80 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50">
                <X size={14} /> Rejeitar {selecionados.length}
              </button>
            </>
          )}
        </div>
      )}

      {carregando ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : itens.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-400">
          {aba === 'pendente' ? 'Nenhum comentário aguardando moderação. 🎉' : 'Nada por aqui.'}
        </div>
      ) : (
        <ul className="space-y-3">
          {itens.map((i) => (
            <li key={i.id} className="flex gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              {aba === 'pendente' && (
                <input type="checkbox" className="mt-1" checked={selecionados.includes(i.id)} aria-label="Selecionar"
                  onChange={(e) => setSelecionados((s) => (e.target.checked ? [...s, i.id] : s.filter((x) => x !== i.id)))} />
              )}
              <Avatar nome={i.autor.nome} usuarioId={i.autor.id} fotoUrl={i.autor.foto_url} tamanho="sm" />
              <div className="min-w-0 flex-1 space-y-2">
                <p className="flex flex-wrap items-center gap-x-2 text-xs">
                  <span className="font-semibold text-slate-100">{i.autor.nome}</span>
                  <span className="text-slate-500">{rotuloPerfil(i.autor.perfil)}</span>
                  <span className="text-slate-500">· {tempoRelativo(i.criado_em)}</span>
                  {i.parent_id && <span className="rounded bg-slate-800 px-1.5 text-[10px] text-slate-400">resposta</span>}
                </p>
                <p className="whitespace-pre-wrap break-words text-sm text-slate-200">{i.texto}</p>
                <Link to={`/feed/${i.post_id}`}
                  className="flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs text-slate-400 hover:border-slate-700">
                  <ExternalLink size={12} className="mt-0.5 shrink-0" />
                  <span className="min-w-0">
                    <span className="font-semibold text-slate-300">Publicação de {i.post_autor_nome}:</span>{' '}
                    <span className="line-clamp-2">{i.post_trecho}</span>
                  </span>
                </Link>
                {aba !== 'pendente' && i.moderado_em && (
                  <p className="text-[11px] text-slate-500">
                    {aba === 'aprovado' ? 'Aprovado' : 'Rejeitado'} {i.moderado_por_nome ? `por ${i.moderado_por_nome}` : ''} · {tempoRelativo(i.moderado_em)}
                    {i.motivo_rejeicao && <> · Motivo: {i.motivo_rejeicao}</>}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 flex-col gap-2">
                {aba !== 'aprovado' && (
                  <button type="button" disabled={!!ocupado} onClick={() => void moderar([i.id], 'aprovar')}
                    className="inline-flex items-center gap-1 rounded-lg bg-emerald-600/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
                    {ocupado === i.id ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Aprovar
                  </button>
                )}
                {aba !== 'rejeitado' && (
                  <button type="button" disabled={!!ocupado} onClick={() => void moderar([i.id], 'rejeitar')}
                    className="inline-flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-500/10 disabled:opacity-50">
                    <X size={13} /> Rejeitar
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {total > POR_PAGINA && (
        <div className="flex items-center justify-center gap-3 text-sm text-slate-400">
          <button type="button" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - POR_PAGINA))}
            className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Anterior</button>
          <span>{offset + 1}–{Math.min(offset + POR_PAGINA, total)} de {total}</span>
          <button type="button" disabled={offset + POR_PAGINA >= total} onClick={() => setOffset((o) => o + POR_PAGINA)}
            className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Próxima</button>
        </div>
      )}
    </div>
  );
};
