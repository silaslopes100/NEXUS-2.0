import React, { useEffect, useState } from 'react';
import { GraduationCap, Loader2, Search, UserCheck, UserPlus, X } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { UsuarioAdmin } from '@/types/admin';
import { Professor, UnidadeOption } from '@/types/professor';

interface Props {
  polos: UnidadeOption[];
  professor: Professor | null;
  onClose: () => void;
  onSuccess: (mensagem: string) => void;
}

const inputCls =
  'w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow';

interface UsuarioVinculado {
  id: string;
  nome: string;
  email?: string | null;
}

const parseMaterias = (texto: string): string[] =>
  texto
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

export const ProfessorModal: React.FC<Props> = ({ polos, professor, onClose, onSuccess }) => {
  const [erro, setErro] = useState('');
  const [isSaving, setIsSaving] = useState(false);

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

  const [form, setForm] = useState({
    polo_id: professor?.polo_id || '',
    escola_id: professor?.escola_id || '',
    materiasTexto: (professor?.materias || []).join(', '),
    data_inicio: professor?.data_inicio ? professor.data_inicio.slice(0, 10) : '',
    quantidade_aulas: professor?.quantidade_aulas ?? 0,
    horas_totais: professor?.horas_totais ?? 0,
    valor_hora_aula: professor?.valor_hora_aula ?? '',
    pix: professor?.pix || '',
    conteudo_programatico: professor?.conteudo_programatico || '',
    status: professor?.status || 'ativo',
  });
  const [escolas, setEscolas] = useState<UnidadeOption[]>([]);

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

    let usuarioId = usuarioSelecionado?.id;
    if (!usuarioId && vinculo === 'novo') {
      if (!novoUsuario.nome.trim() || !novoUsuario.email.trim()) {
        setErro('Informe nome e e-mail do novo usuário docente.');
        return;
      }
      if (novoUsuario.senha.length < 6) {
        setErro('A senha inicial deve possuir no mínimo 6 caracteres.');
        return;
      }
    }
    if (!usuarioId) {
      setErro('Selecione um usuário existente ou cadastre um novo usuário docente.');
      return;
    }

    setIsSaving(true);
    try {
      if (!usuarioSelecionado && vinculo === 'novo') {
        const usuario = await adminApi.createUsuario({
          nome: novoUsuario.nome.trim(),
          email: novoUsuario.email.trim(),
          senha: novoUsuario.senha,
          perfil_nome: 'professor',
          status: 'ativo',
        });
        usuarioId = usuario.id;
      }

      const payload = {
        usuario_id: usuarioId as string,
        polo_id: form.polo_id || null,
        escola_id: form.escola_id || null,
        materias: parseMaterias(form.materiasTexto),
        data_inicio: form.data_inicio || null,
        quantidade_aulas: Number(form.quantidade_aulas) || 0,
        horas_totais: Number(form.horas_totais) || 0,
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

          {/* Polo e Escola */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Polo</label>
              <select
                value={form.polo_id}
                onChange={(e) => setForm({ ...form, polo_id: e.target.value, escola_id: '' })}
                className={inputCls}
              >
                <option value="">Sem polo vinculado</option>
                {polos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Escola</label>
              <select
                value={form.escola_id}
                onChange={(e) => setForm({ ...form, escola_id: e.target.value })}
                disabled={!form.polo_id}
                className={`${inputCls} disabled:opacity-50`}
              >
                <option value="">
                  {form.polo_id ? 'Selecione a escola' : 'Selecione um polo primeiro'}
                </option>
                {escolas.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Disciplinas */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Disciplinas</label>
            <input
              type="text"
              value={form.materiasTexto}
              onChange={(e) => setForm({ ...form, materiasTexto: e.target.value })}
              placeholder="Ex: Matemática, Física, Cálculo"
              className={inputCls}
            />
            <p className="text-[11px] text-slate-500">Separe as disciplinas por vírgula.</p>
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
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Quantidade de aulas</label>
              <input
                type="number"
                min={0}
                value={form.quantidade_aulas}
                onChange={(e) => setForm({ ...form, quantidade_aulas: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Horas totais</label>
              <input
                type="number"
                min={0}
                value={form.horas_totais}
                onChange={(e) => setForm({ ...form, horas_totais: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
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
              disabled={isSaving}
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
