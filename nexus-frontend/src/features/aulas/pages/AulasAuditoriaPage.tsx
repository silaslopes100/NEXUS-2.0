import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  Building2,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Search,
  ShieldCheck,
  UserRound,
  X,
} from 'lucide-react';
import { apiErrorMessage } from '@/features/professores/api';
import { formatarData } from '@/features/turmas/api';
import { AulaDetalhe, AulaResumo, aulasApi, FiltrosAuditoria } from '@/features/aulas/api';
import { ChamadaResumo, MaterialItem, SeloAta, SeloPresenca } from '@/features/aulas/components/AulaComponentes';

const PAGE_SIZE = 25;
const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-nexus-yellow';

/** Chaves da URL: ?disciplina=&polo=&professor=&de=&ate=&q=&pagina= */
type ChaveFiltro = 'disciplina' | 'polo' | 'professor' | 'de' | 'ate' | 'q';

export const AulasAuditoriaPage: React.FC = () => {
  const { disciplinaId: disciplinaDaRota } = useParams<{ disciplinaId?: string }>();
  const [params, setParams] = useSearchParams();
  const disciplinaId = disciplinaDaRota || params.get('disciplina') || '';
  const pagina = Math.max(1, Number(params.get('pagina')) || 1);

  const [opcoes, setOpcoes] = useState<FiltrosAuditoria>({ disciplinas: [], polos: [], professores: [] });
  const [aulas, setAulas] = useState<AulaResumo[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [busca, setBusca] = useState(params.get('q') || '');
  const [aberta, setAberta] = useState<string | null>(null);

  const definir = (chave: ChaveFiltro, valor: string) => {
    const proximo = new URLSearchParams(params);
    if (valor) proximo.set(chave, valor);
    else proximo.delete(chave);
    proximo.delete('pagina');
    setParams(proximo, { replace: true });
  };

  const irParaPagina = (nova: number) => {
    const proximo = new URLSearchParams(params);
    if (nova > 1) proximo.set('pagina', String(nova));
    else proximo.delete('pagina');
    setParams(proximo, { replace: true });
  };

  useEffect(() => {
    aulasApi
      .filtros(disciplinaId || undefined)
      .then(setOpcoes)
      .catch(() => setOpcoes({ disciplinas: [], polos: [], professores: [] }));
  }, [disciplinaId]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const resposta = await aulasApi.auditoria({
        disciplina_id: disciplinaId,
        polo_id: params.get('polo') || '',
        professor_id: params.get('professor') || '',
        data_inicio: params.get('de') || '',
        data_fim: params.get('ate') || '',
        q: params.get('q') || '',
        limit: PAGE_SIZE,
        offset: (pagina - 1) * PAGE_SIZE,
      });
      setAulas(resposta.items);
      setTotal(resposta.total);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar as aulas.'));
    } finally {
      setCarregando(false);
    }
  }, [disciplinaId, pagina, params]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  // Agrupa a página atual por polo (a pergunta da diretoria: "o que cada polo está dando?").
  const grupos = useMemo(() => {
    const mapa = new Map<string, { nome: string; aulas: AulaResumo[] }>();
    for (const aula of aulas) {
      const chave = aula.polo_id || 'sem-polo';
      const grupo = mapa.get(chave) || { nome: aula.polo_nome || 'Sem polo informado', aulas: [] };
      grupo.aulas.push(aula);
      mapa.set(chave, grupo);
    }
    return Array.from(mapa.entries());
  }, [aulas]);

  const nomeDisciplina = opcoes.disciplinas.find((d) => d.id === disciplinaId)?.nome || aulas[0]?.disciplina_nome;
  const temFiltro =
    ['polo', 'professor', 'de', 'ate', 'q'].some((k) => params.get(k)) || Boolean(!disciplinaDaRota && disciplinaId);
  const paginas = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="max-w-7xl space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 p-6 shadow-xl sm:p-8">
        {disciplinaDaRota && (
          <Link to="/admin/disciplinas" className="mb-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
            <ArrowLeft className="h-3.5 w-3.5" /> Disciplinas
          </Link>
        )}
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-nexus-yellow/30 bg-nexus-yellow/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
          <ShieldCheck className="h-3.5 w-3.5" />
          Auditoria de aulas
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          {disciplinaDaRota ? nomeDisciplina || 'Aulas da disciplina' : 'Aulas de todos os polos'}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          Ata, material e presença de cada aula registrada pelos professores. Filtre por polo, professor, período ou
          busque no texto da ata e no nome do material.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-md">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[repeat(3,minmax(0,1fr))_150px_150px]">
          {!disciplinaDaRota && (
            <select aria-label="Disciplina" value={disciplinaId} onChange={(e) => definir('disciplina', e.target.value)} className={campo}>
              <option value="">Todas as disciplinas</option>
              {opcoes.disciplinas.map((o) => (
                <option key={o.id} value={o.id}>{o.nome}</option>
              ))}
            </select>
          )}
          <select aria-label="Polo" value={params.get('polo') || ''} onChange={(e) => definir('polo', e.target.value)} className={campo}>
            <option value="">Todos os polos</option>
            {params.get('polo') && !opcoes.polos.some((o) => o.id === params.get('polo')) && (
              <option value={params.get('polo') || ''}>Polo selecionado (sem aulas registradas)</option>
            )}
            {opcoes.polos.map((o) => (
              <option key={o.id} value={o.id}>{o.nome}</option>
            ))}
          </select>
          <select
            aria-label="Professor"
            value={params.get('professor') || ''}
            onChange={(e) => definir('professor', e.target.value)}
            className={campo}
          >
            <option value="">Todos os professores</option>
            {opcoes.professores.map((o) => (
              <option key={o.id} value={o.id}>{o.nome}</option>
            ))}
          </select>
          <input type="date" aria-label="De" value={params.get('de') || ''} onChange={(e) => definir('de', e.target.value)} className={campo} />
          <input type="date" aria-label="Até" value={params.get('ate') || ''} onChange={(e) => definir('ate', e.target.value)} className={campo} />
        </div>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && definir('q', busca.trim())}
              placeholder="Buscar na ata, observações, material, professor ou polo"
              className={`${campo} pl-9`}
            />
          </div>
          <button
            type="button"
            onClick={() => definir('q', busca.trim())}
            className="rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-nexus-yellow-hover"
          >
            Buscar
          </button>
          {temFiltro && (
            <button
              type="button"
              onClick={() => {
                setBusca('');
                setParams(new URLSearchParams(), { replace: true });
              }}
              className="inline-flex items-center justify-center gap-1 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
            >
              <X className="h-4 w-4" /> Limpar filtros
            </button>
          )}
        </div>
      </section>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
          {erro}
        </div>
      )}

      {carregando ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 py-16 text-center text-sm text-slate-400">
          <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin text-nexus-yellow" />
          Carregando aulas...
        </div>
      ) : aulas.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
          <BookOpen className="mx-auto mb-3 h-8 w-8 text-slate-500" />
          <h2 className="font-semibold text-white">Nenhuma aula encontrada</h2>
          <p className="mt-1 text-sm text-slate-400">
            {temFiltro ? 'Ajuste ou limpe os filtros.' : 'Os professores ainda não registraram aulas aqui.'}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          <p className="text-sm text-slate-400">{total} aula(s) encontrada(s)</p>
          {grupos.map(([poloId, grupo]) => (
            <section key={poloId} className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 shadow-md">
              <h2 className="flex items-center gap-2 border-b border-slate-800 px-5 py-3 font-bold text-white">
                <Building2 className="h-4 w-4 text-nexus-yellow" />
                {grupo.nome}
                <span className="text-xs font-normal text-slate-500">· {grupo.aulas.length} nesta página</span>
              </h2>
              <ul className="divide-y divide-slate-800">
                {grupo.aulas.map((aula) => (
                  <AulaLinha
                    key={aula.id}
                    aula={aula}
                    mostrarDisciplina={!disciplinaId}
                    aberta={aberta === aula.id}
                    onAlternar={() => setAberta(aberta === aula.id ? null : aula.id)}
                  />
                ))}
              </ul>
            </section>
          ))}

          {paginas > 1 && (
            <footer className="flex items-center justify-between text-xs text-slate-400">
              <span>Página {pagina} de {paginas}</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={pagina <= 1}
                  onClick={() => irParaPagina(pagina - 1)}
                  aria-label="Página anterior"
                  className="rounded-lg border border-slate-700 p-1.5 hover:bg-slate-800 disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  disabled={pagina >= paginas}
                  onClick={() => irParaPagina(pagina + 1)}
                  aria-label="Próxima página"
                  className="rounded-lg border border-slate-700 p-1.5 hover:bg-slate-800 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </footer>
          )}
        </div>
      )}
    </div>
  );
};

