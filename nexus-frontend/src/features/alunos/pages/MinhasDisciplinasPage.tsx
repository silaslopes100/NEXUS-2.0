import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, CheckCircle2, ClipboardCheck, Eye, Loader2, XCircle } from 'lucide-react';
import { AvaliacaoAluno, avaliacoesApi, formatarNota } from '@/features/avaliacoes/api';
import { ContentViewer } from '@/components/content/ContentViewer';
import {
  alunosGestaoApi,
  apiErrorMessage,
  ConteudoAprendizado,
  CursoAprendizado,
} from '@/features/alunos/api';

const CartaoAvaliacao: React.FC<{ item: AvaliacaoAluno; destaque: boolean }> = ({ item, destaque }) => {
  const navigate = useNavigate();
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (destaque) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [destaque]);

  const status = (() => {
    switch (item.situacao) {
      case 'aprovado':
        return { texto: `Aprovado · nota ${formatarNota(item.melhor_nota)}`, cor: 'text-emerald-300', icone: <CheckCircle2 size={16} /> };
      case 'reprovado':
        return {
          texto: `Nota ${formatarNota(item.melhor_nota)} · ${item.tentativas_restantes} tentativa(s) restante(s)`,
          cor: 'text-amber-300',
          icone: <XCircle size={16} />,
        };
      case 'sem_tentativas':
        return { texto: `Tentativas esgotadas · nota ${formatarNota(item.melhor_nota)}`, cor: 'text-red-300', icone: <XCircle size={16} /> };
      case 'em_andamento':
        return { texto: 'Avaliação em andamento', cor: 'text-blue-300', icone: <ClipboardCheck size={16} /> };
      case 'sem_avaliacao':
        return { texto: 'A avaliação ainda não foi publicada', cor: 'text-slate-400', icone: <ClipboardCheck size={16} /> };
      case 'ava':
        return { texto: 'Disponível no AVA', cor: 'text-slate-400', icone: <ClipboardCheck size={16} /> };
      default:
        return { texto: 'Disponível', cor: 'text-blue-300', icone: <ClipboardCheck size={16} /> };
    }
  })();

  return (
    <article
      ref={ref}
      className={`flex flex-col gap-3 rounded-2xl border bg-slate-900 p-4 sm:flex-row sm:items-center sm:justify-between ${
        destaque ? 'border-nexus-yellow ring-2 ring-nexus-yellow/30' : 'border-slate-800'
      }`}
    >
      <div className="min-w-0">
        <h3 className="font-semibold text-white">{item.disciplina_nome || 'Disciplina'}</h3>
        <p className={`mt-1 flex items-center gap-1.5 text-sm ${status.cor}`}>
          {status.icone} {status.texto}
        </p>
        {item.pode_realizar && item.tempo_limite_min ? (
          <p className="mt-1 text-xs text-slate-500">Tempo: {item.tempo_limite_min} minutos</p>
        ) : null}
      </div>
      {item.pode_realizar && item.avaliacao_id && (
        <button
          type="button"
          onClick={() => navigate(`/aluno/avaliacoes/${item.avaliacao_id}`)}
          className="shrink-0 rounded-xl bg-nexus-yellow px-5 py-3 text-sm font-bold text-ink hover:bg-nexus-yellow-hover"
        >
          {item.situacao === 'em_andamento' ? 'Continuar Avaliação' : 'Realizar Avaliação'}
        </button>
      )}
    </article>
  );
};

