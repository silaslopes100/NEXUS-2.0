import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  X,
  CheckCircle2,
  Edit2,
  KeyRound,
  Trash2,
  Mail,
  Phone,
  Smartphone,
  CreditCard,
  MapPin,
  Building2,
  Clock,
  CalendarDays,
  GraduationCap,
  BookOpen,
  Award,
  ClipboardCheck,
  Users as UsersIcon,
  RefreshCw,
  Fingerprint,
  BarChart3,
  Shield,
  Camera,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { UsuarioFicha, ResumoMetricasUsuario } from '@/types/admin';
import { UsuarioFormModal } from '@/features/admin/components/UsuarioFormModal';
import { UsuarioAvatar } from '@/features/admin/components/UsuarioAvatar';
import { useAuthStore } from '@/stores/authStore';

function formatarData(iso?: string | null, comHora = false): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return comHora
    ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('pt-BR');
}

function mensagemErro(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === 'string') return response.data.detail;
  }
  return fallback;
}

function valorMetrica(value?: number | null): number | string {
  return value ?? '—';
}

function formatarTelefone(value?: string | null): string {
  if (!value) return '—';
  const digits = value.replace(/\D/g, '');
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }
  return value;
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'ativo':
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    case 'inativo':
      return 'bg-slate-800 text-slate-400 border-slate-700';
    case 'bloqueado':
      return 'bg-red-500/15 text-red-400 border-red-500/30';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
};

const DadoItem: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({
  icon,
  label,
  value,
}) => (
  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
    <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1 mb-1">
      {icon}
      {label}
    </p>
    <p className="text-xs font-semibold text-white">{value}</p>
  </div>
);

const MetricaCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  accent?: string;
}> = ({ icon, label, value, accent = 'text-nexus-yellow' }) => (
  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center gap-3">
    <div className={`p-2.5 rounded-lg bg-slate-900 border border-slate-800 ${accent}`}>{icon}</div>
    <div>
      <p className="text-lg font-extrabold text-white leading-none">{value}</p>
      <p className="text-[11px] text-slate-400 mt-1">{label}</p>
    </div>
  </div>
);

