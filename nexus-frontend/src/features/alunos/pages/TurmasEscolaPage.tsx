import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { alunosApi, apiErrorMessage, EscolaOption, TurmaItem } from '@/features/alunos/api';
import { useAuthStore } from '@/stores/authStore';

const inputCls =
  'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

export const TurmasEscolaPage: React.FC = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.perfil?.nome === 'admin';
  const [escolas, setEscolas] = useState<EscolaOption[]>([]);
  const [escolaId, setEscolaId] = useState<string>(!isAdmin && user?.escola_id ? user.escola_id : '');
  const [turmas, setTurmas] = useState<TurmaItem[]>([]);
  const [nome, setNome] = useState('');
  const [inicio, setInicio] = useState('');
  const [fim, setFim] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const poloId = user?.polo_id;
    const carregarEscolas = async () => {
      try {
        const polos = poloId ? [{ id: poloId, nome: '' }] : await alunosApi.listarPolos();
        const listas = await Promise.all(polos.map((p) => alunosApi.listarEscolas(p.id)));
        const todas = listas.flat();
        setEscolas(todas);
        setEscolaId((atual) => atual || todas[0]?.id || '');
      } catch (e) {
        setErro(apiErrorMessage(e, 'Erro ao carregar escolas.'));
      }
    };
    void carregarEscolas();
  }, [user?.polo_id]);

  const carregar = useCallback(async () => {
    if (!escolaId) return;
    setLoading(true);
    try {
      setTurmas((await alunosApi.listarTurmasEscola(escolaId)).items);
    } catch (e) {
      setErro(apiErrorMessage(e, 'Erro ao carregar turmas.'));
    } finally {
      setLoading(false);
    }
  }, [escolaId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const criar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!escolaId || nome.trim().length < 2) return;
    setSaving(true);
    setErro('');
    try {
      await alunosApi.criarTurmaEscola(escolaId, {
        nome: nome.trim(),
        data_inicio: inicio || null,
        data_fim: fim || null,
      });
      setNome('');
      setInicio('');
      setFim('');
      await carregar();
    } catch (err) {
      setErro(apiErrorMessage(err, 'Erro ao criar turma.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Turmas da escola</h1>

      {erro && <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erro}</div>}

      {(isAdmin || !user?.escola_id) && (
        <select className={inputCls} value={escolaId} onChange={(e) => setEscolaId(e.target.value)}>
          {escolas.map((e) => (
            <option key={e.id} value={e.id}>
              {e.nome}
            </option>
          ))}
        </select>
      )}

      <form onSubmit={criar} className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-800 bg-slate-900 p-4">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Nome da turma</label>
          <input className={inputCls} value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Início</label>
          <input type="date" className={inputCls} value={inicio} onChange={(e) => setInicio(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Fim</label>
          <input type="date" className={inputCls} value={fim} min={inicio || undefined} onChange={(e) => setFim(e.target.value)} />
        </div>
        <button
          type="submit"
          disabled={saving || !escolaId}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Criar turma
        </button>
      </form>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-4">Turma</th>
              <th className="p-4">Início</th>
              <th className="p-4">Fim</th>
              <th className="p-4">Alunos</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={4} className="p-6 text-center">
                  <Loader2 className="mx-auto animate-spin" size={18} />
                </td>
              </tr>
            )}
            {!loading && turmas.length === 0 && (
              <tr>
                <td colSpan={4} className="p-6 text-center text-slate-500">
                  Nenhuma turma cadastrada.
                </td>
              </tr>
            )}
            {!loading &&
              turmas.map((t) => (
                <tr key={t.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="p-4 font-semibold text-white">{t.nome}</td>
                  <td className="p-4">{t.data_inicio || '—'}</td>
                  <td className="p-4">{t.data_fim || '—'}</td>
                  <td className="p-4">{t.total_alunos}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
