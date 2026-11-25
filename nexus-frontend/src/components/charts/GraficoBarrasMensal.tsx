import React, { useState } from 'react';
import { BarChart3, Table2 } from 'lucide-react';

/**
 * Barras mensais (uma ou mais séries agrupadas, mesmo eixo/unidade), com tooltip
 * por mês, legenda quando há mais de uma série e alternativa em tabela.
 * Cores: variáveis --serie-N (index.css), sempre na ordem fixa das séries.
 */

export interface SerieGrafico {
  chave: string;
  rotulo: string;
}

export type LinhaMensal = { mes: string } & Record<string, number | string>;

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
export const rotuloMes = (mes: string) => {
  const [ano, m] = mes.split('-');
  return `${MESES[Number(m) - 1]}/${ano.slice(2)}`;
};

const corSerie = (i: number) => `var(--serie-${i + 1})`;
const formatoInteiro = (v: number) => new Intl.NumberFormat('pt-BR').format(v);

interface Props {
  titulo: string;
  subtitulo?: string;
  series: SerieGrafico[];
  dados: LinhaMensal[];
  formatar?: (valor: number) => string;
  /** Linhas extras no tooltip/tabela (ex.: "3 pago(s) de 5 pedido(s)"). */
  detalhe?: (linha: LinhaMensal) => string | null;
  vazio?: string;
  /** Sem moldura própria, para uso dentro de outro cartão. */
  embutido?: boolean;
  className?: string;
}

export const GraficoBarrasMensal: React.FC<Props> = ({
  titulo, subtitulo, series, dados, formatar = formatoInteiro, detalhe, vazio = 'Sem dados no período.',
  embutido = false, className = '',
}) => {
  const [hover, setHover] = useState<number | null>(null);
  const [tabela, setTabela] = useState(false);
  const valor = (linha: LinhaMensal, chave: string) => Number(linha[chave] || 0);

  const largura = 720;
  const altura = 220;
  const margem = { top: 16, right: 8, bottom: 28, left: 8 };
  const max = Math.max(1, ...dados.flatMap((l) => series.map((s) => valor(l, s.chave))));
  const passo = (largura - margem.left - margem.right) / Math.max(dados.length, 1);
  const gap = 2; // respiro entre barras do mesmo mês
  const grupo = Math.min(passo - 8, series.length * 36);
  const barra = Math.max(4, (grupo - gap * (series.length - 1)) / series.length);
  const plotH = altura - margem.top - margem.bottom;
  const base = margem.top + plotH;
  const linhasGrade = [0.25, 0.5, 0.75, 1].map((f) => margem.top + plotH * (1 - f));
  const semDados = !dados.length || dados.every((l) => series.every((s) => valor(l, s.chave) === 0));

  return (
    <section className={`${embutido ? '' : 'glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4'} ${className}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-bold text-white">{titulo}</h2>
          {subtitulo && <p className="text-xs text-slate-500">{subtitulo}</p>}
        </div>
        <button
          type="button"
          onClick={() => setTabela(!tabela)}
          className="inline-flex shrink-0 items-center gap-1 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
        >
          {tabela ? <BarChart3 size={14} /> : <Table2 size={14} />} {tabela ? 'Ver gráfico' : 'Ver tabela'}
        </button>
      </div>

      {series.length > 1 && !tabela && (
        <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
          {series.map((s, i) => (
            <li key={s.chave} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: corSerie(i) }} />
              {s.rotulo}
            </li>
          ))}
        </ul>
      )}

      {semDados ? (
        <p className="py-12 text-center text-sm text-slate-500">{vazio}</p>
      ) : tabela ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-2">Mês</th>
                {series.map((s) => <th key={s.chave} className="p-2 text-right">{s.rotulo}</th>)}
                {detalhe && <th className="p-2 text-right">Detalhe</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {dados.map((l) => (
                <tr key={l.mes}>
                  <td className="p-2">{rotuloMes(l.mes)}</td>
                  {series.map((s) => <td key={s.chave} className="p-2 text-right text-white">{formatar(valor(l, s.chave))}</td>)}
                  {detalhe && <td className="p-2 text-right text-xs text-slate-400">{detalhe(l) || '—'}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative">
          <svg viewBox={`0 0 ${largura} ${altura}`} className="h-56 w-full" role="img" aria-label={titulo}>
            {linhasGrade.map((y) => (
              <line key={y} x1={margem.left} x2={largura - margem.right} y1={y} y2={y} stroke="currentColor" className="text-slate-800" strokeWidth={1} />
            ))}
            <line x1={margem.left} x2={largura - margem.right} y1={base} y2={base} stroke="currentColor" className="text-slate-700" strokeWidth={1} />
            {dados.map((l, i) => {
              const cx = margem.left + passo * i + passo / 2;
              const inicioGrupo = cx - (barra * series.length + gap * (series.length - 1)) / 2;
              const mostrarRotulo = dados.length <= 12 || i % Math.ceil(dados.length / 12) === 0;
              return (
                <g key={l.mes} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
                  <rect x={cx - passo / 2} y={margem.top} width={passo} height={plotH} fill="transparent" />
                  {series.map((s, j) => {
                    const h = (valor(l, s.chave) / max) * plotH;
                    if (h <= 0) return null;
                    const x = inicioGrupo + j * (barra + gap);
                    const y = base - h;
                    const r = Math.min(4, barra / 2, h);
                    // Topo arredondado (4px), base reta no eixo.
                    const d = `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + barra - r} Q${x + barra},${y} ${x + barra},${y + r} V${base} Z`;
                    return <path key={s.chave} d={d} style={{ fill: corSerie(j), opacity: hover === null || hover === i ? 1 : 0.55 }} />;
                  })}
                  {mostrarRotulo && <text x={cx} y={altura - 8} textAnchor="middle" className="fill-slate-500 text-[11px]">{rotuloMes(l.mes)}</text>}
                </g>
              );
            })}
          </svg>
          {hover !== null && dados[hover] && (
            <div
              className="pointer-events-none absolute top-0 z-10 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs shadow-xl"
              style={{ left: `${Math.min(75, Math.max(0, ((hover + 0.5) / dados.length) * 100 - 10))}%` }}
            >
              <p className="font-semibold text-white">{rotuloMes(dados[hover].mes)}</p>
              {series.map((s, j) => (
                <p key={s.chave} className="flex items-center gap-1.5 text-slate-300">
                  {series.length > 1 && <span className="h-2 w-2 rounded-sm" style={{ background: corSerie(j) }} />}
                  {s.rotulo}: <span className="text-white">{formatar(valor(dados[hover], s.chave))}</span>
                </p>
              ))}
              {detalhe && detalhe(dados[hover]) && <p className="text-slate-400">{detalhe(dados[hover])}</p>}
            </div>
          )}
        </div>
      )}
    </section>
  );
};
