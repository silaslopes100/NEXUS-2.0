import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowDownToLine,
  ArrowUpFromLine,
  CheckCircle2,
  KeyRound,
  Loader2,
  RefreshCw,
  X,
} from 'lucide-react';
import { alunosApi, AlunoItem } from '@/features/alunos/api';
import {
  EscolaLicencaKpis,
  licencasApi,
  MovimentacaoLicenca,
} from '@/features/licencas/api';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { EscolaItem } from '@/types/polos';

const cardStyle = 'rounded-2xl border border-slate-800 bg-slate-900/80 p-4';

export const LicencasEscolaPage: React.FC = () => {
  const { escolaId = '' } = useParams<{ escolaId: string }>();
  const navigate = useNavigate();
  const [school, setSchool] = useState<EscolaItem | null>(null);
  const [kpis, setKpis] = useState<EscolaLicencaKpis | null>(null);
  const [items, setItems] = useState<MovimentacaoLicenca[]>([]);
  const [students, setStudents] = useState<AlunoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [action, setAction] = useState<'venda' | 'devolucao' | null>(null);
  const [alunoId, setAlunoId] = useState('');
  const [quantidade, setQuantidade] = useState(1);

  const load = useCallback(async () => {
    if (!escolaId) return;
    setLoading(true);
    try {
      const [schoolInfo, indicators, movements] = await Promise.all([
        polosEscolasApi.obterEscola(escolaId),
        licencasApi.getKpisEscola(escolaId),
        licencasApi.listMovimentacoesEscola(escolaId, { limit: 50, offset: 0 }),
      ]);
      setSchool(schoolInfo);
      setKpis(indicators);
      setItems(movements.items || []);
      const studentList = await alunosApi.listar(schoolInfo.polo_id, {
        escola_id: escolaId,
        status: 'ativo',
        limit: 200,
        offset: 0,
      });
      setStudents(studentList.items || []);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível carregar as licenças da escola.');
    } finally {
      setLoading(false);
    }
  }, [escolaId]);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!school) return;
    setSaving(true);
    try {
      if (action === 'venda') {
        if (!alunoId) {
          setFeedback('Selecione um aluno para registrar a venda.');
          return;
        }
        await licencasApi.vender(escolaId, { aluno_id: alunoId, quantidade });
      } else if (action === 'devolucao') {
        await licencasApi.devolverEscola(escolaId, quantidade);
      }
      setFeedback('Movimentação de licença registrada com sucesso.');
      setAction(null);
      setAlunoId('');
      setQuantidade(1);
      await load();
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'A movimentação não pôde ser concluída.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <button type="button" onClick={() => navigate(-1)} className="mb-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
            <ArrowLeft size={14} /> Voltar
          </button>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300"><KeyRound size={15} /> Gestão de licenças</p>
          <h1 className="text-3xl font-extrabold text-white">{school?.nome || 'Escola'}</h1>
          <p className="mt-1 text-sm text-slate-400">Estoque, vendas e devoluções de licenças desta unidade.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={!kpis || kpis.licencas_nao_vendidas < 1} onClick={() => setAction('venda')} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
            <ArrowDownToLine size={16} /> Vender licença
          </button>
          <button type="button" disabled={!kpis || kpis.licencas_nao_vendidas < 1} onClick={() => setAction('devolucao')} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
            <ArrowUpFromLine size={16} /> Devolver ao polo
          </button>
        </div>
      </header>

      {feedback && (
        <div role="status" className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
          <span className="flex items-center gap-2"><CheckCircle2 size={16} />{feedback}</span>
          <button type="button" onClick={() => setFeedback('')} aria-label="Fechar mensagem"><X size={16} /></button>
        </div>
      )}

      {loading ? <div className="flex justify-center py-16 text-amber-300"><Loader2 className="animate-spin" /></div> : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {[
              ['Recebidas', kpis?.licencas_recebidas ?? 0],
              ['Vendidas', kpis?.licencas_vendidas ?? 0],
              ['Disponíveis', kpis?.licencas_nao_vendidas ?? 0],
              ['Conversão', `${kpis?.taxa_conversao ?? 0}%`],
              ['Ociosidade', `${kpis?.taxa_ociosidade ?? 0}%`],
            ].map(([label, value]) => <div key={String(label)} className={cardStyle}><p className="text-xs font-semibold uppercase text-slate-500">{label}</p><strong className="mt-2 block text-2xl font-black text-white">{value}</strong></div>)}
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
            <div className="flex items-center justify-between border-b border-slate-800 p-4">
              <div><h2 className="font-bold text-white">Movimentações da escola</h2><p className="text-xs text-slate-500">{items.length} registros carregados</p></div>
              <button type="button" onClick={() => void load()} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} /></button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-500"><tr><th className="p-4">Tipo</th><th className="p-4">Aluno</th><th className="p-4 text-center">Quantidade</th><th className="p-4">Status</th><th className="p-4 text-right">Data</th></tr></thead>
                <tbody className="divide-y divide-slate-800">
                  {items.map((item) => <tr key={item.id} className="text-slate-300"><td className="p-4 font-medium capitalize text-white">{item.tipo.replace(/_/g, ' ')}</td><td className="p-4">{item.aluno_id || '—'}</td><td className="p-4 text-center">{item.quantidade}</td><td className="p-4">{item.status}</td><td className="p-4 text-right">{item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '—'}</td></tr>)}
                  {!items.length && <tr><td colSpan={5} className="p-10 text-center text-slate-500">Nenhuma movimentação encontrada.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {action && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between"><h2 className="text-xl font-bold text-white">{action === 'venda' ? 'Vender licença' : 'Devolver licenças ao polo'}</h2><button type="button" onClick={() => setAction(null)} aria-label="Fechar"><X /></button></div>
            {action === 'venda' && <label className="block space-y-1 text-sm text-slate-300"><span>Aluno</span><select required value={alunoId} onChange={(event) => setAlunoId(event.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white"><option value="">Selecione um aluno</option>{students.map((student) => <option key={student.id} value={student.id}>{student.nome} {student.sobrenome || ''} — {student.numero_matricula || student.id}</option>)}</select></label>}
            <label className="block space-y-1 text-sm text-slate-300"><span>Quantidade</span><input type="number" required min={1} max={kpis?.licencas_nao_vendidas || 1} value={quantidade} onChange={(event) => setQuantidade(Number(event.target.value))} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white" /></label>
            <div className="flex justify-end gap-2"><button type="button" onClick={() => setAction(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="animate-spin" size={15} />}Confirmar</button></div>
          </form>
        </div>
      )}
    </div>
  );
};
