import React, { useState } from 'react';
import { Loader2, Shield, UserMinus, UserPlus, X } from 'lucide-react';
import { Contato, ConversaDetalhe, chatApi, erroApi } from '../api';
import { rotuloPerfil } from '../utils';
import { Avatar } from './Avatar';
import { BuscaContatos } from './BuscaContatos';

interface Props {
  detalhe: ConversaDetalhe;
  meuId: string;
  onFechar: () => void;
  onAtualizado: (d: ConversaDetalhe) => void;
}

/** Painel lateral com os participantes; moderadores adicionam/removem nos grupos. */
export const MembrosPainel: React.FC<Props> = ({ detalhe, meuId, onFechar, onAtualizado }) => {
  const [adicionando, setAdicionando] = useState(false);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const gerencia = detalhe.pode_gerenciar_membros;
  const grupoTurma = !!detalhe.turma_id;

  const alterar = async (adicionar: string[], remover: string[], chave: string) => {
    setOcupado(chave);
    setErro(null);
    try {
      onAtualizado(await chatApi.alterarMembros(detalhe.id, adicionar, remover));
      setAdicionando(false);
    } catch (e) {
      setErro(erroApi(e));
    } finally {
      setOcupado(null);
    }
  };

  const idsAtuais = new Set(detalhe.membros.map((m) => m.id));

  return (
    <aside className="absolute inset-0 z-20 flex flex-col border-l border-slate-800 bg-slate-900 lg:static lg:w-80">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <p className="font-semibold text-white">Participantes ({detalhe.membros.length})</p>
        <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400 hover:text-white"><X size={18} /></button>
      </div>
      {erro && <p className="border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-200">{erro}</p>}
      {gerencia && (
        <div className="border-b border-slate-800 p-3">
          {adicionando ? (
            <BuscaContatos
              excluir={idsAtuais}
              ocultarAlunos={grupoTurma}
              onEscolher={(c: Contato) => void alterar([c.id], [], `add-${c.id}`)}
              onCancelar={() => setAdicionando(false)}
            />
          ) : (
            <button type="button" onClick={() => setAdicionando(true)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 py-2 text-sm text-slate-200 hover:border-nexus-yellow/40">
              <UserPlus size={15} /> Adicionar participante
            </button>
          )}
          {grupoTurma && (
            <p className="mt-2 text-[11px] text-slate-500">
              Alunos e professores do grupo da turma são sincronizados com as matrículas e vínculos ativos.
            </p>
          )}
        </div>
      )}
      <ul className="min-h-0 flex-1 overflow-y-auto">
        {detalhe.membros.map((m) => (
          <li key={m.id} className="flex items-center gap-3 border-b border-slate-800/60 px-4 py-2.5">
            <Avatar nome={m.nome} usuarioId={m.id} fotoUrl={m.foto_url} tamanho="sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-white">{m.nome}{m.id === meuId && <span className="text-slate-500"> (você)</span>}</p>
              <p className="flex items-center gap-1 text-[11px] text-slate-400">
                {rotuloPerfil(m.perfil)}
                {m.papel === 'moderador' && <><Shield size={11} className="ml-1 text-blue-300" /> moderador</>}
              </p>
            </div>
            {gerencia && m.id !== meuId && detalhe.tipo === 'grupo' && (
              <button type="button" disabled={!!ocupado} aria-label={`Remover ${m.nome}`}
                onClick={() => window.confirm(`Remover ${m.nome} do grupo?`) && void alterar([], [m.id], `rm-${m.id}`)}
                className="rounded-lg p-1.5 text-slate-500 hover:bg-red-500/10 hover:text-red-300 disabled:opacity-40">
                {ocupado === `rm-${m.id}` ? <Loader2 size={15} className="animate-spin" /> : <UserMinus size={15} />}
              </button>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
};
