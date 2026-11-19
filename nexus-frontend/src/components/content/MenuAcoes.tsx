import React, { useEffect, useRef, useState } from 'react';
import { MoreVertical } from 'lucide-react';

export interface AcaoMenu {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  perigo?: boolean;
  disabled?: boolean;
}

/** Botão "⋯" que abre uma lista de ações secundárias (fecha ao clicar fora ou com Esc). */
export const MenuAcoes: React.FC<{ acoes: AcaoMenu[]; rotulo: string }> = ({ acoes, rotulo }) => {
  const [aberto, setAberto] = useState(false);
  const [pos, setPos] = useState({ top: 0, right: 0 });
  const ref = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);

  const alternar = () => {
    if (!aberto && botao.current) {
      // Posição fixa: não é cortado pela rolagem horizontal da tabela.
      const r = botao.current.getBoundingClientRect();
      const altura = acoes.length * 40 + 8;
      const top = r.bottom + altura + 8 > window.innerHeight ? r.top - altura - 4 : r.bottom + 4;
      setPos({ top, right: window.innerWidth - r.right });
    }
    setAberto((v) => !v);
  };

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setAberto(false);
    const fechar = () => setAberto(false);
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', esc);
    window.addEventListener('scroll', fechar, true);
    window.addEventListener('resize', fechar);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', esc);
      window.removeEventListener('scroll', fechar, true);
      window.removeEventListener('resize', fechar);
    };
  }, [aberto]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={rotulo}
        aria-haspopup="menu"
        aria-expanded={aberto}
        title="Mais ações"
        ref={botao}
        onClick={alternar}
        className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
      >
        <MoreVertical size={16} />
      </button>
      {aberto && (
        <div
          role="menu"
          style={{ top: pos.top, right: pos.right }}
          className="glass fixed z-50 min-w-[160px] overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-xl"
        >
          {acoes.map((acao) => (
            <button
              key={acao.label}
              type="button"
              role="menuitem"
              disabled={acao.disabled}
              onClick={() => {
                setAberto(false);
                acao.onClick();
              }}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm disabled:opacity-50 ${
                acao.perigo ? 'text-red-300 hover:bg-red-500/10' : 'text-slate-200 hover:bg-slate-800'
              }`}
            >
              {acao.icon}
              {acao.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
