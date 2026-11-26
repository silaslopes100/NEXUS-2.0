import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertCircle, AlertTriangle, ArrowLeft, Ban, CalendarDays, Edit2, Loader2, Lock, RotateCcw, Trash2, X,
} from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import { TurmaCargaHorariaPanel } from '@/features/carga_horaria/components/TurmaCargaHorariaPanel';
import {
  formatarData,
  formatarHora,
  PrazosEad,
  ROTULO_MODALIDADE,
  ROTULO_SITUACAO_TURMA,
  ROTULO_TURNO,
  SituacaoPrazoEad,
  somenteLeitura,
  Turma,
  turmasApi,
} from '@/features/turmas/api';
import { TurmaAlunosPanel } from '@/features/turmas/components/TurmaAlunosPanel';
import { inputCls, TurmaFormModal, useOpcoesTurma } from '@/features/turmas/components/TurmaFormModal';
import { TurmaProfessoresPanel } from '@/features/turmas/components/TurmaProfessoresPanel';
import { TurmaHistoricoPanel } from '@/features/turmas/components/TurmaHistoricoPanel';
import { baseTurmas, SeloSituacao } from '@/features/turmas/pages/TurmasPage';

type Aba = 'dados' | 'alunos' | 'professores' | 'carga' | 'prazos' | 'historico';

const Dado: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
    <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
    <p className="mt-1 break-words text-sm font-semibold text-white">{children}</p>
  </div>
);

const COR_PRAZO: Record<SituacaoPrazoEad, string> = {
  aguardando: 'border-slate-700 bg-slate-800 text-slate-300',
  liberada: 'border-blue-500/40 bg-blue-500/10 text-blue-200',
  concluida: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  vencida: 'border-red-500/40 bg-red-500/10 text-red-200',
};
const ROTULO_PRAZO: Record<SituacaoPrazoEad, string> = {
  aguardando: 'Aguardando', liberada: 'Liberada', concluida: 'Concluída', vencida: 'Vencida',
};

