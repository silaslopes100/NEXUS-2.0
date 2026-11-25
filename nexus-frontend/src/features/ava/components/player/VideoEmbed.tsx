import React, { useEffect, useImperativeHandle, useRef } from 'react';
import { ItemAula } from '../../api';

/** Andamento informado pelo player (percentual 0–100 e posição em segundos). */
export type OnAndamento = (percentual: number, posicaoSeg: number) => void;

export interface VideoEmbedHandle {
  /** Posição atual (segundos), quando o player informa. */
  posicao: () => number | null;
  /** Leva o vídeo até a posição (segundos). */
  irPara: (seg: number) => void;
}

interface Props {
  item: ItemAula;
  inicioSeg?: number | null;
  onAndamento?: OnAndamento;
}

// ---------------------------------------------------------------------------
// YouTube IFrame API (carregada uma única vez)
// ---------------------------------------------------------------------------

interface YTPlayer {
  getCurrentTime(): number;
  getDuration(): number;
  seekTo(seg: number, permitirBuscar: boolean): void;
  destroy(): void;
}

declare global {
  interface Window {
    YT?: { Player: new (el: HTMLElement, opts: Record<string, unknown>) => YTPlayer };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let ytPronto: Promise<void> | null = null;
const carregarYoutube = () => {
  if (window.YT?.Player) return Promise.resolve();
  if (!ytPronto) {
    ytPronto = new Promise<void>((resolve) => {
      const anterior = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        anterior?.();
        resolve();
      };
      const s = document.createElement('script');
      s.src = 'https://www.youtube.com/iframe_api';
      s.async = true;
      document.head.appendChild(s);
    });
  }
  return ytPronto;
};

const YoutubePlayer = React.forwardRef<VideoEmbedHandle, { videoId: string; inicioSeg?: number | null; onAndamento?: OnAndamento }>(
  ({ videoId, inicioSeg, onAndamento }, ref) => {
    const alvo = useRef<HTMLDivElement>(null);
    const player = useRef<YTPlayer | null>(null);
    const cb = useRef(onAndamento);
    cb.current = onAndamento;

    useImperativeHandle(ref, () => ({
      posicao: () => player.current?.getCurrentTime?.() ?? null,
      irPara: (seg: number) => player.current?.seekTo?.(seg, true),
    }), []);

    useEffect(() => {
      let ativo = true;
      let intervalo: number | undefined;
      void carregarYoutube().then(() => {
        if (!ativo || !alvo.current || !window.YT) return;
        const div = document.createElement('div');
        alvo.current.appendChild(div);
        player.current = new window.YT.Player(div, {
          host: 'https://www.youtube-nocookie.com',
          videoId,
          width: '100%',
          height: '100%',
          playerVars: { rel: 0, modestbranding: 1, start: Math.floor(inicioSeg || 0) },
        });
        intervalo = window.setInterval(() => {
          const p = player.current;
          if (!p?.getDuration) return;
          const dur = p.getDuration();
          const pos = p.getCurrentTime();
          if (dur > 0) cb.current?.(Math.min(100, Math.round((pos / dur) * 100)), pos);
        }, 5000);
      });
      return () => {
        ativo = false;
        window.clearInterval(intervalo);
        player.current?.destroy?.();
        player.current = null;
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [videoId]);

    return <div ref={alvo} className="h-full w-full [&>iframe]:h-full [&>iframe]:w-full" />;
  },
);
YoutubePlayer.displayName = 'YoutubePlayer';

// ---------------------------------------------------------------------------
// Vimeo (API de postMessage do player, sem SDK)
// ---------------------------------------------------------------------------

const VimeoPlayer = React.forwardRef<VideoEmbedHandle, { url: string; inicioSeg?: number | null; onAndamento?: OnAndamento }>(
  ({ url, inicioSeg, onAndamento }, ref) => {
    const frame = useRef<HTMLIFrameElement>(null);
    const posicao = useRef<number | null>(null);
    const ultimoEnvio = useRef(0);
    const cb = useRef(onAndamento);
    cb.current = onAndamento;

    const enviar = (method: string, value?: unknown) =>
      frame.current?.contentWindow?.postMessage(JSON.stringify({ method, value }), 'https://player.vimeo.com');

    useImperativeHandle(ref, () => ({
      posicao: () => posicao.current,
      irPara: (seg: number) => enviar('setCurrentTime', seg),
    }), []);

    useEffect(() => {
      const aoReceber = (e: MessageEvent) => {
        if (e.origin !== 'https://player.vimeo.com' || e.source !== frame.current?.contentWindow) return;
        let dados: { event?: string; data?: { seconds?: number; percent?: number } };
        try {
          dados = typeof e.data === 'string' ? JSON.parse(e.data) : e.data;
        } catch {
          return;
        }
        if (dados.event === 'ready') {
          enviar('addEventListener', 'timeupdate');
          if (inicioSeg) enviar('setCurrentTime', inicioSeg);
        }
        if (dados.event === 'timeupdate' && dados.data) {
          posicao.current = dados.data.seconds ?? null;
          const agora = Date.now();
          if (agora - ultimoEnvio.current > 5000 || (dados.data.percent ?? 0) >= 0.9) {
            ultimoEnvio.current = agora;
            cb.current?.(Math.round((dados.data.percent ?? 0) * 100), dados.data.seconds ?? 0);
          }
        }
      };
      window.addEventListener('message', aoReceber);
      return () => window.removeEventListener('message', aoReceber);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [url]);

    const src = `${url}${url.includes('?') ? '&' : '?'}api=1&dnt=1`;
    return (
      <iframe ref={frame} src={src} title="Vídeo da aula" className="h-full w-full" allowFullScreen
        allow="autoplay; fullscreen; picture-in-picture; encrypted-media" />
    );
  },
);
VimeoPlayer.displayName = 'VimeoPlayer';

// ---------------------------------------------------------------------------
// Componente público
// ---------------------------------------------------------------------------

/** Player 16:9. YouTube e Vimeo informam o andamento; Panda e iframes genéricos dependem do botão "Concluir". */
export const VideoEmbed = React.forwardRef<VideoEmbedHandle, Props>(({ item, inicioSeg, onAndamento }, ref) => {
  // Panda/iframe genérico: o ref fica nulo (sem posição para as anotações).
  return (
    <div className="aspect-video w-full overflow-hidden rounded-2xl bg-black shadow-2xl">
      {item.provedor === 'youtube' && item.embed_id ? (
        <YoutubePlayer ref={ref} videoId={item.embed_id} inicioSeg={inicioSeg} onAndamento={onAndamento} />
      ) : item.provedor === 'vimeo' && item.url ? (
        <VimeoPlayer ref={ref} url={item.url} inicioSeg={inicioSeg} onAndamento={onAndamento} />
      ) : (
        <iframe src={item.url ?? ''} title={item.titulo || 'Vídeo da aula'} className="h-full w-full" allowFullScreen
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen" />
      )}
    </div>
  );
});
VideoEmbed.displayName = 'VideoEmbed';
