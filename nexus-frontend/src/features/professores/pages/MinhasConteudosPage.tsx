import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  Eye,
  FileText,
  GraduationCap,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { ContentViewer } from '@/components/content/ContentViewer';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import {
  ProfessorDisciplinaConteudosResumo,
} from '@/types/professor';
import {
  ConteudoMaterialForm,
  ConteudoMaterialFormContext,
} from '@/features/professores/components/ConteudoMaterialForm';

export const MinhasConteudosPage: React.FC = () => {
  const [disciplinas, setDisciplinas] = useState<ProfessorDisciplinaConteudosResumo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [formContext, setFormContext] = useState<ConteudoMaterialFormContext | null>(null);
  const [conteudoAberto, setConteudoAberto] = useState<
    ProfessorDisciplinaConteudosResumo['conteudos'][number] | null
  >(null);

  const carregarConteudos = useCallback(async () => {
    setIsLoading(true);
    setErro('');
    try {
      const resposta = await professoresApi.meusConteudos();
      setDisciplinas(resposta.items);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar seus conteúdos e materiais.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregarConteudos();
  }, [carregarConteudos]);

  const carregarArquivoVisualizado = useCallback(() => {
    if (!conteudoAberto) return Promise.reject(new Error('Nenhum conteúdo selecionado.'));
    return professoresApi.baixarConteudo(conteudoAberto.id);
  }, [conteudoAberto?.id]);

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <GraduationCap className="h-3.5 w-3.5" />
            Espaço do Docente
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Conteúdos AVA
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Conteúdo fixo de cada disciplina, que o aluno acompanha e marca como concluído.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void carregarConteudos()}
          disabled={isLoading}
          className="self-start rounded-xl border border-slate-700 bg-slate-800 p-2 text-slate-300 transition-colors hover:bg-slate-700 disabled:opacity-50 sm:self-auto"
          aria-label="Atualizar conteúdos e materiais"
          title="Atualizar"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {erro && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{erro}</span>
          </div>
          <button
            type="button"
            onClick={() => void carregarConteudos()}
            className="rounded-lg px-3 py-1.5 font-semibold text-red-100 hover:bg-red-500/15"
          >
            Tentar novamente
          </button>
        </div>
      )}

      <section className="space-y-4" aria-label="Conteúdos e materiais das disciplinas">
        {isLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 py-16 text-center text-sm text-slate-400">
            <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin text-nexus-yellow" />
            Carregando conteúdos e materiais...
          </div>
        ) : erro ? null : disciplinas.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
            <BookOpen className="mx-auto mb-3 h-8 w-8 text-slate-500" />
            <h2 className="font-semibold text-white">Nenhuma disciplina vinculada</h2>
            <p className="mt-1 text-sm text-slate-400">
              Quando suas disciplinas forem vinculadas, conteúdos e materiais aparecerão aqui.
            </p>
          </div>
        ) : (
          disciplinas.map((disciplina) => (
            <article
              key={disciplina.id}
              className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 shadow-md"
            >
              <header className="border-b border-slate-800 p-5">
                <div className="flex items-start gap-3">
                  <div className="rounded-xl border border-nexus-yellow/20 bg-nexus-yellow/10 p-2.5 text-nexus-yellow">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">{disciplina.nome}</h2>
                    {disciplina.curso_nome && (
                      <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                        <GraduationCap className="h-3.5 w-3.5" />
                        {disciplina.curso_nome}
                      </p>
                    )}
                    {disciplina.turmas.length > 0 && (
                      <p className="mt-2 text-xs text-slate-400">
                        Turmas: {disciplina.turmas.map((turma) => turma.nome).join(' · ')}
                      </p>
                    )}
                  </div>
                </div>
              </header>

              <div className="grid gap-6 p-5 md:grid-cols-2">
                <section aria-label={`Conteúdos de ${disciplina.nome}`}>
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="flex items-center gap-2 font-semibold text-slate-100">
                      <BookOpen className="h-4 w-4 text-blue-300" />
                      Conteúdos
                    </h3>
                    <button
                      type="button"
                      onClick={() => setFormContext({ kind: 'conteudo', disciplinaId: disciplina.id })}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-xs text-blue-200 hover:bg-slate-800"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Adicionar
                    </button>
                  </div>
                  {disciplina.conteudos.length === 0 ? (
                    <p className="text-sm text-slate-400">Nenhum conteúdo cadastrado.</p>
                  ) : (
                    <ul className="space-y-2">
                      {disciplina.conteudos.map((conteudo) => (
                        <li
                          key={conteudo.id}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                            <div className="min-w-0">
                              <p className="truncate text-sm text-slate-200">
                                {conteudo.titulo || 'Conteúdo sem título'}
                              </p>
                              {conteudo.tipo_midia && (
                                <p className="text-xs text-slate-500">{conteudo.tipo_midia}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            {conteudo.tem_arquivo ? (
                              <button
                                type="button"
                                onClick={() => setConteudoAberto(conteudo)}
                                aria-label={`Visualizar ${conteudo.arquivo_nome || conteudo.titulo || 'arquivo'}`}
                                className="text-blue-300 hover:text-blue-200"
                              >
                                <Eye size={16} />
                              </button>
                            ) : conteudo.url_arquivo ? (
                              <button
                                type="button"
                                onClick={() => setConteudoAberto(conteudo)}
                                aria-label={`Visualizar ${conteudo.titulo || 'conteúdo'}`}
                                className="text-blue-300 hover:text-blue-200"
                              >
                                <Eye size={16} />
                              </button>
                            ) : null}
                            <button
                              type="button"
                              onClick={() =>
                                setFormContext({
                                  kind: 'conteudo',
                                  disciplinaId: disciplina.id,
                                  item: conteudo,
                                })
                              }
                              aria-label={`Editar ${conteudo.titulo || 'conteúdo'}`}
                              className="text-slate-400 hover:text-white"
                            >
                              <Pencil size={15} />
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <aside className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
                  <p className="flex items-center gap-2 font-semibold text-slate-200">
                    <CalendarDays className="h-4 w-4 text-emerald-300" />
                    Material das aulas
                  </p>
                  <p className="mt-1">
                    O material usado em cada aula agora é anexado junto com a ata e a chamada, no{' '}
                    <Link to="/professor/aulas" className="font-semibold text-emerald-300 hover:text-emerald-200">
                      Diário de Aulas
                    </Link>
                    {disciplina.materiais.length > 0 &&
                      ` (${disciplina.materiais.length} material(is) já cadastrado(s) nesta disciplina)`}
                    .
                  </p>
                </aside>
              </div>
            </article>
          ))
        )}
      </section>
      {formContext && (
        <ConteudoMaterialForm
          key={
            formContext.kind === 'conteudo'
              ? `conteudo:${formContext.item?.id ?? formContext.disciplinaId}`
              : `material:${formContext.item?.id ?? formContext.vinculoId}`
          }
          context={formContext}
          onCancel={() => setFormContext(null)}
          onSaved={async () => {
            await carregarConteudos();
            setFormContext(null);
          }}
        />
      )}
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