const PrazosEadTab: React.FC<{ turma: Turma }> = ({ turma }) => {
  const [dados, setDados] = useState<PrazosEad | null>(null);
  const [erro, setErro] = useState('');
  useEffect(() => {
    turmasApi.prazosEad(turma.id).then(setDados).catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar os prazos.')));
  }, [turma.id]);
  if (erro) return <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>;
  if (!dados) return <div className="flex justify-center py-12"><Loader2 className="animate-spin text-slate-400" /></div>;
  const r = dados.regras;
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        Regras do calendário: {r.ead_liberacao === 'todas_no_inicio' ? 'todas as disciplinas liberadas no início' : 'uma disciplina por vez'};{' '}
        prazo padrão de {r.ead_prazo_dias_padrao} dias
        {r.ead_liberacao !== 'todas_no_inicio' && (
          <>; a próxima libera {r.ead_proxima_libera === 'anterior_vencida' ? 'quando a anterior vence'
            : r.ead_proxima_libera === 'anterior_concluida' ? 'só quando a anterior é concluída'
              : 'quando a anterior é concluída ou vence'}</>
        )}
        ; vencida {r.ead_ao_vencer === 'alertar' ? 'só gera aviso' : 'é bloqueada no AVA'}.
      </p>
      {!dados.alunos.length ? (
        <p className="py-10 text-center text-sm text-slate-400">Nenhum aluno ativo na turma.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-3">Aluno</th>
                <th className="p-3">Início</th>
                <th className="p-3">Disciplinas (liberação → data limite)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {dados.alunos.map((a) => (
                <tr key={a.aluno_id} className="align-top">
                  <td className="p-3">
                    <span className="font-semibold text-white">{a.nome || a.aluno_id}</span>
                    {a.numero_matricula && <span className="block text-xs text-slate-500">{a.numero_matricula}</span>}
                    {a.vencidas > 0 && (
                      <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-red-300">
                        <AlertTriangle className="h-3 w-3" aria-hidden /> {a.vencidas} vencida(s)
                      </span>
                    )}
                  </td>
                  <td className="p-3 whitespace-nowrap tabular-nums">{formatarData(a.inicio)}</td>
                  <td className="p-3">
                    <ul className="flex flex-wrap gap-1.5">
                      {a.disciplinas.map((d) => (
                        <li key={d.disciplina_id} className={`rounded-lg border px-2 py-1 text-[11px] ${COR_PRAZO[d.situacao]}`}>
                          <span className="font-semibold">{d.ordem}. {d.nome}</span> · {ROTULO_PRAZO[d.situacao]}
                          <span className="block tabular-nums opacity-80">
                            {d.liberada_em ? `${formatarData(d.liberada_em)} → ${formatarData(d.data_limite)}` : 'Data a definir'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const CancelarModal: React.FC<{ turma: Turma; aoFechar: () => void; aoConcluir: (t: Turma) => void }> = ({
  turma, aoFechar, aoConcluir,
}) => {
  const [motivo, setMotivo] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (motivo.trim().length < 3) {
      setErro('Descreva o motivo (mínimo de 3 caracteres).');
      return;
    }
    setSalvando(true);
    setErro('');
    try {
      aoConcluir(await turmasApi.cancelar(turma.id, motivo.trim()));
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível cancelar a turma.'));
      setSalvando(false);
    }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto">
      <form onSubmit={enviar} role="dialog" aria-modal="true" aria-labelledby="cancelar-turma-titulo"
        className="my-auto glass w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 id="cancelar-turma-titulo" className="flex items-center gap-2 text-lg font-bold text-white">
            <Ban className="h-5 w-5 text-red-400" /> Cancelar turma
          </h2>
          <button type="button" onClick={aoFechar} aria-label="Fechar" className="rounded-lg p-1 text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        <p className="text-sm text-slate-400">
          <strong className="text-white">{turma.nome}</strong> fica só leitura: sem matrículas, professores, cronograma ou atas
          novas. O histórico é mantido e o admin pode reabrir depois.
        </p>
        <label className="block space-y-1.5 text-sm text-slate-300">
          <span>Motivo *</span>
          <textarea className={`${inputCls} min-h-[90px]`} maxLength={1000} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </label>
        {erro && <p role="alert" className="text-sm text-red-300">{erro}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={aoFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300">Voltar</button>
          <button type="submit" disabled={salvando} className="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-red-500 disabled:opacity-60">
            {salvando && <Loader2 size={14} className="animate-spin" />} Cancelar turma
          </button>
        </div>
      </form>
    </div>
  );
};

export const TurmaDetalhePage: React.FC = () => {
  const { turmaId } = useParams<{ turmaId: string }>();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { role, isAdmin, isPolo, cursos, polos, escolas } = useOpcoesTurma();
  const base = baseTurmas(role);
  const [turma, setTurma] = useState<Turma | null>(null);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [modal, setModal] = useState<'editar' | 'cancelar' | 'excluir' | null>(null);
  const [processando, setProcessando] = useState(false);

  const carregar = useCallback(async () => {
    if (!turmaId) return;
    try {
      setTurma(await turmasApi.obter(turmaId));
      setErro('');
    } catch (e) {
      setErro(apiErrorMessage(e, 'Turma não encontrada.'));
    }
  }, [turmaId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const ead = turma?.modalidade === 'ead';
  const abas: { id: Aba; rotulo: string }[] = [
    { id: 'dados', rotulo: 'Dados' },
    { id: 'alunos', rotulo: `Alunos${turma ? ` (${turma.total_alunos}${turma.vagas ? `/${turma.vagas}` : ''})` : ''}` },
    { id: 'professores', rotulo: 'Professores' },
    { id: 'carga', rotulo: 'Cronograma, andamento e frequência' },
    ...(ead ? [{ id: 'prazos' as Aba, rotulo: 'Prazos EAD' }] : []),
    { id: 'historico', rotulo: 'Histórico' },
  ];
  const abaParam = params.get('aba') as Aba | null;
  const aba: Aba = abas.some((a) => a.id === abaParam) ? (abaParam as Aba) : 'dados';
  const trocarAba = (nova: Aba) => {
    const p = new URLSearchParams(params);
    if (nova === 'dados') p.delete('aba'); else p.set('aba', nova);
    setParams(p, { replace: true });
  };

  if (erro && !turma) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-16 text-center">
        <AlertCircle className="mx-auto h-10 w-10 text-red-400" />
        <p className="text-sm text-slate-300">{erro}</p>
        <Link to={base} className="text-sm font-semibold text-blue-400">Voltar para as turmas</Link>
      </div>
    );
  }
  if (!turma) {
    return <div className="flex justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-nexus-yellow" /></div>;
  }

  const leitura = somenteLeitura(turma);
  const podeCancelar = (isAdmin || isPolo) && !leitura;
  const podeExcluir = !leitura && turma.total_alunos === 0;

  const reabrir = async () => {
    setProcessando(true);
    try {
      setTurma(await turmasApi.reabrir(turma.id));
      setAviso('Turma reaberta.');
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível reabrir a turma.'));
    } finally {
      setProcessando(false);
    }
  };

  const excluir = async () => {
    setProcessando(true);
    try {
      await turmasApi.excluir(turma.id);
      navigate(base);
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível excluir a turma.'));
      setModal(null);
      setProcessando(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="glass space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-6">
        <Link to={base} className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-nexus-yellow">
          <ArrowLeft className="h-3.5 w-3.5" /> Voltar para as turmas
        </Link>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="font-mono text-xs text-slate-400">{turma.codigo || '—'} · {ROTULO_MODALIDADE[turma.modalidade ?? 'presencial']}</p>
            <h1 className="mt-1 break-words text-2xl font-extrabold text-white">{turma.nome}</h1>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-400">
              <span>{turma.curso_nome || 'Sem curso'}</span>
              <span>{turma.escola_nome || turma.polo_nome || 'Sem unidade'}</span>
              <span className="inline-flex items-center gap-1 tabular-nums">
                <CalendarDays className="h-3.5 w-3.5" aria-hidden /> {formatarData(turma.data_inicio)} a {formatarData(turma.data_fim)}
              </span>
            </p>
            <div className="mt-2"><SeloSituacao turma={turma} /></div>
          </div>
          <div className="flex flex-wrap gap-2">
            {!leitura && (
              <button type="button" onClick={() => setModal('editar')}
                className="flex items-center gap-1.5 rounded-xl bg-nexus-yellow px-4 py-2 text-xs font-bold text-ink hover:bg-nexus-yellow-hover">
                <Edit2 className="h-3.5 w-3.5" /> Editar dados
              </button>
            )}
            {podeCancelar && (
              <button type="button" onClick={() => setModal('cancelar')}
                className="flex items-center gap-1.5 rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-red-500/15 hover:text-red-300">
                <Ban className="h-3.5 w-3.5" /> Cancelar turma
              </button>
            )}
            {isAdmin && leitura && (
              <button type="button" onClick={() => void reabrir()} disabled={processando}
                className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-on-accent hover:bg-emerald-500 disabled:opacity-60">
                <RotateCcw className="h-3.5 w-3.5" /> Reabrir
              </button>
            )}
            {podeExcluir && (
              <button type="button" onClick={() => setModal('excluir')} aria-label="Excluir turma" title="Excluir turma (sem alunos)"
                className="rounded-xl bg-slate-800 p-2 text-slate-400 hover:bg-red-500/15 hover:text-red-400">
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {leitura && (
          <p role="status" className="flex items-start gap-2 rounded-xl border border-slate-700 bg-slate-950/60 p-3 text-xs text-slate-300">
            <Lock className="h-4 w-4 shrink-0" aria-hidden />
            Turma {ROTULO_SITUACAO_TURMA[turma.situacao!].toLowerCase()} — somente leitura.
            {turma.situacao === 'cancelada' && turma.motivo_cancelamento ? ` Motivo: ${turma.motivo_cancelamento}.` : ''}
            {isAdmin ? ' Use "Reabrir" para voltar a alterar.' : ''}
          </p>
        )}
        {turma.periodo_encerrado && (
          <p role="status" className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
            O período da turma terminou em {formatarData(turma.data_fim)}. Confira o andamento e conclua a turma.
          </p>
        )}
        {(erro || aviso) && (
          <p role={erro ? 'alert' : 'status'} className={`rounded-xl border p-3 text-sm ${erro ? 'border-red-500/30 bg-red-500/10 text-red-200' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'}`}>
            {erro || aviso}
          </p>
        )}
      </header>

      <div role="tablist" aria-label="Seções da turma" className="-mx-1 flex gap-1 overflow-x-auto border-b border-slate-800 px-1">
        {abas.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-turma-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-turma-${a.id}`}
            onClick={() => trocarAba(a.id)}
            className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-bold transition-colors ${
              aba === a.id ? 'border-nexus-yellow text-white' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-turma-${aba}`} aria-labelledby={`aba-turma-${aba}`}>
        {aba === 'dados' && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Dado label="Código">{turma.codigo || '—'}</Dado>
            <Dado label="Curso">{turma.curso_nome || '—'}</Dado>
            <Dado label="Calendário">{turma.calendario_nome || '—'}</Dado>
            <Dado label="Período">{formatarData(turma.data_inicio)} a {formatarData(turma.data_fim)}</Dado>
            <Dado label="Modalidade">{ROTULO_MODALIDADE[turma.modalidade ?? 'presencial']}</Dado>
            <Dado label="Polo">{turma.polo_nome || '—'}</Dado>
            <Dado label="Escola">{turma.escola_nome || '—'}</Dado>
            <Dado label="Responsável">{turma.responsavel_nome || '—'}</Dado>
            <Dado label="Turno">{turma.turno ? ROTULO_TURNO[turma.turno] : '—'}</Dado>
            <Dado label="Horário">{turma.horario_inicio ? `${formatarHora(turma.horario_inicio)} às ${formatarHora(turma.horario_fim) || '—'}` : '—'}</Dado>
            <Dado label="Vagas">{turma.vagas ? `${turma.total_alunos} de ${turma.vagas} ocupadas` : `${turma.total_alunos} aluno(s), sem limite`}</Dado>
            <Dado label="Andamento">{turma.andamento_pct != null ? `${turma.andamento_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : 'Sem cronograma'}</Dado>
            <Dado label="Local">{turma.local_aulas || '—'}</Dado>
          </div>
        )}
        {aba === 'alunos' && (
          <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <TurmaAlunosPanel turma={turma} embutido somenteLeitura={leitura} onAlterado={() => void carregar()} />
          </section>
        )}
        {aba === 'professores' && (
          <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <TurmaProfessoresPanel turma={turma} embutido somenteLeitura={leitura} />
          </section>
        )}
        {aba === 'carga' && (
          <TurmaCargaHorariaPanel
            turma={turma}
            embutido
            podeGerar={(isAdmin || isPolo) && !leitura}
            podeConcluir={isAdmin && !leitura}
            onAlterado={() => void carregar()}
          />
        )}
        {aba === 'historico' && (
          <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <TurmaHistoricoPanel turmaId={turma.id} turmaNome={turma.nome} />
          </section>
        )}
        {aba === 'prazos' && ead && (
          <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <PrazosEadTab turma={turma} />
          </section>
        )}
      </div>

      {modal === 'editar' && (
        <TurmaFormModal
          turma={turma}
          cursos={cursos}
          polos={polos}
          escolas={escolas}
          mostrarPolo={isAdmin}
          mostrarEscola={isAdmin || isPolo}
          onClose={() => setModal(null)}
          onSaved={(t) => {
            setModal(null);
            setTurma(t);
            setAviso('Dados da turma atualizados.');
          }}
        />
      )}
      {modal === 'cancelar' && (
        <CancelarModal
          turma={turma}
          aoFechar={() => setModal(null)}
          aoConcluir={(t) => {
            setModal(null);
            setTurma(t);
            setAviso('Turma cancelada.');
          }}
        />
      )}
      {modal === 'excluir' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto">
          <div role="dialog" aria-modal="true" aria-labelledby="excluir-turma-titulo"
            className="my-auto glass w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h2 id="excluir-turma-titulo" className="flex items-center gap-2 text-lg font-bold text-white">
              <Trash2 className="h-5 w-5 text-red-400" /> Excluir turma
            </h2>
            <p className="text-sm text-slate-400">
              Excluir <strong className="text-white">{turma.nome}</strong>? Só é possível sem alunos, notas ou professores;
              com histórico, cancele a turma.
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300">Voltar</button>
              <button type="button" onClick={() => void excluir()} disabled={processando}
                className="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-red-500 disabled:opacity-60">
                {processando && <Loader2 size={14} className="animate-spin" />} Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
