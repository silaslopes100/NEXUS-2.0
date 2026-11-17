import React, { useState } from 'react';
import { CheckCircle2, Loader2, Pencil, Printer, Truck } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { EnderecoEntrega, Pedido, erroApi, formatData } from '@/features/financeiro/types';
import { abrirPdf, erroDeBlob, nomeDoArquivo } from '@/lib/download';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const CAMPOS: { key: keyof EnderecoEntrega; label: string; span?: string }[] = [
  { key: 'nome', label: 'Destinatário', span: 'col-span-2' },
  { key: 'cep', label: 'CEP' },
  { key: 'uf', label: 'UF' },
  { key: 'logradouro', label: 'Logradouro', span: 'col-span-2' },
  { key: 'numero', label: 'Número' },
  { key: 'complemento', label: 'Complemento' },
  { key: 'bairro', label: 'Bairro' },
  { key: 'cidade', label: 'Cidade' },
  { key: 'telefone', label: 'Telefone', span: 'col-span-2' },
];
const STATUS_FINAIS = ['enviado', 'entregue', 'concluido', 'cancelado'];
const STATUS_ETIQUETA = ['pago_aguardando_envio', 'enviado', 'entregue'];

interface Props {
  pedido: Pedido;
  onAtualizado: (pedido: Pedido) => void;
  /** Área logística: enviar e confirmar entrega (o financeiro só edita a entrega). */
  podeEnvio?: boolean;
}

