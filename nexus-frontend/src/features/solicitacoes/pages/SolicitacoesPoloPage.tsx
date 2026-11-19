import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, FileText, Loader2, X } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { cursosApiErrorMessage } from '@/features/cursos/api';
import { abrirPdf, erroDeBlob } from '@/lib/download';
import { brl, dataBR, Solicitacao, solicitacoesApi, STATUS_SOLICITACAO } from '@/features/solicitacoes/api';

type Aba = 'pendentes' | 'prestacao' | 'historico';

const ModalAtender: React.FC<{ poloId: string; s: Solicitacao; onFechar: () => void; onFeito: (msg: string) => void }> = ({
  poloId,
  s,
  onFechar,
  onFeito,
}) => {
  const [qtd, setQtd] = useState<Record<string, number>>(() =>
    Object.fromEntries(s.itens.map((i) => [i.id, Math.min(i.quantidade, Math.max(0, i.saldo_polo ?? i.quantidade))]))
  );
  const [recusando, setRecusando] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const total = s.itens.reduce((t, i) => t + (qtd[i.id] || 0) * i.valor_unitario, 0);

  const executar = async (acao: () => Promise<Solicitacao>, msg: (r: Solicitacao) => string) => {
    setEnviando(true);
    setErro('');
    try {
      onFeito(msg(await acao()));
    } catch (err) {
      setErro(cursosApiErrorMessage(err, 'Não foi possível concluir.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(e) => e.target === e.currentTarget && !enviando && onFechar()}>
      <div role="dialog" aria-modal="true" className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900">
        <header className="flex items-start justify-between border-b border-slate-800 p-5">
          <div>
            <h2 className="text-lg font-bold text-white">{s.numero} · {s.escola_nome}</h2>
            <p className="text-sm text-slate-400">Enviada em {dataBR(s.criado_em)}</p>
            {s.observacao && <p className="mt-1 text-sm text-slate-300">“{s.observacao}”</p>}
          </div>
          <button type="button" aria-label="Fechar" onClick={onFechar} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800"><X size={18} /></button>
        </header>
        <div className="space-y-3 p-5">
          {recusando ? (
            <label className="block">
              <span className="mb-1 block text-sm text-slate-300">Motivo da recusa (a Escola verá)</span>
              <textarea rows={3} autoFocus value={motivo} onChange={(e) => setMotivo(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
            </label>
          ) : (
            <>
              <p className="text-sm text-slate-400">Ajuste quanto vai entregar de cada disciplina (licença + livro).</p>
              {s.itens.map((i) => {
                const saldo = i.saldo_polo ?? 0;
                const falta = (qtd[i.id] || 0) > saldo;
                return (
                  <div key={i.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 p-3">
                    <div className="min-w-0">
                      <p className="font-medium text-white">{i.disciplina_nome}</p>
                      <p className={`text-xs ${saldo < i.quantidade ? 'text-amber-300' : 'text-slate-500'}`}>
                        Pedido: {i.quantidade} · seu estoque: {saldo} · {brl(i.valor_unitario)} cada
                      </p>
                    </div>
                    <input aria-label={`Entregar de ${i.disciplina_nome}`} inputMode="numeric" value={qtd[i.id] ?? 0}
                      onChange={(e) => setQtd((q) => ({ ...q, [i.id]: Math.min(i.quantidade, Number(e.target.value.replace(/\D/g, '')) || 0) }))}
                      className={`w-20 rounded-lg border bg-slate-950 px-2 py-1.5 text-center text-white ${falta ? 'border-red-500' : 'border-slate-700'}`} />
                  </div>
                );
              })}
              <p className="text-right font-semibold text-white">Valor da Nota: {brl(total)}</p>
            </>
          )}
          {erro && (
            <div className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              <AlertCircle size={16} className="mt-0.5 shrink-0" /> {erro}
            </div>
          )}
        </div>
        <footer className="flex flex-wrap justify-between gap-2 border-t border-slate-800 p-5">
          <button type="button" disabled={enviando} onClick={() => setRecusando((v) => !v)}
            className="rounded-xl border border-red-500/40 px-4 py-2.5 text-sm text-red-300 hover:bg-red-500/10">
            {recusando ? 'Voltar' : 'Recusar'}
          </button>
          {recusando ? (
            <button type="button" disabled={enviando || motivo.trim().length < 3}
              onClick={() => void executar(() => solicitacoesApi.recusar(poloId, s.id, motivo.trim()), (r) => `${r.numero} recusada. A Escola foi avisada.`)}
              className="rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-40">
              Confirmar recusa
            </button>
          ) : (
            <button type="button" disabled={enviando || !Object.values(qtd).some(Boolean)}
              onClick={() => void executar(
                () => solicitacoesApi.atender(poloId, s.id, s.itens.map((i) => ({ item_id: i.id, quantidade_atendida: qtd[i.id] || 0 }))),
                (r) => `${r.numero} atendida. Licenças enviadas à Escola e Nota ${r.nota_numero} emitida.`
              )}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-40">
              {enviando ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />} Atender e emitir Nota
            </button>
          )}
        </footer>
      </div>
    </div>
  );
};

export const SolicitacoesPoloPage: React.FC = () => {
  const poloId = useAuthStore((s) => s.user?.polo_id) || '';
  const [lista, setLista] = useState<Solicitacao[] | null>(null);
  const [aba, setAba] = useState<Aba>('pendentes');
  const [aberta, setAberta] = useState<Solicitacao | null>(null);
  const [aviso, setAviso] = useState('');
  const [erro, setErro] = useState('');
  const [confirmando, setConfirmando] = useState<string | null>(null);

  const carregar = () =>
    solicitacoesApi
      .doPolo(poloId)
      .then(setLista)
      .catch((err) => {
        setLista([]);
        setErro(cursosApiErrorMessage(err, 'Não foi possível carregar as solicitações.'));
      });

  useEffect(() => {
    if (poloId) void carregar();
    else setLista([]);
  }, [poloId]);

  if (!poloId) return <p className="p-8 text-center text-slate-400">Seu usuário não está vinculado a um Polo.</p>;

  const pendentes = (lista || []).filter((s) => s.status === 'pendente');
  const comNota = (lista || []).filter((s) => s.nota_id);
  const aReceber = comNota.filter((s) => s.nota_status === 'emitida').reduce((t, s) => t + Number(s.nota_valor_total || 0), 0);
  const itensAba = aba === 'pendentes' ? pendentes : aba === 'prestacao' ? comNota : lista || [];

  const repasse = async (s: Solicitacao) => {
    if (!s.nota_id) return;
    setConfirmando(s.id);
    setErro('');
    try {
      await solicitacoesApi.repasseRecebido(poloId, s.nota_id);
      setAviso(`Repasse da Nota ${s.nota_numero} registrado.`);
      void carregar();
    } catch (err) {
      setErro(cursosApiErrorMessage(err, 'Não foi possível registrar o repasse.'));
    } finally {
      setConfirmando(null);
    }
  };

  const baixarNota = async (s: Solicitacao) => {
    try {
      abrirPdf(await solicitacoesApi.notaPdf(s.id), `${s.nota_numero || 'nota'}.pdf`);
    } catch (err) {
      setErro(await erroDeBlob(err, 'Não foi possível gerar a Nota.'));
    }
  };

  const abas: { id: Aba; rotulo: string; n?: number }[] = [
    { id: 'pendentes', rotulo: 'Pendentes', n: pendentes.length },
    { id: 'prestacao', rotulo: 'Prestação de contas' },
    { id: 'historico', rotulo: 'Todas' },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <h1 className="text-2xl font-bold text-white">Solicitações das Escolas</h1>
        <p className="text-sm text-slate-400">Atenda os pedidos de licenças e livros; a Nota de Prestação de Contas é emitida na hora.</p>
      </header>
      {aviso && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{aviso}</div>}
      {erro && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</div>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900 p-1">
          {abas.map((a) => (
            <button key={a.id} type="button" role="tab" aria-selected={aba === a.id} onClick={() => setAba(a.id)}
              className={`rounded-lg px-3 py-1.5 text-sm ${aba === a.id ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
              {a.rotulo}
              {a.n ? <span className="ml-1.5 rounded-full bg-nexus-yellow px-1.5 text-xs font-bold text-ink">{a.n}</span> : null}
            </button>
          ))}
        </div>
        {aReceber > 0 && <p className="text-sm text-amber-200">A receber das Escolas: <strong>{brl(aReceber)}</strong></p>}
      </div>

      {lista === null ? (
        <div className="flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="space-y-3">
          {itensAba.map((s) => (
            <article key={s.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">{s.escola_nome} · {s.numero}</p>
                  <p className="text-xs text-slate-500">
                    {dataBR(s.criado_em)} · {s.itens.reduce((t, i) => t + i.quantidade, 0)} unidade(s) · {brl(s.valor_estimado)}
                  </p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${STATUS_SOLICITACAO[s.status].classe}`}>
                  {s.status === 'pendente' ? 'Pendente' : STATUS_SOLICITACAO[s.status].texto}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-300">
                {s.itens.map((i) => `${i.disciplina_nome} (${s.status === 'pendente' ? i.quantidade : `${i.quantidade_atendida}/${i.quantidade}`})`).join(' · ')}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {s.status === 'pendente' && (
                  <button type="button" onClick={() => setAberta(s)}
                    className="rounded-xl bg-nexus-yellow px-4 py-2 text-sm font-bold text-ink">Analisar e atender</button>
                )}
                {s.nota_id && (
                  <>
                    <span className="text-sm text-slate-400">
                      Nota {s.nota_numero} · {brl(s.nota_valor_total)} ·{' '}
                      {s.nota_status === 'repasse_recebido'
                        ? <span className="text-emerald-300">repasse recebido</span>
                        : <span className="text-amber-300">vence {dataBR(s.nota_vencimento)}</span>}
                    </span>
                    <button type="button" onClick={() => void baixarNota(s)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800">
                      <FileText size={14} /> Nota
                    </button>
                    {s.nota_status === 'emitida' && (
                      <button type="button" disabled={confirmando === s.id} onClick={() => void repasse(s)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 px-3 py-1.5 text-sm text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50">
                        {confirmando === s.id ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                        Marcar repasse recebido
                      </button>
                    )}
                  </>
                )}
              </div>
            </article>
          ))}
          {itensAba.length === 0 && (
            <p className="rounded-2xl border border-slate-800 bg-slate-900 p-10 text-center text-sm text-slate-500">
              {aba === 'pendentes' ? 'Nenhuma solicitação aguardando.' : 'Nada por aqui ainda.'}
            </p>
          )}
        </div>
      )}

      {aberta && (
        <ModalAtender poloId={poloId} s={aberta} onFechar={() => setAberta(null)}
          onFeito={(msg) => {
            setAberta(null);
            setAviso(msg);
            void carregar();
          }} />
      )}
    </div>
  );
};
