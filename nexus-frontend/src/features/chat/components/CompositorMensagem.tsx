import React, { useEffect, useRef, useState } from 'react';
import { Loader2, Mic, Paperclip, Send, Square, Trash2, X } from 'lucide-react';
import { AnexoEnviado, chatApi, erroApi } from '../api';
import { tamanhoLegivel } from '../utils';

const ACEITOS = [
  'image/jpeg', 'image/png', 'image/webp', 'image/gif',
  'video/mp4', 'video/webm', 'video/quicktime',
  'audio/*',
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip',
].join(',');

interface Props {
  desabilitado: boolean;
  motivoDesabilitado?: string;
  onEnviar: (texto: string | null, anexo: AnexoEnviado | null) => Promise<void>;
}

const extensaoAudio = (mime: string) => (mime.includes('ogg') ? 'ogg' : mime.includes('mp4') ? 'm4a' : 'webm');

export const CompositorMensagem: React.FC<Props> = ({ desabilitado, motivoDesabilitado, onEnviar }) => {
  const [texto, setTexto] = useState('');
  const [arquivo, setArquivo] = useState<{ blob: Blob; nome: string } | null>(null);
  const [progresso, setProgresso] = useState<number | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [gravando, setGravando] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const textoRef = useRef<HTMLTextAreaElement>(null);
  const gravadorRef = useRef<MediaRecorder | null>(null);
  const partesRef = useRef<Blob[]>([]);
  const descartarRef = useRef(false);

  useEffect(() => {
    if (!gravando) return undefined;
    const id = window.setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [gravando]);

  useEffect(() => () => gravadorRef.current?.stream.getTracks().forEach((t) => t.stop()), []);

  const ajustarAltura = () => {
    const el = textoRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const enviar = async () => {
    const conteudo = texto.trim();
    if (enviando || desabilitado || (!conteudo && !arquivo)) return;
    setEnviando(true);
    setErro(null);
    try {
      let anexo: AnexoEnviado | null = null;
      if (arquivo) {
        setProgresso(0);
        anexo = await chatApi.enviarArquivo(arquivo.blob, arquivo.nome, setProgresso);
      }
      await onEnviar(conteudo || null, anexo);
      setTexto('');
      setArquivo(null);
      window.requestAnimationFrame(ajustarAltura);
    } catch (e) {
      setErro(erroApi(e, 'Não foi possível enviar a mensagem.'));
    } finally {
      setEnviando(false);
      setProgresso(null);
      textoRef.current?.focus();
    }
  };

  const iniciarGravacao = async () => {
    setErro(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setErro('Seu navegador não permite gravar áudio.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const gravador = new MediaRecorder(stream);
      partesRef.current = [];
      descartarRef.current = false;
      gravador.ondataavailable = (e) => e.data.size && partesRef.current.push(e.data);
      gravador.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if (descartarRef.current) return;
        const mime = (gravador.mimeType || 'audio/webm').split(';')[0];
        const blob = new Blob(partesRef.current, { type: mime });
        const agora = new Date().toLocaleString('pt-BR').replace(/[/:, ]+/g, '-');
        setArquivo({ blob, nome: `audio-${agora}.${extensaoAudio(mime)}` });
      };
      gravadorRef.current = gravador;
      gravador.start();
      setSegundos(0);
      setGravando(true);
    } catch {
      setErro('Não foi possível acessar o microfone.');
    }
  };

  const pararGravacao = (descartar = false) => {
    descartarRef.current = descartar;
    gravadorRef.current?.stop();
    gravadorRef.current = null;
    setGravando(false);
  };

  if (desabilitado) {
    return (
      <div className="border-t border-slate-800 p-4 text-center text-sm text-slate-500">
        {motivoDesabilitado ?? 'Não é possível enviar mensagens nesta conversa.'}
      </div>
    );
  }

  return (
    <div className="border-t border-slate-800 p-3">
      {erro && (
        <div className="mb-2 flex items-start justify-between gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {erro}
          <button type="button" onClick={() => setErro(null)} aria-label="Fechar"><X size={14} /></button>
        </div>
      )}
      {arquivo && (
        <div className="mb-2 flex items-center justify-between gap-2 rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-slate-200">
          <span className="min-w-0 truncate">
            📎 {arquivo.nome} <span className="text-xs text-slate-400">({tamanhoLegivel(arquivo.blob.size)})</span>
          </span>
          {progresso !== null ? (
            <span className="text-xs text-nexus-yellow">{progresso}%</span>
          ) : (
            <button type="button" onClick={() => setArquivo(null)} aria-label="Remover anexo" className="text-slate-400 hover:text-red-300">
              <Trash2 size={15} />
            </button>
          )}
        </div>
      )}
      {gravando ? (
        <div className="flex items-center gap-3 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-2.5">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
          <span className="flex-1 text-sm text-red-100">
            Gravando… {String(Math.floor(segundos / 60)).padStart(2, '0')}:{String(segundos % 60).padStart(2, '0')}
          </span>
          <button type="button" onClick={() => pararGravacao(true)} className="text-xs text-slate-300 hover:text-white">Descartar</button>
          <button type="button" onClick={() => pararGravacao()} aria-label="Parar gravação"
            className="rounded-full bg-red-500 p-2 text-on-accent hover:bg-red-600"><Square size={14} /></button>
        </div>
      ) : (
        <div className="flex items-end gap-2">
          <input ref={inputRef} type="file" accept={ACEITOS} className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setArquivo({ blob: f, nome: f.name });
              e.target.value = '';
            }} />
          <button type="button" onClick={() => inputRef.current?.click()} disabled={enviando} aria-label="Anexar arquivo"
            className="rounded-xl p-2.5 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50">
            <Paperclip size={18} />
          </button>
          <textarea ref={textoRef} value={texto} rows={1} maxLength={5000} placeholder="Escreva uma mensagem"
            onChange={(e) => { setTexto(e.target.value); ajustarAltura(); }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void enviar();
              }
            }}
            className="max-h-40 min-h-[42px] flex-1 resize-none rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-nexus-yellow/50 focus:outline-none" />
          {texto.trim() || arquivo ? (
            <button type="button" onClick={() => void enviar()} disabled={enviando} aria-label="Enviar"
              className="rounded-xl bg-nexus-yellow p-2.5 text-ink hover:bg-nexus-yellow/90 disabled:opacity-60">
              {enviando ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          ) : (
            <button type="button" onClick={() => void iniciarGravacao()} aria-label="Gravar áudio"
              className="rounded-xl p-2.5 text-slate-400 hover:bg-slate-800 hover:text-white">
              <Mic size={18} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};
