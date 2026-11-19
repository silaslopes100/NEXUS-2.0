import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Award,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  Loader2,
  Lock,
  MessageSquareWarning,
  PlayCircle,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import { baixarArquivo, erroDeBlob } from '@/lib/download';
import { urlArquivo } from '@/lib/uploadDireto';
import {
  ArquivoBase,
  CentralAluno,
  EtapaAluno,
  STATUS_ESTAGIO,
  erroEstagio,
  estagiosApi,
  formatarDataHora,
  formatarTamanho,
} from '@/features/estagios/api';
import { ArquivosSubmissao, StatusEstagioBadge } from '@/features/estagios/components/EstagioComum';
import { FormularioEnvioEtapa } from '@/features/estagios/components/FormularioEnvioEtapa';

const ICONE_BASE: Record<string, { cor: string; formato: string }> = {
  manual: { cor: 'bg-red-500/15 text-red-300', formato: 'PDF' },
  carta_modelo: { cor: 'bg-blue-500/15 text-blue-300', formato: 'DOCX' },
  relatorio_modelo: { cor: 'bg-blue-500/15 text-blue-300', formato: 'DOCX' },
};

const CardDownload: React.FC<{ arquivo: ArquivoBase }> = ({ arquivo }) => {
  const visual = ICONE_BASE[arquivo.chave];
  const extensao = arquivo.nome?.split('.').pop()?.toUpperCase() || visual.formato;
  return (
    <div className="glass flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${visual.cor}`}>
        <FileText size={22} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-white">{arquivo.titulo}</p>
        <p className="text-xs text-slate-500">
          {arquivo.disponivel ? `${extensao} · ${formatarTamanho(arquivo.tamanho)}` : 'Ainda não disponibilizado'}
        </p>
      </div>
      {arquivo.disponivel && arquivo.url ? (
        <a
          href={urlArquivo(arquivo.url)}
          target="_blank"
          rel="noreferrer"
          download={arquivo.nome || undefined}
          className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-on-accent hover:bg-blue-500"
        >
          <Download size={14} /> Baixar
        </a>
      ) : (
        <span className="rounded-xl border border-slate-800 px-3 py-2 text-xs text-slate-500">Indisponível</span>
      )}
    </div>
  );
};

