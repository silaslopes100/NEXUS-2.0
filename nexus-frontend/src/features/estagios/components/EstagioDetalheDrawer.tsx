import React, { useEffect, useState } from 'react';
import { Ban, CheckCircle2, Download, Loader2, X } from 'lucide-react';
import { UserAvatar } from '@/components/avatar/UserAvatar';
import { baixarArquivo, erroDeBlob } from '@/lib/download';
import { SubmissaoDetalhe, erroEstagio, estagiosApi, formatarDataHora } from '@/features/estagios/api';
import { ArquivosSubmissao, LinhaDoTempo, StatusEstagioBadge } from '@/features/estagios/components/EstagioComum';

interface Props {
  submissaoId: string;
  /** Admin (Coordenação): aprova/nega. Polo e Escola: somente leitura. */
  podeAvaliar: boolean;
  onFechar: () => void;
  onAtualizado: () => void;
}

const Campo: React.FC<{ rotulo: string; valor?: string | null }> = ({ rotulo, valor }) => (
  <div className="min-w-0">
    <p className="text-[11px] uppercase text-slate-500">{rotulo}</p>
    <p className="truncate text-sm text-white" title={valor || undefined}>{valor || '—'}</p>
  </div>
);

export const EstagioDetalheDrawer: React.FC<Props> = ({ submissaoId, podeAvaliar, onFechar, onAtualizado }) => {
  const [s, setS] = useState<SubmissaoDetalhe | null>(null);
  const [erro, setErro] = useState('');
  const [decisao, setDecisao] = useState<'aprovado' | 'negado' | null>(null);
  const [comentario, setComentario] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [baixando, setBaixando] = useState(false);

  useEffect(() => {
    let ativo = true;
    setS(null);
    setErro('');
    estagiosApi.detalhe(submissaoId)
      .then((d) => ativo && setS(d))
      .catch((e) => ativo && setErro(erroEstagio(e, 'Não foi possível carregar a solicitação.')));
    return () => { ativo = false; };
  }, [submissaoId]);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && onFechar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [onFechar]);

  const salvar = async () => {
    if (!decisao) return;
    setSalvando(true);
    setErro('');
    try {
      setS(await estagiosApi.avaliar(submissaoId, decisao, comentario.trim()));
      setDecisao(null);
      setComentario('');
      onAtualizado();
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível salvar a avaliação.'));
    } finally {
      setSalvando(false);
    }
  };

  const baixarComprovante = async () => {
    setBaixando(true);
    try {
      const { blob, nome } = await estagiosApi.comprovante(submissaoId);
      baixarArquivo(blob, nome);
    } catch (e) {
      setErro(await erroDeBlob(e, 'Não foi possível gerar o comprovante.'));
    } finally {
      setBaixando(false);
    }
  };

  const comentarioValido = decisao === 'aprovado' || comentario.trim().length >= 3;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onFechar}>
      <aside
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Solicitação de estágio"
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Solicitação de estágio</p>
            <h2 className="text-xl font-bold text-white">{s ? `Estágio · ${s.etapa_titulo}` : 'Carregando…'}</h2>
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {erro && <p role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}

        {!s ? (
          !erro && <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="space-y-6">
            <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
              <div className="flex items-center gap-3">
                <UserAvatar
                  usuarioId={s.aluno.usuario_id || undefined}
                  fotoUrl={s.aluno.foto_url}
                  nome={s.aluno.nome}
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue text-base font-bold text-on-accent"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold text-white">{s.aluno.nome}</p>
                  <p className="text-xs text-slate-500">Enviado em {formatarDataHora(s.enviado_em)}</p>
                </div>
                <StatusEstagioBadge status={s.status} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Campo rotulo="Matrícula" valor={s.aluno.numero_matricula} />
                <Campo rotulo="CPF" valor={s.aluno.cpf} />
                <Campo rotulo="Telefone" valor={s.aluno.telefone} />
                <Campo rotulo="E-mail" valor={s.aluno.email} />
                <Campo rotulo="Polo" valor={s.aluno.polo_nome} />
                <Campo rotulo="Escola" valor={s.aluno.escola_nome} />
              </div>
            </section>

            {s.comentario_feedback && s.status !== 'em_analise' && (
              <section className={`rounded-xl border p-4 ${s.status === 'negado' ? 'border-red-500/30 bg-red-500/10' : 'border-emerald-500/30 bg-emerald-500/10'}`}>
                <p className="text-xs font-semibold uppercase text-slate-400">Comentários de feedback</p>
                <p className="mt-1 whitespace-pre-line text-sm text-white">{s.comentario_feedback}</p>
              </section>
            )}

            {s.status === 'aprovado' && (
              <button
                type="button"
                onClick={() => void baixarComprovante()}
                disabled={baixando}
                className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/40 px-4 py-2 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50"
              >
                {baixando ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                Comprovante ({s.codigo_comprovante})
              </button>
            )}

            <section>
              <h3 className="mb-3 text-xs font-bold uppercase text-slate-500">Documentos e fotos</h3>
              <ArquivosSubmissao arquivos={s.arquivos} />
            </section>

            {podeAvaliar && s.status === 'em_analise' && (
              <section className="space-y-3 rounded-xl border border-blue-500/30 bg-blue-500/5 p-4">
                <h3 className="text-xs font-bold uppercase text-blue-300">Gestão de status</h3>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDecisao('aprovado')}
                    aria-pressed={decisao === 'aprovado'}
                    className={`inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-semibold ${
                      decisao === 'aprovado' ? 'border-emerald-500 bg-emerald-600 text-on-accent' : 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10'
                    }`}
                  >
                    <CheckCircle2 size={16} /> Aprovar
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecisao('negado')}
                    aria-pressed={decisao === 'negado'}
                    className={`inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-semibold ${
                      decisao === 'negado' ? 'border-red-500 bg-red-600 text-on-accent' : 'border-red-500/40 text-red-300 hover:bg-red-500/10'
                    }`}
                  >
                    <Ban size={16} /> Negar
                  </button>
                </div>
                {decisao && (
                  <>
                    <label className="block">
                      <span className="mb-1 block text-xs font-semibold text-slate-400">
                        Comentários de feedback {decisao === 'negado' ? '(obrigatório — o aluno recebe este texto)' : '(opcional)'}
                      </span>
                      <textarea
                        value={comentario}
                        onChange={(e) => setComentario(e.target.value)}
                        rows={4}
                        maxLength={4000}
                        placeholder={decisao === 'negado' ? 'Explique o que precisa ser corrigido…' : 'Mensagem ao aluno (opcional)'}
                        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                      />
                    </label>
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => { setDecisao(null); setComentario(''); }} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">
                        Cancelar
                      </button>
                      <button
                        type="button"
                        onClick={() => void salvar()}
                        disabled={salvando || !comentarioValido}
                        className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-on-accent disabled:opacity-50 ${
                          decisao === 'aprovado' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-red-600 hover:bg-red-500'
                        }`}
                      >
                        {salvando && <Loader2 size={15} className="animate-spin" />}
                        {decisao === 'aprovado' ? 'Confirmar aprovação' : 'Confirmar negativa'}
                      </button>
                    </div>
                    <p className="text-xs text-slate-500">
                      {decisao === 'aprovado'
                        ? 'O aluno é notificado e o comprovante de cumprimento do estágio é liberado.'
                        : 'O aluno é notificado com o comentário e poderá reenviar a documentação.'}
                    </p>
                  </>
                )}
              </section>
            )}

            <section>
              <h3 className="mb-3 text-xs font-bold uppercase text-slate-500">Histórico</h3>
              <LinhaDoTempo eventos={s.eventos} />
            </section>
          </div>
        )}
      </aside>
    </div>
  );
};
