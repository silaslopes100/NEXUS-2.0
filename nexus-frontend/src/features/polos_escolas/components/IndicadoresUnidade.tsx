import React from 'react';
import {
  ArrowLeftRight,
  BadgeCheck,
  BookOpen,
  CalendarDays,
  Library,
  Package,
  School,
  ShoppingCart,
  UserCheck,
  Users,
} from 'lucide-react';
import { IndicadorCard, IndicadorGrupo } from '@/features/polos_escolas/components/IndicadorCard';
import {
  AreaIndicadores,
  rotasIndicadoresEscola,
  rotasIndicadoresPolo,
} from '@/features/polos_escolas/indicadores';
import { ResumoOperacionalEscola, ResumoOperacionalPolo } from '@/types/polos';

const ICONE = 18;

/** Indicadores operacionais do Polo, agrupados e clicáveis. */
export const IndicadoresPolo: React.FC<{ resumo: ResumoOperacionalPolo; poloId: string; area: AreaIndicadores }> = ({
  resumo,
  poloId,
  area,
}) => {
  const rotas = rotasIndicadoresPolo(area, poloId);
  return (
    <div className="space-y-5">
      <IndicadorGrupo titulo="Estrutura acadêmica">
        <IndicadorCard label="Escolas" value={resumo.escolas} icon={<School size={ICONE} />} to={rotas.escolas} />
        <IndicadorCard label="Turmas" value={resumo.turmas} icon={<CalendarDays size={ICONE} />} to={rotas.turmas} />
        <IndicadorCard label="Professores" value={resumo.professores} icon={<UserCheck size={ICONE} />} to={rotas.professores} />
        <IndicadorCard label="Alunos" value={resumo.alunos} icon={<Users size={ICONE} />} accent="emerald" to={rotas.alunos} />
        <IndicadorCard label="Aulas" value={resumo.aulas} icon={<BookOpen size={ICONE} />} to={rotas.aulas} />
      </IndicadorGrupo>
      <div className="grid gap-5 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <IndicadorGrupo titulo="Licenças" colunas="grid-cols-2 sm:grid-cols-3">
            <IndicadorCard label="Em estoque" value={resumo.licencas_estoque} icon={<Package size={ICONE} />} accent="indigo" to={rotas.licencas_estoque} />
            <IndicadorCard label="Atribuídas" value={resumo.licencas_atribuidas} icon={<BadgeCheck size={ICONE} />} accent="indigo" to={rotas.licencas_atribuidas} />
            <IndicadorCard label="Movimentações" value={resumo.licencas_movimentacoes} icon={<ArrowLeftRight size={ICONE} />} accent="indigo" to={rotas.licencas_movimentacoes} />
          </IndicadorGrupo>
        </div>
        <div className="lg:col-span-2">
          <IndicadorGrupo titulo="Pedidos" colunas="grid-cols-2">
            <IndicadorCard label="De licenças" value={resumo.pedidos_licencas} icon={<ShoppingCart size={ICONE} />} accent="amber" to={rotas.pedidos_licencas} />
            <IndicadorCard label="De livros" value={resumo.pedidos_livros} icon={<Library size={ICONE} />} accent="amber" to={rotas.pedidos_livros} />
          </IndicadorGrupo>
        </div>
      </div>
    </div>
  );
};

/** Indicadores operacionais da Escola, agrupados e clicáveis. */
export const IndicadoresEscola: React.FC<{
  resumo: ResumoOperacionalEscola;
  escola: { id: string; polo_id: string | null };
  area: AreaIndicadores;
}> = ({ resumo, escola, area }) => {
  const rotas = rotasIndicadoresEscola(area, escola);
  const colunas = 'grid-cols-2 sm:grid-cols-4';
  return (
    <div className="space-y-5">
      <IndicadorGrupo titulo="Acadêmico" colunas={colunas}>
        <IndicadorCard label="Alunos" value={resumo.alunos} icon={<Users size={ICONE} />} accent="emerald" to={rotas.alunos} />
        <IndicadorCard label="Turmas" value={resumo.turmas} icon={<CalendarDays size={ICONE} />} to={rotas.turmas} />
        <IndicadorCard label="Professores" value={resumo.professores} icon={<UserCheck size={ICONE} />} to={rotas.professores} />
        <IndicadorCard
          label="Aulas"
          value={resumo.aulas}
          icon={<BookOpen size={ICONE} />}
          to={rotas.aulas}
          hint={rotas.aulas ? 'Abre as aulas do polo (a auditoria não filtra por escola)' : undefined}
        />
      </IndicadorGrupo>
      <IndicadorGrupo titulo="Licenças" colunas={colunas}>
        <IndicadorCard label="Em estoque" value={resumo.licencas_estoque} icon={<Package size={ICONE} />} accent="indigo" to={rotas.licencas_estoque} />
        <IndicadorCard label="De alunos" value={resumo.licencas_alunos} icon={<Users size={ICONE} />} accent="indigo" to={rotas.licencas_alunos} />
        <IndicadorCard label="Atribuídas" value={resumo.licencas_atribuidas} icon={<BadgeCheck size={ICONE} />} accent="indigo" to={rotas.licencas_atribuidas} />
        <IndicadorCard label="Movimentações" value={resumo.licencas_movimentacoes} icon={<ArrowLeftRight size={ICONE} />} accent="indigo" to={rotas.licencas_movimentacoes} />
      </IndicadorGrupo>
      <IndicadorGrupo titulo="Pedidos" colunas={colunas}>
        <IndicadorCard label="De licenças" value={resumo.pedidos_licencas} icon={<ShoppingCart size={ICONE} />} accent="amber" to={rotas.pedidos_licencas} />
        <IndicadorCard label="De livros" value={resumo.pedidos_livros} icon={<Library size={ICONE} />} accent="amber" to={rotas.pedidos_livros} />
      </IndicadorGrupo>
    </div>
  );
};