export const MinhasDisciplinasPage: React.FC = () => {
  const [params] = useSearchParams();
  const disciplinaDestaque = params.get('disciplina');
  const [avaliacoes, setAvaliacoes] = useState<AvaliacaoAluno[] | null>(null);
  const [cursos, setCursos] = useState<CursoAprendizado[] | null>(null);
  const [erro, setErro] = useState('');
  const [salvandoId, setSalvandoId] = useState<string | null>(null);
  const [conteudoAberto, setConteudoAberto] = useState<ConteudoAprendizado | null>(null);

  useEffect(() => {
    avaliacoesApi
      .minhas()
      .then(setAvaliacoes)
      .catch(() => setAvaliacoes([]));
    alunosGestaoApi
      .aprendizado()
      .then(setCursos)
      .catch((err: unknown) => {
        setCursos([]);
        setErro(apiErrorMessage(err, 'Não foi possível carregar suas disciplinas.'));
      });
  }, []);

  const alternar = async (conteudoId: string, concluido: boolean) => {
    setSalvandoId(conteudoId);
    setErro('');
    try {
      await alunosGestaoApi.marcarConteudo(conteudoId, concluido);
      setCursos((atuais) =>
        (atuais ?? []).map((curso) => ({
          ...curso,
          disciplinas: curso.disciplinas.map((disciplina) => ({
            ...disciplina,
            conteudos: disciplina.conteudos.map((conteudo) =>
              conteudo.id === conteudoId ? { ...conteudo, concluido } : conteudo
            ),
          })),
        }))
      );
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível salvar o progresso.'));
    } finally {
      setSalvandoId(null);
    }
  };

  const carregarArquivoVisualizado = useCallback(() => {
    if (!conteudoAberto) return Promise.reject(new Error('Nenhum conteúdo selecionado.'));
    return alunosGestaoApi.baixarConteudoArquivo(conteudoAberto.id);
  }, [conteudoAberto?.id]);

  if (cursos === null || avaliacoes === null) {
    return (
      <div className="flex justify-center py-16 text-blue-400">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Minhas Disciplinas</h1>
        <p className="text-sm text-slate-400">Marque os conteúdos concluídos para acompanhar seu progresso.</p>
      </header>

      {erro && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {erro}
        </div>
      )}

      {avaliacoes.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 font-bold text-white">
            <ClipboardCheck size={17} className="text-nexus-yellow" />
            Avaliações
          </h2>
          {[...avaliacoes]
            .sort((a, b) => Number(b.disciplina_id === disciplinaDestaque) - Number(a.disciplina_id === disciplinaDestaque))
            .map((item) => (
              <CartaoAvaliacao key={item.disciplina_id} item={item} destaque={item.disciplina_id === disciplinaDestaque} />
            ))}
        </section>
      )}

      {cursos.length === 0 && avaliacoes.length === 0 && !erro && (
        <p className="rounded-2xl border border-slate-800 bg-slate-900 p-10 text-center text-sm text-slate-500">
          Você ainda não tem disciplinas vinculadas.
        </p>
      )}

      {cursos.map((curso) => (
        <section key={curso.id} className="space-y-3">
          <h2 className="flex items-center gap-2 font-bold text-white">
            <BookOpen size={17} className="text-blue-300" />
            {curso.nome}
          </h2>
          {curso.disciplinas.map((disciplina) => {
            const concluidos = disciplina.conteudos.filter((c) => c.concluido).length;
            const total = disciplina.conteudos.length;
            return (
              <article key={disciplina.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold text-slate-100">{disciplina.nome}</h3>
                  <span className="shrink-0 text-xs text-slate-400">
                    {total ? `${Math.round((concluidos / total) * 100)}%` : 'Sem conteúdo'}
                  </span>
                </div>
                {total > 0 && (
                  <ul className="mt-3 space-y-1">
                    {disciplina.conteudos.map((conteudo) => (
                      <li key={conteudo.id} className="flex items-center justify-between gap-3 rounded-lg p-1.5 hover:bg-slate-800/50">
                        <label className="flex min-w-0 cursor-pointer items-center gap-2 text-sm text-slate-300">
                          <input
                            type="checkbox"
                            checked={conteudo.concluido}
                            disabled={salvandoId === conteudo.id}
                            onChange={(event) => void alternar(conteudo.id, event.target.checked)}
                            className="h-4 w-4 shrink-0 rounded border-slate-600 bg-slate-950"
                          />
                          <span className="truncate">{conteudo.titulo || 'Conteúdo sem título'}</span>
                        </label>
                        {conteudo.tem_arquivo ? (
                          <button
                            type="button"
                            onClick={() => setConteudoAberto(conteudo)}
                            aria-label={`Visualizar ${conteudo.arquivo_nome || conteudo.titulo || 'conteúdo'}`}
                            className="shrink-0 text-blue-300 hover:text-blue-200"
                          >
                            <Eye size={15} />
                          </button>
                        ) : conteudo.url_arquivo ? (
                          <button
                            type="button"
                            onClick={() => setConteudoAberto(conteudo)}
                            aria-label={`Visualizar ${conteudo.titulo || 'conteúdo'}`}
                            className="shrink-0 text-blue-300 hover:text-blue-200"
                          >
                            <Eye size={15} />
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            );
          })}
        </section>
      ))}
      {conteudoAberto && (
        <ContentViewer
          title={conteudoAberto.titulo || 'Conteúdo da disciplina'}
          url={conteudoAberto.tem_arquivo ? undefined : conteudoAberto.url_arquivo}
          file={
            conteudoAberto.tem_arquivo
              ? {
                  name: conteudoAberto.arquivo_nome || conteudoAberto.titulo || 'conteudo',
                  mimeType: conteudoAberto.arquivo_mime_type,
                  load: carregarArquivoVisualizado,
                }
              : undefined
          }
          onClose={() => setConteudoAberto(null)}
        />
      )}
    </div>
  );
};
