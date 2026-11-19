import { put } from '@vercel/blob/client';
import { apiClient } from '@/api/client';

/** Resposta do backend ao preparar um upload (Blob em produção, disco local em desenvolvimento). */
export interface UploadPreparado {
  modo: 'blob' | 'local';
  pathname: string;
  content_type: string;
  token?: string | null;
  upload_url?: string | null;
}

/** Metadados de um arquivo já enviado, para informar ao backend. */
export interface ArquivoEnviado {
  url: string;
  pathname: string;
  nome: string;
  mime: string;
  tamanho: number;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/** URLs locais (desenvolvimento) são relativas à API; as do Blob já são absolutas. */
export const urlArquivo = (url?: string | null) =>
  !url ? '' : url.startsWith('/') ? `${API_BASE_URL}${url}` : url;

/** Tipo MIME aceito pelo backend (alguns navegadores anexam codecs: "audio/webm;codecs=opus"). */
export const mimeBase = (mime: string) => mime.split(';')[0].trim().toLowerCase();

/**
 * Envia o arquivo direto ao armazenamento e devolve os metadados.
 * `rotaPreparo`: endpoint que valida tipo/tamanho e emite o token (ex.: '/chat/anexos/upload').
 */
export async function enviarArquivoDireto(
  rotaPreparo: string,
  arquivo: File | Blob,
  nome: string,
  onProgresso?: (pct: number) => void,
): Promise<ArquivoEnviado> {
  const mime = mimeBase(arquivo.type || 'application/octet-stream');
  const prep = await apiClient
    .post<UploadPreparado>(rotaPreparo, { nome, mime, tamanho: arquivo.size })
    .then((r) => r.data);
  if (prep.modo === 'blob' && prep.token) {
    const res = await put(prep.pathname, arquivo, {
      access: 'public',
      token: prep.token,
      contentType: prep.content_type,
      multipart: arquivo.size > 8 * 1024 * 1024,
      onUploadProgress: (e) => onProgresso?.(e.percentage),
    });
    return { url: res.url, pathname: prep.pathname, nome, mime, tamanho: arquivo.size };
  }
  const form = new FormData();
  form.append('arquivo', new File([arquivo], nome, { type: mime }));
  const res = await apiClient.post<{ url: string; pathname: string }>(prep.upload_url!, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
    onUploadProgress: (e) => e.total && onProgresso?.(Math.round((e.loaded / e.total) * 100)),
  });
  return { url: res.data.url, pathname: prep.pathname, nome, mime, tamanho: arquivo.size };
}
