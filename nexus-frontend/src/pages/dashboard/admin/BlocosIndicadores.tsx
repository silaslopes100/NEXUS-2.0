import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Award, ChevronRight, ClipboardList, KeyRound, TrendingUp, Wallet } from 'lucide-react';
import { GraficoBarrasMensal, LinhaMensal } from '@/components/charts/GraficoBarrasMensal';
import { VendasKpis, formatBRL } from '@/features/financeiro/types';
import { AtividadeDocente } from '@/features/aulas/api';
import { DashboardExecutivo } from '@/types/admin';
import { fmtInt, fmtPct } from './formato';

/** Abaixo disso o estoque de licenças entra em alerta de ruptura. */
export const COBERTURA_MINIMA_DIAS = 30;

const Mini: React.FC<{ rotulo: string; valor: string; detalhe?: string }> = ({ rotulo, valor, detalhe }) => (
  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{rotulo}</p>
    <p className="mt-1 text-lg font-black text-white">{valor}</p>
    {detalhe && <p className="text-[11px] text-slate-500">{detalhe}</p>}
  </div>
);

const Cabecalho: React.FC<{ icone: React.ElementType; titulo: string; to?: string; acao?: string }> = ({
  icone: Icone, titulo, to, acao,
}) => (
  <div className="mb-4 flex items-center justify-between gap-2">
    <h2 className="flex items-center gap-2 text-base font-bold text-white">
      <Icone className="h-5 w-5 text-nexus-yellow" /> {titulo}
    </h2>
    {to && (
      <Link to={to} className="inline-flex items-center gap-0.5 text-xs font-semibold text-nexus-yellow hover:underline">
        {acao || 'Abrir'} <ChevronRight className="h-3.5 w-3.5" />
      </Link>
    )}
  </div>
);

const Estado: React.FC<{ erro: boolean }> = ({ erro }) => (
  <p className="py-6 text-sm text-slate-500">{erro ? 'Dados indisponíveis no momento.' : 'Carregando...'}</p>
);

const cardCls = 'glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5';

export const BlocoCrescimento: React.FC<{ dados: DashboardExecutivo['crescimento'] | null; erro: boolean }> = ({ dados, erro }) => (
  <section className={cardCls}>
    <Cabecalho icone={TrendingUp} titulo="Crescimento da base" to="/admin/alunos" acao="Alunos" />
    {!dados ? <Estado erro={erro} /> : (
      <>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Mini rotulo="Alunos ativos" valor={fmtInt(dados.alunos_ativos)} detalhe="hoje" />
          <Mini rotulo="Novos alunos" valor={fmtInt(dados.novos_alunos)} detalhe={`anterior: ${fmtInt(dados.novos_alunos_anterior)}`} />
          <Mini rotulo="Matrículas EAD" valor={fmtInt(dados.novas_matriculas)} detalhe={`anterior: ${fmtInt(dados.novas_matriculas_anterior)}`} />
          <Mini rotulo="Desistências" valor={fmtInt(dados.desistencias)} detalhe={`anterior: ${fmtInt(dados.desistencias_anterior)}`} />
        </div>
        <GraficoBarrasMensal
          embutido
          className="mt-4"
          titulo="Últimos 12 meses"
          subtitulo="Novos alunos cadastrados no NEXUS 2.0 (sem a carga migrada), matrículas EAD e desistências"
          series={[
            { chave: 'novos_alunos', rotulo: 'Novos alunos' },
            { chave: 'desistencias', rotulo: 'Desistências' },
            { chave: 'matriculas', rotulo: 'Matrículas EAD' },
          ]}
          dados={dados.serie_12m as unknown as LinhaMensal[]}
          vazio="Ainda sem movimentação nos últimos 12 meses."
        />
      </>
    )}
  </section>
);

