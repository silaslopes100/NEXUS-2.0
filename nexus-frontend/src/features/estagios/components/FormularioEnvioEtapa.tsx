import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, FileText, ImagePlus, Loader2, Send, Upload, X } from 'lucide-react';
import { ArquivoEnviado } from '@/lib/uploadDireto';
import {
  Etapa,
  FOTOS_MAX,
  FOTOS_MIN,
  Submissao,
  erroEstagio,
  estagiosApi,
  formatarTamanho,
} from '@/features/estagios/api';

interface Item {
  chave: string;
  arquivo: File;
  preview?: string;
  progresso: number;
  enviado?: ArquivoEnviado;
  erro?: string;
}

const ACEITE_DOC = '.pdf,.doc,.docx,image/jpeg,image/png,image/webp';
const ACEITE_FOTO = 'image/jpeg,image/png,image/webp';

let seq = 0;
const novoItem = (arquivo: File, comPreview = false): Item => ({
  chave: `${Date.now()}-${seq++}`,
  arquivo,
  preview: comPreview ? URL.createObjectURL(arquivo) : undefined,
  progresso: 0,
});

interface Props {
  etapa: Etapa;
  titulo: string;
  reenvio: boolean;
  onEnviado: (s: Submissao) => void;
  onCancelar?: () => void;
}

