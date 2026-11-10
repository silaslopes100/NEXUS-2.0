import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, ChevronDown, FileText, Loader2, Plus, Search } from 'lucide-react';
import {
  alunosApi,
  alunosGestaoApi,
  AlunoGestao,
  apiErrorMessage,
  EscolaOption,
  Observacao,
} from '@/features/alunos/api';
import { AlunoFormModal } from '@/features/alunos/components/AlunoFormModal';
import { BoletimModal } from '@/features/alunos/components/BoletimModal';
import { DisciplinasExpandidas } from '@/features/alunos/components/DisciplinasExpandidas';
import { GerarMatriculaModal } from '@/features/alunos/components/GerarMatriculaModal';
import { observacaoInfo, TagsAluno } from '@/features/alunos/components/TagsAluno';
import { useAuthStore } from '@/stores/authStore';

const PAGE_SIZE = 20;
const FILTRO_EAD = '__ead';
const MODALIDADE_LABEL: Record<string, string> = { polo: 'Polo', escola: 'Escola', ead: 'EAD' };
const selectCls =
  'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const dataHora = (valor?: string | null) =>
  valor
    ? new Date(valor).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
    : 'Sem registro';

const observacaoDaUrl = (valor: string | null): Observacao | '' =>
  valor && valor in observacaoInfo ? (valor as Observacao) : '';