const AulaLinha: React.FC<{
  aula: AulaResumo;
  mostrarDisciplina: boolean;
  aberta: boolean;
  onAlternar: () => void;
}> = ({ aula, mostrarDisciplina, aberta, onAlternar }) => {
  const [detalhe, setDetalhe] = useState<AulaDetalhe | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!aberta || detalhe) return;
    aulasApi
      .auditoriaDetalhe(aula.id)
      .then(setDetalhe)
      .catch((error: unknown) => setErro(apiErrorMessage(error, 'Não foi possível abrir a aula.')));
  }, [aberta, aula.id, detalhe]);

  return (
    <li>
      <button
        type="button"
        onClick={onAlternar}
        aria-expanded={aberta}
        className="flex w-full flex-col gap-2 p-4 text-left hover:bg-slate-800/40 lg:flex-row lg:items-center lg:justify-between"
      >
        <div className="min-w-0 space-y-1">
          <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-white">
            <CalendarDays className="h-4 w-4 text-nexus-yellow" />
            {formatarData(aula.data_aula)} · Aula {aula.numero_aula}
            <SeloAta temAta={Boolean(aula.conteudo_ministrado)} />
          </p>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
            {mostrarDisciplina && <span className="font-semibold text-slate-200">{aula.disciplina_nome}</span>}
            <span className="inline-flex items-center gap-1">
              <UserRound className="h-3.5 w-3.5" /> {aula.professor_nome || 'Professor'}
            </span>
            <span>{aula.turma_nome}{aula.escola_nome ? ` · ${aula.escola_nome}` : ''}</span>
          </p>
          {!aberta && aula.conteudo_ministrado && (
            <p className="line-clamp-1 text-xs text-slate-500">{aula.conteudo_ministrado}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <span className="inline-flex items-center gap-1 text-xs text-slate-400">
            <FileText className="h-3.5 w-3.5" /> {aula.total_materiais}
          </span>
          <SeloPresenca presentes={aula.presentes} total={aula.total_chamada} />
          <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${aberta ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {aberta && (
        <div className="grid gap-5 border-t border-slate-800 bg-slate-950/40 p-5 lg:grid-cols-3">
          {erro && <p role="alert" className="text-sm text-red-300 lg:col-span-3">{erro}</p>}
          {!detalhe && !erro ? (
            <Loader2 className="h-5 w-5 animate-spin text-nexus-yellow lg:col-span-3" />
          ) : detalhe ? (
            <>
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Ata</h3>
                <p className="whitespace-pre-wrap text-sm text-slate-200">
                  {detalhe.conteudo_ministrado || <span className="text-slate-500">Ata não preenchida.</span>}
                </p>
                {detalhe.observacoes && (
                  <p className="whitespace-pre-wrap text-xs text-slate-400">Obs.: {detalhe.observacoes}</p>
                )}
              </div>
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Material</h3>
                {detalhe.materiais.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhum material anexado.</p>
                ) : (
                  <ul className="space-y-2">
                    {detalhe.materiais.map((m) => (
                      <MaterialItem key={m.id} material={m} onErro={setErro} />
                    ))}
                  </ul>
                )}
              </div>
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Presença · {detalhe.presentes}/{detalhe.total_chamada}
                </h3>
                <ChamadaResumo chamada={detalhe.chamada} />
              </div>
            </>
          ) : null}
        </div>
      )}
    </li>
  );
};