/** Uma etapa do estágio: status, feedback, arquivos enviados, formulário e comprovante. */
const CartaoEtapa: React.FC<{ etapa: EtapaAluno; onAtualizar: () => void }> = ({ etapa, onAtualizar }) => {
  const s = etapa.submissao;
  const [refazendo, setRefazendo] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState('');
  const mostrarFormulario = etapa.pode_enviar && (!s || refazendo);

  const baixarComprovante = async () => {
    if (!s) return;
    setBaixando(true);
    setErro('');
    try {
      const { blob, nome } = await estagiosApi.comprovante(s.id);
      baixarArquivo(blob, nome);
    } catch (e) {
      setErro(await erroDeBlob(e, 'Não foi possível gerar o comprovante.'));
    } finally {
      setBaixando(false);
    }
  };

  const borda = etapa.bloqueada
    ? 'border-slate-800 opacity-70'
    : s?.status === 'aprovado'
      ? 'border-emerald-500/30'
      : s?.status === 'negado'
        ? 'border-red-500/30'
        : s?.status === 'em_analise'
          ? 'border-amber-500/30'
          : 'border-blue-500/30';

  return (
    <li className={`glass relative rounded-2xl border bg-slate-900/80 p-5 ${borda}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-black ${
            s?.status === 'aprovado' ? 'bg-emerald-500 text-on-accent' : etapa.bloqueada ? 'bg-slate-800 text-slate-500' : 'bg-blue-600 text-on-accent'
          }`}>
            {s?.status === 'aprovado' ? <CheckCircle2 size={20} /> : etapa.bloqueada ? <Lock size={16} /> : etapa.ordem}
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Etapa {etapa.ordem} · {etapa.descricao}</p>
            <h3 className="text-lg font-bold text-white">Estágio na disciplina {etapa.titulo}</h3>
            {s?.enviado_em && <p className="text-xs text-slate-500">Enviado em {formatarDataHora(s.enviado_em)}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-slate-700 px-2.5 py-0.5 text-[11px] text-slate-300">{etapa.horas}h</span>
          {s ? <StatusEstagioBadge status={s.status} /> : etapa.bloqueada ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-slate-700 px-2.5 py-0.5 text-[11px] text-slate-400"><Lock size={11} /> Bloqueada</span>
          ) : (
            <span className="rounded-full border border-blue-500/40 bg-blue-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-blue-300">Disponível</span>
          )}
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {etapa.bloqueada && (
          <p className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm text-slate-400">
            <Lock size={16} className="shrink-0" /> Liberada após a aprovação do estágio da Etapa 1 (Teologia do Ministério).
          </p>
        )}

        {s?.status === 'em_analise' && (
          <p className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
            <Clock3 size={16} className="shrink-0" /> Sua documentação está em análise pela Coordenação de Estágio.
          </p>
        )}

        {s?.status === 'negado' && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-red-200">
              <MessageSquareWarning size={16} /> Comentário do Coordenador
            </p>
            <p className="mt-1 whitespace-pre-line text-sm text-red-100">{s.comentario_feedback || '—'}</p>
            <p className="mt-2 text-xs text-red-300/80">
              Avaliado em {formatarDataHora(s.avaliado_em)}{s.avaliado_por_nome ? ` por ${s.avaliado_por_nome}` : ''}
            </p>
          </div>
        )}

        {s?.status === 'aprovado' && (
          <div className="flex flex-col gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-emerald-200"><Award size={16} /> Estágio aprovado</p>
              <p className="text-xs text-emerald-200/80">
                Aprovado em {formatarDataHora(s.avaliado_em)} · Código {s.codigo_comprovante}
              </p>
              {s.comentario_feedback && <p className="mt-1 text-sm text-emerald-100">“{s.comentario_feedback}”</p>}
            </div>
            <button
              type="button"
              onClick={() => void baixarComprovante()}
              disabled={baixando}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-emerald-500 disabled:opacity-50"
            >
              {baixando ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />} Baixar comprovante
            </button>
          </div>
        )}

        {erro && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-sm text-red-200">{erro}</p>}

        {s && !refazendo && s.arquivos.length > 0 && (
          <details className="group rounded-xl border border-slate-800 bg-slate-950/30" open={s.status !== 'aprovado'}>
            <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-300">
              Documentos enviados ({s.arquivos.length})
            </summary>
            <div className="border-t border-slate-800 p-4">
              <ArquivosSubmissao arquivos={s.arquivos} />
            </div>
          </details>
        )}

        {s?.status === 'negado' && !refazendo && (
          <button
            type="button"
            onClick={() => setRefazendo(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-red-500"
          >
            <RotateCcw size={16} /> Refazer envio
          </button>
        )}

        {mostrarFormulario && (
          <FormularioEnvioEtapa
            etapa={etapa.etapa}
            titulo={etapa.titulo}
            reenvio={!!s}
            onCancelar={s ? () => setRefazendo(false) : undefined}
            onEnviado={() => { setRefazendo(false); onAtualizar(); }}
          />
        )}
      </div>
    </li>
  );
};

/** Central de Estágio do aluno: manual, vídeo, modelos e envio das duas etapas. */
export const CentralEstagioAlunoPage: React.FC = () => {
  const [dados, setDados] = useState<CentralAluno | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      setDados(await estagiosApi.central());
      window.dispatchEvent(new Event('nexus:contadores-menu'));
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível carregar a Central de Estágio.'));
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => { void carregar(); }, []);

  const pct = dados ? Math.round((dados.horas_cumpridas / dados.horas_totais) * 100) : 0;
  const etapaAtual = dados?.etapas.find((e) => e.submissao?.status !== 'aprovado');

  return (
    <div className="max-w-6xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl md:flex-row md:items-center">
        <div className="flex items-start gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white">Central de Estágio ETADEMP</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              Baixe o manual e os modelos, assista ao vídeo explicativo e envie a documentação de cada etapa para a
              Coordenação de Estágio.
            </p>
          </div>
        </div>
        {dados && (
          <div className="min-w-[220px] rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <div className="flex items-baseline justify-between">
              <span className="text-xs font-semibold uppercase text-slate-500">Progresso</span>
              <span className="text-lg font-black text-white">{dados.horas_cumpridas}/{dados.horas_totais}h</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
            </div>
            <p className="mt-1.5 text-xs text-slate-400">
              {etapaAtual ? `Etapa ${etapaAtual.ordem} de ${dados.etapas.length} · ${etapaAtual.titulo}` : 'Estágio concluído 🎉'}
            </p>
          </div>
        )}
      </header>

      {erro && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <span className="flex items-center gap-2"><AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}</span>
          <button type="button" onClick={() => void carregar()} className="inline-flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs hover:bg-red-500/10">
            <RefreshCw size={13} /> Tentar de novo
          </button>
        </div>
      )}

      {carregando && !dados ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : dados ? (
        <>
          {dados.video_url && (
            <section className="glass grid gap-5 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 p-5 lg:grid-cols-5">
              <div className="aspect-video w-full overflow-hidden rounded-xl bg-black lg:col-span-3">
                <iframe
                  src={dados.video_url}
                  title="Vídeo explicativo do Manual de Estágio"
                  className="h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                />
              </div>
              <div className="flex flex-col justify-center lg:col-span-2">
                <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-300"><PlayCircle size={14} /> Assista antes de começar</p>
                <h2 className="mt-1 text-xl font-bold text-white">Como funciona o estágio</h2>
                <p className="mt-2 text-sm text-slate-400">
                  O vídeo explica o Manual de Estágio passo a passo: como preencher a Carta de Apresentação e o
                  Relatório, quais fotos registrar e como enviar tudo por aqui.
                </p>
                <ul className="mt-3 space-y-1.5 text-sm text-slate-300">
                  <li className="flex items-center gap-2"><BookOpenCheck size={15} className="text-emerald-400" /> Etapa 1: Teologia do Ministério (50h)</li>
                  <li className="flex items-center gap-2"><BookOpenCheck size={15} className="text-emerald-400" /> Etapa 2: Homilética (50h)</li>
                </ul>
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-400">Downloads</h2>
            <div className="grid gap-3 md:grid-cols-3">
              {dados.arquivos_base.map((a) => <CardDownload key={a.chave} arquivo={a} />)}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-400">Etapas do estágio</h2>
            <ol className="space-y-4">
              {dados.etapas.map((e) => <CartaoEtapa key={e.etapa} etapa={e} onAtualizar={() => void carregar()} />)}
            </ol>
          </section>

          <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
            <h2 className="border-b border-slate-800 px-5 py-4 font-bold text-white">Minhas solicitações</h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm text-slate-300">
                <thead className="bg-slate-950/50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-5 py-3">Etapa</th>
                    <th className="px-5 py-3">Enviado em</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Avaliado em</th>
                    <th className="px-5 py-3">Carga horária</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {dados.etapas.filter((e) => e.submissao).length === 0 ? (
                    <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">Nenhuma solicitação enviada ainda.</td></tr>
                  ) : dados.etapas.filter((e) => e.submissao).map((e) => (
                    <tr key={e.etapa}>
                      <td className="px-5 py-3 font-medium text-white">{e.titulo}</td>
                      <td className="px-5 py-3">{formatarDataHora(e.submissao!.enviado_em)}</td>
                      <td className="px-5 py-3"><StatusEstagioBadge status={e.submissao!.status} /></td>
                      <td className="px-5 py-3">{formatarDataHora(e.submissao!.avaliado_em)}</td>
                      <td className="px-5 py-3">
                        {e.submissao!.status === 'aprovado' ? `${e.horas}h cumpridas` : <span className="text-slate-500">{STATUS_ESTAGIO[e.submissao!.status].label}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
};
