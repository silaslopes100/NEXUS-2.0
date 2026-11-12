import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileText,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { AlunoChamada, presencasApi, PresencaVinculo } from '@/features/presencas/api';
import { ConteudoMaterialForm } from '@/features/professores/components/ConteudoMaterialForm';
import { formatarData } from '@/features/turmas/api';
import { AulaDetalhe, AulaResumo, aulasApi, dataLocalHoje } from '@/features/aulas/api';
import { MaterialItem, SeloAta, SeloPresenca } from '@/features/aulas/components/AulaComponentes';

const PAGE_SIZE = 20;
const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-400 disabled:opacity-60';

const nomeVinculo = (v?: Pick<PresencaVinculo, 'disciplina_nome' | 'turma_nome'> | null) =>
  v ? `${v.disciplina_nome || 'Disciplina'} — ${v.turma_nome || 'Turma'}` : '';

export const DiarioAulasPage: React.FC = () => {
  const [vinculos, setVinculos] = useState<PresencaVinculo[]>([]);
  const [aulas, setAulas] = useState<AulaResumo[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [filtroVinculo, setFiltroVinculo] = useState('');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [editor, setEditor] = useState<{ aulaId?: string } | null>(null);
  const [excluindo, setExcluindo] = useState<AulaResumo | null>(null);

  useEffect(() => {
    presencasApi
      .listarVinculos()
      .then(setVinculos)
      .catch((error: unknown) =>
        setErro(apiErrorMessage(error, 'Não foi possível carregar suas turmas.'))
      );
  }, []);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const resposta = await aulasApi.listarMinhas({
        vinculo_id: filtroVinculo,
        data_inicio: dataInicio,
        data_fim: dataFim,
        q: buscaAplicada,
        limit: PAGE_SIZE,
        offset,
      });
      setAulas(resposta.items);
      setTotal(resposta.total);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar suas aulas.'));
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, dataFim, dataInicio, filtroVinculo, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const confirmarExclusao = async () => {
    if (!excluindo) return;
    try {
      await aulasApi.excluir(excluindo.id);
      setSucesso('Aula excluída, com a chamada e os materiais.');
      setExcluindo(null);
      void carregar();
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível excluir a aula.'));
      setExcluindo(null);
    }
  };

  const paginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const paginaAtual = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-300">
            <ClipboardList className="h-3.5 w-3.5" />
            Espaço do Docente
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">Diário de Aulas</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Registre cada aula em um só lugar: a ata (o que foi ministrado), o material usado e a chamada.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setSucesso('');
            setEditor({});
          }}
          disabled={vinculos.length === 0}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50 sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Registrar aula
        </button>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
          {erro}
        </div>
      )}
      {sucesso && (
        <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
          {sucesso}
        </div>
      )}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/80 shadow-md">
        <div className="grid gap-3 border-b border-slate-800 p-4 md:grid-cols-[minmax(0,1.4fr)_150px_150px_minmax(0,1fr)_auto]">
          <select
            aria-label="Filtrar por disciplina e turma"
            value={filtroVinculo}
            onChange={(e) => {
              setOffset(0);
              setFiltroVinculo(e.target.value);
            }}
            className={campo}
          >
            <option value="">Todas as disciplinas e turmas</option>
            {vinculos.map((v) => (
              <option key={v.id} value={v.id}>
                {nomeVinculo(v)}
              </option>
            ))}
          </select>
          <input
            type="date"
            aria-label="De"
            value={dataInicio}
            onChange={(e) => {
              setOffset(0);
              setDataInicio(e.target.value);
            }}
            className={campo}
          />
          <input
            type="date"
            aria-label="Até"
            value={dataFim}
            onChange={(e) => {
              setOffset(0);
              setDataFim(e.target.value);
            }}
            className={campo}
          />
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setOffset(0);
                  setBuscaAplicada(busca.trim());
                }
              }}
              placeholder="Buscar na ata ou no material"
              className={`${campo} pl-9`}
            />
          </div>
          <button
            type="button"
            onClick={() => void carregar()}
            aria-label="Atualizar"
            className="rounded-xl border border-slate-700 p-2.5 text-slate-300 hover:bg-slate-800"
          >
            <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {carregando ? (
          <div className="py-16 text-center text-sm text-slate-400">
            <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin text-emerald-400" />
            Carregando aulas...
          </div>
        ) : aulas.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <CalendarDays className="mx-auto mb-3 h-8 w-8 text-slate-500" />
            <h2 className="font-semibold text-white">Nenhuma aula registrada</h2>
            <p className="mt-1 text-sm text-slate-400">
              {vinculos.length === 0
                ? 'Você ainda não tem turmas vinculadas. Fale com a coordenação.'
                : 'Use "Registrar aula" para lançar a ata, o material e a chamada.'}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-800">
            {aulas.map((aula) => (
              <li key={aula.id} className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-white">
                    <CalendarDays className="h-4 w-4 text-emerald-300" />
                    {formatarData(aula.data_aula)} · Aula {aula.numero_aula}
                    <SeloAta temAta={Boolean(aula.conteudo_ministrado)} />
                  </p>
                  <p className="truncate text-sm text-slate-300">
                    {aula.disciplina_nome} — {aula.turma_nome}
                    {aula.polo_nome ? ` · ${aula.polo_nome}` : ''}
                  </p>
                  {aula.conteudo_ministrado && (
                    <p className="line-clamp-1 text-xs text-slate-500">{aula.conteudo_ministrado}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                    <FileText className="h-3.5 w-3.5" />
                    {aula.total_materiais} material(is)
                  </span>
                  <SeloPresenca presentes={aula.presentes} total={aula.total_chamada} />
                  <button
                    type="button"
                    onClick={() => {
                      setSucesso('');
                      setEditor({ aulaId: aula.id });
                    }}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Abrir
                  </button>
                  <button
                    type="button"
                    onClick={() => setExcluindo(aula)}
                    aria-label={`Excluir aula de ${formatarData(aula.data_aula)}`}
                    className="rounded-lg p-1.5 text-slate-500 hover:bg-red-500/10 hover:text-red-300"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {total > PAGE_SIZE && (
          <footer className="flex items-center justify-between border-t border-slate-800 p-4 text-xs text-slate-400">
            <span>
              {total} aula(s) · página {paginaAtual} de {paginas}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                aria-label="Página anterior"
                className="rounded-lg border border-slate-700 p-1.5 hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                aria-label="Próxima página"
                className="rounded-lg border border-slate-700 p-1.5 hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </footer>
        )}
      </section>

      {editor && (
        <AulaEditor
          aulaId={editor.aulaId}
          vinculos={vinculos}
          vinculoInicial={filtroVinculo}
          onClose={() => {
            setEditor(null);
            void carregar();
          }}
        />
      )}

      {excluindo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <section role="alertdialog" aria-modal="true" className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6">
            <h2 className="text-lg font-bold text-white">Excluir esta aula?</h2>
            <p className="mt-2 text-sm text-slate-400">
              A aula de {formatarData(excluindo.data_aula)} (nº {excluindo.numero_aula}) será removida com a ata, a
              chamada e os materiais anexados. Esta ação não pode ser desfeita.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setExcluindo(null)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void confirmarExclusao()}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500"
              >
                Excluir aula
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Editor da aula: Ata → Materiais → Chamada
// ---------------------------------------------------------------------------

interface AulaEditorProps {
  aulaId?: string;
  vinculos: PresencaVinculo[];
  vinculoInicial: string;
  onClose: () => void;
}

const AulaEditor: React.FC<AulaEditorProps> = ({ aulaId, vinculos, vinculoInicial, onClose }) => {
  const [aula, setAula] = useState<AulaDetalhe | null>(null);
  const [carregando, setCarregando] = useState(Boolean(aulaId));
  const [vinculoId, setVinculoId] = useState(vinculoInicial || vinculos[0]?.id || '');
  const [dataAula, setDataAula] = useState(dataLocalHoje);
  const [numeroAula, setNumeroAula] = useState(1);
  const [ata, setAta] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [salvandoAta, setSalvandoAta] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [novoMaterial, setNovoMaterial] = useState(false);
  // Aula nova: anexos e chamada ficam guardados aqui e vão junto no "Registrar aula".
  const [pendentes, setPendentes] = useState<MaterialPendente[]>([]);
  const [chamadaRascunho, setChamadaRascunho] = useState<AlunoChamada[]>([]);

  const aplicar = (detalhe: AulaDetalhe) => {
    setAula(detalhe);
    setVinculoId(detalhe.professor_disciplina_id);
    setDataAula(detalhe.data_aula.slice(0, 10));
    setNumeroAula(detalhe.numero_aula);
    setAta(detalhe.conteudo_ministrado || '');
    setObservacoes(detalhe.observacoes || '');
  };

  const recarregar = useCallback(async (id: string) => {
    try {
      aplicar(await aulasApi.obter(id));
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar a aula.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (aulaId) void recarregar(aulaId);
  }, [aulaId, recarregar]);

  const marcados = chamadaRascunho.filter((a) => typeof a.presente === 'boolean');
  const chamadaParcial = marcados.length > 0 && marcados.length < chamadaRascunho.length;

  const salvarAta = async (event: React.FormEvent) => {
    event.preventDefault();
    setErro('');
    setAviso('');
    const dados = {
      data_aula: dataAula,
      numero_aula: numeroAula,
      conteudo_ministrado: ata,
      observacoes,
    };

    if (aula) {
      setSalvandoAta(true);
      try {
        aplicar(await aulasApi.atualizar(aula.id, dados));
        setAviso('Ata atualizada.');
      } catch (error) {
        setErro(apiErrorMessage(error, 'Não foi possível salvar a aula.'));
      } finally {
        setSalvandoAta(false);
      }
      return;
    }

    // Aula nova: valida a chamada antes de criar qualquer coisa.
    if (chamadaParcial) {
      setErro('Marque todos os alunos na chamada, ou desmarque todos para fazer a chamada depois.');
      return;
    }

    setSalvandoAta(true);
    let criada: AulaDetalhe;
    try {
      criada = await aulasApi.registrar({ ...dados, professor_disciplina_id: vinculoId });
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível registrar a aula.'));
      setSalvandoAta(false);
      return;
    }

    // A aula existe: envia os anexos guardados e a chamada. Falhas não desfazem a aula.
    const falhas: string[] = [];
    for (const pendente of pendentes) {
      pendente.form.set('professor_disciplina_id', criada.professor_disciplina_id);
      pendente.form.set('aula_id', criada.id);
      try {
        await professoresApi.criarMaterial(pendente.form);
      } catch (error) {
        falhas.push(`"${pendente.descricao}": ${apiErrorMessage(error, 'falha no envio')}`);
      }
    }
    if (marcados.length > 0) {
      try {
        await presencasApi.salvarChamada({
          professor_disciplina_id: criada.professor_disciplina_id,
          data_aula: criada.data_aula.slice(0, 10),
          numero_aula: criada.numero_aula,
          presencas: marcados.map((a) => ({ aluno_id: a.aluno_id, presente: Boolean(a.presente) })),
        });
      } catch (error) {
        falhas.push(`chamada: ${apiErrorMessage(error, 'falha ao salvar')}`);
      }
    }

    setPendentes([]);
    setChamadaRascunho([]);
    await recarregar(criada.id);
    setSalvandoAta(false);
    if (falhas.length) {
      setErro(`Aula registrada, mas alguns itens não foram salvos. Refaça-os abaixo: ${falhas.join('; ')}.`);
    } else {
      setAviso('Aula registrada com a ata, os anexos e a chamada.');
    }
  };

  const removerMaterial = async (materialId: string) => {
    if (!aula) return;
    try {
      await aulasApi.excluirMaterial(aula.id, materialId);
      await recarregar(aula.id);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível remover o material.'));
    }
  };

  const vinculoAtual = vinculos.find((v) => v.id === vinculoId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="aula-editor-titulo"
        className="my-auto max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
      >
        <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-800 bg-slate-900 p-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-300">
              {aula ? 'Aula registrada' : 'Nova aula'}
            </p>
            <h2 id="aula-editor-titulo" className="mt-1 text-lg font-bold text-white">
              {aula
                ? `${aula.disciplina_nome} — ${aula.turma_nome} · ${formatarData(aula.data_aula)}`
                : 'Registrar aula'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {carregando ? (
          <div className="py-16 text-center">
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-emerald-400" />
          </div>
        ) : (
          <div className="space-y-6 p-5">
            {erro && (
              <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                {erro}
              </p>
            )}
            {aviso && (
              <p role="status" className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
                {aviso}
              </p>
            )}

            {/* 1. Ata */}
            <form id="aula-form" onSubmit={(e) => void salvarAta(e)} className="space-y-4">
              <h3 className="flex items-center gap-2 font-semibold text-white">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15 text-xs text-emerald-300">1</span>
                Ata da aula
              </h3>
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px_110px]">
                <label className="space-y-1.5 text-sm text-slate-300">
                  <span>Disciplina e turma</span>
                  <select
                    value={vinculoId}
                    onChange={(e) => setVinculoId(e.target.value)}
                    disabled={Boolean(aula)}
                    required
                    className={campo}
                  >
                    {vinculos.map((v) => (
                      <option key={v.id} value={v.id}>
                        {nomeVinculo(v)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1.5 text-sm text-slate-300">
                  <span>Data</span>
                  <input type="date" value={dataAula} onChange={(e) => setDataAula(e.target.value)} required className={campo} />
                </label>
                <label className="space-y-1.5 text-sm text-slate-300">
                  <span>Nº da aula</span>
                  <input
                    type="number"
                    min={1}
                    value={numeroAula}
                    onChange={(e) => setNumeroAula(Math.max(1, Number(e.target.value) || 1))}
                    required
                    className={campo}
                  />
                </label>
              </div>
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Conteúdo ministrado</span>
                <textarea
                  value={ata}
                  onChange={(e) => setAta(e.target.value)}
                  rows={4}
                  placeholder="O que foi trabalhado nesta aula"
                  className={campo}
                />
              </label>
              <label className="block space-y-1.5 text-sm text-slate-300">
                <span>Observações (opcional)</span>
                <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)} rows={2} className={campo} />
              </label>
              {aula && (
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={salvandoAta}
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                  >
                    {salvandoAta ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Salvar ata
                  </button>
                </div>
              )}
            </form>

            {/* 2. Materiais */}
            <section className="space-y-3 border-t border-slate-800 pt-5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 font-semibold text-white">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15 text-xs text-emerald-300">2</span>
                  Material da aula
                </h3>
                <button
                  type="button"
                  onClick={() => setNovoMaterial(true)}
                  disabled={!vinculoId}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-slate-800 disabled:cursor-not-allowed"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Anexar link ou arquivo
                </button>
              </div>
              {!aula ? (
                pendentes.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhum material anexado.</p>
                ) : (
                  <ul className="space-y-2">
                    {pendentes.map((pendente) => (
                      <li
                        key={pendente.chave}
                        className="flex items-center justify-between gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-3"
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <FileText className="h-4 w-4 shrink-0 text-emerald-300" />
                          <div className="min-w-0">
                            <p className="truncate text-sm text-slate-200">{pendente.descricao}</p>
                            <p className="truncate text-xs text-slate-500">
                              {pendente.detalhe} · será enviado ao registrar
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setPendentes((atuais) => atuais.filter((p) => p.chave !== pendente.chave))}
                          aria-label={`Remover ${pendente.descricao}`}
                          className="shrink-0 text-slate-500 hover:text-red-300"
                        >
                          <Trash2 size={15} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )
              ) : aula.materiais.length === 0 ? (
                <p className="text-sm text-slate-500">Nenhum material anexado.</p>
              ) : (
                <ul className="space-y-2">
                  {aula.materiais.map((material) => (
                    <MaterialItem
                      key={material.id}
                      material={material}
                      onErro={setErro}
                      acoes={
                        <button
                          type="button"
                          onClick={() => void removerMaterial(material.id)}
                          aria-label={`Remover ${material.descricao || 'material'}`}
                          className="text-slate-500 hover:text-red-300"
                        >
                          <Trash2 size={15} />
                        </button>
                      }
                    />
                  ))}
                </ul>
              )}
            </section>

            {/* 3. Chamada */}
            <section className="space-y-3 border-t border-slate-800 pt-5">
              <h3 className="flex items-center gap-2 font-semibold text-white">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15 text-xs text-emerald-300">3</span>
                Chamada
              </h3>
              {aula ? (
                <ChamadaEditor
                  key={`${aula.id}:${aula.data_aula}:${aula.numero_aula}`}
                  vinculoId={aula.professor_disciplina_id}
                  dataAula={aula.data_aula.slice(0, 10)}
                  numeroAula={aula.numero_aula}
                  onSalva={() => void recarregar(aula.id)}
                  onErro={setErro}
                />
              ) : vinculoId && dataAula ? (
                <ChamadaEditor
                  key={`rascunho:${vinculoId}:${dataAula}:${numeroAula}`}
                  vinculoId={vinculoId}
                  dataAula={dataAula}
                  numeroAula={numeroAula}
                  onSalva={() => undefined}
                  onErro={setErro}
                  onRascunho={setChamadaRascunho}
                />
              ) : (
                <p className="text-sm text-slate-500">Escolha a turma e a data para fazer a chamada.</p>
              )}
            </section>

            {!aula && (
              <footer className="flex flex-col gap-2 border-t border-slate-800 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-400">
                  {pendentes.length} anexo(s) ·{' '}
                  {chamadaParcial
                    ? `chamada incompleta (${marcados.length}/${chamadaRascunho.length})`
                    : marcados.length
                      ? 'chamada completa'
                      : 'chamada pode ser feita depois'}
                  {vinculoAtual ? ` · ${vinculoAtual.turma_nome}` : ''}
                </p>
                <button
                  type="submit"
                  form="aula-form"
                  disabled={salvandoAta || !vinculoId}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                >
                  {salvandoAta ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {salvandoAta ? 'Registrando...' : 'Registrar aula'}
                </button>
              </footer>
            )}
          </div>
        )}
      </section>

      {novoMaterial && aula && (
        <ConteudoMaterialForm
          context={{ kind: 'material', vinculoId: aula.professor_disciplina_id, aulaId: aula.id }}
          onCancel={() => setNovoMaterial(false)}
          onSaved={async () => {
            setNovoMaterial(false);
            await recarregar(aula.id);
          }}
        />
      )}
      {novoMaterial && !aula && (
        <ConteudoMaterialForm
          context={{ kind: 'material', vinculoId }}
          onCancel={() => setNovoMaterial(false)}
          onSaved={async () => setNovoMaterial(false)}
          aoConfirmar={(form) => {
            setPendentes((atuais) => [...atuais, materialPendente(form)]);
            setNovoMaterial(false);
          }}
        />
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Chamada (reutiliza /presencas: lista os alunos ativos e grava a chamada completa)
// ---------------------------------------------------------------------------

const ChamadaEditor: React.FC<{
  vinculoId: string;
  dataAula: string;
  numeroAula: number;
  onSalva: () => void;
  onErro: (mensagem: string) => void;
  /** Aula ainda não registrada: só informa as marcações; quem salva é o "Registrar aula". */
  onRascunho?: (alunos: AlunoChamada[]) => void;
}> = ({ vinculoId, dataAula, numeroAula, onSalva, onErro, onRascunho }) => {
  const [alunos, setAlunos] = useState<AlunoChamada[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [salva, setSalva] = useState(false);
  const requisicao = useRef(0);

  useEffect(() => {
    const atual = ++requisicao.current;
    setCarregando(true);
    presencasApi
      .listarAlunos(vinculoId, dataAula, numeroAula)
      .then((lista) => {
        if (atual === requisicao.current) setAlunos(lista);
      })
      .catch((error: unknown) => onErro(apiErrorMessage(error, 'Não foi possível carregar os alunos.')))
      .finally(() => {
        if (atual === requisicao.current) setCarregando(false);
      });
  }, [dataAula, numeroAula, onErro, vinculoId]);

  useEffect(() => {
    onRascunho?.(alunos);
  }, [alunos, onRascunho]);

  const completa = useMemo(
    () => alunos.length > 0 && alunos.every((a) => typeof a.presente === 'boolean'),
    [alunos]
  );

  const marcar = (alunoId: string | null, presente: boolean | null) => {
    setSalva(false);
    setAlunos((atuais) =>
      atuais.map((a) => (alunoId === null || a.aluno_id === alunoId ? { ...a, presente } : a))
    );
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      await presencasApi.salvarChamada({
        professor_disciplina_id: vinculoId,
        data_aula: dataAula,
        numero_aula: numeroAula,
        presencas: alunos.map((a) => ({ aluno_id: a.aluno_id, presente: Boolean(a.presente) })),
      });
      setSalva(true);
      onSalva();
    } catch (error) {
      onErro(apiErrorMessage(error, 'Não foi possível salvar a chamada.'));
    } finally {
      setSalvando(false);
    }
  };

  if (carregando) {
    return (
      <p className="flex items-center gap-2 text-sm text-slate-400">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando alunos...
      </p>
    );
  }
  if (alunos.length === 0) {
    return <p className="text-sm text-slate-500">Nenhum aluno ativo matriculado nesta turma.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-sm text-slate-300">
          <Users className="h-4 w-4 text-blue-400" />
          {alunos.length} aluno(s)
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => marcar(null, true)}
            className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/10"
          >
            Todos presentes
          </button>
          <button
            type="button"
            onClick={() => marcar(null, false)}
            className="rounded-lg border border-amber-500/30 px-3 py-1.5 text-xs font-semibold text-amber-200 hover:bg-amber-500/10"
          >
            Todos ausentes
          </button>
          {onRascunho && (
            <button
              type="button"
              onClick={() => marcar(null, null)}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
            >
              Limpar marcações
            </button>
          )}
        </div>
      </div>
      <ul className="divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800">
        {alunos.map((aluno) => (
          <li key={aluno.aluno_id} className="flex items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">{aluno.nome}</p>
              <p className="text-xs text-slate-500">{aluno.numero_matricula || 'Sem matrícula'}</p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                aria-pressed={aluno.presente === true}
                onClick={() => marcar(aluno.aluno_id, true)}
                className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                  aluno.presente === true
                    ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200'
                    : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Check className="h-3.5 w-3.5" /> Presente
              </button>
              <button
                type="button"
                aria-pressed={aluno.presente === false}
                onClick={() => marcar(aluno.aluno_id, false)}
                className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                  aluno.presente === false
                    ? 'border-amber-500/50 bg-amber-500/15 text-amber-200'
                    : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <X className="h-3.5 w-3.5" /> Ausente
              </button>
            </div>
          </li>
        ))}
      </ul>
      {onRascunho ? (
        <p className="text-xs text-slate-400">A chamada é salva junto com o registro da aula.</p>
      ) : (
      <div className="flex items-center justify-end gap-3">
        {!completa && <p className="text-xs text-amber-200">Marque todos os alunos antes de salvar.</p>}
        {salva && <p className="text-xs text-emerald-300">Chamada salva.</p>}
        <button
          type="button"
          onClick={() => void salvar()}
          disabled={!completa || salvando}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Salvar chamada
        </button>
      </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Anexo guardado antes de a aula existir
// ---------------------------------------------------------------------------

interface MaterialPendente {
  chave: string;
  form: FormData;
  descricao: string;
  detalhe: string;
}

const materialPendente = (form: FormData): MaterialPendente => {
  const arquivo = form.get('arquivo');
  return {
    chave: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    form,
    descricao: String(form.get('descricao') || 'Material'),
    detalhe: arquivo instanceof File ? arquivo.name : String(form.get('url_arquivo') || 'Link'),
  };
};