/** Ações de logística do pedido de livro: envio (com rastreio), entrega e edição da entrega. */
export const LogisticaPedido: React.FC<Props> = ({ pedido, onAtualizado, podeEnvio = true }) => {
  const [modo, setModo] = useState<'envio' | 'editar' | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [envio, setEnvio] = useState({ transportadora: 'Correios', codigo_rastreio: '', volumes: 1, peso_total_g: '', observacao: '' });
  const [endereco, setEndereco] = useState<EnderecoEntrega>(pedido.endereco || {});
  const [observacao, setObservacao] = useState(pedido.observacao || '');
  const [gerandoEtiqueta, setGerandoEtiqueta] = useState(false);

  const executar = async (acao: () => Promise<Pedido>) => {
    setSalvando(true);
    setErro('');
    try {
      onAtualizado(await acao());
      setModo(null);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a ação.'));
    } finally {
      setSalvando(false);
    }
  };

  const enviar = () => executar(() => financeiroApi.marcarEnviado(pedido.id, {
    transportadora: envio.transportadora.trim(),
    codigo_rastreio: envio.codigo_rastreio.trim() || undefined,
    volumes: envio.volumes,
    peso_total_g: envio.peso_total_g ? Number(envio.peso_total_g) : null,
    observacao: envio.observacao.trim() || undefined,
  }));
  const salvarEdicao = () => executar(() => financeiroApi.editarPedido(pedido.id, {
    endereco: pedido.tipo === 'livro' ? endereco : undefined,
    observacao,
  }));

  const podeEnviar = podeEnvio && pedido.tipo === 'livro' && pedido.status === 'pago_aguardando_envio';
  const podeEntregar = podeEnvio && pedido.status === 'enviado';
  const podeEditar = !STATUS_FINAIS.includes(pedido.status);
  const podeEtiqueta = podeEnvio && pedido.tipo === 'livro' && STATUS_ETIQUETA.includes(pedido.status);
  if (!podeEnviar && !podeEntregar && !podeEditar && !podeEtiqueta && !(pedido.envios || []).length) return null;

  const imprimirEtiqueta = async () => {
    setGerandoEtiqueta(true);
    setErro('');
    try {
      const { blob, disposition } = await financeiroApi.etiqueta(pedido.id);
      abrirPdf(blob, nomeDoArquivo(disposition, `etiqueta-${pedido.numero}.pdf`));
    } catch (error) {
      setErro(await erroDeBlob(error, 'Não foi possível gerar a etiqueta.'));
    } finally {
      setGerandoEtiqueta(false);
    }
  };

  return (
    <div className="space-y-3 rounded-xl border border-indigo-500/30 bg-slate-950/50 p-4">
      <h3 className="flex items-center gap-1 text-xs font-bold uppercase text-indigo-300"><Truck size={13} /> Logística</h3>

      {(pedido.envios || []).map((e) => (
        <p key={e.id} className="text-xs text-slate-300">
          {e.transportadora || 'Envio'}{e.codigo_rastreio ? ` · rastreio ${e.codigo_rastreio}` : ''} · {e.volumes} volume(s)
          {e.peso_total_g ? ` · ${e.peso_total_g} g` : ''} · {formatData(e.enviado_em, true)}
        </p>
      ))}

      {erro && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-300">{erro}</p>}

      {!modo && (
        <div className="flex flex-wrap gap-2">
          {podeEnviar && (
            <button onClick={() => setModo('envio')} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white">
              <Truck size={14} /> Marcar enviado
            </button>
          )}
          {podeEtiqueta && (
            <button onClick={imprimirEtiqueta} disabled={gerandoEtiqueta} title="Etiqueta 10×15 (uma página por volume + declaração de conteúdo)" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:text-white disabled:opacity-50">
              {gerandoEtiqueta ? <Loader2 size={14} className="animate-spin" /> : <Printer size={14} />} Imprimir etiqueta
            </button>
          )}
          {podeEntregar && (
            <button onClick={() => executar(() => financeiroApi.marcarEntregue(pedido.id))} disabled={salvando} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
              {salvando ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Confirmar entrega
            </button>
          )}
          {podeEditar && (
            <button onClick={() => setModo('editar')} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-200">
              <Pencil size={14} /> Editar {pedido.tipo === 'livro' ? 'entrega' : 'observação'}
            </button>
          )}
        </div>
      )}

      {modo === 'envio' && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input className={`${inputClass} col-span-2`} placeholder="Transportadora" value={envio.transportadora} onChange={(e) => setEnvio({ ...envio, transportadora: e.target.value })} />
            <input className={`${inputClass} col-span-2`} placeholder="Código de rastreio (opcional)" value={envio.codigo_rastreio} onChange={(e) => setEnvio({ ...envio, codigo_rastreio: e.target.value })} />
            <input className={inputClass} type="number" min={1} placeholder="Volumes" value={envio.volumes} onChange={(e) => setEnvio({ ...envio, volumes: Math.max(1, Number(e.target.value) || 1) })} />
            <input className={inputClass} type="number" min={0} placeholder="Peso (g) — vazio = calcular" value={envio.peso_total_g} onChange={(e) => setEnvio({ ...envio, peso_total_g: e.target.value })} />
            <input className={`${inputClass} col-span-2`} placeholder="Observação (opcional)" value={envio.observacao} onChange={(e) => setEnvio({ ...envio, observacao: e.target.value })} />
          </div>
          <div className="flex gap-2">
            <button onClick={enviar} disabled={salvando || envio.transportadora.trim().length < 2} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">
              {salvando && <Loader2 size={14} className="animate-spin" />} Confirmar envio
            </button>
            <button onClick={() => setModo(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300">Voltar</button>
          </div>
        </div>
      )}

      {modo === 'editar' && (
        <div className="space-y-2">
          {pedido.tipo === 'livro' && (
            <div className="grid grid-cols-2 gap-2">
              {CAMPOS.map((c) => (
                <input
                  key={c.key}
                  className={`${inputClass} ${c.span || ''}`}
                  placeholder={c.label}
                  maxLength={c.key === 'uf' ? 2 : undefined}
                  value={endereco[c.key] || ''}
                  onChange={(e) => setEndereco({ ...endereco, [c.key]: c.key === 'uf' ? e.target.value.toUpperCase() : e.target.value })}
                />
              ))}
            </div>
          )}
          <textarea className={inputClass} rows={2} placeholder="Observação" value={observacao} onChange={(e) => setObservacao(e.target.value)} />
          <div className="flex gap-2">
            <button onClick={salvarEdicao} disabled={salvando} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">
              {salvando && <Loader2 size={14} className="animate-spin" />} Salvar
            </button>
            <button onClick={() => setModo(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300">Voltar</button>
          </div>
        </div>
      )}
    </div>
  );
};