/** Upload da Carta assinada, do Relatório preenchido e de 5 a 10 fotos; cada arquivo sobe assim que é escolhido. */
export const FormularioEnvioEtapa: React.FC<Props> = ({ etapa, titulo, reenvio, onEnviado, onCancelar }) => {
  const [carta, setCarta] = useState<Item | null>(null);
  const [relatorio, setRelatorio] = useState<Item | null>(null);
  const [fotos, setFotos] = useState<Item[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const inputFotos = useRef<HTMLInputElement>(null);
  const previews = useRef<string[]>([]);

  useEffect(() => () => previews.current.forEach((u) => URL.revokeObjectURL(u)), []);

  const subir = async (item: Item, atualizar: (fn: (i: Item) => Item) => void) => {
    try {
      const enviado = await estagiosApi.enviarArquivo(item.arquivo, (pct) => atualizar((i) => ({ ...i, progresso: pct })));
      atualizar((i) => ({ ...i, enviado, progresso: 100, erro: undefined }));
    } catch (e) {
      atualizar((i) => ({ ...i, erro: erroEstagio(e, 'Falha ao enviar o arquivo.') }));
    }
  };

  const escolherDoc = (arquivo: File | undefined, setter: React.Dispatch<React.SetStateAction<Item | null>>) => {
    if (!arquivo) return;
    const item = novoItem(arquivo, arquivo.type.startsWith('image/'));
    if (item.preview) previews.current.push(item.preview);
    setter(item);
    void subir(item, (fn) => setter((atual) => (atual && atual.chave === item.chave ? fn(atual) : atual)));
  };

  const escolherFotos = (lista: FileList | null) => {
    if (!lista) return;
    const vagas = FOTOS_MAX - fotos.length;
    const selecionadas = Array.from(lista).slice(0, Math.max(0, vagas));
    if (lista.length > vagas) setErro(`Limite de ${FOTOS_MAX} fotos: ${lista.length - selecionadas.length} foto(s) ignorada(s).`);
    const novos = selecionadas.map((f) => novoItem(f, true));
    novos.forEach((n) => n.preview && previews.current.push(n.preview));
    setFotos((atual) => [...atual, ...novos]);
    novos.forEach((item) =>
      void subir(item, (fn) => setFotos((atual) => atual.map((i) => (i.chave === item.chave ? fn(i) : i)))),
    );
    if (inputFotos.current) inputFotos.current.value = '';
  };

  const subindo = [carta, relatorio, ...fotos].some((i) => i && !i.enviado && !i.erro);
  const comErro = [carta, relatorio, ...fotos].some((i) => i?.erro);
  const fotosOk = fotos.filter((f) => f.enviado).length;
  const pronto = !!carta?.enviado && !!relatorio?.enviado && fotosOk >= FOTOS_MIN && fotosOk <= FOTOS_MAX && !subindo && !comErro;

  const enviar = async () => {
    if (!pronto || !carta?.enviado || !relatorio?.enviado) return;
    setEnviando(true);
    setErro('');
    try {
      const s = await estagiosApi.enviar(etapa, {
        carta: carta.enviado,
        relatorio: relatorio.enviado,
        fotos: fotos.map((f) => f.enviado!).filter(Boolean),
      });
      onEnviado(s);
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível enviar a documentação.'));
    } finally {
      setEnviando(false);
    }
  };

  const campoDoc = ({ rotulo, ajuda, item, onEscolher, onRemover }: {
    rotulo: string; ajuda: string; item: Item | null; onEscolher: (f?: File) => void; onRemover: () => void;
  }) => (
    <div>
      <p className="mb-1.5 text-sm font-semibold text-white">{rotulo} <span className="text-red-400">*</span></p>
      {item ? (
        <div className={`flex items-center gap-3 rounded-xl border p-3 ${item.erro ? 'border-red-500/40 bg-red-500/5' : 'border-slate-700 bg-slate-950/60'}`}>
          {item.preview ? (
            <img src={item.preview} alt="" className="h-10 w-10 rounded-lg object-cover" />
          ) : (
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300"><FileText size={18} /></span>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm text-white">{item.arquivo.name}</p>
            {item.erro ? (
              <p className="text-xs text-red-300">{item.erro}</p>
            ) : item.enviado ? (
              <p className="inline-flex items-center gap-1 text-xs text-emerald-300"><CheckCircle2 size={12} /> Enviado · {formatarTamanho(item.arquivo.size)}</p>
            ) : (
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div className="h-full bg-blue-500 transition-all" style={{ width: `${item.progresso}%` }} />
              </div>
            )}
          </div>
          <button type="button" onClick={onRemover} aria-label={`Remover ${rotulo}`} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={16} />
          </button>
        </div>
      ) : (
        <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-4 py-5 text-center hover:border-blue-500/60 hover:bg-blue-500/5">
          <Upload size={20} className="text-blue-300" />
          <span className="text-sm text-slate-200">Clique para selecionar</span>
          <span className="text-[11px] text-slate-500">{ajuda}</span>
          <input type="file" accept={ACEITE_DOC} className="sr-only" onChange={(e) => { onEscolher(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
      )}
    </div>
  );

  return (
    <div className="space-y-5 rounded-xl border border-blue-500/25 bg-blue-500/5 p-4 sm:p-5">
      <div>
        <h4 className="font-bold text-white">{reenvio ? 'Refazer envio' : 'Enviar documentação'} · {titulo}</h4>
        <p className="text-xs text-slate-400">
          {reenvio
            ? 'Os arquivos do envio anterior serão excluídos e substituídos pelos novos.'
            : 'Envie os documentos preenchidos. Cada arquivo sobe assim que você o seleciona.'}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {campoDoc({
          rotulo: '1. Carta de Apresentação assinada',
          ajuda: 'PDF, DOC, DOCX ou foto do documento · até 30 MB',
          item: carta,
          onEscolher: (f) => escolherDoc(f, setCarta),
          onRemover: () => setCarta(null),
        })}
        {campoDoc({
          rotulo: '2. Relatório de Estágio preenchido',
          ajuda: 'PDF, DOC, DOCX ou foto do documento · até 30 MB',
          item: relatorio,
          onEscolher: (f) => escolherDoc(f, setRelatorio),
          onRemover: () => setRelatorio(null),
        })}
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-white">3. Galeria de fotos <span className="text-red-400">*</span></p>
          <span className={`text-xs font-semibold ${fotos.length >= FOTOS_MIN ? 'text-emerald-300' : 'text-amber-300'}`}>
            {fotos.length}/{FOTOS_MAX} (mínimo {FOTOS_MIN})
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {fotos.map((f) => (
            <div key={f.chave} className={`relative aspect-square overflow-hidden rounded-lg border ${f.erro ? 'border-red-500/60' : 'border-slate-700'}`}>
              <img src={f.preview} alt={f.arquivo.name} className="h-full w-full object-cover" />
              {!f.enviado && !f.erro && (
                <div className="absolute inset-x-0 bottom-0 h-1.5 bg-black/50">
                  <div className="h-full bg-blue-500 transition-all" style={{ width: `${f.progresso}%` }} />
                </div>
              )}
              {f.erro && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-950/70 p-1 text-center text-[10px] text-red-200" title={f.erro}>
                  Falhou
                </div>
              )}
              <button
                type="button"
                onClick={() => setFotos((atual) => atual.filter((i) => i.chave !== f.chave))}
                aria-label="Remover foto"
                className="absolute right-1 top-1 rounded-full bg-black/70 p-1 text-white hover:bg-red-600"
              >
                <X size={12} />
              </button>
            </div>
          ))}
          {fotos.length < FOTOS_MAX && (
            <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-slate-700 bg-slate-950/40 text-slate-400 hover:border-blue-500/60 hover:text-blue-300">
              <ImagePlus size={20} />
              <span className="text-[11px]">Adicionar</span>
              <input ref={inputFotos} type="file" multiple accept={ACEITE_FOTO} className="sr-only" onChange={(e) => escolherFotos(e.target.files)} />
            </label>
          )}
        </div>
        <p className="mt-1.5 text-[11px] text-slate-500">JPG, PNG ou WEBP · até 10 MB cada.</p>
      </div>

      {erro && (
        <p role="alert" className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5 text-sm text-red-200">
          <AlertCircle size={16} className="shrink-0" /> {erro}
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        {onCancelar && (
          <button type="button" onClick={onCancelar} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800">
            Cancelar
          </button>
        )}
        <button
          type="button"
          onClick={() => void enviar()}
          disabled={!pronto || enviando}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enviando ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Enviar para análise
        </button>
      </div>
    </div>
  );
};
