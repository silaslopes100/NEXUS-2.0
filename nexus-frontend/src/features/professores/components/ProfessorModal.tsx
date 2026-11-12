import React, { useEffect, useMemo, useState } from 'react';
import { GraduationCap, Loader2, MapPin, Plus, Search, Trash2, UserCheck, UserPlus, X } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { cursosApi, Curso, Disciplina } from '@/features/cursos/api';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { UsuarioAdmin } from '@/types/admin';
import { Lotacao, Professor, UnidadeOption, rotuloLotacao } from '@/types/professor';

interface Props {
  polos: UnidadeOption[];
  professor: Professor | null;
  onClose: () => void;
  onSuccess: (mensagem: string) => void;
}

const inputCls =
  'w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow';

const normalizarMateria = (nome: string): string => nome.trim().toLocaleLowerCase();

/** Lotação ainda não salva (sem id) ou já existente. */
type LotacaoRascunho = Omit<Lotacao, 'id'> & { chave: string };

const chaveLotacao = (poloId: string, escolaId?: string | null) => `${poloId}:${escolaId || ''}`;

const lotacoesIniciais = (professor: Professor | null): LotacaoRascunho[] => {
  if (professor?.lotacoes?.length) {
    return professor.lotacoes.map((l) => ({ ...l, chave: chaveLotacao(l.polo_id, l.escola_id) }));
  }
  if (professor?.polo_id) {
    return [{
      chave: chaveLotacao(professor.polo_id, professor.escola_id),
      polo_id: professor.polo_id,
      polo_nome: professor.polo_nome,
      escola_id: professor.escola_id,
      escola_nome: professor.escola_nome,
    }];
  }
  return [];
};

interface UsuarioVinculado {
  id: string;
  nome: string;
  email?: string | null;
}

