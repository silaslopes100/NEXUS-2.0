/** Salva um Blob como arquivo (mesmo padrão do boletim, centralizado). */
export const baixarArquivo = (blob: Blob, nome: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

/** Abre um PDF numa nova aba (ex.: etiqueta para imprimir); se o navegador bloquear, baixa. */
export const abrirPdf = (blob: Blob, nome: string) => {
  const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
  const janela = window.open(url, '_blank');
  if (!janela) baixarArquivo(blob, nome);
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
};

/** Nome do arquivo vindo do Content-Disposition (fallback quando ausente). */
export const nomeDoArquivo = (disposition: string | undefined, padrao: string) => {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition || '');
  return match ? decodeURIComponent(match[1]) : padrao;
};

/** Mensagem de erro de uma resposta blob (o corpo JSON do erro vem como Blob). */
export const erroDeBlob = async (error: any, padrao: string): Promise<string> => {
  const data = error?.response?.data;
  if (data instanceof Blob) {
    try {
      const json = JSON.parse(await data.text());
      if (typeof json.detail === 'string') return json.detail;
    } catch {
      return padrao;
    }
  }
  return padrao;
};
