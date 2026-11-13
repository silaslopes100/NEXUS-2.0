import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Copy, Loader2, PlugZap, RefreshCw, Save, ShieldCheck, Webhook, XCircle,
} from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import {
  Ambiente, GatewayConfig, GatewayNome, GatewaysResposta, NOME_GATEWAY, WebhookEvento, erroApi, formatData,
} from '@/features/financeiro/types';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const INSTRUCOES: Record<GatewayNome, string> = {
  asaas: 'Painel Asaas → Integrações → Webhooks: cole a URL abaixo, informe o mesmo token de autenticação e marque os eventos de cobrança (PAYMENT_*).',
  pagbank: 'O PagBank recebe a URL automaticamente em cada pedido (notification_urls) e assina as notificações com ECDSA; não há token a configurar.',
  mercadopago: 'Painel Mercado Pago → Suas integrações → Webhooks: cole a URL abaixo, selecione o evento "Pagamentos" e copie a assinatura secreta para o campo de token. (Integração a validar na documentação antes de produção.)',
};

const COR_EVENTO: Record<string, string> = {
  processado: 'text-emerald-400', erro: 'text-red-400', ignorado: 'text-slate-400', recebido: 'text-amber-300',
};

// ---------------------------------------------------------------------------
// Card de um gateway (sandbox/produção)
// ---------------------------------------------------------------------------

