import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, ExternalLink, FileText, X } from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import {
  ArquivoEstagio,
  EventoEstagio,
  STATUS_ESTAGIO,
  StatusEstagio,
  formatarDataHora,
  formatarTamanho,
} from '@/features/estagios/api';

export const StatusEstagioBadge: React.FC<{ status: StatusEstagio; className?: string }> = ({ status, className = '' }) => {
  const s = STATUS_ESTAGIO[status];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${s.classe} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.ponto}`} /> {s.label}
    </span>
  );
};

const ROTULO_DOC: Record<string, string> = { carta: 'Carta de Apresentação', relatorio: 'Relatório de Estágio' };

/** Galeria em tela cheia (setas do teclado e Esc). */
export const Lightbox: React.FC<{ fotos: ArquivoEstagio[]; inicial: number; onFechar: () => void }> = ({
  fotos,
  inicial,
  onFechar,
}) => {
  const [i, setI] = useState(inicial);
  const total = fotos.length;
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFechar();
      if (e.key === 'ArrowRight') setI((v) => (v + 1) % total);
      if (e.key === 'ArrowLeft') setI((v) => (v - 1 + total) % total);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [onFechar, total]);
  const foto = fotos[i];
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 p-4" onClick={onFechar} role="dialog" aria-modal="true">
      <button type="button" aria-label="Fechar" onClick={onFechar} className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
        <X size={20} />
      </button>
      {total > 1 && (
        <button type="button" aria-label="Anterior" onClick={(e) => { e.stopPropagation(); setI((i - 1 + total) % total); }} className="absolute left-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
          <ChevronLeft size={24} />
        </button>
      )}
      <figure className="max-h-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
        <img src={urlArquivo(foto.url)} alt={foto.nome} className="max-h-[80vh] max-w-full rounded-lg object-contain" />
        <figcaption className="mt-3 flex items-center justify-between gap-4 text-sm text-white/80">
          <span className="truncate">{foto.nome} · {i + 1}/{total}</span>
          <a href={urlArquivo(foto.url)} target="_blank" rel="noreferrer" download={foto.nome} className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs hover:bg-white/20">
            <Download size={14} /> Baixar
          </a>
        </figcaption>
      </figure>
      {total > 1 && (
        <button type="button" aria-label="Próxima" onClick={(e) => { e.stopPropagation(); setI((i + 1) % total); }} className="absolute right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
          <ChevronRight size={24} />
        </button>
      )}
    </div>
  );
};

/** Documentos (carta e relatório) e galeria de fotos de uma submissão. */
export const ArquivosSubmissao: React.FC<{ arquivos: ArquivoEstagio[] }> = ({ arquivos }) => {
  const [aberta, setAberta] = useState<number | null>(null);
  const docs = arquivos.filter((a) => a.tipo !== 'foto');
  const fotos = arquivos.filter((a) => a.tipo === 'foto');
  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2">
        {docs.map((d) => {
          const ehImagem = d.mime.startsWith('image/');
          return (
            <a
              key={d.id}
              href={urlArquivo(d.url)}
              target="_blank"
              rel="noreferrer"
              download={d.nome}
              className="group flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3 hover:border-blue-500/50"
            >
              {ehImagem ? (
                <img src={urlArquivo(d.url)} alt="" className="h-10 w-10 shrink-0 rounded-lg object-cover" />
              ) : (
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
                  <FileText size={18} />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-semibold text-slate-400">{ROTULO_DOC[d.tipo] || 'Documento'}</span>
                <span className="block truncate text-sm text-white">{d.nome}</span>
                <span className="block text-[11px] text-slate-500">{formatarTamanho(d.tamanho)}</span>
              </span>
              <ExternalLink size={15} className="shrink-0 text-slate-500 group-hover:text-blue-300" />
            </a>
          );
        })}
      </div>
      {fotos.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Galeria de fotos ({fotos.length})</p>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
            {fotos.map((f, i) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setAberta(i)}
                className="aspect-square overflow-hidden rounded-lg border border-slate-800 hover:border-blue-500/60"
                title={f.nome}
              >
                <img src={urlArquivo(f.url)} alt={f.nome} loading="lazy" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </div>
      )}
      {aberta !== null && <Lightbox fotos={fotos} inicial={aberta} onFechar={() => setAberta(null)} />}
    </div>
  );
};

const ACAO_LABEL: Record<EventoEstagio['acao'], string> = {
  enviado: 'Documentação enviada',
  reenviado: 'Documentação reenviada',
  aprovado: 'Aprovado',
  negado: 'Negado',
};
const ACAO_COR: Record<EventoEstagio['acao'], string> = {
  enviado: 'bg-amber-400',
  reenviado: 'bg-amber-400',
  aprovado: 'bg-emerald-400',
  negado: 'bg-red-400',
};

export const LinhaDoTempo: React.FC<{ eventos: EventoEstagio[] }> = ({ eventos }) => (
  <ol className="space-y-3 border-l border-slate-800 pl-4">
    {eventos.map((e, i) => (
      <li key={i} className="relative">
        <span className={`absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full ${ACAO_COR[e.acao]}`} />
        <p className="text-sm font-semibold text-white">{ACAO_LABEL[e.acao]}</p>
        <p className="text-xs text-slate-500">
          {formatarDataHora(e.criado_em)}{e.usuario_nome ? ` · ${e.usuario_nome}` : ''}
        </p>
        {e.comentario && <p className="mt-1 text-sm text-slate-300">“{e.comentario}”</p>}
      </li>
    ))}
  </ol>
);
