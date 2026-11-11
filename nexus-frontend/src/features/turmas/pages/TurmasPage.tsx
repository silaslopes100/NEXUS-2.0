import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Edit2, GraduationCap, Loader2, Plus, Search, Trash2, Users } from 'lucide-react';
import { alunosApi, apiErrorMessage, EscolaOption } from '@/features/alunos/api';
import { Curso, cursosApi } from '@/features/cursos/api';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { formatarData, Turma, turmasApi } from '@/features/turmas/api';
import { CalendariosTab } from '@/features/turmas/components/CalendariosTab';
import { TurmaAlunosPanel } from '@/features/turmas/components/TurmaAlunosPanel';
import { TurmaProfessoresPanel } from '@/features/turmas/components/TurmaProfessoresPanel';
import { EscolaOpcao, inputCls, TurmaFormModal } from '@/features/turmas/components/TurmaFormModal';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const PAGE_SIZE = 10;
const BUSCA_DEBOUNCE_MS = 300;

type Aba = 'turmas' | 'calendarios';
type FormState = { aberto: false } | { aberto: true; turma: Turma | null };

export const TurmasPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome ?? user?.perfil?.nome);
  const isAdmin = role === 'admin';
  const isPolo = role === 'polo';
  const poloUsuario = user?.polo_id ?? '';

  const [aba, setAba] = useState<Aba>('turmas');
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [busca, setBusca] = useState('');
  const [termo, setTermo] = useState('');
  const [cursoFiltro, setCursoFiltro] = useState('');
  const [escolaFiltro, setEscolaFiltro] = useState('');
  const [versao, setVersao] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');

  const [cursos, setCursos] = useState<Curso[]>([]);
  const [polos, setPolos] = useState<EscolaOption[]>([]);
  const [escolas, setEscolas] = useState<EscolaOpcao[]>([]);

  const [form, setForm] = useState<FormState>({ aberto: false });
  const [turmaAlunos, setTurmaAlunos] = useState<Turma | null>(null);
  const [turmaProfessores, setTurmaProfessores] = useState<Turma | null>(null);
  const [confirmandoId, setConfirmandoId] = useState<string | null>(null);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setTermo(busca.trim());
      setOffset(0);
    }, BUSCA_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [busca]);

  useEffect(() => {
    cursosApi
      .listar()
      .then(setCursos)
      .catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar cursos.')));
  }, []);

  useEffect(() => {
    // Sem as listas, a tela segue funcionando: apenas os seletores de polo e escola ficam vazios.
    if (isAdmin) {
      alunosApi.listarPolos().then(setPolos).catch(() => setPolos([]));
      polosEscolasApi
        .listarEscolas({ limit: 200 })
        .then((data: { items?: EscolaOpcao[] }) => setEscolas(data.items ?? []))
        .catch(() => setEscolas([]));
    } else if (isPolo && poloUsuario) {
      alunosApi.listarEscolas(poloUsuario).then(setEscolas).catch(() => setEscolas([]));
    }
  }, [isAdmin, isPolo, poloUsuario]);

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    turmasApi
      .listarPaginado({
        q: termo || undefined,
        curso_id: cursoFiltro || undefined,
        escola_id: escolaFiltro || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      .then((pagina) => {
        if (!ativo) return;
        setTurmas(pagina.items);
        setTotal(pagina.total);
      })
      .catch((e) => ativo && setErro(apiErrorMessage(e, 'Erro ao carregar turmas.')))
      .finally(() => ativo && setLoading(false));
    return () => {
      ativo = false;
    };
  }, [termo, cursoFiltro, escolaFiltro, offset, versao]);

  const recarregar = () => setVersao((atual) => atual + 1);

  const excluir = async (turma: Turma) => {
    setExcluindoId(turma.id);
    setErro('');
    try {
      await turmasApi.excluir(turma.id);
      setConfirmandoId(null);
      // Ao excluir o último item da página, volta para a anterior.
      if (turmas.length === 1 && offset > 0) {
        setOffset(Math.max(0, offset - PAGE_SIZE));
      } else {
        recarregar();
      }
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível excluir a turma.'));
    } finally {
      setExcluindoId(null);
    }
  };

  const mostrarEscolaFiltro = (isAdmin || isPolo) && escolas.length > 0;
  const paginaAtual = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const abaCls = (ativa: boolean) =>
    `rounded-lg px-4 py-2 text-sm font-semibold ${
      ativa ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
    }`;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-white">{isAdmin ? 'Turmas & Calendários' : 'Turmas'}</h1>
        {aba === 'turmas' && (
          <button
            type="button"
            onClick={() => setForm({ aberto: true, turma: null })}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <Plus size={16} /> Cadastrar turma
          </button>
        )}
      </header>

      {isAdmin && (
        <div role="tablist" className="flex gap-2">
          <button type="button" role="tab" aria-selected={aba === 'turmas'} className={abaCls(aba === 'turmas')} onClick={() => setAba('turmas')}>
            Turmas
          </button>
          <button type="button" role="tab" aria-selected={aba === 'calendarios'} className={abaCls(aba === 'calendarios')} onClick={() => setAba('calendarios')}>
            Calendários
          </button>
        </div>
      )}

      {aba === 'calendarios' ? (
        <CalendariosTab cursos={cursos} />
      ) : (
        <>
          {erro && (
            <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {erro}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="relative block">
              <span className="sr-only">Buscar turma</span>
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                className={`${inputCls} pl-9`}
                placeholder="Buscar turma"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
              />
            </label>
            <select
              aria-label="Filtrar por curso"
              className={inputCls}
              value={cursoFiltro}
              onChange={(e) => {
                setCursoFiltro(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">Todos os cursos</option>
              {cursos.map((curso) => (
                <option key={curso.id} value={curso.id}>
                  {curso.nome}
                </option>
              ))}
            </select>
            {mostrarEscolaFiltro && (
              <select
                aria-label="Filtrar por escola"
                className={inputCls}
                value={escolaFiltro}
                onChange={(e) => {
                  setEscolaFiltro(e.target.value);
                  setOffset(0);
                }}
              >
                <option value="">Todas as escolas</option>
                {escolas.map((escola) => (
                  <option key={escola.id} value={escola.id}>
                    {escola.nome}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Turma</th>
                  <th className="p-4">Curso</th>
                  {(isAdmin || isPolo) && <th className="p-4">Escola</th>}
                  <th className="p-4">Início</th>
                  <th className="p-4">Fim</th>
                  <th className="p-4">Alunos</th>
                  <th className="p-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center">
                      <Loader2 className="mx-auto animate-spin" size={18} />
                    </td>
                  </tr>
                )}
                {!loading && turmas.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-slate-500">
                      Nenhuma turma encontrada.
                    </td>
                  </tr>
                )}
                {!loading &&
                  turmas.map((turma) => (
                    <tr key={turma.id} className="border-b border-slate-800/60 last:border-0">
                      <td className="p-4 font-semibold text-white">{turma.nome}</td>
                      <td className="p-4">{turma.curso_nome || '—'}</td>
                      {(isAdmin || isPolo) && <td className="p-4">{turma.escola_nome || '—'}</td>}
                      <td className="p-4">{formatarData(turma.data_inicio)}</td>
                      <td className="p-4">{formatarData(turma.data_fim)}</td>
                      <td className="p-4">{turma.total_alunos}</td>
                      <td className="p-4">
                        {confirmandoId === turma.id ? (
                          <span className="flex justify-end gap-2">
                            <button
                              type="button"
                              disabled={excluindoId !== null}
                              onClick={() => void excluir(turma)}
                              className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-60"
                            >
                              Confirmar
                            </button>
                            <button
                              type="button"
                              disabled={excluindoId !== null}
                              onClick={() => setConfirmandoId(null)}
                              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-60"
                            >
                              Cancelar
                            </button>
                          </span>
                        ) : (
                          <span className="flex justify-end gap-2">
                            <button
                              type="button"
                              aria-label={`Professores de ${turma.nome}`}
                              onClick={() => setTurmaProfessores(turma)}
                              title="Gerenciar professores"
                              className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
                            >
                              <GraduationCap size={14} />
                            </button>
                            <button
                              type="button"
                              aria-label={`Alunos de ${turma.nome}`}
                              onClick={() => setTurmaAlunos(turma)}
                              className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
                            >
                              <Users size={14} />
                            </button>
                            <button
                              type="button"
                              aria-label={`Editar ${turma.nome}`}
                              onClick={() => setForm({ aberto: true, turma })}
                              className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              type="button"
                              aria-label={`Excluir ${turma.nome}`}
                              onClick={() => setConfirmandoId(turma.id)}
                              className="rounded-lg border border-red-500/30 p-2 text-red-300 hover:bg-red-500/10"
                            >
                              <Trash2 size={14} />
                            </button>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <footer className="flex items-center justify-between text-sm text-slate-400">
            <span>
              {total} {total === 1 ? 'turma' : 'turmas'}
            </span>
            <span className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Página anterior"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronLeft size={16} />
              </button>
              Página {paginaAtual} de {totalPaginas}
              <button
                type="button"
                aria-label="Próxima página"
                disabled={paginaAtual >= totalPaginas}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronRight size={16} />
              </button>
            </span>
          </footer>
        </>
      )}

      {form.aberto && (
        <TurmaFormModal
          turma={form.turma}
          cursos={cursos}
          polos={polos}
          escolas={escolas}
          mostrarPolo={isAdmin}
          mostrarEscola={isAdmin || isPolo}
          onClose={() => setForm({ aberto: false })}
          onSaved={() => {
            setForm({ aberto: false });
            recarregar();
          }}
        />
      )}

      {turmaAlunos && (
        <TurmaAlunosPanel
          turma={turmaAlunos}
          onClose={(houveAlteracao) => {
            setTurmaAlunos(null);
            if (houveAlteracao) recarregar();
          }}
        />
      )}
      {turmaProfessores && (
        <TurmaProfessoresPanel
          turma={turmaProfessores}
          onClose={() => {
            setTurmaProfessores(null);
            recarregar();
          }}
        />
      )}
    </div>
  );
};