const GatewayCard: React.FC<{
  gateway: GatewayNome;
  configs: GatewayConfig[];
  ambienteAtivo: Ambiente;
  podeEditar: boolean;
  onSalvo: () => void;
}> = ({ gateway, configs, ambienteAtivo, podeEditar, onSalvo }) => {
  const [ambiente, setAmbiente] = useState<Ambiente>(ambienteAtivo);
  const config = configs.find((c) => c.ambiente === ambiente)!;
  const [credenciais, setCredenciais] = useState<Record<string, string>>({});
  const [token, setToken] = useState('');
  const [ativo, setAtivo] = useState(config.ativo);
  const [padrao, setPadrao] = useState(config.padrao);
  const [salvando, setSalvando] = useState(false);
  const [testando, setTestando] = useState(false);
  const [mensagem, setMensagem] = useState<{ ok: boolean; texto: string } | null>(null);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setCredenciais({});
    setToken('');
    setAtivo(config.ativo);
    setPadrao(config.padrao);
    setMensagem(null);
  }, [config.ativo, config.padrao, ambiente]);

  const salvar = async () => {
    setSalvando(true);
    setMensagem(null);
    try {
      const preenchidas = Object.fromEntries(Object.entries(credenciais).filter(([, v]) => v.trim()));
      await financeiroApi.salvarGateway(gateway, ambiente, {
        ...(Object.keys(preenchidas).length ? { credenciais: preenchidas } : {}),
        ...(token.trim() ? { webhook_token: token.trim() } : {}),
        ativo,
        padrao: padrao && ativo,
      });
      setMensagem({ ok: true, texto: 'Configuração salva.' });
      onSalvo();
    } catch (error) {
      setMensagem({ ok: false, texto: erroApi(error, 'Não foi possível salvar.') });
    } finally {
      setSalvando(false);
    }
  };

  const testar = async () => {
    setTestando(true);
    setMensagem(null);
    try {
      const res = await financeiroApi.testarGateway(gateway, ambiente);
      setMensagem({ ok: res.ok, texto: res.mensagem });
      onSalvo();
    } catch (error) {
      setMensagem({ ok: false, texto: erroApi(error, 'Falha ao testar a conexão.') });
    } finally {
      setTestando(false);
    }
  };

  const copiar = async () => {
    if (!config.webhook_url) return;
    try {
      await navigator.clipboard.writeText(config.webhook_url);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    } catch {
      setCopiado(false);
    }
  };

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">{NOME_GATEWAY[gateway]}</h2>
          {config.ativo && <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">Ativo</span>}
          {config.padrao && <span className="rounded-full bg-blue-500/15 px-2 py-0.5 text-[11px] font-semibold text-blue-300">Padrão</span>}
          {config.ultimo_teste_ok === true && <CheckCircle2 size={15} className="text-emerald-400" aria-label="Último teste OK" />}
          {config.ultimo_teste_ok === false && <XCircle size={15} className="text-red-400" aria-label="Último teste falhou" />}
        </div>
        <div className="inline-flex rounded-xl border border-slate-700 p-1">
          {(['sandbox', 'producao'] as Ambiente[]).map((a) => (
            <button
              key={a}
              onClick={() => setAmbiente(a)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold ${ambiente === a ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              {a === 'sandbox' ? 'Sandbox' : 'Produção'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {config.campos.map((c) => (
          <div key={c.campo}>
            <label className="mb-1 block text-xs font-semibold text-slate-400">{c.label}{c.obrigatorio ? ' *' : ''}</label>
            <input
              type="password"
              autoComplete="new-password"
              disabled={!podeEditar}
              className={inputClass}
              placeholder={config.credenciais[c.campo] || 'não configurado'}
              value={credenciais[c.campo] || ''}
              onChange={(e) => setCredenciais({ ...credenciais, [c.campo]: e.target.value })}
            />
          </div>
        ))}
        {config.rotulo_webhook_token && (
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-400">{config.rotulo_webhook_token} *</label>
            <input
              type="password"
              autoComplete="new-password"
              disabled={!podeEditar}
              className={inputClass}
              placeholder={config.webhook_token || 'não configurado'}
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </div>
        )}
      </div>
      <p className="text-[11px] text-slate-500">Os valores atuais aparecem mascarados. Deixe em branco para manter; preencha só o que quiser trocar.</p>

      <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
        <p className="mb-1 flex items-center gap-1 text-xs font-bold uppercase text-slate-500"><Webhook size={13} /> URL do webhook</p>
        {config.webhook_url ? (
          <div className="flex items-center gap-2">
            <code className="flex-1 break-all text-xs text-blue-300">{config.webhook_url}</code>
            <button onClick={copiar} className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white" title="Copiar">
              {copiado ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>
          </div>
        ) : (
          <p className="text-xs text-amber-300">Defina PUBLIC_API_URL no backend para gerar a URL.</p>
        )}
        <p className="mt-2 text-[11px] text-slate-500">{INSTRUCOES[gateway]}</p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-300">
        <label className="flex items-center gap-2">
          <input type="checkbox" disabled={!podeEditar} checked={ativo} onChange={(e) => { setAtivo(e.target.checked); if (!e.target.checked) setPadrao(false); }} /> Ativo
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" disabled={!podeEditar || !ativo} checked={padrao} onChange={(e) => setPadrao(e.target.checked)} /> Padrão neste ambiente
        </label>
        {config.ultimo_teste_em && <span className="text-xs text-slate-500">Último teste: {formatData(config.ultimo_teste_em, true)}</span>}
      </div>

      {mensagem && (
        <p className={`rounded-xl border p-3 text-sm ${mensagem.ok ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>
          {mensagem.texto}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {podeEditar && (
          <button onClick={salvar} disabled={salvando} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {salvando ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Salvar
          </button>
        )}
        <button onClick={testar} disabled={testando} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 disabled:opacity-50">
          {testando ? <Loader2 size={15} className="animate-spin" /> : <PlugZap size={15} />} Testar conexão
        </button>
      </div>
    </section>
  );
};

// ---------------------------------------------------------------------------
// Log de eventos de webhook
// ---------------------------------------------------------------------------

const EventosWebhook: React.FC = () => {
  const [items, setItems] = useState<WebhookEvento[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [aberto, setAberto] = useState<string | null>(null);
  const [erro, setErro] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setErro('');
    try {
      const res = await financeiroApi.listWebhookEventos({ status: status || undefined, limit: 100 });
      setItems(res.items);
      setTotal(res.total);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar os eventos.'));
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { load(); }, [load]);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
        <div>
          <h2 className="font-bold text-white">Eventos de webhook</h2>
          <p className="text-xs text-slate-500">{total} evento(s) — idempotentes por gateway + id do evento</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="processado">Processado</option>
            <option value="erro">Erro</option>
            <option value="ignorado">Ignorado</option>
          </select>
          <button onClick={load} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white" title="Recarregar">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
      {erro && <p className="border-b border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr><th className="p-3" /><th className="p-3">Recebido</th><th className="p-3">Gateway</th><th className="p-3">Evento</th><th className="p-3">Cobrança</th><th className="p-3">Status</th><th className="p-3">Detalhe</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {items.map((w) => (
              <React.Fragment key={w.id}>
                <tr className="cursor-pointer text-slate-300 hover:bg-slate-800/40" onClick={() => setAberto(aberto === w.id ? null : w.id)}>
                  <td className="p-3 text-slate-500">{aberto === w.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                  <td className="p-3 text-xs">{formatData(w.recebido_em, true)}</td>
                  <td className="p-3 text-xs">{w.gateway} ({w.ambiente})</td>
                  <td className="p-3 font-mono text-xs">{w.tipo_evento || '-'}</td>
                  <td className="p-3 font-mono text-xs">{w.gateway_payment_id || '-'}</td>
                  <td className={`p-3 text-xs font-semibold ${COR_EVENTO[w.status] || ''}`}>{w.status}{w.tentativas > 1 ? ` (${w.tentativas}x)` : ''}</td>
                  <td className="p-3 text-xs text-slate-500">{w.erro || '-'}</td>
                </tr>
                {aberto === w.id && (
                  <tr><td colSpan={7} className="bg-slate-950/60 p-3"><pre className="max-h-72 overflow-auto text-[11px] text-slate-400">{JSON.stringify(w.payload, null, 2)}</pre></td></tr>
                )}
              </React.Fragment>
            ))}
            {!items.length && !loading && <tr><td colSpan={7} className="p-12 text-center text-slate-500">Nenhum evento recebido ainda.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
};

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------

export const GatewaysPage: React.FC = () => {
  const { perfil } = useAuthStore();
  const podeEditar = normalizeUserRole(perfil?.nome) === 'admin';
  const [aba, setAba] = useState<'config' | 'eventos'>('config');
  const [dados, setDados] = useState<GatewaysResposta | null>(null);
  const [erro, setErro] = useState('');

  const load = useCallback(async () => {
    try {
      setDados(await financeiroApi.listGateways());
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar os gateways.'));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const gateways: GatewayNome[] = ['asaas', 'pagbank', 'mercadopago'];

  return (
    <div className="max-w-7xl space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl">
        <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300"><ShieldCheck size={15} /> Financeiro</p>
        <h1 className="text-3xl font-extrabold text-white">Gateways de Pagamento</h1>
        <p className="mt-1 text-sm text-slate-400">Credenciais por ambiente (criptografadas no banco), URL de webhook e teste de conexão.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {dados && (
            <span className={`rounded-full px-3 py-1 text-xs font-bold ${dados.ambiente_ativo === 'producao' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'}`}>
              Ambiente em uso: {dados.ambiente_ativo === 'producao' ? 'PRODUÇÃO' : 'Sandbox'}
            </span>
          )}
          <div className="inline-flex rounded-xl border border-slate-700 p-1">
            {(['config', 'eventos'] as const).map((a) => (
              <button key={a} onClick={() => setAba(a)} className={`rounded-lg px-4 py-1.5 text-sm font-semibold ${aba === a ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}>
                {a === 'config' ? 'Configuração' : 'Eventos de webhook'}
              </button>
            ))}
          </div>
        </div>
      </header>

      {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
      {dados && !dados.chave_configurada && (
        <p className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          <AlertTriangle size={16} /> PAYMENT_SECRETS_KEY não configurada no backend: não é possível salvar credenciais.
        </p>
      )}
      {dados && !dados.public_api_url_configurada && (
        <p className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          <AlertTriangle size={16} /> PUBLIC_API_URL não configurada: as URLs de webhook não podem ser geradas.
        </p>
      )}
      {!podeEditar && <p className="text-xs text-slate-500">Somente administradores alteram credenciais. Você pode testar conexões e ver eventos.</p>}

      {aba === 'eventos' ? <EventosWebhook /> : !dados ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="space-y-4">
          {gateways.map((g) => (
            <GatewayCard
              key={g}
              gateway={g}
              configs={dados.items.filter((i) => i.gateway === g)}
              ambienteAtivo={dados.ambiente_ativo}
              podeEditar={podeEditar}
              onSalvo={load}
            />
          ))}
        </div>
      )}
    </div>
  );
};
