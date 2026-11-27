import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, Ban, Camera, CheckCircle2, KeyRound, Loader2, RefreshCw, RotateCcw, Shield, Trash2, X,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { UsuarioAvatar } from '@/features/admin/components/UsuarioAvatar';
import { HistoricoTab } from '@/features/admin/components/ficha/HistoricoTab';
import { InativarModal, TransferenciaModal } from '@/features/admin/components/ficha/FichaModais';
import { SecoesPessoais } from '@/features/admin/components/ficha/SecoesPessoais';
import { SecoesVinculo } from '@/features/admin/components/ficha/SecoesVinculo';
import { formatarData, mensagemErro, rotuloStatus, statusBadge } from '@/features/admin/components/ficha/fichaUtils';
import { useAuthStore } from '@/stores/authStore';
import { AbaHistorico, PodeExcluir, ResumoMetricasUsuario, UsuarioFicha } from '@/types/admin';

type Aba = 'cadastro' | AbaHistorico;

const ABAS: { id: Aba; rotulo: string }[] = [
  { id: 'cadastro', rotulo: 'Cadastro' },
  { id: 'academico', rotulo: 'Acadêmico' },
  { id: 'financeiro', rotulo: 'Financeiro' },
  { id: 'movimentacoes', rotulo: 'Movimentações' },
  { id: 'auditoria', rotulo: 'Auditoria' },
];

type Feedback = { type: 'success' | 'error'; message: string } | null;

/** Destino do "Voltar": quem abriu a ficha (ex.: lista de Alunos) pode informá-lo via state. */
type VoltarPara = { to: string; rotulo: string };
const VOLTAR_PADRAO: VoltarPara = { to: '/admin/usuarios', rotulo: 'Voltar para a consulta' };

const voltarDoEstado = (state: unknown): VoltarPara => {
  const voltar = (state as { voltar?: Partial<VoltarPara> } | null)?.voltar;
  return voltar && typeof voltar.to === 'string' && voltar.to.startsWith('/') && typeof voltar.rotulo === 'string'
    ? { to: voltar.to, rotulo: voltar.rotulo }
    : VOLTAR_PADRAO;
};

