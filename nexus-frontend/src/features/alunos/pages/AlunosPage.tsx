import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Plus, Search } from 'lucide-react';
import { alunosApi, apiErrorMessage, AlunoItem, EscolaOption } from '@/features/alunos/api';
import { AlunoFormModal } from '@/features/alunos/components/AlunoFormModal';
import { useAuthStore } from '@/stores/authStore';

const PAGE_SIZE = 20;
const MODALIDADE_LABEL: Record<string, string> = { polo: 'Polo', escola: 'Escola', ead: 'EAD' };
const selectCls =
  'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

export const AlunosPage: React.FC = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.perfil?.nome === 'admin';
  const escolaFixaId = !isAdmin && user?.escola_id ? user.escola_id : null;

  const [polos, setPolos] = useState<EscolaOption[]>([]);
  const [poloId, setPoloId] = useState<string>(user?.polo_id || '');
  const [escolas, setEscolas] = useState<EscolaOption[]>([]);
  const [escolaFiltro, setEscolaFiltro] = useState<string>(escolaFixaId || '');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [alunos, setAlunos] = useState<AlunoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (isAdmin) {
      alunosApi
        .listarPolos()
        .then((p) => {
          setPolos(p);
          setPoloId((atual) => atual || p[0]?.id || '');
        })
        .catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar polos.')));
    }
  }, [isAdmin]);

  useEffect(() => {
    if (!poloId) return;
    alunosApi
      .listarEscolas(poloId)
      .then(setEscolas)
      .catch(() => setEscolas([]));
  }, [poloId]);

  const carregar = useCallback(async () => {
    if (!poloId) return;
    setLoading(true);
    setErro('');
    try {
      const resp = await alunosApi.listar(poloId, {
        q: buscaAplicada || undefined,
        escola_id: escolaFiltro || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setAlunos(resp.items);
      setTotal(resp.total);
    } catch (e) {
      setErro(apiErrorMessage(e, 'Erro ao carregar alunos.'));
    } finally {
      setLoading(false);
    }
  }, [poloId, buscaAplicada, escolaFiltro, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const aplicarBusca = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setBuscaAplicada(busca.trim());
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Alunos</h1>
          <p className="text-sm text-slate-400">{total} aluno(s) encontrado(s)</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          disabled={!poloId}
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
            className={selectCls}
            value={poloId}
            onChange={(e) => {
              setPoloId(e.target.value);
              setEscolaFiltro('');
              setOffset(0);
            }}
          >
            {polos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        )}
        {!escolaFixaId && (
          <select
            className={selectCls}
            value={escolaFiltro}
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
        <form onSubmit={aplicarBusca} className="relative">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Nome, e-mail, CPF ou matrícula"
            className={`${selectCls} w-72 pl-9`}
          />
        </form>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-4">Matrícula</th>
              <th className="p-4">Nome</th>
              <th className="p-4">E-mail</th>
              <th className="p-4">Modalidade</th>
              <th className="p-4">Presença</th>
              <th className="p-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="p-6 text-center">
                  <Loader2 className="mx-auto animate-spin" size={18} />
                </td>
              </tr>
            )}
            {!loading && alunos.length === 0 && (
              <tr>
                <td colSpan={6} className="p-6 text-center text-slate-500">
                  Nenhum aluno encontrado.
                </td>
              </tr>
            )}
            {!loading &&
              alunos.map((a) => (
                <tr key={a.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="p-4 font-mono text-xs text-slate-400">{a.numero_matricula || '—'}</td>
                  <td className="p-4 font-semibold text-white">
                    {a.nome} {a.sobrenome}
                  </td>
                  <td className="p-4">{a.email || '—'}</td>
                  <td className="p-4">{MODALIDADE_LABEL[a.modalidade] ?? a.modalidade}</td>
                  <td className="p-4">{a.percentual_presenca.toFixed(0)}%</td>
                  <td className="p-4 capitalize">{a.status}</td>
                </tr>
              ))}
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
          poloId={poloId}
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
    </div>
  );
};
