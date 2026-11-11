import React, { useEffect, useState } from 'react';
import { BookOpen, Download, ExternalLink, Loader2 } from 'lucide-react';
import { alunosGestaoApi, apiErrorMessage, CursoAprendizado } from '@/features/alunos/api';

export const MinhasDisciplinasPage: React.FC = () => {
  const [cursos, setCursos] = useState<CursoAprendizado[] | null>(null);
  const [erro, setErro] = useState('');
  const [salvandoId, setSalvandoId] = useState<string | null>(null);
  const [baixandoId, setBaixandoId] = useState<string | null>(null);

  useEffect(() => {
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

  const baixarArquivo = async (conteudoId: string, nome: string) => {
    setErro('');
    setBaixandoId(conteudoId);
    try {
      const arquivo = await alunosGestaoApi.baixarConteudoArquivo(conteudoId);
      const url = URL.createObjectURL(arquivo);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = nome;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível baixar este arquivo.'));
    } finally {
      setBaixandoId(null);
    }
  };

  if (cursos === null) {
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

      {cursos.length === 0 && !erro && (
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
                            disabled={baixandoId === conteudo.id}
                            onClick={() =>
                              void baixarArquivo(
                                conteudo.id,
                                conteudo.arquivo_nome || conteudo.titulo || 'conteudo'
                              )
                            }
                            aria-label={`Baixar ${conteudo.arquivo_nome || conteudo.titulo || 'conteúdo'}`}
                            className="shrink-0 text-blue-300 hover:text-blue-200 disabled:opacity-50"
                          >
                            <Download size={15} />
                          </button>
                        ) : conteudo.url_arquivo ? (
                          <a
                            href={conteudo.url_arquivo}
                            target="_blank"
                            rel="noreferrer"
                            aria-label={`Abrir ${conteudo.titulo || 'conteúdo'}`}
                            className="shrink-0 text-blue-300 hover:text-blue-200"
                          >
                            <ExternalLink size={15} />
                          </a>
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
    </div>
  );
};
