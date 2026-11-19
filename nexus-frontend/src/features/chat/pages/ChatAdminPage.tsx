import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, FileDown, Loader2, Lock, Search, Trash2, Users } from 'lucide-react';
import { ConversaAdmin, TipoConversa, chatApi, erroApi } from '../api';
import { horaCurta, rotuloPerfil } from '../utils';

const POR_PAGINA = 30;

/** Gestão do Chat (Admin): todas as conversas, exportação em PDF e exclusão definitiva. */
export const ChatAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [busca, setBusca] = useState('');
  const [tipo, setTipo] = useState<TipoConversa | ''>('');
  const [pagina, setPagina] = useState(0);
  const [dados, setDados] = useState<{ total: number; itens: ConversaAdmin[] } | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    let vivo = true;
    setDados(null);
    const id = window.setTimeout(() => {
      chatApi.adminListar({ busca: busca.trim() || undefined, tipo: tipo || undefined, limite: POR_PAGINA, offset: pagina * POR_PAGINA })
        .then((r) => vivo && setDados(r))
        .catch((e) => { if (vivo) { setErro(erroApi(e)); setDados({ total: 0, itens: [] }); } });
    }, 300);
    return () => { vivo = false; window.clearTimeout(id); };
  }, [busca, tipo, pagina, recarga]);

  const exportar = async (c: ConversaAdmin) => {
    setOcupado(`exp-${c.id}`);
    setErro(null);
    try {
      const blob = await chatApi.exportar(c.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversa-${c.titulo}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErro(erroApi(e, 'Não foi possível exportar a conversa.'));
    } finally {
      setOcupado(null);
    }
  };

  const excluir = async (c: ConversaAdmin) => {
    if (!window.confirm(`Excluir DEFINITIVAMENTE a conversa "${c.titulo}" para todos os participantes?\n\nMensagens e anexos serão apagados e não poderão ser recuperados.`)) return;
    setOcupado(`del-${c.id}`);
    setErro(null);
    try {
      await chatApi.excluir(c.id);
      setRecarga((n) => n + 1);
    } catch (e) {
      setErro(erroApi(e, 'Não foi possível excluir a conversa.'));
    } finally {
      setOcupado(null);
    }
  };

  const totalPaginas = dados ? Math.max(1, Math.ceil(dados.total / POR_PAGINA)) : 1;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Gestão do Chat</h1>
        <p className="mt-1 text-sm text-slate-400">
          Todas as conversas da plataforma. Mensagens ficam 48h na base ativa e 90 dias no histórico.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="flex flex-1 items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2">
          <Search size={15} className="text-slate-500" />
          <input value={busca} onChange={(e) => { setBusca(e.target.value); setPagina(0); }}
            placeholder="Participante (nome ou e-mail) ou nome do grupo"
            className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none" />
        </label>
        <select value={tipo} onChange={(e) => { setTipo(e.target.value as TipoConversa | ''); setPagina(0); }}
          className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white">
          <option value="">Todos os tipos</option>
          <option value="individual">Individuais</option>
          <option value="grupo">Grupos</option>
        </select>
      </div>

      {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-200">{erro}</p>}

      <div className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
        {dados === null ? (
          <div className="flex justify-center p-10 text-slate-400"><Loader2 className="animate-spin" /></div>
        ) : dados.itens.length === 0 ? (
          <p className="p-10 text-center text-sm text-slate-500">Nenhuma conversa encontrada.</p>
        ) : (
          <ul className="divide-y divide-slate-800">
            {dados.itens.map((c) => (
              <li key={c.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 font-medium text-white">
                    {c.tipo === 'grupo' && <Users size={15} className="text-blue-300" />}
                    <span className="truncate">{c.titulo}</span>
                    {c.status === 'encerrada' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-300">
                        <Lock size={10} /> encerrada
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-slate-400">
                    {c.membros.slice(0, 6).map((m) => `${m.nome} (${rotuloPerfil(m.perfil)})`).join(', ')}
                    {c.membros.length > 6 && ` e mais ${c.membros.length - 6}`}
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {c.total_mensagens} mensagem(ns) · última {horaCurta(c.ultima_mensagem_em ?? c.criado_em) || '-'}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" onClick={() => navigate(`/chat?c=${c.id}`)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:border-nexus-yellow/40">
                    <Eye size={14} /> Ver
                  </button>
                  <button type="button" onClick={() => void exportar(c)} disabled={!!ocupado}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:border-blue-400/40 disabled:opacity-50">
                    {ocupado === `exp-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} PDF
                  </button>
                  <button type="button" onClick={() => void excluir(c)} disabled={!!ocupado}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-50">
                    {ocupado === `del-${c.id}` ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />} Excluir
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {dados && dados.total > POR_PAGINA && (
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>{dados.total} conversa(s)</span>
          <div className="flex items-center gap-2">
            <button type="button" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}
              className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Anterior</button>
            <span>{pagina + 1} / {totalPaginas}</span>
            <button type="button" disabled={pagina + 1 >= totalPaginas} onClick={() => setPagina((p) => p + 1)}
              className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Próxima</button>
          </div>
        </div>
      )}
    </div>
  );
};
