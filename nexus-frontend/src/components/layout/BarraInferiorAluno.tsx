import React from 'react';
import { NavLink } from 'react-router-dom';
import { Award, BookOpen, Home, Laptop, Medal, Menu, MessageSquare, ShoppingBag, Trophy, type LucideIcon } from 'lucide-react';

interface Item { para: string; rotulo: string; icone: LucideIcon; exato?: boolean }

const EAD: Item[] = [
  { para: '/aluno/ava', rotulo: 'AVA', icone: Laptop, exato: true },
  { para: '/aluno/compras', rotulo: 'Disciplinas', icone: ShoppingBag },
  { para: '/aluno/ava/conquistas', rotulo: 'Conquistas', icone: Medal },
  { para: '/aluno/ava/ranking', rotulo: 'Ranking', icone: Trophy },
];

const PRESENCIAL: Item[] = [
  { para: '/aluno/dashboard', rotulo: 'Início', icone: Home },
  { para: '/aluno/disciplinas', rotulo: 'Disciplinas', icone: BookOpen },
  { para: '/aluno/historico', rotulo: 'Notas', icone: Award },
  { para: '/chat', rotulo: 'Chat', icone: MessageSquare },
];

/** Navegação inferior do aluno no celular (acesso rápido com o polegar). Some a partir de lg. */
export const BarraInferiorAluno: React.FC<{ ead: boolean; onAbrirMenu: () => void }> = ({ ead, onAbrirMenu }) => {
  const itens = ead ? EAD : PRESENCIAL;
  const classe = (ativo: boolean) =>
    `flex min-h-[52px] flex-1 flex-col items-center justify-center gap-0.5 rounded-xl text-[10px] font-semibold transition ${
      ativo ? 'text-nexus-yellow' : 'text-slate-400 active:text-white'}`;
  return (
    <nav aria-label="Navegação rápida"
      className="glass-panel fixed inset-x-0 bottom-0 z-40 border-t border-slate-800/80 px-2 pb-safe lg:hidden">
      <div className="mx-auto flex max-w-lg items-stretch gap-1 py-1">
        {itens.map((i) => (
          <NavLink key={i.para} to={i.para} end={i.exato} className={({ isActive }) => classe(isActive)}>
            {({ isActive }) => (
              <>
                <span className={`flex h-7 w-12 items-center justify-center rounded-full transition ${isActive ? 'bg-nexus-yellow/15' : ''}`}>
                  <i.icone size={19} strokeWidth={isActive ? 2.4 : 2} />
                </span>
                {i.rotulo}
              </>
            )}
          </NavLink>
        ))}
        <button type="button" onClick={onAbrirMenu} className={classe(false)} aria-label="Abrir menu">
          <span className="flex h-7 w-12 items-center justify-center"><Menu size={19} /></span>
          Menu
        </button>
      </div>
    </nav>
  );
};
