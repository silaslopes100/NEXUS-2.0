import React, { useEffect, useState } from 'react';
import { AlertCircle, CalendarCheck, Loader2, RefreshCw } from 'lucide-react';
import { MinhaFrequencia, minhasPresencasApi } from '@/features/presencas/api';
import { FrequenciaPorDisciplina, ResumoFrequencia } from '@/features/presencas/components/FrequenciaPorDisciplina';

const erroTexto = (error: unknown, padrao: string) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
};

/** Presenças e frequência do aluno por Disciplina, vindas das chamadas e atas registradas pelos professores. */
export const MinhasPresencasPage: React.FC = () => {
  const [dados, setDados] = useState<MinhaFrequencia | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      setDados(await minhasPresencasApi.carregar());
    } catch (error) {
      setErro(erroTexto(error, 'Não foi possível carregar suas presenças.'));
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => { void carregar(); }, []);

  const minimo = dados?.frequencia_minima ?? 75;

  return (
    <div className="max-w-6xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Frequência &amp; Presença</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Escolha a disciplina para ver suas presenças, faltas e o conteúdo de cada aula registrado pelo professor. A
            frequência mínima é de {minimo}%.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void carregar()}
          disabled={carregando}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} /> Atualizar
        </button>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {carregando && !dados ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : dados && dados.disciplinas.length === 0 ? (
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
          <CalendarCheck className="mx-auto mb-3 h-8 w-8 text-slate-500" />
          <h2 className="font-semibold text-white">Nenhuma chamada registrada ainda</h2>
          <p className="mt-1 text-sm text-slate-400">Assim que os professores fizerem a chamada, suas presenças aparecem aqui.</p>
        </div>
      ) : dados ? (
        <>
          <ResumoFrequencia dados={dados} />
          <FrequenciaPorDisciplina dados={dados} />
        </>
      ) : null}
    </div>
  );
};
