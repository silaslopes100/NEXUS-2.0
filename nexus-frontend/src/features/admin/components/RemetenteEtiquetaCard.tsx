import React, { useEffect, useState } from 'react';
import { Loader2, Save, Truck } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { useCepAddress } from '@/features/polos_escolas/useCepAddress';
import { EnderecoCompleto } from '@/types/polos';

/** Chave em `configuracoes` lida pelo backend ao gerar a etiqueta 10×15. */
export const CHAVE_REMETENTE = 'remetente_etiqueta';

/** Mesmo padrão do backend (relatorios.REMETENTE_PADRAO), usado quando nada foi salvo. */
const REMETENTE_PADRAO = {
  nome: 'ETADEMP', logradouro: 'Rua Crispim do Amaral', numero: '33', bairro: 'Perus',
  cidade: 'São Paulo', uf: 'SP', cep: '05207-180',
};

interface Remetente {
  nome?: string;
  documento?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  cep?: string;
  telefone?: string;
}

const inputCls = 'w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow';

const mascaraDocumento = (valor: string) => {
  const d = valor.replace(/\D/g, '').slice(0, 14);
  if (d.length <= 11) {
    return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  }
  return d.replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2');
};

/** Dados do remetente impressos na etiqueta de envio dos livros. */
export const RemetenteEtiquetaCard: React.FC<{ valorAtual?: unknown; onSalvo: (msg: string, erro?: boolean) => void }> = ({
  valorAtual, onSalvo,
}) => {
  const [dados, setDados] = useState<Remetente>({});
  const [endereco, setEndereco] = useState<EnderecoCompleto>({});
  const [salvando, setSalvando] = useState(false);
  const { changeAddress, lookup } = useCepAddress(setEndereco, 'remetente');

  useEffect(() => {
    const configurado = valorAtual && typeof valorAtual === 'object' && (valorAtual as Remetente).nome;
    const atual = (configurado ? valorAtual : REMETENTE_PADRAO) as Remetente;
    setDados({ nome: atual.nome, documento: atual.documento, telefone: atual.telefone });
    setEndereco({
      cep: atual.cep, logradouro: atual.logradouro, numero: atual.numero, complemento: atual.complemento,
      bairro: atual.bairro, cidade: atual.cidade, estado: atual.uf,
    });
  }, [valorAtual]);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      await adminApi.setConfiguracao(CHAVE_REMETENTE, {
        nome: dados.nome?.trim(),
        documento: dados.documento?.trim() || undefined,
        telefone: dados.telefone?.trim() || undefined,
        cep: endereco.cep, logradouro: endereco.logradouro, numero: endereco.numero,
        complemento: endereco.complemento || undefined, bairro: endereco.bairro,
        cidade: endereco.cidade, uf: (endereco.estado || '').toUpperCase(),
      });
      onSalvo('Remetente das etiquetas salvo.');
    } catch (err: any) {
      onSalvo(err.response?.data?.detail || 'Não foi possível salvar o remetente.', true);
    } finally {
      setSalvando(false);
    }
  };

  const campo = (rotulo: string, valor: string | undefined, onChange: (v: string) => void, extra = '', props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <label className={`space-y-1 ${extra}`}>
      <span className="text-[11px] font-semibold text-slate-400">{rotulo}</span>
      <input className={inputCls} value={valor || ''} onChange={(e) => onChange(e.target.value)} {...props} />
    </label>
  );

  return (
    <form onSubmit={salvar} className="glass space-y-4 rounded-2xl border border-indigo-500/30 bg-slate-900/80 p-5 shadow-md">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-bold text-white"><Truck className="h-4 w-4 text-indigo-300" /> Remetente das etiquetas</h2>
          <p className="text-xs text-slate-500">
            Impresso na etiqueta 10×15 dos pedidos de livros. Padrão: ETADEMP, Rua Crispim do Amaral, 33 – Perus – São Paulo/SP.
            O destinatário é sempre o endereço cadastrado no Polo.
          </p>
        </div>
        <button disabled={salvando} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-on-accent disabled:opacity-50">
          {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />} Salvar
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {campo('Nome / razão social *', dados.nome, (v) => setDados({ ...dados, nome: v }), 'col-span-2', { required: true })}
        {campo('CPF/CNPJ', dados.documento, (v) => setDados({ ...dados, documento: mascaraDocumento(v) }))}
        {campo('Telefone', dados.telefone, (v) => setDados({ ...dados, telefone: v }))}
        {campo('CEP *', endereco.cep, (v) => changeAddress('cep', v), '', { required: true, inputMode: 'numeric' })}
        {campo('Logradouro *', endereco.logradouro, (v) => changeAddress('logradouro', v), 'col-span-2', { required: true })}
        {campo('Número', endereco.numero, (v) => changeAddress('numero', v))}
        {campo('Complemento', endereco.complemento, (v) => changeAddress('complemento', v))}
        {campo('Bairro', endereco.bairro, (v) => changeAddress('bairro', v))}
        {campo('Cidade *', endereco.cidade, (v) => changeAddress('cidade', v), '', { required: true })}
        {campo('UF *', endereco.estado, (v) => changeAddress('estado', v.toUpperCase().slice(0, 2)), '', { required: true, maxLength: 2 })}
      </div>
      {lookup.message && (
        <p className={`text-xs ${lookup.status === 'error' ? 'text-red-300' : 'text-slate-400'}`}>{lookup.message}</p>
      )}
    </form>
  );
};
