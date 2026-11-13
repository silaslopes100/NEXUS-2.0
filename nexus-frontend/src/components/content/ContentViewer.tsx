import React, { useEffect, useState } from 'react';
import { AlertCircle, Download, ExternalLink, Loader2, X } from 'lucide-react';

export interface ContentViewerFile {
  name: string;
  mimeType?: string | null;
  load: () => Promise<Blob>;
}

export interface ContentViewerProps {
  title: string;
  url?: string | null;
  file?: ContentViewerFile;
  onClose: () => void;
}

const safeExternalUrl = (value: string): string => {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : '';
  } catch {
    return '';
  }
};

const embeddedUrl = (value: string): string => {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    const isYoutube =
      host === 'youtube.com' ||
      host.endsWith('.youtube.com') ||
      host === 'youtube-nocookie.com' ||
      host.endsWith('.youtube-nocookie.com');

    if (host === 'youtu.be') {
      return `https://www.youtube-nocookie.com/embed/${url.pathname.slice(1)}`;
    }
    if (isYoutube) {
      const videoId = url.searchParams.get('v');
      if (url.pathname === '/watch' && videoId) {
        return `https://www.youtube-nocookie.com/embed/${videoId}`;
      }
      if (url.pathname.startsWith('/shorts/')) {
        const shortId = url.pathname.split('/')[2];
        if (shortId) return `https://www.youtube-nocookie.com/embed/${shortId}`;
      }
    }
    const vimeoVideo = url.pathname.match(/^\/(\d+)\/?$/);
    if ((host === 'vimeo.com' || host.endsWith('.vimeo.com')) && vimeoVideo) {
      return `https://player.vimeo.com/video/${vimeoVideo[1]}`;
    }
    return value;
  } catch {
    return value;
  }
};

export const ContentViewer: React.FC<ContentViewerProps> = ({ title, url, file, onClose }) => {
  const [fileUrl, setFileUrl] = useState('');
  const [fileMimeType, setFileMimeType] = useState('');
  const [isLoading, setIsLoading] = useState(Boolean(file));
  const [erro, setErro] = useState('');
  const [embedErro, setEmbedErro] = useState(false);

  useEffect(() => {
    const load = file?.load;
    if (!load || !file) {
      setIsLoading(false);
      return;
    }

    let active = true;
    setIsLoading(true);
    setErro('');

    void load()
      .then((blob) => {
        if (!active) return;
        const objectUrl = URL.createObjectURL(blob);
        setFileUrl(objectUrl);
        setFileMimeType(
          blob.type && blob.type !== 'application/octet-stream' ? blob.type : file.mimeType || blob.type
        );
      })
      .catch(() => {
        if (active) setErro('Não foi possível carregar este arquivo.');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [file?.load, file?.mimeType]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  useEffect(
    () => () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    },
    [fileUrl]
  );

  const baixarArquivo = () => {
    if (!fileUrl || !file) return;
    const anchor = document.createElement('a');
    anchor.href = fileUrl;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  const mimeType = fileMimeType.toLowerCase();
  const externalUrl = url ? safeExternalUrl(url) : '';
  const fileExtension = file?.name.split('.').pop()?.toLowerCase();
  const isPdf = mimeType === 'application/pdf' || fileExtension === 'pdf';
  const isImage = mimeType.startsWith('image/');
  const isVideo = mimeType.startsWith('video/');
  const isAudio = mimeType.startsWith('audio/');
  const canPreviewFile = isPdf || isImage || isVideo || isAudio;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-3 sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="content-viewer-title"
        className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl"
      >
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-800 px-4 py-3 sm:px-6">
          <h2 id="content-viewer-title" className="min-w-0 truncate font-semibold text-white">
            {title}
          </h2>
          <div className="flex shrink-0 items-center gap-2">
            {file && fileUrl && (
              <button
                type="button"
                onClick={baixarArquivo}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
              >
                <Download size={15} />
                <span className="hidden sm:inline">Baixar original</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar visualizador"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="min-h-[55vh] overflow-auto bg-slate-900">
          {isLoading ? (
            <div className="flex min-h-[55vh] items-center justify-center gap-3 text-sm text-slate-300">
              <Loader2 className="h-5 w-5 animate-spin text-blue-300" />
              Carregando conteúdo...
            </div>
          ) : erro ? (
            <div role="alert" className="flex min-h-[55vh] items-center justify-center gap-2 p-6 text-sm text-red-200">
              <AlertCircle size={18} />
              {erro}
            </div>
          ) : file && fileUrl ? (
            canPreviewFile ? (
              <div className="flex min-h-[55vh] items-center justify-center p-2 sm:p-4">
                {isPdf ? (
                  <iframe
                    title={title}
                    src={fileUrl}
                    className="h-[75vh] w-full rounded-lg bg-white"
                  />
                ) : isImage ? (
                  <img src={fileUrl} alt={title} className="max-h-[78vh] max-w-full object-contain" />
                ) : isVideo ? (
                  <video src={fileUrl} controls className="max-h-[78vh] max-w-full" />
                ) : (
                  <audio src={fileUrl} controls className="w-full max-w-xl" />
                )}
              </div>
            ) : (
              <div className="flex min-h-[55vh] flex-col items-center justify-center gap-3 p-8 text-center">
                <AlertCircle className="h-8 w-8 text-amber-300" />
                <p className="max-w-lg text-sm text-slate-300">
                  Este formato não pode ser pré-visualizado diretamente no navegador. Baixe o arquivo original para
                  abri-lo.
                </p>
                <button
                  type="button"
                  onClick={baixarArquivo}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-400"
                >
                  <Download size={16} />
                  Baixar {file.name}
                </button>
              </div>
            )
          ) : externalUrl ? (
            <div className="relative min-h-[55vh]">
              <iframe
                title={title}
                src={embeddedUrl(externalUrl)}
                onError={() => setEmbedErro(true)}
                referrerPolicy="no-referrer"
                sandbox="allow-forms allow-scripts allow-presentation allow-downloads"
                allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                allowFullScreen
                className="h-[75vh] min-h-[55vh] w-full border-0 bg-slate-950"
              />
              {embedErro && (
                <p role="status" className="absolute inset-x-0 bottom-0 bg-amber-950/95 p-3 text-center text-sm text-amber-100">
                  O site não permitiu a incorporação. Você pode abrir o conteúdo em uma nova aba.
                </p>
              )}
            </div>
          ) : url ? (
            <div role="alert" className="flex min-h-[55vh] items-center justify-center p-6 text-sm text-red-200">
              Este link não é válido. Somente endereços HTTP ou HTTPS podem ser exibidos.
            </div>
          ) : (
            <div className="flex min-h-[55vh] items-center justify-center p-6 text-sm text-slate-400">
              Este conteúdo não possui arquivo ou link disponível.
            </div>
          )}
        </div>

        {externalUrl && (
          <footer className="flex shrink-0 items-center justify-between gap-3 border-t border-slate-800 px-4 py-3 text-xs text-slate-400 sm:px-6">
            <span>Se o site não carregar neste visualizador, use a alternativa externa.</span>
            <a
              href={externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex shrink-0 items-center gap-1 font-semibold text-blue-300 hover:text-blue-200"
            >
              Abrir externamente
              <ExternalLink size={14} />
            </a>
          </footer>
        )}
      </section>
    </div>
  );
};
