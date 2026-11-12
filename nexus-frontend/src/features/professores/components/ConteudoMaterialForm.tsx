import React, { useState } from 'react';
import { Loader2, Save, X } from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { ProfessorConteudoItem, ProfessorMaterialResumo } from '@/types/professor';

/**
 * Formulário de conteúdo AVA (por disciplina) ou de material de aula (por turma).
 * Com `aulaId`, o material é anexado a uma aula do Diário de Aulas e herda a data dela.
 */
export type ConteudoMaterialFormContext =
  | { kind: 'conteudo'; disciplinaId: string; item?: ProfessorConteudoItem }
  | { kind: 'material'; vinculoId: string; aulaId?: string; item?: ProfessorMaterialResumo };

export interface ConteudoMaterialFormProps {
  context: ConteudoMaterialFormContext;
  onCancel: () => void;
  onSaved: () => Promise<void>;
  /**
   * Quando informado, o formulário NÃO envia nada: entrega o FormData montado
   * (ex.: anexo guardado até a aula ser registrada no Diário de Aulas).
   */
  aoConfirmar?: (form: FormData) => void;
}

export const ConteudoMaterialForm: React.FC<ConteudoMaterialFormProps> = ({
  context,
  onCancel,
  onSaved,
  aoConfirmar,
}) => {
  const conteudo = context.kind === 'conteudo' ? context.item : undefined;
  const material = context.kind === 'material' ? context.item : undefined;
  const aulaId = context.kind === 'material' ? context.aulaId : undefined;
  // Anexo de uma aula (já registrada ou ainda em rascunho): a data vem da aula.
  const anexoDeAula = Boolean(aulaId || aoConfirmar);
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
      if (aulaId) form.append('aula_id', aulaId);
      else if (dataAula && !anexoDeAula) form.append('data_aula', dataAula);
      if (expiraEm) form.append('expira_em', expiraEm);
      if (!material) form.append('professor_disciplina_id', context.vinculoId);
    }

    if (aoConfirmar) {
      aoConfirmar(form);
      return;
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
              <div className={`grid gap-3 ${anexoDeAula ? '' : 'sm:grid-cols-2'}`}>
                {!anexoDeAula && (
                  <label className="block space-y-1.5 text-sm text-slate-300">
                    <span>Data da aula</span>
                    <input
                      type="date"
                      value={dataAula}
                      onChange={(event) => setDataAula(event.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                    />
                  </label>
                )}
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