export const UsuarioFichaPage: React.FC = () => {
  const { usuarioId } = useParams<{ usuarioId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const voltar = voltarDoEstado(location.state);
  const [params, setParams] = useSearchParams();
  const { user: loggedAdmin, setUser } = useAuthStore();
  const abaParam = params.get('aba') as Aba | null;
  const aba: Aba = ABAS.some((a) => a.id === abaParam) ? (abaParam as Aba) : 'cadastro';

  const [ficha, setFicha] = useState<UsuarioFicha | null>(null);
  const [resumo, setResumo] = useState<ResumoMetricasUsuario | null>(null);
  const [podeExcluir, setPodeExcluir] = useState<PodeExcluir | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resumoError, setResumoError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [versao, setVersao] = useState(0);

  const [modal, setModal] = useState<'senha' | 'excluir' | 'inativar' | 'transferencia' | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [processando, setProcessando] = useState(false);
  const [fotoObjectUrl, setFotoObjectUrl] = useState<string | null>(null);

  const loadAll = useCallback(async (silencioso = false) => {
    if (!usuarioId) return;
    if (!silencioso) setIsLoading(true);
    setError(null);
    setResumoError(null);
    try {
      const [fichaResult, resumoResult, excluirResult] = await Promise.allSettled([
        adminApi.getUsuarioFicha(usuarioId),
        adminApi.getResumoUsuario(usuarioId),
        adminApi.podeExcluirUsuario(usuarioId),
      ]);
      if (fichaResult.status === 'rejected') throw fichaResult.reason;
      setFicha(fichaResult.value);
      if (resumoResult.status === 'fulfilled') {
        setResumo(resumoResult.value);
      } else {
        setResumo(null);
        setResumoError(mensagemErro(resumoResult.reason, 'Não foi possível carregar as métricas do usuário.'));
      }
      setPodeExcluir(excluirResult.status === 'fulfilled' ? excluirResult.value : null);
      setVersao((v) => v + 1);
    } catch (err) {
      setError(mensagemErro(err, 'Erro ao carregar a ficha do usuário.'));
    } finally {
      setIsLoading(false);
    }
  }, [usuarioId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!ficha) return;
    const storedFilename = /^[a-f0-9]{32}\.(?:jpg|png|webp)$/.test(ficha.foto_url || '');
    const storedAdminUrl = ficha.foto_url?.startsWith(`/admin/usuarios/${ficha.id}/foto`) || storedFilename;
    if (!storedAdminUrl) {
      setFotoObjectUrl(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    void adminApi.getUsuarioFoto(ficha.id).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      if (cancelled) URL.revokeObjectURL(objectUrl);
      else setFotoObjectUrl(objectUrl);
    }).catch((err: unknown) => {
      if (!cancelled) {
        setFotoObjectUrl(null);
        setFeedback({ type: 'error', message: mensagemErro(err, 'Não foi possível carregar a foto do usuário.') });
      }
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [ficha?.id, ficha?.foto_url]);

  const sucesso = (message: string) => {
    setFeedback({ type: 'success', message });
    void loadAll(true);
  };

  const trocarAba = (nova: Aba) => {
    const p = new URLSearchParams(params);
    if (nova === 'cadastro') p.delete('aba');
    else p.set('aba', nova);
    // Mantém o state (destino do "Voltar") ao trocar de aba.
    setParams(p, { replace: true, state: location.state });
  };

  const handleUploadFoto = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const foto = event.target.files?.[0];
    event.target.value = '';
    if (!foto || !ficha) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(foto.type) || foto.size > 4 * 1024 * 1024) {
      setFeedback({ type: 'error', message: 'Envie uma imagem JPEG, PNG ou WebP de até 4 MB.' });
      return;
    }
    try {
      const resultado = await adminApi.uploadUsuarioFoto(ficha.id, foto);
      setFicha((atual) => (atual ? { ...atual, foto_url: resultado.foto_url } : atual));
      if (loggedAdmin?.id === ficha.id) setUser({ ...loggedAdmin, foto_url: resultado.foto_url });
      setFeedback({ type: 'success', message: 'Foto atualizada para o usuário e o aluno.' });
    } catch (err) {
      setFeedback({ type: 'error', message: mensagemErro(err, 'Não foi possível atualizar a foto.') });
    }
  };

  const confirmarSenha = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ficha || newPassword.length < 6) {
      setFeedback({ type: 'error', message: 'A nova senha deve ter no mínimo 6 caracteres.' });
      return;
    }
    setProcessando(true);
    try {
      await adminApi.resetUsuarioSenha(ficha.id, newPassword);
      setFeedback({ type: 'success', message: 'Senha redefinida com sucesso.' });
      setModal(null);
    } catch (err) {
      setFeedback({ type: 'error', message: mensagemErro(err, 'Erro ao redefinir a senha.') });
    } finally {
      setProcessando(false);
    }
  };

  const confirmarExclusao = async () => {
    if (!ficha) return;
    setProcessando(true);
    try {
      await adminApi.deleteUsuario(ficha.id);
      setModal(null);
      setFeedback({ type: 'success', message: `Usuário ${ficha.nome} excluído.` });
      setTimeout(() => navigate('/admin/usuarios'), 800);
    } catch (err) {
      setModal(null);
      setFeedback({ type: 'error', message: mensagemErro(err, 'Erro ao excluir usuário.') });
    } finally {
      setProcessando(false);
    }
  };

  const reativar = async () => {
    if (!ficha) return;
    setProcessando(true);
    try {
      await adminApi.reativarUsuario(ficha.id);
      sucesso(`${ficha.nome} foi reativado(a).`);
    } catch (err) {
      setFeedback({ type: 'error', message: mensagemErro(err, 'Não foi possível reativar o usuário.') });
    } finally {
      setProcessando(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-nexus-yellow mr-3" />
        Carregando ficha cadastral...
      </div>
    );
  }

  if (error || !ficha) {
    return (
      <div className="max-w-3xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-sm text-slate-300">{error || 'Usuário não encontrado.'}</p>
        <button
          onClick={() => navigate(voltar.to)}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
        >
          {voltar === VOLTAR_PADRAO ? 'Voltar para a lista' : voltar.rotulo}
        </button>
      </div>
    );
  }

  const nomeCompleto = `${ficha.nome} ${ficha.sobrenome || ''}`.trim();
  const ativo = ficha.status === 'ativo';
  const proprio = loggedAdmin?.id === ficha.id;
  const dicaExcluir = podeExcluir?.pode_excluir
    ? 'Excluir definitivamente (cadastro sem histórico)'
    : `Exclusão indisponível: ${podeExcluir?.motivos.length ? `há ${podeExcluir.motivos.join(', ')}` : 'não foi possível verificar o histórico'}. Inative o usuário.`;

  return (
    <div className="space-y-6 max-w-6xl">
      {feedback && (
        <div
          role={feedback.type === 'error' ? 'alert' : 'status'}
          className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-sm animate-fadeIn ${
            feedback.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
              : 'bg-red-500/15 border-red-500/30 text-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success'
              ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              : <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />}
            <span>{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white" aria-label="Fechar aviso">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {resumoError && (
        <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          Não foi possível carregar as métricas do usuário. Os valores indisponíveis aparecem como “—”. {resumoError}
        </div>
      )}

      {/* Cabeçalho */}
      <div className="glass p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl">
        <button
          onClick={() => navigate(voltar.to)}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-nexus-yellow transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          {voltar.rotulo}
        </button>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <div className="relative shrink-0">
              {fotoObjectUrl ? (
                <img src={fotoObjectUrl} alt={nomeCompleto} className="w-16 h-16 rounded-2xl object-cover border border-slate-700" />
              ) : (
                <UsuarioAvatar fotoUrl={ficha.foto_url} nome={nomeCompleto}
                  className="w-16 h-16 rounded-2xl object-cover border border-slate-700 text-xl" />
              )}
              <label
                htmlFor="usuario-foto-upload"
                title="Alterar foto do usuário"
                className="absolute -bottom-2 -right-2 p-1.5 rounded-full bg-nexus-yellow text-ink cursor-pointer shadow-lg hover:bg-yellow-300"
              >
                <Camera className="w-3.5 h-3.5" />
                <span className="sr-only">Alterar foto do usuário</span>
              </label>
              <input id="usuario-foto-upload" type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleUploadFoto} />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-extrabold text-white tracking-tight break-words">{nomeCompleto}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-nexus-blue/15 border border-nexus-blue/30 text-blue-400">
                  <Shield className="w-3 h-3" />
                  {ficha.perfil_nome || 'Sem perfil'}
                </span>
                <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${statusBadge(ficha.status)}`}>
                  {rotuloStatus(ficha.status)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => {
                setNewPassword('');
                setModal('senha');
              }}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors flex items-center gap-1.5"
            >
              <KeyRound className="w-3.5 h-3.5" /> Redefinir senha
            </button>
            {!proprio && (ativo ? (
              <button
                onClick={() => setModal('inativar')}
                className="px-4 py-2.5 bg-slate-800 hover:bg-red-500/15 text-slate-300 hover:text-red-300 font-semibold text-xs rounded-xl transition-colors flex items-center gap-1.5"
              >
                <Ban className="w-3.5 h-3.5" /> Inativar
              </button>
            ) : (
              <button
                onClick={() => void reativar()}
                disabled={processando}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-on-accent font-bold text-xs rounded-xl transition-colors flex items-center gap-1.5 disabled:opacity-60"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Reativar
              </button>
            ))}
            {!proprio && (
              <button
                onClick={() => setModal('excluir')}
                disabled={!podeExcluir?.pode_excluir}
                title={dicaExcluir}
                aria-label={dicaExcluir}
                className="p-2.5 bg-slate-800 hover:bg-red-500/15 text-slate-400 hover:text-red-400 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-slate-800 disabled:hover:text-slate-400 disabled:cursor-not-allowed"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              onClick={() => void loadAll()}
              className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
              title="Recarregar"
              aria-label="Recarregar ficha"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {!ativo && (
          <p role="status" className="mt-5 flex items-start gap-2 text-xs text-red-200 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
            <Ban className="w-4 h-4 shrink-0" />
            <span>
              {ficha.status === 'bloqueado' ? 'Bloqueado' : 'Inativo'}
              {ficha.dados.inativado_em ? ` desde ${formatarData(ficha.dados.inativado_em, true)}` : ''}
              {ficha.dados.inativado_por_nome ? ` por ${ficha.dados.inativado_por_nome}` : ''}
              {ficha.dados.motivo_inativacao ? ` — ${ficha.dados.motivo_inativacao}` : ''}. Sem acesso ao sistema.
            </span>
          </p>
        )}
      </div>

      {/* Abas */}
      <div role="tablist" aria-label="Seções da ficha" className="flex gap-1 overflow-x-auto border-b border-slate-800 -mx-1 px-1">
        {ABAS.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={aba === a.id}
            aria-controls={`painel-${a.id}`}
            onClick={() => trocarAba(a.id)}
            className={`px-4 py-2.5 text-xs font-bold whitespace-nowrap border-b-2 -mb-px transition-colors ${
              aba === a.id ? 'border-nexus-yellow text-white' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="space-y-6">
        {aba === 'cadastro' ? (
          <>
            <SecoesPessoais ficha={ficha} aoSalvar={sucesso} />
            <SecoesVinculo ficha={ficha} resumo={resumo} aoSalvar={sucesso} aoSolicitarTransferencia={() => setModal('transferencia')} />
          </>
        ) : (
          <div className="glass rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-5 sm:p-6">
            <HistoricoTab usuarioId={ficha.id} aba={aba} versao={versao} />
          </div>
        )}
      </div>

      {modal === 'inativar' && <InativarModal ficha={ficha} aoFechar={() => setModal(null)} aoConcluir={(m) => { setModal(null); sucesso(m); }} />}
      {modal === 'transferencia' && ficha.aluno && (
        <TransferenciaModal ficha={ficha} aoFechar={() => setModal(null)} aoConcluir={(m) => { setModal(null); sucesso(m); }} />
      )}

      {modal === 'senha' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div role="dialog" aria-modal="true" aria-labelledby="titulo-senha"
            className="my-auto glass bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 id="titulo-senha" className="flex items-center gap-2 text-white font-bold text-sm">
                <KeyRound className="w-4 h-4 text-nexus-yellow" /> Redefinir senha
              </h2>
              <button onClick={() => setModal(null)} className="p-1 text-slate-400 hover:text-white" aria-label="Fechar">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={confirmarSenha} className="space-y-4 mt-4">
              <p className="text-xs text-slate-400">
                Nova senha de <strong className="text-white">{nomeCompleto}</strong> ({ficha.email}). Informe a senha ao usuário por um canal seguro.
              </p>
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-slate-300">Nova senha *</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                  placeholder="Mínimo 6 caracteres"
                />
              </label>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
                <button type="button" onClick={() => setModal(null)} className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium">
                  Cancelar
                </button>
                <button type="submit" disabled={processando}
                  className="px-4 py-2 bg-nexus-yellow hover:bg-nexus-yellow-hover text-ink text-xs font-bold rounded-xl shadow flex items-center gap-1.5 disabled:opacity-60">
                  {processando && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Confirmar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modal === 'excluir' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div role="dialog" aria-modal="true" aria-labelledby="titulo-excluir"
            className="my-auto glass bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <h2 id="titulo-excluir" className="flex items-center gap-2 text-white font-bold text-sm pb-3 border-b border-slate-800">
              <Trash2 className="w-4 h-4 text-red-400" /> Excluir definitivamente
            </h2>
            <p className="text-xs text-slate-400 mt-4">
              <strong className="text-white">{nomeCompleto}</strong> ({ficha.email}) não tem histórico no sistema. A exclusão
              não pode ser desfeita e fica registrada na auditoria.
            </p>
            <div className="pt-4 flex items-center justify-end gap-2 border-t border-slate-800 mt-4">
              <button onClick={() => setModal(null)} className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium">
                Cancelar
              </button>
              <button onClick={() => void confirmarExclusao()} disabled={processando}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-on-accent text-xs font-bold rounded-xl shadow flex items-center gap-1.5 disabled:opacity-60">
                {processando && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Excluir definitivamente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