export const BlocoReceita: React.FC<{
  kpis: VendasKpis | null;
  serie: LinhaMensal[];
  erro: boolean;
}> = ({ kpis, serie, erro }) => (
  <section className={cardCls}>
    <Cabecalho icone={Wallet} titulo="Receita" to="/admin/vendas" acao="Vendas" />
    {!kpis ? <Estado erro={erro} /> : (
      <>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Mini rotulo="Recebido" valor={formatBRL(kpis.receita_paga)} detalhe={`${fmtInt(kpis.pedidos_pagos)} pedido(s) pago(s)`} />
          <Mini rotulo="A receber" valor={formatBRL(kpis.a_receber)} detalhe="aguardando pagamento" />
          <Mini rotulo="Vencido" valor={formatBRL(kpis.vencido)} detalhe="de pedidos não pagos" />
          <Mini rotulo="Ticket médio" valor={formatBRL(kpis.ticket_medio)} detalhe={`${fmtInt(kpis.licencas_vendidas)} licença(s) vendida(s)`} />
        </div>
        <GraficoBarrasMensal
          embutido
          className="mt-4"
          titulo="Receita paga · últimos 12 meses"
          subtitulo="Pelo mês de criação do pedido (mesmo critério da tela de Vendas)"
          series={[{ chave: 'receita', rotulo: 'Receita' }]}
          dados={serie}
          formatar={formatBRL}
          detalhe={(l) => (l.pedidos ? `${l.pedidos_pagos} pago(s) de ${l.pedidos} pedido(s)` : null)}
          vazio="Sem pedidos nos últimos 12 meses."
        />
      </>
    )}
  </section>
);

export const BlocoLicencas: React.FC<{ dados: DashboardExecutivo['licencas'] | null; erro: boolean }> = ({ dados, erro }) => {
  const alerta = dados?.cobertura_dias !== null && dados?.cobertura_dias !== undefined && dados.cobertura_dias < COBERTURA_MINIMA_DIAS;
  return (
    <section className={cardCls}>
      <Cabecalho icone={KeyRound} titulo="Licenças" to="/admin/licencas" acao="Gestão de licenças" />
      {!dados ? <Estado erro={erro} /> : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 [&>*:last-child:nth-child(odd)]:col-span-2 sm:[&>*:last-child:nth-child(odd)]:col-span-1">
            <Mini rotulo="Em estoque" valor={fmtInt(dados.estoque_disponivel)} detalhe="disponível hoje" />
            <Mini rotulo="Consumidas" valor={fmtInt(dados.consumo_periodo)} detalhe={`anterior: ${fmtInt(dados.consumo_anterior)}`} />
            <Mini
              rotulo="Cobertura"
              valor={dados.cobertura_dias === null ? '—' : `${fmtInt(dados.cobertura_dias)} dias`}
              detalhe={dados.cobertura_dias === null ? 'sem consumo no período' : 'no ritmo atual'}
            />
          </div>
          {alerta ? (
            <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              Estoque dura menos de {COBERTURA_MINIMA_DIAS} dias no ritmo de consumo do período. Planeje a reposição.
            </p>
          ) : (
            <p className="mt-4 text-xs text-slate-500">
              Consumo = licenças entregues a alunos (vendas e reingressos). Cobertura = estoque ÷ consumo médio diário.
            </p>
          )}
        </>
      )}
    </section>
  );
};

export const BlocoAcademico: React.FC<{
  dados: DashboardExecutivo['academico'] | null;
  atividade: AtividadeDocente | null;
  erro: boolean;
}> = ({ dados, atividade, erro }) => (
  <section className={cardCls}>
    <Cabecalho icone={Award} titulo="Qualidade acadêmica" to="/admin/presencas" acao="Presenças" />
    {!dados ? <Estado erro={erro} /> : (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Mini
          rotulo="Presença média"
          valor={fmtPct(dados.presenca_media_pct)}
          detalhe={dados.presenca_media_anterior_pct === null ? 'sem base anterior' : `anterior: ${fmtPct(dados.presenca_media_anterior_pct)}`}
        />
        <Mini rotulo="Chamadas lançadas" valor={fmtInt(dados.registros_presenca)} detalhe="registros de presença" />
        <Mini rotulo="Certificados" valor={fmtInt(dados.certificados_periodo)} detalhe={`anterior: ${fmtInt(dados.certificados_anterior)}`} />
        <Mini
          rotulo="Aulas (30 dias)"
          valor={atividade ? fmtInt(atividade.aulas_registradas) : '—'}
          detalhe={atividade ? `${fmtInt(atividade.polos_com_aula)} polo(s) com aula` : undefined}
        />
      </div>
    )}
    <p className="mt-4 flex items-center gap-1.5 text-xs text-slate-500">
      <ClipboardList className="h-3.5 w-3.5" /> Detalhe da atividade docente logo abaixo.
    </p>
  </section>
);
