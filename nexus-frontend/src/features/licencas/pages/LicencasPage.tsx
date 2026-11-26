import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowUpFromLine,
  CheckCircle2,
  Gift,
  Loader2,
  Printer,
  RefreshCw,
  Repeat,
  Shuffle,
  X,
} from 'lucide-react';
import { cursosApi, Curso, Disciplina } from '@/features/cursos/api';
import {
  AlunoTurmaLicenca, DistribuicaoAlunosResultado, EstoqueDisciplina, licencasApi, LicencaKpis, MovimentacaoLicenca,
  nomeDisciplina, TurmaOpcao,
} from '@/features/licencas/api';
import {
  DisciplinaSelect, paraDisciplinaId, TabelaEstoqueDisciplina, useDisciplinas, VALOR_SEM_DISCIPLINA,
} from '@/features/licencas/components/EstoqueDisciplina';
import { LicencasEscolaPage } from '@/features/licencas/pages/LicencasEscolaPage';
import { TrocaLicencaModal } from '@/features/licencas/components/TrocaLicencaModal';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { abrirPdf, erroDeBlob } from '@/lib/download';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'block space-y-1 text-sm text-slate-300';

type Acao = 'distribuir' | 'liberar' | 'reclassificar' | 'trocar';
interface Opcao { id: string; nome: string }

const listaDe = (data: unknown): Opcao[] => {
  const itens = Array.isArray(data) ? data : ((data as { items?: Opcao[] })?.items || []);
  return itens.map((i: Opcao) => ({ id: i.id, nome: i.nome }));
};
const erroTexto = (error: any, padrao: string) => error?.response?.data?.detail && typeof error.response.data.detail === 'string'
  ? error.response.data.detail : padrao;

/** Licenças do Polo: saldo por disciplina, distribuição (Escola ou alunos de uma turma) e liberação pelo admin. */
export const LicencasPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome || user?.perfil?.nome);
  if (role === 'escola' && user?.escola_id) return <LicencasEscolaPage escolaIdFixo={user.escola_id} />;
  return <LicencasPolo isAdmin={role === 'admin'} poloDoUsuario={user?.polo_id || ''} />;
};

