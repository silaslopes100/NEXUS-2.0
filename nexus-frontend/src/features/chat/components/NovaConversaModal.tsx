import React, { useEffect, useState } from 'react';
import { GraduationCap, Loader2, Search, User, Users, X } from 'lucide-react';
import { Contato, ConversaDetalhe, TurmaChat, chatApi, erroApi } from '../api';
import { rotuloPerfil } from '../utils';
import { BuscaContatos } from './BuscaContatos';

type Aba = 'pessoa' | 'turma' | 'grupo';

interface Props {
  souAluno: boolean;
  onFechar: () => void;
  onAberta: (c: ConversaDetalhe) => void;
}

export const NovaConversaModal: React.FC<Props> = ({ souAluno, onFechar, onAberta }) => {
  const [aba, setAba] = useState<Aba>('pessoa');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onFechar();
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [onFechar]);

  const executar = async (fn: () => Promise<ConversaDetalhe>) => {
    setOcupado(true);
    setErro(null);
    try {
      onAberta(await fn());
    } catch (e) {
      setErro(erroApi(e));
    } finally {
      setOcupado(false);
    }
  };

  const abas: [Aba, string, React.ReactNode][] = [
    ['pessoa', 'Pessoa', <User key="p" size={14} />],
    ['turma', 'Grupo da turma', <GraduationCap key="t" size={14} />],
    ...(!souAluno ? [['grupo', 'Novo grupo', <Users key="g" size={14} />] as [Aba, string, React.ReactNode]] : []),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4" onMouseDown={onFechar}>
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl border border-slate-700 bg-slate-900 shadow-2xl sm:rounded-2xl"
        onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Nova conversa">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h3 className="font-semibold text-white">Nova conversa</h3>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="rolagem-sem-barra flex gap-1 overflow-x-auto border-b border-slate-800 px-3 pt-2 [&>button]:shrink-0">
          {abas.map(([v, r, ic]) => (
            <button key={v} type="button" onClick={() => { setAba(v); setErro(null); }}
              className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm ${aba === v ? 'border-nexus-yellow text-white' : 'border-transparent text-slate-400 hover:text-white'}`}>
              {ic}{r}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {erro && <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">{erro}</p>}
          {ocupado && <div className="mb-3 flex justify-center text-slate-400"><Loader2 size={18} className="animate-spin" /></div>}
          {aba === 'pessoa' && (
            <>
              {souAluno && (
                <p className="mb-3 text-xs text-slate-400">
                  Converse com professores, escola, polo e equipe. Para falar com colegas, use o grupo da sua turma.
                </p>
              )}
              <BuscaContatos onEscolher={(c: Contato) => void executar(() => chatApi.iniciarIndividual(c.id))} />
            </>
          )}
          {aba === 'turma' && <TurmasLista onEscolher={(t) => void executar(() => chatApi.abrirGrupoTurma(t.id))} />}
          {aba === 'grupo' && <NovoGrupoForm ocupado={ocupado} onCriar={(titulo, ids) => void executar(() => chatApi.criarGrupo(titulo, ids))} />}
        </div>
      </div>
    </div>
  );
};

const TurmasLista: React.FC<{ onEscolher: (t: TurmaChat) => void }> = ({ onEscolher }) => {
  const [busca, setBusca] = useState('');
  const [itens, setItens] = useState<TurmaChat[] | null>(null);

  useEffect(() => {
    let vivo = true;
    setItens(null);
    const id = window.setTimeout(() => {
      chatApi.turmas(busca.trim()).then((r) => vivo && setItens(r)).catch(() => vivo && setItens([]));
    }, 300);
    return () => { vivo = false; window.clearTimeout(id); };
  }, [busca]);

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2">
        <Search size={14} className="text-slate-500" />
        <input autoFocus value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Turma, curso ou escola"
          className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none" />
      </label>
      <div className="max-h-72 overflow-y-auto rounded-xl border border-slate-800">
        {itens === null ? (
          <div className="flex justify-center p-4 text-slate-400"><Loader2 size={16} className="animate-spin" /></div>
        ) : itens.length === 0 ? (
          <p className="p-4 text-center text-xs text-slate-500">Nenhuma turma disponível.</p>
        ) : (
          itens.map((t) => (
            <button key={t.id} type="button" onClick={() => onEscolher(t)}
              className="flex w-full items-center justify-between gap-3 border-b border-slate-800/60 px-3 py-2.5 text-left last:border-0 hover:bg-slate-800/60">
              <div className="min-w-0">
                <p className="truncate text-sm text-white">{t.nome}</p>
                <p className="truncate text-[11px] text-slate-400">
                  {[t.curso_nome, t.escola_nome || t.polo_nome].filter(Boolean).join(' · ')}
                </p>
              </div>
              <span className="shrink-0 text-[11px] text-slate-500">{t.conversa_id ? 'Abrir' : 'Criar grupo'}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
};

const NovoGrupoForm: React.FC<{ ocupado: boolean; onCriar: (titulo: string, ids: string[]) => void }> = ({ ocupado, onCriar }) => {
  const [titulo, setTitulo] = useState('');
  const [membros, setMembros] = useState<Contato[]>([]);
  const alunos = membros.filter((m) => m.perfil?.toLowerCase() === 'aluno').length;

  return (
    <div className="space-y-3">
      <input value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} placeholder="Nome do grupo"
        className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-nexus-yellow/50 focus:outline-none" />
      {membros.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {membros.map((m) => (
            <span key={m.id} className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-200">
              {m.nome} <span className="text-slate-500">{rotuloPerfil(m.perfil)}</span>
              <button type="button" aria-label={`Remover ${m.nome}`} onClick={() => setMembros((l) => l.filter((x) => x.id !== m.id))}
                className="text-slate-400 hover:text-red-300"><X size={12} /></button>
            </span>
          ))}
        </div>
      )}
      <BuscaContatos autoFocus={false} excluir={new Set(membros.map((m) => m.id))} ocultarAlunos={alunos >= 1}
        onEscolher={(c) => setMembros((l) => [...l, c])} />
      <p className="text-[11px] text-slate-500">
        Grupos livres aceitam no máximo um aluno. Para reunir os alunos, use o grupo da turma.
      </p>
      <button type="button" disabled={ocupado || !titulo.trim() || membros.length === 0}
        onClick={() => onCriar(titulo.trim(), membros.map((m) => m.id))}
        className="w-full rounded-xl bg-nexus-yellow py-2.5 text-sm font-semibold text-ink hover:bg-nexus-yellow/90 disabled:opacity-50">
        Criar grupo
      </button>
    </div>
  );
};