export const AlunosPage: React.FC = () => {
  const { user } = useAuthStore();
  const [searchParams] = useSearchParams();
  const isAdmin = user?.perfil?.nome === 'admin';
  const escolaFixaId = !isAdmin && user?.escola_id ? user.escola_id : null;

  const [polos, setPolos] = useState<EscolaOption[]>([]);
  // Admin vê toda a base por padrão: alunos EAD e em Churn não têm Polo.
  const [poloId, setPoloId] = useState<string>(isAdmin ? '' : user?.polo_id || '');
  const [escolas, setEscolas] = useState<EscolaOption[]>([]);
  const [escolaFiltro, setEscolaFiltro] = useState<string>(escolaFixaId || '');
  const [observacao, setObservacao] = useState<Observacao | ''>(
    observacaoDaUrl(searchParams.get('observacao'))
  );
  const [busca, setBusca] = useState(searchParams.get('q') ?? '');
  const [buscaAplicada, setBuscaAplicada] = useState(searchParams.get('q') ?? '');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [alunos, setAlunos] = useState<AlunoGestao[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());
  const [boletimId, setBoletimId] = useState<string | null>(null);
  const [gerandoMatricula, setGerandoMatricula] = useState<AlunoGestao | null>(null);
  const [enviandoChurnId, setEnviandoChurnId] = useState<string | null>(null);

  const somenteEad = poloId === FILTRO_EAD;
  const poloSelecionado = poloId && !somenteEad ? poloId : '';

  useEffect(() => {
    if (isAdmin) {
      alunosApi
        .listarPolos()
        .then(setPolos)
        .catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar polos.')));
    }
  }, [isAdmin]);

  useEffect(() => {
    if (!poloSelecionado) {
      setEscolas([]);
      return;
    }
    alunosApi
      .listarEscolas(poloSelecionado)
      .then(setEscolas)
      .catch(() => setEscolas([]));
  }, [poloSelecionado]);

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro('');
    try {
      const resp = await alunosGestaoApi.listar({
        polo_id: poloSelecionado || undefined,
        escola_id: escolaFiltro || undefined,
        somente_ead: somenteEad || undefined,
        observacao: observacao || undefined,
        q: buscaAplicada || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setAlunos(resp.items);
      setTotal(resp.total);
      setExpandidos(new Set());
    } catch (e) {
      setErro(apiErrorMessage(e, 'Erro ao carregar alunos.'));
    } finally {
      setLoading(false);
    }
  }, [poloSelecionado, somenteEad, buscaAplicada, escolaFiltro, observacao, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const aplicarBusca = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setBuscaAplicada(busca.trim());
  };

  const alternarExpansao = (alunoId: string) => {
    setExpandidos((atuais) => {
      const proximos = new Set(atuais);
      if (!proximos.delete(alunoId)) proximos.add(alunoId);
      return proximos;
    });
  };

  const enviarAoChurn = async (aluno: AlunoGestao) => {
    const confirmado = window.confirm(
      `Enviar ${aluno.nome} para o Churn? O aluno ficará com status desistente, sem Polo e fora das turmas.`
    );
    if (!confirmado) return;
    setEnviandoChurnId(aluno.id);
    setErro('');
    setSucesso('');
    try {
      await alunosGestaoApi.confirmarChurn(aluno.id);
      setSucesso(`${aluno.nome} foi enviado para o Churn.`);
      await carregar();
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível enviar o aluno para o Churn.'));
    } finally {
      setEnviandoChurnId(null);
    }
  };

  const colunas = isAdmin ? 11 : 10;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Alunos</h1>
          <p className="text-sm text-slate-400">{total} aluno(s) encontrado(s)</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          disabled={!poloSelecionado}
          title={poloSelecionado ? undefined : 'Selecione um Polo para cadastrar'}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
        >
          <Plus size={16} /> Novo aluno
        </button>
      </div>

      {sucesso && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          <CheckCircle2 size={16} /> {sucesso}
        </div>
      )}
      {erro && <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erro}</div>}

      <div className="flex flex-wrap items-center gap-3">
        {isAdmin && (
          <select
            aria-label="Filtrar por Polo"
            className={selectCls}
            value={poloId}
            onChange={(e) => {
              setPoloId(e.target.value);
              setEscolaFiltro('');
              setOffset(0);
            }}
          >
            <option value="">Todos os polos</option>
            <option value={FILTRO_EAD}>EAD</option>
            {polos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        )}
        {!escolaFixaId && (
          <select
            aria-label="Filtrar por escola"
            className={selectCls}
            value={escolaFiltro}
            disabled={!poloSelecionado}
            onChange={(e) => {
              setEscolaFiltro(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Todas as escolas</option>
            {escolas.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nome}
              </option>
            ))}
          </select>
        )}
        <select
          aria-label="Filtrar por observação"
          className={selectCls}
          value={observacao}
          onChange={(e) => {
            setObservacao(e.target.value as Observacao | '');
            setOffset(0);
          }}
        >
          <option value="">Todas as observações</option>
          {(Object.keys(observacaoInfo) as Observacao[]).map((valor) => (
            <option key={valor} value={valor}>
              {observacaoInfo[valor].label}
            </option>
          ))}
        </select>
        <form onSubmit={aplicarBusca} className="flex items-stretch gap-2">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Nome, e-mail, CPF ou matrícula"
              className={`${selectCls} w-72 pl-9`}
            />
          </div>
          <button
            type="submit"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500"
          >
            Buscar
          </button>
        </form>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
        <table className="w-full min-w-[1280px] text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-4">Matrícula</th>
              <th className="p-4">Aluno</th>
              <th className="p-4">Modalidade</th>
              <th className="p-4">Turma</th>
              <th className="p-4">Disciplinas</th>
              <th className="p-4">Presença</th>
              <th className="p-4">Último acesso</th>
              <th className="p-4">Observações</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-center">Histórico</th>
              {isAdmin && <th className="p-4 text-right">Ações</th>}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={colunas} className="p-6 text-center">
                  <Loader2 className="mx-auto animate-spin" size={18} />
                </td>
              </tr>
            )}
            {!loading && alunos.length === 0 && (
              <tr>
                <td colSpan={colunas} className="p-6 text-center text-slate-500">
                  Nenhum aluno encontrado.
                </td>
              </tr>
            )}
            {!loading &&
              alunos.map((a) => {
                const expandido = expandidos.has(a.id);
                return (
                  <React.Fragment key={a.id}>
                    <tr className="border-b border-slate-800/60 last:border-0">
                      <td className="p-4 font-mono text-xs text-slate-400">{a.numero_matricula || '—'}</td>
                      <td className="p-4">
                        <p className="font-semibold text-white">{a.nome}</p>
                        <p className="text-xs text-slate-500">{a.email || '—'}</p>
                      </td>
                      <td className="p-4">
                        {MODALIDADE_LABEL[a.modalidade ?? ''] ?? a.modalidade ?? '—'}
                      </td>
                      <td className="p-4">{a.turmas.length ? a.turmas.join(', ') : '—'}</td>
                      <td className="p-4">
                        {a.disciplinas_em_curso > 0 ? (
                          <button
                            type="button"
                            aria-expanded={expandido}
                            onClick={() => alternarExpansao(a.id)}
                            className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-semibold text-blue-300 hover:text-blue-200"
                          >
                            <ChevronDown
                              size={14}
                              className={`transition-transform ${expandido ? 'rotate-180' : ''}`}
                            />
                            {a.disciplinas_em_curso} em curso
                          </button>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="p-4">{a.percentual_presenca.toFixed(0)}%</td>
                      <td className="whitespace-nowrap p-4 text-xs">{dataHora(a.ultimo_acesso_em)}</td>
                      <td className="p-4">
                        <TagsAluno observacoes={a.observacoes} />
                      </td>
                      <td className="p-4 capitalize">{a.status}</td>
                      <td className="p-4 text-center">
                        <button
                          type="button"
                          aria-label={`Abrir boletim de ${a.nome}`}
                          title="Histórico Escolar"
                          onClick={() => setBoletimId(a.id)}
                          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                        >
                          <FileText size={16} />
                        </button>
                      </td>
                      {isAdmin && (
                        <td className="p-4 text-right">
                          {a.status === 'desistente' && (
                            <button
                              type="button"
                              onClick={() => {
                                setSucesso('');
                                setGerandoMatricula(a);
                              }}
                              className="whitespace-nowrap rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-200 hover:bg-blue-500/20"
                            >
                              Gerar nova matrícula
                            </button>
                          )}
                          {a.observacoes.includes('sem_movimentacao') && (
                            <button
                              type="button"
                              disabled={enviandoChurnId === a.id}
                              onClick={() => void enviarAoChurn(a)}
                              className="whitespace-nowrap rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-semibold text-red-200 hover:bg-red-500/10 disabled:opacity-50"
                            >
                              Enviar ao Churn
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                    {expandido && (
                      <tr className="border-b border-slate-800/60 bg-slate-950/40">
                        <td colSpan={colunas} className="px-8 py-4">
                          <DisciplinasExpandidas alunoId={a.id} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-end gap-3 text-sm text-slate-400">
        <button
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          className="rounded-lg px-3 py-1 hover:text-white disabled:opacity-40"
        >
          Anterior
        </button>
        <span>
          {total === 0 ? 0 : offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
        </span>
        <button
          disabled={offset + PAGE_SIZE >= total}
          onClick={() => setOffset(offset + PAGE_SIZE)}
          className="rounded-lg px-3 py-1 hover:text-white disabled:opacity-40"
        >
          Próxima
        </button>
      </div>

      {showForm && (
        <AlunoFormModal
          poloId={poloSelecionado}
          escolas={escolaFixaId ? escolas.filter((e) => e.id === escolaFixaId) : escolas}
          escolaFixaId={escolaFixaId}
          onClose={() => setShowForm(false)}
          onSuccess={(aluno) => {
            setShowForm(false);
            setSucesso(
              `Aluno cadastrado com matrícula ${aluno.numero_matricula}. ${
                aluno.convite_enviado ? 'Convite enviado por e-mail.' : 'Não foi possível enviar o convite por e-mail.'
              }`
            );
            setOffset(0);
            void carregar();
          }}
        />
      )}
      {boletimId && <BoletimModal alunoId={boletimId} onClose={() => setBoletimId(null)} />}
      {gerandoMatricula && (
        <GerarMatriculaModal
          aluno={gerandoMatricula}
          onClose={() => setGerandoMatricula(null)}
          onSuccess={(resultado) => {
            setGerandoMatricula(null);
            setSucesso(
              `Nova matrícula ${resultado.numero_matricula} gerada.${
                resultado.licencas_debitadas
                  ? ` ${resultado.licencas_debitadas} licenças debitadas do Polo de destino.`
                  : ''
              }`
            );
            void carregar();
          }}
        />
      )}
    </div>
  );
};