export const ProfessorModal: React.FC<Props> = ({ polos, professor, onClose, onSuccess }) => {
  const [erro, setErro] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [carregandoDisciplinas, setCarregandoDisciplinas] = useState(true);
  const [erroDisciplinas, setErroDisciplinas] = useState('');
  const [buscaDisciplina, setBuscaDisciplina] = useState('');
  const [tentativaDisciplinas, setTentativaDisciplinas] = useState(0);

  // Vínculo com o usuário (busca de existente ou cadastro manual)
  const [vinculo, setVinculo] = useState<'existente' | 'novo'>('existente');
  const [buscaUsuario, setBuscaUsuario] = useState('');
  const [usuariosEncontrados, setUsuariosEncontrados] = useState<UsuarioAdmin[]>([]);
  const [buscandoUsuario, setBuscandoUsuario] = useState(false);
  const [usuarioSelecionado, setUsuarioSelecionado] = useState<UsuarioVinculado | null>(
    professor?.usuario_id
      ? { id: professor.usuario_id, nome: professor.nome || '', email: professor.email }
      : null
  );
  const [novoUsuario, setNovoUsuario] = useState({ nome: '', email: '', senha: '' });

  const [lotacoes, setLotacoes] = useState<LotacaoRascunho[]>(() => lotacoesIniciais(professor));
  const [form, setForm] = useState({
    // Linha "adicionar lotação" (polo + escola opcional)
    polo_id: '',
    escola_id: '',
    disciplina_ids: [...(professor?.disciplina_ids || [])],
    materias: (professor?.materias || []).reduce<string[]>((materias, materia) => {
      const nome = materia.trim();
      if (nome && !materias.some((item) => normalizarMateria(item) === normalizarMateria(nome))) {
        materias.push(nome);
      }
      return materias;
    }, []),
    data_inicio: professor?.data_inicio ? professor.data_inicio.slice(0, 10) : '',
    valor_hora_aula: professor?.valor_hora_aula ?? '',
    pix: professor?.pix || '',
    conteudo_programatico: professor?.conteudo_programatico || '',
    status: professor?.status || 'ativo',
  });
  const [escolas, setEscolas] = useState<UnidadeOption[]>([]);

  useEffect(() => {
    let active = true;
    setCarregandoDisciplinas(true);
    setErroDisciplinas('');
    Promise.all([cursosApi.listarDisciplinas(), cursosApi.listar()])
      .then(([itens, cursosDisponiveis]) => {
        if (active) {
          setDisciplinas(itens);
          setCursos(cursosDisponiveis);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setErroDisciplinas(apiErrorMessage(err, 'Não foi possível carregar as disciplinas cadastradas.'));
        }
      })
      .finally(() => {
        if (active) setCarregandoDisciplinas(false);
      });

    return () => {
      active = false;
    };
  }, [tentativaDisciplinas]);

  useEffect(() => {
    if (!form.polo_id) {
      setEscolas([]);
      return;
    }
    professoresApi
      .listarEscolasDoPolo(form.polo_id)
      .then((itens) => {
        setEscolas(itens);
        setForm((atual) =>
          atual.escola_id && !itens.some((e) => e.id === atual.escola_id)
            ? { ...atual, escola_id: '' }
            : atual
        );
      })
      .catch(() => setEscolas([]));
  }, [form.polo_id]);

  /** Lotação escolhida nos selects e ainda não adicionada à lista. */
  const lotacaoSelecionada = (): LotacaoRascunho | null => {
    if (!form.polo_id) return null;
    return {
      chave: chaveLotacao(form.polo_id, form.escola_id),
      polo_id: form.polo_id,
      polo_nome: polos.find((p) => p.id === form.polo_id)?.nome,
      escola_id: form.escola_id || null,
      escola_nome: escolas.find((e) => e.id === form.escola_id)?.nome ?? null,
    };
  };

  const incluirLotacao = (atuais: LotacaoRascunho[], nova: LotacaoRascunho | null) =>
    !nova || atuais.some((l) => l.chave === nova.chave) ? atuais : [...atuais, nova];

  const adicionarLotacao = () => {
    setLotacoes((atuais) => incluirLotacao(atuais, lotacaoSelecionada()));
    setForm((atual) => ({ ...atual, polo_id: '', escola_id: '' }));
  };

  const buscarUsuarios = async () => {
    const termo = buscaUsuario.trim();
    if (termo.length < 3) {
      setErro('Digite ao menos 3 caracteres para buscar um usuário.');
      return;
    }
    setErro('');
    setBuscandoUsuario(true);
    try {
      const resposta = await adminApi.listUsuarios({ q: termo, limit: 10 });
      setUsuariosEncontrados(resposta.items || []);
      if (!resposta.items?.length) {
        setErro('Nenhum usuário encontrado. Você pode cadastrá-lo na aba "Novo usuário".');
      }
    } catch (err) {
      setErro(apiErrorMessage(err, 'Erro ao buscar usuários.'));
    } finally {
      setBuscandoUsuario(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErro('');

    if (carregandoDisciplinas || erroDisciplinas) {
      setErro('Aguarde o carregamento das disciplinas antes de salvar.');
      return;
    }

    let usuarioId = usuarioSelecionado?.id;
    const criarNovoUsuario = !usuarioId && vinculo === 'novo';
    if (criarNovoUsuario) {
      if (!novoUsuario.nome.trim() || !novoUsuario.email.trim()) {
        setErro('Informe nome e e-mail do novo usuário docente.');
        return;
      }
      if (novoUsuario.senha.length < 6) {
        setErro('A senha inicial deve possuir no mínimo 6 caracteres.');
        return;
      }
    } else if (!usuarioId) {
      setErro('Selecione um usuário existente ou cadastre um novo usuário docente.');
      return;
    }

    setIsSaving(true);
    try {
      if (criarNovoUsuario) {
        const usuario = await adminApi.createUsuario({
          nome: novoUsuario.nome.trim(),
          email: novoUsuario.email.trim(),
          senha: novoUsuario.senha,
          perfil_nome: 'professor',
          status: 'ativo',
        });
        usuarioId = usuario.id;
      }

      // Se ficou um polo selecionado sem clicar em "Adicionar", ele também entra.
      const lotacoesFinais = incluirLotacao(lotacoes, lotacaoSelecionada());
      const payload = {
        usuario_id: usuarioId as string,
        lotacoes: lotacoesFinais.map((l) => ({ polo_id: l.polo_id, escola_id: l.escola_id || null })),
        materias: form.materias,
        disciplina_ids: form.disciplina_ids,
        data_inicio: form.data_inicio || null,
        valor_hora_aula: form.valor_hora_aula === '' ? null : Number(form.valor_hora_aula),
        pix: form.pix.trim() || null,
        conteudo_programatico: form.conteudo_programatico.trim() || null,
      };

      if (professor) {
        await professoresApi.atualizar(professor.id, { ...payload, status: form.status });
        onSuccess('Professor atualizado com sucesso!');
      } else {
        await professoresApi.criar(payload);
        onSuccess('Professor cadastrado com sucesso!');
      }
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível salvar o professor.'));
    } finally {
      setIsSaving(false);
    }
  };

  const opcoesDisciplinas = useMemo(() => {
    const opcoes: { id: string | null; nome: string; legado: boolean; curso: string }[] =
      disciplinas.filter((disciplina) => disciplina.nome.trim()).map((disciplina) => ({
        id: disciplina.id,
        nome: disciplina.nome.trim(),
        legado: false,
        curso: cursos.find((curso) => curso.id === disciplina.curso_id)?.nome || 'Sem curso',
      }));
    const nomes = new Set(opcoes.map((opcao) => normalizarMateria(opcao.nome)));
    for (const materia of form.materias) {
      const nome = materia.trim();
      const chave = normalizarMateria(nome);
      if (nome && !nomes.has(chave)) {
        opcoes.push({ id: null, nome, legado: true, curso: '' });
        nomes.add(chave);
      }
    }
    return opcoes
      .filter(({ nome }) => normalizarMateria(nome).includes(normalizarMateria(buscaDisciplina)))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR') || a.curso.localeCompare(b.curso, 'pt-BR'));
  }, [disciplinas, cursos, form.materias, buscaDisciplina]);

  const alternarDisciplina = (id: string | null, nome: string, selecionada: boolean) => {
    setForm((atual) => {
      const disciplinaIds = id
        ? selecionada
          ? [...new Set([...atual.disciplina_ids, id])]
          : atual.disciplina_ids.filter((disciplinaId) => disciplinaId !== id)
        : atual.disciplina_ids;
      const manterNome = selecionada || disciplinas.some(
        (disciplina) => disciplinaIds.includes(disciplina.id) && normalizarMateria(disciplina.nome) === normalizarMateria(nome)
      );
      return {
        ...atual,
        disciplina_ids: disciplinaIds,
        materias: [
          ...atual.materias.filter((materia) => normalizarMateria(materia) !== normalizarMateria(nome)),
          ...(manterNome ? [nome] : []),
        ],
      };
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 sm:p-8 animate-fadeIn my-auto">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-white font-bold text-lg">
            <GraduationCap className="w-5 h-5 text-nexus-yellow" />
            <span>{professor ? 'Editar Professor' : 'Novo Professor & Docente'}</span>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {erro && (
          <div className="mt-4 p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-xs text-red-300">
            {erro}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 mt-5">
          {/* Vínculo com usuário */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-nexus-yellow">
              Usuário docente *
            </label>

            {!professor && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setVinculo('existente')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                    vinculo === 'existente'
                      ? 'bg-nexus-yellow/10 border-nexus-yellow/40 text-nexus-yellow'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <UserCheck className="w-3.5 h-3.5" /> Usuário existente
                </button>
                <button
                  type="button"
                  onClick={() => setVinculo('novo')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                    vinculo === 'novo'
                      ? 'bg-nexus-yellow/10 border-nexus-yellow/40 text-nexus-yellow'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <UserPlus className="w-3.5 h-3.5" /> Novo usuário
                </button>
              </div>
            )}

            {usuarioSelecionado ? (
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-950 border border-emerald-500/30">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-white truncate">
                    {usuarioSelecionado.nome}
                  </p>
                  <p className="text-[11px] text-slate-400 truncate">
                    {usuarioSelecionado.email || 'Sem e-mail'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setUsuarioSelecionado(null);
                    setUsuariosEncontrados([]);
                    setBuscaUsuario('');
                  }}
                  className="text-[11px] text-slate-400 hover:text-nexus-yellow shrink-0"
                >
                  Trocar
                </button>
              </div>
            ) : vinculo === 'existente' ? (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={buscaUsuario}
                      onChange={(e) => setBuscaUsuario(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          void buscarUsuarios();
                        }
                      }}
                      placeholder="Buscar usuário por nome ou e-mail..."
                      className={`${inputCls} pl-8`}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => void buscarUsuarios()}
                    disabled={buscandoUsuario}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 shrink-0 disabled:opacity-60"
                  >
                    {buscandoUsuario ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                    Buscar
                  </button>
                </div>

                {usuariosEncontrados.length > 0 && (
                  <div className="max-h-40 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 divide-y divide-slate-800/60">
                    {usuariosEncontrados.map((u) => (
                      <button
                        key={u.id}
                        type="button"
                        onClick={() => {
                          setUsuarioSelecionado({ id: u.id, nome: u.nome, email: u.email });
                          setUsuariosEncontrados([]);
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-slate-900 transition-colors"
                      >
                        <p className="text-xs text-white font-medium">
                          {u.nome} {u.sobrenome || ''}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {u.email || 'Sem e-mail'} · {u.perfil_nome || 'sem perfil'}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                <input
                  type="text"
                  required
                  value={novoUsuario.nome}
                  onChange={(e) => setNovoUsuario({ ...novoUsuario, nome: e.target.value })}
                  placeholder="Nome completo *"
                  className={inputCls}
                />
                <input
                  type="email"
                  required
                  value={novoUsuario.email}
                  onChange={(e) => setNovoUsuario({ ...novoUsuario, email: e.target.value })}
                  placeholder="E-mail *"
                  className={inputCls}
                />
                <input
                  type="password"
                  required
                  value={novoUsuario.senha}
                  onChange={(e) => setNovoUsuario({ ...novoUsuario, senha: e.target.value })}
                  placeholder="Senha (mín. 6) *"
                  className={inputCls}
                />
              </div>
            )}
          </div>

          {/* Polos e escolas (N lotações) */}
          <div className="space-y-2">
            <div>
              <label className="text-xs font-semibold text-slate-300">Polos e escolas</label>
              <p className="text-[11px] text-slate-500">
                Onde o professor pode dar aula. Sem escola, ele atende todas as escolas do polo. Ao associá-lo a
                uma turma, o polo/escola dela é incluído automaticamente.
              </p>
            </div>

            {lotacoes.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-800 px-3 py-2 text-xs text-slate-500">
                Nenhum polo vinculado.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {lotacoes.map((lotacao) => (
                  <li
                    key={lotacao.chave}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-950 py-1 pl-3 pr-1.5 text-xs text-slate-200"
                  >
                    <MapPin size={12} className="text-nexus-yellow" />
                    {rotuloLotacao({ ...lotacao, id: lotacao.chave })}
                    {!lotacao.escola_id && <span className="text-slate-500">(todas as escolas)</span>}
                    <button
                      type="button"
                      onClick={() => setLotacoes((atuais) => atuais.filter((l) => l.chave !== lotacao.chave))}
                      aria-label={`Remover ${rotuloLotacao({ ...lotacao, id: lotacao.chave })}`}
                      className="rounded-full p-1 text-slate-500 hover:bg-slate-800 hover:text-red-300"
                    >
                      <Trash2 size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto]">
              <select
                value={form.polo_id}
                onChange={(e) => setForm({ ...form, polo_id: e.target.value, escola_id: '' })}
                className={inputCls}
                aria-label="Polo da lotação"
              >
                <option value="">Selecione o polo</option>
                {polos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}
                  </option>
                ))}
              </select>
              <select
                value={form.escola_id}
                onChange={(e) => setForm({ ...form, escola_id: e.target.value })}
                disabled={!form.polo_id}
                className={`${inputCls} disabled:opacity-50`}
                aria-label="Escola da lotação"
              >
                <option value="">
                  {form.polo_id ? 'Todas as escolas do polo' : 'Selecione um polo primeiro'}
                </option>
                {escolas.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={adicionarLotacao}
                disabled={!form.polo_id}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
              >
                <Plus size={14} />
                Adicionar
              </button>
            </div>
          </div>

          {/* Disciplinas */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Disciplinas</label>
            <input
              type="search"
              value={buscaDisciplina}
              onChange={(e) => setBuscaDisciplina(e.target.value)}
              placeholder="Buscar disciplina..."
              className={inputCls}
              disabled={carregandoDisciplinas || Boolean(erroDisciplinas)}
            />
            <div className="max-h-36 space-y-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-2">
              {carregandoDisciplinas ? (
                <p className="flex items-center gap-2 p-2 text-xs text-slate-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Carregando disciplinas...
                </p>
              ) : erroDisciplinas ? (
                <div className="flex items-center justify-between gap-2 p-2">
                  <p role="alert" className="text-xs text-red-300">{erroDisciplinas}</p>
                  <button
                    type="button"
                    onClick={() => setTentativaDisciplinas((tentativa) => tentativa + 1)}
                    className="shrink-0 text-xs font-semibold text-nexus-yellow hover:underline"
                  >
                    Tentar novamente
                  </button>
                </div>
              ) : opcoesDisciplinas.length ? (
                opcoesDisciplinas.map(({ id, nome, legado, curso }) => (
                  <label
                    key={id || nome.toLocaleLowerCase()}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
                  >
                    <input
                      type="checkbox"
                      checked={id ? form.disciplina_ids.includes(id) : form.materias.some(
                        (materia) => normalizarMateria(materia) === normalizarMateria(nome)
                      )}
                      onChange={(event) => alternarDisciplina(id, nome, event.target.checked)}
                      className="accent-yellow-400"
                    />
                    <span>{nome}</span>
                    <span className="text-[10px] text-slate-500">
                      {legado ? 'nome antigo, não conta no total' : curso}
                    </span>
                  </label>
                ))
              ) : (
                <p className="p-2 text-xs text-slate-400">
                  {buscaDisciplina
                    ? 'Nenhuma disciplina corresponde à busca.'
                    : 'Nenhuma disciplina cadastrada.'}
                </p>
              )}
            </div>
            <p className="text-[11px] text-slate-500">
              {form.disciplina_ids.length} disciplina{form.disciplina_ids.length === 1 ? '' : 's'} vinculada{form.disciplina_ids.length === 1 ? '' : 's'}.
            </p>
          </div>

          {/* Carga horária e contraprestação */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Data de início</label>
              <input
                type="date"
                value={form.data_inicio}
                onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
                className={inputCls}
              />
            </div>
            <p className="text-xs text-slate-400 sm:col-span-2 self-center">
              A carga horária e as aulas previstas são calculadas pelas disciplinas vinculadas.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Valor hora/aula (R$)</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.valor_hora_aula}
                onChange={(e) => setForm({ ...form, valor_hora_aula: e.target.value })}
                placeholder="Ex: 120,00"
                className={inputCls}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Chave PIX</label>
              <input
                type="text"
                value={form.pix}
                onChange={(e) => setForm({ ...form, pix: e.target.value })}
                placeholder="CPF, e-mail ou chave aleatória"
                className={inputCls}
              />
            </div>
          </div>

          {/* Conteúdo programático */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Conteúdo programático</label>
            <textarea
              rows={4}
              value={form.conteudo_programatico}
              onChange={(e) => setForm({ ...form, conteudo_programatico: e.target.value })}
              placeholder="Ementa, unidades, bibliografia..."
              className={`${inputCls} resize-y`}
            />
          </div>

          {professor && (
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className={inputCls}
              >
                <option value="ativo">Ativo</option>
                <option value="inativo">Inativo</option>
              </select>
            </div>
          )}

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSaving || carregandoDisciplinas || Boolean(erroDisciplinas)}
              className="px-5 py-2.5 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl shadow-lg transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{professor ? 'Salvar Alterações' : 'Cadastrar Professor'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
