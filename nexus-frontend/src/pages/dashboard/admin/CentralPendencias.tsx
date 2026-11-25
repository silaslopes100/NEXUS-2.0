import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeftRight, CalendarClock, CheckCircle2, ChevronRight, FileCheck2, Inbox, Receipt, Truck } from 'lucide-react';
import { formatBRL } from '@/features/financeiro/types';
import { DashboardExecutivo } from '@/types/admin';
import { fmtInt } from './formato';

interface Item {
  rotulo: string;
  valor: number;
  extra?: string;
  icone: React.ElementType;
  to?: string;
  dica: string;
}

/** Fila de trabalho atual do admin: cada card leva à tela onde a pendência é resolvida. */
export const CentralPendencias: React.FC<{ pendencias: DashboardExecutivo['pendencias'] | null; erro: boolean }> = ({
  pendencias, erro,
}) => {
  const itens: Item[] = pendencias
    ? [
      {
        rotulo: 'Cobranças vencidas', valor: pendencias.cobrancas_vencidas_qtd,
        extra: pendencias.cobrancas_vencidas_qtd ? formatBRL(pendencias.cobrancas_vencidas_valor) : undefined,
        icone: Receipt, to: '/admin/financeiro?status=vencido', dica: 'Emitir 2ª via ou negociar',
      },
      {
        rotulo: 'Pedidos aguardando envio', valor: pendencias.pedidos_aguardando_envio,
        icone: Truck, to: '/admin/logistica/pendentes', dica: 'Pagos, falta despachar',
      },
      {
        rotulo: 'Transferências pendentes', valor: pendencias.transferencias_pendentes,
        icone: ArrowLeftRight, to: '/admin/transferencias', dica: 'Aguardando análise',
      },
      {
        rotulo: 'Turmas atrasadas', valor: pendencias.turmas_atrasadas ?? 0,
        icone: CalendarClock, to: '/admin/turmas-calendarios', dica: 'Aula prevista sem ata ou reposição',
      },
      {
        rotulo: 'Estágios em análise', valor: pendencias.estagios_em_analise,
        icone: FileCheck2, to: '/admin/estagios', dica: 'Comprovantes para avaliar',
      },
      {
        rotulo: 'Solicitações de escolas', valor: pendencias.solicitacoes_unidade_pendentes,
        icone: Inbox, dica: 'Aguardando resposta do Polo',
      },
    ]
    : [];
  const total = itens.reduce((s, i) => s + (i.to ? i.valor : 0), 0);

  return (
    <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-bold text-white">
          <AlertTriangle className="h-5 w-5 text-amber-400" /> Central de pendências
        </h2>
        <span className="text-xs text-slate-500">
          {pendencias ? (total ? `${fmtInt(total)} item(ns) para o admin resolver` : 'Tudo em dia') : ''} · situação atual, independe do período
        </span>
      </div>
      {erro ? (
        <p className="text-sm text-slate-500">Dados indisponíveis no momento.</p>
      ) : !pendencias ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {itens.map((i) => {
            const Icone = i.icone;
            const ativo = i.valor > 0;
            const conteudo = (
              <>
                <div className="flex items-center justify-between">
                  <Icone className={`h-4 w-4 ${ativo ? 'text-amber-400' : 'text-slate-500'}`} />
                  {i.to && <ChevronRight className="h-4 w-4 text-slate-600" />}
                </div>
                <p className="mt-3 flex items-baseline gap-2">
                  <span className="text-2xl font-black text-white">{fmtInt(i.valor)}</span>
                  {i.extra && <span className="text-xs font-semibold text-slate-300">{i.extra}</span>}
                </p>
                <p className="mt-1 text-xs font-semibold text-slate-300">{i.rotulo}</p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-slate-500">
                  {!ativo && <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden />}
                  {ativo ? i.dica : 'Em dia'}
                </p>
              </>
            );
            const cls = `block rounded-xl border p-4 transition-colors ${ativo ? 'border-amber-500/30 bg-amber-500/5' : 'border-slate-800 bg-slate-950/40'}`;
            return i.to ? (
              <Link key={i.rotulo} to={i.to} className={`${cls} hover:border-nexus-yellow/50`}>{conteudo}</Link>
            ) : (
              <div key={i.rotulo} className={cls} title="Resolvidas pelo coordenador do Polo">{conteudo}</div>
            );
          })}
        </div>
      )}
    </section>
  );
};
