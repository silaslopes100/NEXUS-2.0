import React, { useEffect, useState } from 'react';
import { AlertTriangle, ClipboardCheck, Loader2 } from 'lucide-react';
import { cursosApi, Curso } from '@/features/cursos/api';
import { mensagemErro } from '@/features/comunicacao/api';
import { avaAdminApi, AvaliacaoOpcao } from '../../api';
import { campo, rotulo } from './estilos';

interface Props {
  /** Curso da disciplina em edição (vem pré-selecionado). */
  cursoInicial?: string | null;
  valor?: string | null;
  onChange: (avaliacaoId: string | null, opcao?: AvaliacaoOpcao) => void;
}

/** Dropdown Curso → avaliações das disciplinas do curso escolhido (vindas do CRUD de Disciplinas). */
export const SeletorAvaliacao: React.FC<Props> = ({ cursoInicial, valor, onChange }) => {
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [cursoId, setCursoId] = useState(cursoInicial || '');
  const [opcoes, setOpcoes] = useState<AvaliacaoOpcao[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    cursosApi
      .listar()
      .then((l) => setCursos([...l].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))))
      .catch((e) => setErro(mensagemErro(e)));
  }, []);

  useEffect(() => {
    if (!cursoId) {
      setOpcoes([]);
      return;
    }
    setCarregando(true);
    setErro(null);
    avaAdminApi
      .avaliacoesDoCurso(cursoId)
      .then(setOpcoes)
      .catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar as avaliações.')))
      .finally(() => setCarregando(false));
  }, [cursoId]);

  const selecionada = opcoes.find((o) => o.avaliacao_id === valor);

  return (
    <div className="space-y-4 rounded-2xl border border-blue-500/30 bg-blue-500/5 p-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-blue-200">
        <ClipboardCheck size={16} /> Avaliação da disciplina
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>
          <span className={rotulo}>Curso</span>
          <select value={cursoId} onChange={(e) => { setCursoId(e.target.value); onChange(null); }} className={campo}>
            <option value="">Selecione o curso…</option>
            {cursos.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
        </label>
        <label>
          <span className={rotulo}>Avaliação</span>
          <select value={valor || ''} disabled={!cursoId || carregando}
            onChange={(e) => onChange(e.target.value || null, opcoes.find((o) => o.avaliacao_id === e.target.value))}
            className={`${campo} disabled:opacity-50`}>
            <option value="">{carregando ? 'Carregando…' : opcoes.length ? 'Selecione a avaliação…' : 'Nenhuma avaliação neste curso'}</option>
            {opcoes.map((o) => (
              <option key={o.avaliacao_id} value={o.avaliacao_id}>
                {o.disciplina_nome} — {o.titulo}{o.ativo ? '' : ' (inativa)'}
              </option>
            ))}
          </select>
        </label>
      </div>
      {carregando && <Loader2 size={14} className="animate-spin text-blue-300" />}
      {erro && <p className="text-xs text-red-300">{erro}</p>}
      {selecionada && (
        <p className="text-xs text-slate-400">
          {selecionada.total_questoes} questão(ões). As regras (tempo, tentativas e nota mínima) são as do cadastro da avaliação.
        </p>
      )}
      {selecionada && !selecionada.ativo && (
        <p className="flex items-center gap-1.5 text-xs text-amber-300">
          <AlertTriangle size={13} /> Esta avaliação está inativa: ative-a no cadastro de Disciplinas para o aluno conseguir realizá-la.
        </p>
      )}
    </div>
  );
};