export const UsuarioFichaPage: React.FC = () => {
  const { usuarioId } = useParams<{ usuarioId: string }>();
  const navigate = useNavigate();
  const { user: loggedAdmin } = useAuthStore();

  const [ficha, setFicha] = useState<UsuarioFicha | null>(null);
  const [resumo, setResumo] = useState<ResumoMetricasUsuario | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resumoError, setResumoError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [fotoObjectUrl, setFotoObjectUrl] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!usuarioId) return;
    setIsLoading(true);
    setError(null);
    setResumoError(null);
    try {
      const [fichaResult, resumoResult] = await Promise.allSettled([
        adminApi.getUsuarioFicha(usuarioId),
        adminApi.getResumoUsuario(usuarioId),
      ]);

      if (fichaResult.status === 'rejected') throw fichaResult.reason;
      setFicha(fichaResult.value);

      if (resumoResult.status === 'fulfilled') {
        setResumo(resumoResult.value);
      } else {
        setResumo(null);
        setResumoError(mensagemErro(resumoResult.reason, 'Não foi possível carregar as métricas do usuário.'));
      }

    } catch (err: any) {
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
    const adminPhotoUrl = `/admin/usuarios/${ficha.id}/foto`;
    const storedAdminUrl = ficha.foto_url?.startsWith(adminPhotoUrl) || storedFilename;
    if (!storedAdminUrl) {
      setFotoObjectUrl(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    void adminApi.getUsuarioFoto(ficha.id).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      if (cancelled) {
        URL.revokeObjectURL(objectUrl);
      } else {
        setFotoObjectUrl(objectUrl);
      }
    }).catch((err: unknown) => {
      if (!cancelled) {
        setFotoObjectUrl(null);
        setFeedback({
          type: 'error',
          message: mensagemErro(err, 'Não foi possível carregar a foto do usuário.'),
        });
      }
    });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [ficha?.id, ficha?.foto_url]);

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
      setFicha((atual) => atual ? { ...atual, foto_url: resultado.foto_url } : atual);
      setFeedback({ type: 'success', message: 'Foto atualizada para o usuário e o aluno.' });
    } catch (err: unknown) {
      setFeedback({ type: 'error', message: mensagemErro(err, 'Não foi possível atualizar a foto.') });
    }
  };

  const handleConfirmResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ficha || newPassword.length < 6) {
      setFeedback({ type: 'error', message: 'A nova senha deve ter no mínimo 6 caracteres.' });
      return;
    }
    try {
      await adminApi.resetUsuarioSenha(ficha.id, newPassword);
      setFeedback({ type: 'success', message: 'Senha redefinida com sucesso (Argon2id).' });
      setIsResetPasswordOpen(false);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Erro ao redefinir a senha.' });
    }
  };

  const handleConfirmDelete = async () => {
    if (!ficha) return;
    try {
      await adminApi.deleteUsuario(ficha.id);
      setFeedback({ type: 'success', message: `Usuário ${ficha.nome} excluído com sucesso.` });
      setIsDeleteConfirmOpen(false);
      setTimeout(() => navigate('/admin/usuarios'), 800);
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Erro ao excluir usuário.' });
      setIsDeleteConfirmOpen(false);
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
          onClick={() => navigate('/admin/usuarios')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
        >
          Voltar para a lista
        </button>
      </div>
    );
  }

  const nomeCompleto = `${ficha.nome} ${ficha.sobrenome || ''}`.trim();
  const resumoAluno = resumo?.aluno;
  const resumoProfessor = resumo?.professor;
  const resumoUnidade = resumo?.unidade;
  const temVinculoUnidade = Boolean(
    ficha.polo_id
    || ficha.escola_id
    || ficha.aluno?.polo_id
    || ficha.aluno?.escola_id
    || ficha.professor?.polo_id
    || ficha.professor?.escola_id
  );

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-sm animate-fadeIn ${
            feedback.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
              : 'bg-red-500/15 border-red-500/30 text-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {resumoError && (
        <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          Não foi possível carregar as métricas do usuário. Os valores indisponíveis aparecem como “—”. {resumoError}
        </div>
      )}

      {/* Header da Ficha */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl">
        <button
          onClick={() => navigate('/admin/usuarios')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-nexus-yellow transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Voltar para a consulta
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="relative shrink-0">
              {fotoObjectUrl ? (
                <img
                  src={fotoObjectUrl}
                  alt={nomeCompleto}
                  className="w-16 h-16 rounded-2xl object-cover border border-slate-700"
                />
              ) : (
                <UsuarioAvatar
                  fotoUrl={ficha.foto_url}
                  nome={nomeCompleto}
                  className="w-16 h-16 rounded-2xl object-cover border border-slate-700 text-xl"
                />
              )}
              <label
                htmlFor="usuario-foto-upload"
                title="Alterar foto do usuário"
                className="absolute -bottom-2 -right-2 p-1.5 rounded-full bg-nexus-yellow text-slate-950 cursor-pointer shadow-lg hover:bg-yellow-300"
              >
                <Camera className="w-3.5 h-3.5" />
                <span className="sr-only">Alterar foto do usuário</span>
              </label>
              <input
                id="usuario-foto-upload"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleUploadFoto}
              />
            </div>
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-yellow/15 border border-nexus-yellow/30 text-nexus-yellow text-[10px] font-bold uppercase tracking-wider mb-1.5">
                <Fingerprint className="w-3 h-3" />
                Ficha Cadastral
              </div>
              <h1 className="text-2xl font-extrabold text-white tracking-tight">{nomeCompleto}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-nexus-blue/15 border border-nexus-blue/30 text-blue-400">
                  <Shield className="w-3 h-3" />
                  {ficha.perfil_nome || 'Sem perfil'}
                </span>
                <span
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${getStatusBadge(ficha.status)}`}
                >
                  {ficha.status}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsFormOpen(true)}
              className="px-4 py-2.5 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl shadow-lg transition-colors flex items-center gap-1.5"
            >
              <Edit2 className="w-3.5 h-3.5" />
              Editar
            </button>
            <button
              onClick={() => {
                setNewPassword('');
                setIsResetPasswordOpen(true);
              }}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors flex items-center gap-1.5"
            >
              <KeyRound className="w-3.5 h-3.5" />
              Redefinir Senha
            </button>
            {loggedAdmin?.id !== ficha.id && (
              <button
                onClick={() => setIsDeleteConfirmOpen(true)}
                className="px-4 py-2.5 bg-slate-800 hover:bg-red-500/15 text-slate-300 hover:text-red-400 font-semibold text-xs rounded-xl transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Excluir
              </button>
            )}
            <button
              onClick={() => void loadAll()}
              className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
              title="Recarregar"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Identificação & Dados Cadastrais */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-6">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-4">
          <CreditCard className="w-4 h-4 text-nexus-yellow" />
          Identificação & Dados Cadastrais
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <DadoItem icon={<Mail className="w-3 h-3" />} label="E-mail" value={ficha.email || '—'} />
          <DadoItem icon={<CreditCard className="w-3 h-3" />} label="CPF" value={ficha.cpf || '—'} />
          <DadoItem icon={<Phone className="w-3 h-3" />} label="Telefone" value={formatarTelefone(ficha.telefone)} />
          <DadoItem icon={<Smartphone className="w-3 h-3" />} label="Celular" value={formatarTelefone(ficha.celular)} />
          <DadoItem
            icon={<MapPin className="w-3 h-3" />}
            label="Polo"
            value={ficha.polo_nome || '—'}
          />
          <DadoItem
            icon={<Building2 className="w-3 h-3" />}
            label="Escola"
            value={ficha.escola_nome || '—'}
          />
          <DadoItem
            icon={<Clock className="w-3 h-3" />}
            label="Último Acesso"
            value={formatarData(ficha.ultimo_login_em, true)}
          />
          <DadoItem
            icon={<CalendarDays className="w-3 h-3" />}
            label="Data de Cadastro"
            value={formatarData(ficha.criado_em)}
          />
        </div>
      </div>

      {/* Painéis por perfil */}
      {/* Aluno */}
      {ficha.aluno && (
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-6">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-4">
            <GraduationCap className="w-4 h-4 text-nexus-yellow" />
            Vínculo de Aluno
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <DadoItem
              icon={<CreditCard className="w-3 h-3" />}
              label="Nº de Matrícula"
              value={ficha.aluno.numero_matricula || '—'}
            />
            <DadoItem
              icon={<BookOpen className="w-3 h-3" />}
              label="Modalidade"
              value={ficha.aluno.modalidade || '—'}
            />
            <DadoItem
              icon={<CalendarDays className="w-3 h-3" />}
              label="Data de Nascimento"
              value={formatarData(ficha.aluno.data_nascimento)}
            />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricaCard
              icon={<BookOpen className="w-4 h-4" />}
              label="Matrículas EAD"
              value={valorMetrica(resumoAluno?.matriculas_total)}
            />
            <MetricaCard
              icon={<BarChart3 className="w-4 h-4" />}
              label={
                resumoAluno?.media_notas != null
                  ? `Média de Notas (${resumoAluno.total_notas} avaliações)`
                  : 'Média de Notas'
              }
              value={resumoAluno?.media_notas != null ? resumoAluno.media_notas.toFixed(1) : '—'}
              accent="text-blue-400"
            />
            <MetricaCard
              icon={<ClipboardCheck className="w-4 h-4" />}
              label={
                resumoAluno?.percentual_presenca != null
                  ? `Presença (${resumoAluno.presencas_positivas}/${resumoAluno.total_presencas})`
                  : 'Presença'
              }
              value={
                resumoAluno?.percentual_presenca != null
                  ? `${resumoAluno.percentual_presenca}%`
                  : '—'
              }
              accent="text-emerald-400"
            />
            <MetricaCard
              icon={<Award className="w-4 h-4" />}
              label="Certificados"
              value={valorMetrica(resumoAluno?.certificados_total)}
              accent="text-amber-400"
            />
          </div>
        </div>
      )}

      {/* Professor */}
      {ficha.professor && (
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-6">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-4">
            <BookOpen className="w-4 h-4 text-nexus-yellow" />
            Vínculo de Professor
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <DadoItem
              icon={<BookOpen className="w-3 h-3" />}
              label="Matérias"
              value={
                ficha.professor.materias.length > 0
                  ? ficha.professor.materias.join(', ')
                  : '—'
              }
            />
            <DadoItem
              icon={<CalendarDays className="w-3 h-3" />}
              label="Início das Aulas"
              value={formatarData(ficha.professor.data_inicio)}
            />
            <DadoItem
              icon={<Clock className="w-3 h-3" />}
              label="Aulas / Horas Contratadas"
              value={`${ficha.professor.quantidade_aulas} aulas · ${
                ficha.professor.horas_totais != null ? `${ficha.professor.horas_totais}h` : '—'
              }`}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <MetricaCard
              icon={<ClipboardCheck className="w-4 h-4" />}
              label="Aulas Registradas"
              value={valorMetrica(resumoProfessor?.aulas_registradas)}
            />
            <MetricaCard
              icon={<Award className="w-4 h-4" />}
              label="Treinamentos"
              value={valorMetrica(resumoProfessor?.treinamentos_total)}
              accent="text-blue-400"
            />
          </div>
        </div>
      )}

      {/* Unidade (Polo/Escola) */}
      {temVinculoUnidade && (
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-6">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-4">
            <UsersIcon className="w-4 h-4 text-nexus-yellow" />
            Resumo da Unidade ({ficha.polo_nome || ficha.escola_nome || '—'})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <MetricaCard icon={<Building2 className="w-4 h-4" />} label="Escolas" value={valorMetrica(resumoUnidade?.escolas)} />
            <MetricaCard icon={<UsersIcon className="w-4 h-4" />} label="Alunos Ativos" value={valorMetrica(resumoUnidade?.alunos)} accent="text-blue-400" />
            <MetricaCard icon={<BookOpen className="w-4 h-4" />} label="Professores" value={valorMetrica(resumoUnidade?.professores)} accent="text-emerald-400" />
            <MetricaCard icon={<ClipboardCheck className="w-4 h-4" />} label="Aulas" value={valorMetrica(resumoUnidade?.aulas)} accent="text-amber-400" />
            <MetricaCard icon={<GraduationCap className="w-4 h-4" />} label="Turmas" value={valorMetrica(resumoUnidade?.turmas)} accent="text-purple-400" />
          </div>
        </div>
      )}

      {/* Modal de Edição */}
      <UsuarioFormModal
        open={isFormOpen}
        editingUser={ficha}
        onClose={() => setIsFormOpen(false)}
        onSaved={(message) => {
          setFeedback({ type: 'success', message });
          void loadAll();
        }}
      />

      {/* Modal Redefinir Senha */}
      {isResetPasswordOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-white font-bold text-sm">
                <KeyRound className="w-4 h-4 text-nexus-yellow" />
                <span>Redefinir Senha</span>
              </div>
              <button onClick={() => setIsResetPasswordOpen(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleConfirmResetPassword} className="space-y-4 mt-4">
              <p className="text-xs text-slate-400">
                Alterando a senha de <strong>{nomeCompleto}</strong> ({ficha.email}). A nova senha
                será criptografada em <strong>Argon2id</strong>.
              </p>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Nova Senha *</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                  placeholder="Mínimo 6 caracteres"
                />
              </div>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsResetPasswordOpen(false)}
                  className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 text-xs font-bold rounded-xl shadow transition-colors cursor-pointer"
                >
                  Confirmar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Confirmar Exclusão */}
      {isDeleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <div className="flex items-center gap-2 text-white font-bold text-sm pb-3 border-b border-slate-800">
              <Trash2 className="w-4 h-4 text-red-400" />
              <span>Confirmar Exclusão</span>
            </div>
            <p className="text-xs text-slate-400 mt-4">
              Tem certeza que deseja excluir o usuário{' '}
              <strong className="text-white">{nomeCompleto}</strong> ({ficha.email})? Esta ação será
              registrada em auditoria.
            </p>
            <div className="pt-4 flex items-center justify-end gap-2 border-t border-slate-800 mt-4">
              <button
                onClick={() => setIsDeleteConfirmOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-bold rounded-xl shadow transition-colors cursor-pointer"
              >
                Excluir Definitivamente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