const LicencasPolo: React.FC<{ isAdmin: boolean; poloDoUsuario: string }> = ({ isAdmin, poloDoUsuario }) => {
  const todasDisciplinas = useDisciplinas();
  const [searchParams] = useSearchParams();
  const [polos, setPolos] = useState<Opcao[]>([]);
  // ?polo_id=<id> chega dos indicadores da tela de Polos (só o admin escolhe o polo).
  const [poloId, setPoloId] = useState(() => (isAdmin && searchParams.get('polo_id')) || poloDoUsuario);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [kpis, setKpis] = useState<LicencaKpis | null>(null);
  const [estoque, setEstoque] = useState<EstoqueDisciplina | null>(null);
  const [items, setItems] = useState<MovimentacaoLicenca[]>([]);
  const [loading, setLoading] = useState(true);
  const [aviso, setAviso] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null);
  const [action, setAction] = useState<Acao | null>(null);
  const [ultimaDistribuicao, setUltimaDistribuicao] = useState<DistribuicaoAlunosResultado | null>(null);

  useEffect(() => {
    if (!isAdmin) return;
    polosEscolasApi.listarPolos({ limit: 200 })
      .then((data) => {
        const lista = listaDe(data);
        setPolos(lista);
        setPoloId((atual) => atual || lista[0]?.id || '');
      })
      .catch(() => setPolos([]));
  }, [isAdmin]);

  const load = useCallback(async () => {
    if (!poloId) { setLoading(false); return; }
    setLoading(true);
    // allSettled: uma falha (ex.: KPIs) não apaga o saldo nem o extrato.
    const [k, e, m, esc] = await Promise.allSettled([
      licencasApi.getKpis(poloId),
      licencasApi.estoquePolo(poloId),
      licencasApi.listMovimentacoes(poloId),
      polosEscolasApi.listarEscolasDoPolo(poloId),
    ]);
    if (k.status === 'fulfilled') setKpis(k.value);
    if (e.status === 'fulfilled') setEstoque(e.value);
    if (m.status === 'fulfilled') setItems(m.value.items);
    if (esc.status === 'fulfilled') setEscolas(listaDe(esc.value));
    const falha = [k, e, m, esc].find((r) => r.status === 'rejected') as PromiseRejectedResult | undefined;
    if (falha) setAviso({ tipo: 'erro', texto: erroTexto(falha.reason, 'Parte das informações não pôde ser carregada.') });
    setLoading(false);
  }, [poloId]);
  useEffect(() => { load(); }, [load]);

  const concluir = async (texto: string, distribuicao?: DistribuicaoAlunosResultado) => {
    setAction(null);
    setAviso({ tipo: 'ok', texto });
    if (distribuicao) setUltimaDistribuicao(distribuicao);
    await load();
  };

  const imprimirCartoes = async (ids: string[]) => {
    try {
      abrirPdf(await licencasApi.cartoes(ids), 'cartoes-acesso.pdf');
    } catch (error) {
      setAviso({ tipo: 'erro', texto: await erroDeBlob(error, 'Não foi possível gerar os cartões.') });
    }
  };

  const semDisciplina = (estoque?.items || []).find((i) => !i.materia_id && i.quantidade_disponivel > 0);
  const metricCards = kpis ? [
    ['Recebidas', kpis.total_licencas_compradas, 'text-white'],
    ['Entregues a alunos', kpis.total_licencas_vendidas_alunos, 'text-emerald-400'],
    ['Disponíveis', kpis.total_licencas_nao_vendidas, 'text-amber-300'],
    ['No Polo', kpis.total_nao_vendidas_polo, 'text-blue-400'],
  ] : [];

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Minhas Licenças</h1>
          <p className="mt-1 text-sm text-slate-400">Saldo por disciplina e entrega de licenças para Escolas ou diretamente aos alunos de uma turma.</p>
          {isAdmin && (
            <label className="mt-3 block text-xs text-slate-400">
              Polo
              <select value={poloId} onChange={(e) => setPoloId(e.target.value)} className="ml-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
                {!polos.length && <option value="">Nenhum polo</option>}
                {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
              </select>
            </label>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {isAdmin && (
            <button onClick={() => setAction('liberar')} disabled={!poloId} className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-50">
              <Gift size={16} /> Liberar licenças (sem cobrança)
            </button>
          )}
          <button onClick={() => setAction('distribuir')} disabled={!poloId} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-50">
            <ArrowUpFromLine size={16} /> Distribuir
          </button>
          {!isAdmin && (
            <button onClick={() => setAction('trocar')} disabled={!poloId} className="inline-flex items-center gap-2 rounded-xl border border-blue-500/40 px-4 py-2.5 text-sm font-semibold text-blue-300 hover:bg-blue-500/10 disabled:opacity-50">
              <Repeat size={16} /> Trocar licença
            </button>
          )}
        </div>
      </header>

      {aviso && (
        <div className={`flex items-center justify-between rounded-xl border p-3 text-sm ${aviso.tipo === 'ok' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-red-500/30 bg-red-500/10 text-red-200'}`}>
          <span className="flex items-center gap-2">{aviso.tipo === 'ok' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />} {aviso.texto}</span>
          <button onClick={() => setAviso(null)} aria-label="Fechar aviso"><X size={16} /></button>
        </div>
      )}

      {ultimaDistribuicao && ultimaDistribuicao.licencas.length > 0 && (
        <section className="glass rounded-2xl border border-indigo-500/30 bg-slate-900/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-white">Licenças entregues aos alunos</h2>
              <p className="text-xs text-slate-400">Imprima os cartões e entregue a cada aluno: com o número ele entra direto na avaliação.</p>
            </div>
            <button onClick={() => imprimirCartoes(ultimaDistribuicao.licencas.map((l) => l.licenca_id))} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-on-accent">
              <Printer size={15} /> Imprimir cartões de acesso
            </button>
          </div>
          <ul className="mt-3 grid gap-1 text-sm sm:grid-cols-2">
            {ultimaDistribuicao.licencas.map((l) => (
              <li key={l.licenca_id} className="flex justify-between rounded-lg bg-slate-950/60 px-3 py-1.5 text-slate-300">
                <span>{l.aluno_nome || 'Aluno'}</span><span className="font-mono text-white">{l.numero_licenca}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!poloId && !loading && <p className="text-sm text-slate-400">Nenhum polo vinculado ao seu usuário.</p>}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metricCards.map(([label, value, color]) => (
          <div key={String(label)} className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
            <strong className={`mt-2 block text-2xl font-black ${color}`}>{value}</strong>
          </div>
        ))}
      </section>

      {semDisciplina && (
        <p className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
          <AlertTriangle size={16} />
          Há {semDisciplina.quantidade_disponivel} licença(s) sem disciplina definida (saldo antigo).
          {isAdmin ? ' Use "Reclassificar saldo" para definir a disciplina antes de distribuir.' : ' Peça ao administrador para definir a disciplina.'}
        </p>
      )}

      <TabelaEstoqueDisciplina
        estoque={estoque}
        acao={isAdmin && semDisciplina ? (
          <button onClick={() => setAction('reclassificar')} className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 px-3 py-2 text-xs font-semibold text-amber-300">
            <Shuffle size={14} /> Reclassificar saldo
          </button>
        ) : undefined}
      />

      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <div><h2 className="font-bold text-white">Últimas movimentações</h2><p className="text-xs text-slate-500">{items.length} registro(s)</p></div>
          <button onClick={load} title="Recarregar" aria-label="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
        </div>
        {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr><th className="p-4">Movimentação</th><th className="p-4">Disciplina</th><th className="p-4">Destino</th><th className="p-4 text-center">Qtd.</th><th className="p-4">Observação</th><th className="p-4 text-right">Data</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((item) => (
                  <tr key={item.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-semibold text-white">{ROTULO_MOVIMENTO[item.tipo] || item.tipo.split('_').join(' ')}</td>
                    <td className="p-4 text-xs">{nomeDisciplina(item)}</td>
                    <td className="p-4 text-xs text-slate-400">
                      {item.aluno_id ? 'Aluno' : item.escola_id ? (escolas.find((e) => e.id === item.escola_id)?.nome || 'Escola') : 'Polo'}
                    </td>
                    <td className="p-4 text-center font-bold">{item.quantidade}</td>
                    <td className="p-4 text-xs text-slate-400">{item.observacao || '—'}</td>
                    <td className="p-4 text-right text-xs text-slate-500">{item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '-'}</td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={6} className="p-12 text-center text-slate-500">Nenhuma movimentação ainda.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {action === 'distribuir' && (
        <ModalDistribuir
          poloId={poloId}
          escolas={escolas}
          estoque={estoque}
          onFechar={() => setAction(null)}
          onConcluido={concluir}
        />
      )}
      {action === 'trocar' && (
        <TrocaLicencaModal
          estoque={estoque}
          onFechar={() => setAction(null)}
          onConcluido={(pedido) => concluir(`Solicitação de troca ${pedido.numero} enviada ao administrador.`)}
        />
      )}
      {action === 'liberar' && (
        <ModalLiberar poloId={poloId} poloNome={polos.find((p) => p.id === poloId)?.nome} onFechar={() => setAction(null)} onConcluido={concluir} />
      )}
      {action === 'reclassificar' && (
        <ModalReclassificar poloId={poloId} estoque={estoque} disciplinas={todasDisciplinas} onFechar={() => setAction(null)} onConcluido={concluir} />
      )}
    </div>
  );
};

const ROTULO_MOVIMENTO: Record<string, string> = {
  compra_fornecedor: 'Compra',
  liberacao_admin: 'Liberada pelo Admin',
  distribuicao_polo_escola: 'Enviada para a Escola',
  distribuicao_polo_aluno: 'Entregue ao aluno',
  venda_aluno: 'Entregue ao aluno',
  devolucao_escola_polo: 'Devolvida pela Escola',
  devolucao_aluno_escola: 'Devolvida pelo aluno',
  reingresso_churn: 'Reingresso de aluno',
  reclassificacao: 'Disciplina definida',
  troca_reserva: 'Reservada para troca',
  troca_recebimento: 'Recebida na troca',
  troca_estorno: 'Troca recusada (estorno)',
};

// ---------------------------------------------------------------------------
// Curso → Disciplina (todas as do curso, com saldo; sem saldo aparece desabilitada)
// ---------------------------------------------------------------------------

const useCursos = () => {
  const [cursos, setCursos] = useState<Curso[]>([]);
  useEffect(() => { cursosApi.listar().then(setCursos).catch(() => setCursos([])); }, []);
  return cursos;
};

const CursoDisciplina: React.FC<{
  estoque: EstoqueDisciplina | null;
  cursoId: string;
  disciplinaId: string;
  onCurso: (id: string) => void;
  onDisciplina: (id: string) => void;
  exigirSaldo?: boolean;
}> = ({ estoque, cursoId, disciplinaId, onCurso, onDisciplina, exigirSaldo = true }) => {
  const cursos = useCursos();
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  useEffect(() => {
    if (!cursoId) { setDisciplinas([]); return; }
    cursosApi.listarDisciplinas(cursoId).then(setDisciplinas).catch(() => setDisciplinas([]));
  }, [cursoId]);
  const saldo = (id: string) => (estoque?.items || []).find((i) => i.materia_id === id)?.quantidade_disponivel || 0;
  return (
    <>
      <label className={labelCls}>
        <span>Curso</span>
        <select required className={inputClass} value={cursoId} onChange={(e) => { onCurso(e.target.value); onDisciplina(''); }}>
          <option value="">Selecione o curso</option>
          {cursos.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
      </label>
      {cursoId && (
        <label className={labelCls}>
          <span>Disciplina</span>
          <select required className={inputClass} value={disciplinaId} onChange={(e) => onDisciplina(e.target.value)}>
            <option value="">Selecione a disciplina</option>
            {disciplinas.map((d) => {
              const s = saldo(d.id);
              return (
                <option key={d.id} value={d.id} disabled={exigirSaldo && s <= 0}>
                  {d.nome}{exigirSaldo ? ` — ${s > 0 ? `${s} disponível(is)` : 'sem saldo'}` : ''}
                </option>
              );
            })}
          </select>
          {!disciplinas.length && <span className="block text-xs text-amber-300">Este curso ainda não tem disciplinas cadastradas.</span>}
        </label>
      )}
    </>
  );
};

// ---------------------------------------------------------------------------
// Distribuir: Escola ou Alunos de uma turma
// ---------------------------------------------------------------------------

const ModalDistribuir: React.FC<{
  poloId: string;
  escolas: Opcao[];
  estoque: EstoqueDisciplina | null;
  onFechar: () => void;
  onConcluido: (texto: string, distribuicao?: DistribuicaoAlunosResultado) => void;
}> = ({ poloId, escolas, estoque, onFechar, onConcluido }) => {
  const [cursoId, setCursoId] = useState('');
  const [disciplinaId, setDisciplinaId] = useState('');
  const [destino, setDestino] = useState<'escola' | 'aluno'>('escola');
  const [escolaId, setEscolaId] = useState('');
  const [quantidade, setQuantidade] = useState(1);
  const [turmas, setTurmas] = useState<TurmaOpcao[]>([]);
  const [turmaId, setTurmaId] = useState('');
  const [alunos, setAlunos] = useState<AlunoTurmaLicenca[]>([]);
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');

  const saldo = (estoque?.items || []).find((i) => i.materia_id === disciplinaId)?.quantidade_disponivel || 0;

  useEffect(() => {
    setTurmaId('');
    setTurmas([]);
    if (destino !== 'aluno' || !cursoId) return;
    licencasApi.turmasDoCurso(cursoId, poloId).then(setTurmas).catch(() => setTurmas([]));
  }, [destino, cursoId, poloId]);

  useEffect(() => {
    setAlunos([]);
    setSelecionados(new Set());
    if (!turmaId || !disciplinaId) return;
    licencasApi.alunosTurma(poloId, turmaId, disciplinaId)
      .then((r) => {
        setAlunos(r.alunos);
        setSelecionados(new Set(r.alunos.filter((a) => !a.possui_licenca).map((a) => a.aluno_id)));
      })
      .catch((error) => setErro(erroTexto(error, 'Não foi possível carregar os alunos da turma.')));
  }, [turmaId, disciplinaId, poloId]);

  const alternar = (id: string) => setSelecionados((s) => {
    const novo = new Set(s);
    if (novo.has(id)) novo.delete(id); else novo.add(id);
    return novo;
  });

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setErro('');
    try {
      if (destino === 'escola') {
        await licencasApi.distribuir(poloId, { escola_id: escolaId, quantidade, disciplina_id: disciplinaId });
        onConcluido(`${quantidade} licença(s) enviada(s) para a escola.`);
      } else {
        const r = await licencasApi.distribuirAlunos(poloId, { disciplina_id: disciplinaId, turma_id: turmaId, aluno_ids: Array.from(selecionados) });
        const extra = r.ja_possuiam ? ` ${r.ja_possuiam} aluno(s) já tinham licença e foram mantidos.` : '';
        onConcluido(`${r.distribuidas} licença(s) entregue(s) aos alunos.${extra}`, r);
      }
    } catch (error) {
      setErro(erroTexto(error, 'A distribuição não pôde ser concluída.'));
    } finally {
      setSaving(false);
    }
  };

  const excede = destino === 'aluno' ? selecionados.size > saldo : quantidade > saldo;
  const podeEnviar = !!disciplinaId && !excede && (destino === 'escola' ? !!escolaId && quantidade > 0 : selecionados.size > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
      <form onSubmit={submit} className="glass my-auto w-full max-w-lg space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Distribuir licenças</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400"><X /></button>
        </div>
        {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}

        <CursoDisciplina estoque={estoque} cursoId={cursoId} disciplinaId={disciplinaId} onCurso={setCursoId} onDisciplina={setDisciplinaId} />

        {disciplinaId && (
          <div className="space-y-2">
            <p className="text-sm text-slate-300">Para quem?</p>
            <div className="grid grid-cols-2 gap-2">
              {(['escola', 'aluno'] as const).map((d) => (
                <button key={d} type="button" onClick={() => setDestino(d)} className={`rounded-xl border px-3 py-2 text-sm font-semibold ${destino === d ? 'border-indigo-500 bg-indigo-600/20 text-white' : 'border-slate-700 text-slate-300'}`}>
                  {d === 'escola' ? 'Para uma Escola' : 'Para alunos de uma turma'}
                </button>
              ))}
            </div>
          </div>
        )}

        {disciplinaId && destino === 'escola' && (
          <>
            <label className={labelCls}>
              <span>Escola</span>
              <select required className={inputClass} value={escolaId} onChange={(e) => setEscolaId(e.target.value)}>
                <option value="">Selecione</option>
                {escolas.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
              </select>
            </label>
            <label className={labelCls}>
              <span>Quantidade (disponível: {saldo})</span>
              <input className={inputClass} type="number" min={1} max={saldo} required value={quantidade} onChange={(e) => setQuantidade(Number(e.target.value))} />
            </label>
          </>
        )}

        {disciplinaId && destino === 'aluno' && (
          <>
            <label className={labelCls}>
              <span>Turma</span>
              <select required className={inputClass} value={turmaId} onChange={(e) => setTurmaId(e.target.value)}>
                <option value="">Selecione a turma</option>
                {turmas.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
              </select>
              {!turmas.length && <span className="block text-xs text-amber-300">Nenhuma turma deste curso no Polo.</span>}
            </label>
            {turmaId && (
              <div className="max-h-64 space-y-1 overflow-y-auto rounded-xl border border-slate-800 p-2">
                {alunos.map((a) => (
                  <label key={a.aluno_id} className={`flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-sm ${a.possui_licenca ? 'text-slate-500' : 'text-slate-200 hover:bg-slate-800/50'}`}>
                    <span className="flex items-center gap-2">
                      <input type="checkbox" disabled={a.possui_licenca} checked={selecionados.has(a.aluno_id)} onChange={() => alternar(a.aluno_id)} />
                      {a.nome || a.numero_matricula || 'Aluno'}
                    </span>
                    {a.possui_licenca && <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">já possui</span>}
                  </label>
                ))}
                {!alunos.length && <p className="p-3 text-center text-xs text-slate-500">Nenhum aluno ativo nesta turma.</p>}
              </div>
            )}
            {turmaId && (
              <p className={`text-xs ${excede ? 'text-red-300' : 'text-slate-400'}`}>
                Serão usadas {selecionados.size} de {saldo} licença(s) disponível(is) nesta disciplina.
              </p>
            )}
          </>
        )}

        <button disabled={saving || !podeEnviar} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 font-semibold text-on-accent disabled:opacity-50">
          {saving && <Loader2 className="animate-spin" size={16} />} Confirmar distribuição
        </button>
      </form>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Admin: liberar licenças ao Polo sem cobrança
// ---------------------------------------------------------------------------

const ModalLiberar: React.FC<{
  poloId: string;
  poloNome?: string;
  onFechar: () => void;
  onConcluido: (texto: string) => void;
}> = ({ poloId, poloNome, onFechar, onConcluido }) => {
  const [cursoId, setCursoId] = useState('');
  const [disciplinaId, setDisciplinaId] = useState('');
  const [quantidade, setQuantidade] = useState(10);
  const [enviarLivros, setEnviarLivros] = useState(true);
  const [observacao, setObservacao] = useState('');
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setErro('');
    try {
      const r = await licencasApi.liberar(poloId, {
        itens: [{ disciplina_id: disciplinaId, quantidade }], enviar_livros: enviarLivros,
        observacao: observacao.trim() || undefined,
      });
      onConcluido(r.message);
    } catch (error) {
      setErro(erroTexto(error, 'Não foi possível liberar as licenças.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto">
      <form onSubmit={submit} className="my-auto glass w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Liberar licenças{poloNome ? ` para ${poloNome}` : ''}</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400"><X /></button>
        </div>
        <p className="text-xs text-slate-400">Sem cobrança. Fica registrado no extrato e nos relatórios como "Enviada pelo Admin" com o seu e-mail.</p>
        {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
        <CursoDisciplina estoque={null} cursoId={cursoId} disciplinaId={disciplinaId} onCurso={setCursoId} onDisciplina={setDisciplinaId} exigirSaldo={false} />
        <label className={labelCls}>
          <span>Quantidade</span>
          <input className={inputClass} type="number" min={1} required value={quantidade} onChange={(e) => setQuantidade(Number(e.target.value))} />
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={enviarLivros} onChange={(e) => setEnviarLivros(e.target.checked)} />
          Enviar também os livros (cria um pedido de envio para a logística)
        </label>
        <label className={labelCls}>
          <span>Observação (opcional)</span>
          <input className={inputClass} value={observacao} onChange={(e) => setObservacao(e.target.value)} placeholder="Ex.: bonificação do semestre" />
        </label>
        <button disabled={saving || !disciplinaId || quantidade < 1} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 py-2.5 font-semibold text-on-accent disabled:opacity-50">
          {saving && <Loader2 className="animate-spin" size={16} />} Liberar licenças
        </button>
      </form>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Admin: definir a disciplina do saldo antigo ("Sem disciplina")
// ---------------------------------------------------------------------------

const ModalReclassificar: React.FC<{
  poloId: string;
  estoque: EstoqueDisciplina | null;
  disciplinas: Disciplina[];
  onFechar: () => void;
  onConcluido: (texto: string) => void;
}> = ({ poloId, estoque, disciplinas, onFechar, onConcluido }) => {
  const [origem, setOrigem] = useState(VALOR_SEM_DISCIPLINA);
  const [destino, setDestino] = useState('');
  const [quantidade, setQuantidade] = useState(1);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');
  const saldos = useMemo(() => estoque?.items || [], [estoque]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setErro('');
    try {
      await licencasApi.reclassificar(poloId, {
        de_disciplina_id: paraDisciplinaId(origem), para_disciplina_id: paraDisciplinaId(destino), quantidade,
      });
      onConcluido(`${quantidade} licença(s) com disciplina definida.`);
    } catch (error) {
      setErro(erroTexto(error, 'Não foi possível reclassificar.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto">
      <form onSubmit={submit} className="my-auto glass w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Definir a disciplina do saldo</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400"><X /></button>
        </div>
        <p className="text-xs text-slate-400">Move licenças do saldo "Sem disciplina" (anterior ao estoque por disciplina) para uma disciplina.</p>
        {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
        <DisciplinaSelect label="De" value={origem} onChange={setOrigem} saldos={saldos} />
        <DisciplinaSelect label="Para" value={destino} onChange={setDestino} disciplinas={disciplinas} incluirSemDisciplina={false} />
        <label className={labelCls}>
          <span>Quantidade</span>
          <input className={inputClass} type="number" min={1} required value={quantidade} onChange={(e) => setQuantidade(Number(e.target.value))} />
        </label>
        <button disabled={saving || !destino} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-on-accent disabled:opacity-50">
          {saving && <Loader2 className="animate-spin" size={16} />} Confirmar
        </button>
      </form>
    </div>
  );
};
