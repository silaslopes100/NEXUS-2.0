import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, BookOpen, Layers, Laptop, Loader2, PlayCircle, Search } from 'lucide-react';
import { cursosApi, Curso } from '@/features/cursos/api';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { avaAdminApi, DisciplinaAva } from '../../api';

const CHAVE_CURSO = 'nexus:ava:curso';

const lerCursoSalvo = () => {
  try {
    return localStorage.getItem(CHAVE_CURSO) || '';
  } catch {
    return '';
  }
};

const salvarCurso = (id: string) => {
  try {
    localStorage.setItem(CHAVE_CURSO, id);
  } catch {
    /* armazenamento indisponível */
  }
};

/** Gestor de Conteúdo EAD: escolhe o curso e a disciplina para montar Capítulos e Aulas. */
export const AvaConteudoPage: React.FC = () => {
  const navigate = useNavigate();
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [cursoId, setCursoId] = useState(lerCursoSalvo);
  const [disciplinas, setDisciplinas] = useState<DisciplinaAva[]>([]);
  const [busca, setBusca] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    cursosApi
      .listar()
      .then((lista) => {
        const ordenados = [...lista].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
        setCursos(ordenados);
        setCursoId((atual) => (atual && ordenados.some((c) => c.id === atual) ? atual : ordenados[0]?.id ?? ''));
      })
      .catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar os cursos.')));
  }, []);

  const carregar = useCallback(async () => {
    if (!cursoId) return;
    setCarregando(true);
    setErro(null);
    try {
      setDisciplinas(await avaAdminApi.disciplinas(cursoId));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar as disciplinas.'));
    } finally {
      setCarregando(false);
    }
  }, [cursoId]);

  useEffect(() => {
    salvarCurso(cursoId);
    void carregar();
  }, [cursoId, carregar]);

  const filtradas = useMemo(() => {
    const t = busca.trim().toLowerCase();
    return t ? disciplinas.filter((d) => d.nome.toLowerCase().includes(t)) : disciplinas;
  }, [busca, disciplinas]);

  const resumo = useMemo(
    () => ({
      publicadas: disciplinas.filter((d) => d.publicado).length,
      aulas: disciplinas.reduce((s, d) => s + d.total_aulas, 0),
    }),
    [disciplinas],
  );

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl lg:flex-row lg:items-center">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow">
            <Laptop size={24} />
          </span>
          <div>
            <h1 className="text-3xl font-extrabold text-white">Conteúdo EAD</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              Monte a Sala de Aula Virtual de cada disciplina: capítulos, aulas, vídeos, materiais e avaliações. As
              disciplinas vêm do cadastro de Disciplinas.
            </p>
          </div>
        </div>
        <div className="flex gap-3 text-center">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2">
            <p className="text-xl font-bold text-white">{resumo.publicadas}/{disciplinas.length}</p>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">publicadas</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2">
            <p className="text-xl font-bold text-white">{resumo.aulas}</p>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">aulas</p>
          </div>
        </div>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="sm:w-80">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">Curso</span>
          <select value={cursoId} onChange={(e) => setCursoId(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-nexus-yellow focus:outline-none">
            {cursos.length === 0 && <option value="">Nenhum curso cadastrado</option>}
            {cursos.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
        </label>
        <label className="flex-1">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">Disciplina</span>
          <span className="relative block">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar disciplina…"
              className="w-full rounded-xl border border-slate-700 bg-slate-950 py-2 pl-8 pr-3 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
          </span>
        </label>
      </div>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {carregando ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : filtradas.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <BookOpen className="mx-auto mb-3 text-slate-600" size={32} />
          <p className="text-sm text-slate-300">
            {disciplinas.length ? 'Nenhuma disciplina encontrada na busca.' : 'Este curso ainda não tem disciplinas.'}
          </p>
          {!disciplinas.length && (
            <p className="mt-1 text-xs text-slate-500">Cadastre as disciplinas em Disciplinas e volte aqui para montar o conteúdo.</p>
          )}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtradas.map((d) => (
            <button key={d.id} type="button" onClick={() => navigate(`/admin/ava/disciplinas/${d.id}`)}
              className="group flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 text-left transition hover:-translate-y-0.5 hover:border-nexus-yellow/60 hover:shadow-nexus-glow">
              <div className="relative aspect-[16/7] w-full bg-gradient-to-br from-blue-900/60 via-slate-900 to-slate-950">
                {d.capa_url ? (
                  <img src={urlArquivo(d.capa_url)} alt="" className="h-full w-full object-cover" />
                ) : (
                  <span className="absolute inset-0 flex items-center justify-center text-4xl font-black text-white/10">
                    {d.nome.slice(0, 2).toUpperCase()}
                  </span>
                )}
                <span className={`absolute left-3 top-3 rounded-full px-2 py-0.5 text-[11px] font-bold ${
                  d.publicado ? 'bg-emerald-500/90 text-white' : 'bg-slate-800/90 text-slate-300'}`}>
                  {d.publicado ? 'Publicado' : 'Rascunho'}
                </span>
                {!d.ativo && (
                  <span className="absolute right-3 top-3 rounded-full bg-red-500/80 px-2 py-0.5 text-[11px] font-bold text-white">
                    Disciplina inativa
                  </span>
                )}
              </div>
              <div className="flex flex-1 flex-col gap-3 p-4">
                <div>
                  <p className="line-clamp-2 font-semibold text-white">{d.nome}</p>
                  {d.semestre ? <p className="text-xs text-slate-500">{d.semestre}º semestre</p> : null}
                </div>
                <div className="mt-auto flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-3">
                    <span className="flex items-center gap-1"><Layers size={13} /> {d.total_capitulos} capítulos</span>
                    <span className="flex items-center gap-1"><PlayCircle size={13} /> {d.total_aulas} aulas</span>
                  </span>
                  <span className="font-semibold text-nexus-yellow opacity-0 transition group-hover:opacity-100">
                    Montar conteúdo →
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
