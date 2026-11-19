import React, { useEffect, useState } from 'react';
import { CheckCircle2, ExternalLink, FileText, Loader2, PlayCircle, Save, Upload } from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import { ArquivoBase, ChaveBase, erroEstagio, estagiosApi, formatarDataHora, formatarTamanho } from '@/features/estagios/api';

const ACEITE: Record<ChaveBase, string> = {
  manual: 'application/pdf,.pdf',
  carta_modelo: '.docx,.doc,.pdf',
  relatorio_modelo: '.docx,.doc,.pdf',
};
const AJUDA: Record<ChaveBase, string> = {
  manual: 'PDF · até 30 MB',
  carta_modelo: 'DOCX (ou DOC/PDF) · até 30 MB',
  relatorio_modelo: 'DOCX (ou DOC/PDF) · até 30 MB',
};

/** Arquivos-base que o aluno baixa (Manual e modelos) e o link do vídeo explicativo. */
export const GestaoArquivosEstagio: React.FC = () => {
  const [arquivos, setArquivos] = useState<ArquivoBase[] | null>(null);
  const [enviando, setEnviando] = useState<{ chave: ChaveBase; pct: number } | null>(null);
  const [video, setVideo] = useState('');
  const [videoSalvo, setVideoSalvo] = useState<string | null>(null);
  const [salvandoVideo, setSalvandoVideo] = useState(false);
  const [aviso, setAviso] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null);

  useEffect(() => {
    estagiosApi.arquivosBase().then(setArquivos).catch((e) => setAviso({ tipo: 'erro', texto: erroEstagio(e, 'Não foi possível carregar os arquivos.') }));
    estagiosApi.config().then((c) => { setVideo(c.video_url || ''); setVideoSalvo(c.video_url || null); }).catch(() => undefined);
  }, []);

  const substituir = async (chave: ChaveBase, arquivo?: File) => {
    if (!arquivo) return;
    setAviso(null);
    setEnviando({ chave, pct: 0 });
    try {
      const enviado = await estagiosApi.enviarArquivo(arquivo, (pct) => setEnviando({ chave, pct }));
      setArquivos(await estagiosApi.substituirBase(chave, enviado));
      setAviso({ tipo: 'ok', texto: 'Arquivo atualizado. Os alunos já baixam a nova versão.' });
    } catch (e) {
      setAviso({ tipo: 'erro', texto: erroEstagio(e, 'Não foi possível substituir o arquivo.') });
    } finally {
      setEnviando(null);
    }
  };

  const salvarVideo = async () => {
    setSalvandoVideo(true);
    setAviso(null);
    try {
      const r = await estagiosApi.salvarConfig(video.trim());
      setVideo(r.video_url || '');
      setVideoSalvo(r.video_url || null);
      setAviso({ tipo: 'ok', texto: r.video_url ? 'Vídeo atualizado.' : 'Vídeo removido da Central do aluno.' });
    } catch (e) {
      setAviso({ tipo: 'erro', texto: erroEstagio(e, 'Não foi possível salvar o vídeo.') });
    } finally {
      setSalvandoVideo(false);
    }
  };

  return (
    <section className="space-y-5">
      {aviso && (
        <p role="status" className={`rounded-xl border p-3 text-sm ${aviso.tipo === 'ok' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-red-500/30 bg-red-500/10 text-red-200'}`}>
          {aviso.texto}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {!arquivos ? (
          <div className="col-span-full flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : arquivos.map((a) => {
          const subindo = enviando?.chave === a.chave;
          return (
            <div key={a.chave} className="glass flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="flex items-start gap-3">
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${a.chave === 'manual' ? 'bg-red-500/15 text-red-300' : 'bg-blue-500/15 text-blue-300'}`}>
                  <FileText size={20} />
                </span>
                <div className="min-w-0">
                  <p className="font-bold text-white">{a.titulo}</p>
                  {a.disponivel ? (
                    <p className="inline-flex items-center gap-1 text-xs text-emerald-300"><CheckCircle2 size={12} /> Disponível para os alunos</p>
                  ) : (
                    <p className="text-xs text-amber-300">Ainda não enviado</p>
                  )}
                </div>
              </div>
              {a.disponivel && (
                <a href={urlArquivo(a.url)} target="_blank" rel="noreferrer" className="group rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs hover:border-blue-500/50">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm text-white">{a.nome}</span>
                    <ExternalLink size={13} className="shrink-0 text-slate-500 group-hover:text-blue-300" />
                  </span>
                  <span className="text-slate-500">{formatarTamanho(a.tamanho)} · atualizado em {formatarDataHora(a.atualizado_em)}</span>
                </a>
              )}
              <label className={`mt-auto inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold ${
                enviando ? 'pointer-events-none opacity-60' : ''
              } ${a.disponivel ? 'border border-slate-700 text-slate-200 hover:bg-slate-800' : 'bg-blue-600 text-on-accent hover:bg-blue-500'}`}>
                {subindo ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
                {subindo ? `Enviando… ${enviando!.pct}%` : a.disponivel ? 'Substituir arquivo' : 'Enviar arquivo'}
                <input type="file" accept={ACEITE[a.chave]} className="sr-only" onChange={(e) => { void substituir(a.chave, e.target.files?.[0]); e.target.value = ''; }} />
              </label>
              <p className="text-center text-[11px] text-slate-500">{AJUDA[a.chave]}</p>
            </div>
          );
        })}
      </div>

      <div className="glass grid gap-5 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 lg:grid-cols-2">
        <div className="space-y-3">
          <div>
            <p className="flex items-center gap-2 font-bold text-white"><PlayCircle size={18} className="text-red-400" /> Vídeo explicativo do manual</p>
            <p className="text-xs text-slate-400">Cole o link do YouTube. Sem link, a área do vídeo fica oculta para o aluno.</p>
          </div>
          <input
            value={video}
            onChange={(e) => setVideo(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
          />
          <button
            type="button"
            onClick={() => void salvarVideo()}
            disabled={salvandoVideo || (video.trim() || null) === videoSalvo}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:opacity-50"
          >
            {salvandoVideo ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Salvar vídeo
          </button>
        </div>
        <div className="aspect-video overflow-hidden rounded-xl border border-slate-800 bg-black">
          {videoSalvo ? (
            <iframe src={videoSalvo} title="Prévia do vídeo" className="h-full w-full" allowFullScreen />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">Prévia do vídeo</div>
          )}
        </div>
      </div>
    </section>
  );
};
