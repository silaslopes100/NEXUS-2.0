/** Formatação compartilhada pelos blocos da Dashboard Executiva. */

export const fmtInt = (valor?: number | null) =>
  valor === undefined || valor === null ? '—' : new Intl.NumberFormat('pt-BR').format(valor);

export const fmtPct = (valor?: number | null, casas = 1) =>
  valor === undefined || valor === null
    ? '—'
    : `${new Intl.NumberFormat('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(valor)}%`;

/** "2026-11-05" ou ISO completo -> "05/11/2026". */
export const fmtData = (valor?: string | null) => {
  if (!valor) return '—';
  const d = new Date(valor.length === 10 ? `${valor}T00:00:00` : valor);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};

/** Variação percentual; null quando não há base de comparação. */
export const variacaoPct = (atual: number, anterior: number): number | null =>
  anterior ? Math.round(((atual - anterior) / anterior) * 1000) / 10 : null;

/** Data local AAAA-MM-DD (sem conversão para UTC). */
export const isoLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Lista "AAAA-MM" dos 12 meses que terminam no mês de `fim` (AAAA-MM-DD). */
export const ultimos12Meses = (fim: string): string[] => {
  let ano = Number(fim.slice(0, 4));
  let mes = Number(fim.slice(5, 7));
  const out: string[] = [];
  for (let i = 0; i < 12; i += 1) {
    out.unshift(`${ano}-${String(mes).padStart(2, '0')}`);
    mes -= 1;
    if (mes === 0) { mes = 12; ano -= 1; }
  }
  return out;
};
