import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  ExternalLink,
  FileText,
  GraduationCap,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  X,
} from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import {
  ProfessorConteudoItem,
  ProfessorDisciplinaConteudosResumo,
  ProfessorMaterialResumo,
} from '@/types/professor';
import { formatarData } from '@/features/turmas/api';

type ConteudoMaterialFormContext =
  | { kind: 'conteudo'; disciplinaId: string; item?: ProfessorConteudoItem }
  | { kind: 'material'; vinculoId: string; item?: ProfessorMaterialResumo };

export const MinhasConteudosPage: React.FC = () => {
  const [disciplinas, setDisciplinas] = useState<ProfessorDisciplinaConteudosResumo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [formContext, setFormContext] = useState<ConteudoMaterialFormContext | null>(null);
  const [baixandoId, setBaixandoId] = useState<string | null>(null);

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

  const baixarArquivo = async (tipo: 'conteudo' | 'material', id: string, nome: string) => {
    setErro('');
    setBaixandoId(`${tipo}:${id}`);
    try {
      const arquivo =
        tipo === 'conteudo'
          ? await professoresApi.baixarConteudo(id)
          : await professoresApi.baixarMaterial(id);
      const url = URL.createObjectURL(arquivo);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = nome;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível baixar o arquivo.'));
    } finally {
      setBaixandoId(null);
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <GraduationCap className="h-3.5 w-3.5" />
            Espaço do Docente
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Conteúdos &amp; Materiais
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Consulte os conteúdos e materiais cadastrados para suas disciplinas e turmas.
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
                                disabled={baixandoId === `conteudo:${conteudo.id}`}
                                onClick={() =>
                                  void baixarArquivo(
                                    'conteudo',
                                    conteudo.id,
                                    conteudo.arquivo_nome || conteudo.titulo || 'conteudo'
                                  )
                                }
                                aria-label={`Baixar ${conteudo.arquivo_nome || conteudo.titulo || 'arquivo'}`}
                                className="text-blue-300 hover:text-blue-200 disabled:opacity-50"
                              >
                                <ExternalLink size={16} />
                              </button>
                            ) : conteudo.url_arquivo ? (
                              <a
                                href={conteudo.url_arquivo}
                                target="_blank"
                                rel="noreferrer"
                                aria-label={`Abrir ${conteudo.titulo || 'conteúdo'}`}
                                className="text-blue-300 hover:text-blue-200"
                              >
                                <ExternalLink size={16} />
                              </a>
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

                <section aria-label={`Materiais de ${disciplina.nome}`}>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-100">
                    <FileText className="h-4 w-4 text-emerald-300" />
                    Materiais
                  </h3>
                  {disciplina.turmas.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-2">
                      {disciplina.turmas.map((turma) => (
                        <button
                          key={turma.id}
                          type="button"
                          disabled={!turma.professor_disciplina_id}
                          onClick={() =>
                            turma.professor_disciplina_id &&
                            setFormContext({
                              kind: 'material',
                              vinculoId: turma.professor_disciplina_id,
                            })
                          }
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-xs text-emerald-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Plus className="h-3.5 w-3.5" />
                          {turma.nome}
                        </button>
                      ))}
                    </div>
                  )}
                  {disciplina.materiais.length === 0 ? (
                    <p className="text-sm text-slate-400">Nenhum material cadastrado.</p>
                  ) : (
                    <ul className="space-y-2">
                      {disciplina.materiais.map((material) => (
                        <li
                          key={material.id}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm text-slate-200">
                              {material.descricao || 'Material da disciplina'}
                            </p>
                            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                              {material.turma_nome && <span>{material.turma_nome}</span>}
                              {material.data_aula && (
                                <span className="inline-flex items-center gap-1">
                                  <CalendarDays className="h-3 w-3" />
                                  {formatarData(material.data_aula)}
                                </span>
                              )}
                              {material.expira_em && (
                                <span>Expira em {formatarData(material.expira_em)}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            {material.tem_arquivo ? (
                              <button
                                type="button"
                                disabled={baixandoId === `material:${material.id}`}
                                onClick={() =>
                                  void baixarArquivo(
                                    'material',
                                    material.id,
                                    material.arquivo_nome || material.descricao || 'material'
                                  )
                                }
                                aria-label={`Baixar ${material.arquivo_nome || material.descricao || 'arquivo'}`}
                                className="text-emerald-300 hover:text-emerald-200 disabled:opacity-50"
                              >
                                <ExternalLink size={16} />
                              </button>
                            ) : material.arquivo_url ? (
                              <a
                                href={material.arquivo_url}
                                target="_blank"
                                rel="noreferrer"
                                aria-label={`Abrir ${material.descricao || 'material'}`}
                                className="text-emerald-300 hover:text-emerald-200"
                              >
                                <ExternalLink size={16} />
                              </a>
                            ) : null}
                            <button
                              type="button"
                              onClick={() => setFormContext({ kind: 'material', vinculoId: material.professor_disciplina_id, item: material })}
                              aria-label={`Editar ${material.descricao || 'material'}`}
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
    </div>
  );
};

interface ConteudoMaterialFormProps {
  context: ConteudoMaterialFormContext;
  onCancel: () => void;
  onSaved: () => Promise<void>;
}

const ConteudoMaterialForm: React.FC<ConteudoMaterialFormProps> = ({
  context,
  onCancel,
  onSaved,
}) => {
  const conteudo = context.kind === 'conteudo' ? context.item : undefined;
  const material = context.kind === 'material' ? context.item : undefined;
  const [titulo, setTitulo] = useState(conteudo?.titulo || '');
  const [tipoMidia, setTipoMidia] = useState(conteudo?.tipo_midia || 'documento');
  const [descricao, setDescricao] = useState(material?.descricao || '');
  const [url, setUrl] = useState(conteudo?.url_arquivo || material?.arquivo_url || '');
  const [dataAula, setDataAula] = useState(material?.data_aula?.slice(0, 10) || '');
  const [expiraEm, setExpiraEm] = useState(material?.expira_em?.slice(0, 16) || '');
  const [modo, setModo] = useState<'link' | 'arquivo'>(
    conteudo?.tem_arquivo || material?.tem_arquivo ? 'arquivo' : 'link'
  );
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [erro, setErro] = useState('');
  const [salvando, setSalvando] = useState(false);

  const salvar = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErro('');

    if (modo === 'link' && !url.trim()) {
      setErro('Informe o endereço do link.');
      return;
    }
    if (modo === 'arquivo' && !arquivo && !conteudo?.tem_arquivo && !material?.tem_arquivo) {
      setErro('Selecione um arquivo para enviar.');
      return;
    }

    const form = new FormData();
    form.append('modo', modo);
    if (modo === 'link') form.append('url_arquivo', url.trim());
    if (arquivo) form.append('arquivo', arquivo);

    if (context.kind === 'conteudo') {
      form.append('titulo', titulo.trim());
      form.append('tipo_midia', tipoMidia);
      form.append('ordem', String(conteudo?.ordem ?? 0));
      if (!conteudo) form.append('disciplina_id', context.disciplinaId);
    } else {
      form.append('descricao', descricao.trim());
      if (dataAula) form.append('data_aula', dataAula);
      if (expiraEm) form.append('expira_em', expiraEm);
      if (!material) form.append('professor_disciplina_id', context.vinculoId);
    }

    setSalvando(true);
    try {
      if (context.kind === 'conteudo') {
        if (conteudo) {
          await professoresApi.atualizarConteudo(conteudo.id, form);
        } else {
          await professoresApi.criarConteudo(form);
        }
      } else if (material) {
        await professoresApi.atualizarMaterial(material.id, form);
      } else {
        await professoresApi.criarMaterial(form);
      }
      await onSaved();
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível salvar o conteúdo.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="conteudo-material-form-titulo"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
      >
        <header className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 id="conteudo-material-form-titulo" className="text-lg font-bold text-white">
              {context.kind === 'conteudo'
                ? conteudo
                  ? 'Editar conteúdo'
                  : 'Adicionar conteúdo'
                : material
                  ? 'Editar material da turma'
                  : 'Adicionar material à turma'}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Arquivos de até 4 MiB. Links devem começar com HTTP ou HTTPS.
            </p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Fechar formulário"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <form onSubmit={(event) => void salvar(event)} className="space-y-4">
          {context.kind === 'conteudo' ? (
            <>
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Título</span>
                <input
                  value={titulo}
                  onChange={(event) => setTitulo(event.target.value)}
                  required
                  maxLength={255}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Tipo</span>
                <select
                  value={tipoMidia}
                  onChange={(event) => setTipoMidia(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                >
                  <option value="documento">Documento</option>
                  <option value="video">Vídeo</option>
                  <option value="link">Link</option>
                  <option value="imagem">Imagem</option>
                </select>
              </label>
            </>
          ) : (
            <>
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Descrição</span>
                <input
                  value={descricao}
                  onChange={(event) => setDescricao(event.target.value)}
                  required
                  maxLength={500}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-1.5 text-sm text-slate-300">
                  <span>Data da aula</span>
                  <input
                    type="date"
                    value={dataAula}
                    onChange={(event) => setDataAula(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                  />
                </label>
                <label className="block space-y-1.5 text-sm text-slate-300">
                  <span>Expira em</span>
                  <input
                    type="datetime-local"
                    value={expiraEm}
                    onChange={(event) => setExpiraEm(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                  />
                </label>
              </div>
            </>
          )}

          <label className="block space-y-1.5 text-sm text-slate-300">
            <span>Origem do material</span>
            <select
              value={modo}
              onChange={(event) => setModo(event.target.value as 'link' | 'arquivo')}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
            >
              <option value="link">Link externo</option>
              <option value="arquivo">Enviar arquivo</option>
            </select>
          </label>

          {modo === 'link' ? (
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Link HTTP/HTTPS</span>
              <input
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                required
                placeholder="https://..."
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
              />
            </label>
          ) : (
            <div className="space-y-2">
              {((conteudo?.tem_arquivo && conteudo.arquivo_nome) ||
                (material?.tem_arquivo && material.arquivo_nome)) && !arquivo && (
                <p className="text-xs text-slate-400">
                  Arquivo atual:{' '}
                  {conteudo?.arquivo_nome || material?.arquivo_nome}. Selecione outro para substituir.
                </p>
              )}
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Arquivo (máximo 4 MiB)</span>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.jpg,.jpeg,.png,.webp"
                  onChange={(event) => {
                    const selected = event.target.files?.[0] ?? null;
                    if (selected && selected.size > 4 * 1024 * 1024) {
                      setErro('O arquivo deve ter no máximo 4 MiB.');
                      setArquivo(null);
                      event.target.value = '';
                      return;
                    }
                    setErro('');
                    setArquivo(selected);
                  }}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-1 file:text-slate-200"
                />
              </label>
            </div>
          )}

          {erro && (
            <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {erro}
            </p>
          )}
          <footer className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={salvando}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
            >
              {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Salvar
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
};
