import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail, AlertCircle, Loader2, LogIn, ShieldAlert, KeyRound, ArrowLeft } from 'lucide-react';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { loginSchema, LoginFormData } from '@/features/auth/schemas';
import { authApi } from '@/features/auth/api';
import { dashboardDoPerfil, normalizeUserRole, useAuthStore } from '@/stores/authStore';

// Áreas exclusivas de um perfil (/admin/..., /polo/... etc.). As demais rotas (feed, chat, treinamentos...)
// são compartilhadas.
const PREFIXOS_DE_PERFIL = ['admin', 'polo', 'escola', 'professor', 'aluno', 'financeiro', 'logistica'];

/**
 * A rota guardada antes do login (state.from) serve para o perfil que entrou?
 * Evita mandar o novo usuário para a tela do usuário anterior (ex.: Polo caindo em /admin → "Acesso Não Autorizado").
 */
const rotaDoPerfil = (rota: string, perfil: string, tambemAluno: boolean): boolean => {
  const prefixo = rota.split('/')[1] || '';
  if (!PREFIXOS_DE_PERFIL.includes(prefixo)) return true;
  return prefixo === perfil || (prefixo === 'aluno' && tambemAluno);
};

/** "nx 2a3b c4d5" -> "NX-2A3B-C4D5" enquanto o aluno digita. */
const mascararLicenca = (valor: string): string => {
  let limpo = valor.toUpperCase().replace(/[^0-9A-Z]/g, '');
  if (limpo.startsWith('NX')) limpo = limpo.slice(2);
  limpo = limpo.slice(0, 8);
  const partes = [limpo.slice(0, 4), limpo.slice(4, 8)].filter(Boolean);
  return ['NX', ...partes].join('-');
};

const LoginLicenca: React.FC<{ onVoltar: () => void }> = ({ onVoltar }) => {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const setViaLicenca = useAuthStore((state) => state.setViaLicenca);
  const [numero, setNumero] = useState('NX-');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const completo = /^NX-[0-9A-Z]{4}-[0-9A-Z]{4}$/.test(numero);

  const entrar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completo) {
      setErro('Digite os 8 caracteres do número que está no seu cartão.');
      return;
    }
    setErro(null);
    setEnviando(true);
    try {
      const r = await authApi.loginLicenca(numero);
      setSession(r.access_token, r.refresh_token, r.usuario, r.perfil || r.usuario.perfil, r.permissoes || []);
      setViaLicenca(true);
      const disciplina = r.destino?.disciplina_id;
      navigate(disciplina ? `/aluno/disciplinas?disciplina=${disciplina}` : '/aluno/disciplinas', { replace: true });
    } catch (err: any) {
      const status = err.response?.status;
      const detalhe = err.response?.data?.detail;
      setErro(
        status === 429
          ? typeof detalhe === 'string' ? detalhe : 'Muitas tentativas. Aguarde 15 minutos e tente de novo.'
          : status === 401
            ? 'Número de licença não encontrado ou inativo. Confira o cartão.'
            : typeof detalhe === 'string' ? detalhe : 'Não foi possível conectar ao servidor.'
      );
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={entrar} className="space-y-5" noValidate>
      {erro && (
        <div className="p-4 rounded-xl flex items-start gap-3 text-sm bg-amber-500/15 border border-amber-500/30 text-amber-200">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="leading-snug">{erro}</div>
        </div>
      )}
      <div className="space-y-1.5">
        <label htmlFor="numero-licenca" className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
          Número da licença
        </label>
        <p className="text-sm text-slate-400">Digite o número do seu cartão de acesso.</p>
        <input
          id="numero-licenca"
          autoFocus
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          value={numero}
          disabled={enviando}
          onChange={(e) => setNumero(mascararLicenca(e.target.value))}
          placeholder="NX-____-____"
          className="w-full px-4 py-4 bg-slate-950/70 border border-slate-800 rounded-xl text-center font-mono text-2xl tracking-[0.2em] text-white placeholder-slate-600 focus:outline-none focus:border-nexus-yellow focus:ring-1 focus:ring-nexus-yellow/30"
        />
      </div>
      <button
        type="submit"
        disabled={enviando}
        className="w-full py-3.5 px-4 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 text-ink font-bold rounded-xl flex items-center justify-center gap-2 disabled:opacity-60"
      >
        {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
        {enviando ? 'Entrando...' : 'Entrar'}
      </button>
      <button
        type="button"
        onClick={onVoltar}
        className="w-full flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white"
      >
        <ArrowLeft className="w-4 h-4" /> Entrar com e-mail e senha
      </button>
    </form>
  );
};

export const LoginPage: React.FC = () => {
  const [modoLicenca, setModoLicenca] = useState(false);
  if (modoLicenca) {
    return (
      <AuthLayout title="Sou aluno" subtitle="Entre com o número da licença para fazer sua avaliação.">
        <LoginLicenca onVoltar={() => setModoLicenca(false)} />
      </AuthLayout>
    );
  }
  return <LoginEmailSenha onLicenca={() => setModoLicenca(true)} />;
};

const LoginEmailSenha: React.FC<{ onLicenca: () => void }> = ({ onLicenca }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);

  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBlocked, setIsBlocked] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      senha: '',
      lembrarEmail: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setErrorMessage(null);
    setIsBlocked(false);

    try {
      // 1. Efetua login na API
      const response = await authApi.login({
        email: data.email,
        senha: data.senha,
      });

      // 2. Armazena sessão no Zustand authStore (em memória)
      setSession(
        response.access_token,
        response.refresh_token,
        response.usuario,
        response.perfil || response.usuario.perfil,
        response.permissoes || response.usuario.permissoes
      );

      // 3. Tenta obter dados detalhados via /auth/me se necessário
      let userRole = (response.perfil?.nome || response.usuario.perfil?.nome || '').toLowerCase().trim();
      try {
        const meData = await authApi.getMe();
        if (meData.perfil?.nome) {
          userRole = meData.perfil.nome.toLowerCase().trim();
        }
      } catch (meErr) {
        // Usa o perfil retornado no payload de login caso getMe falhe
      }

      // 4. Redireciona para rota anterior solicitada ou dashboard específico do perfil
      const from = (location.state as { from?: { pathname?: string } })?.from?.pathname;
      if (from && !from.startsWith('/auth') && rotaDoPerfil(from, normalizeUserRole(userRole) || userRole, !!response.usuario.tambem_aluno)) {
        navigate(from, { replace: true });
        return;
      }

      // Mesma regra do authStore (inclui financeiro e logística).
      // Perfil não mapeado mantém o comportamento anterior (/admin/dashboard, que mostra o acesso negado).
      const destino = dashboardDoPerfil(userRole);
      navigate(destino === '/auth/login' ? '/admin/dashboard' : destino, { replace: true });
    } catch (err: any) {
      if (err.response?.status === 429) {
        setIsBlocked(true);
        setErrorMessage(
          err.response?.data?.detail ||
            'Muitas tentativas incorretas. Conta bloqueada temporariamente por 15 minutos.'
        );
      } else if (err.response?.status === 401) {
        setErrorMessage('E-mail ou senha incorretos. Verifique os dados informados.');
      } else if (err.response?.data?.detail) {
        setErrorMessage(
          typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : 'Erro ao autenticar. Tente novamente.'
        );
      } else {
        setErrorMessage('Não foi possível conectar ao servidor. Verifique sua conexão.');
      }
    }
  };

  return (
    <AuthLayout
      title="Acesse sua conta"
      subtitle="Insira suas credenciais para acessar a plataforma NEXUS 2.0."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {/* Banner de Erro ou Bloqueio */}
        {errorMessage && (
          <div
            className={`p-4 rounded-xl flex items-start gap-3 text-sm animate-fadeIn ${
              isBlocked
                ? 'bg-red-500/15 border border-red-500/30 text-red-300'
                : 'bg-amber-500/15 border border-amber-500/30 text-amber-200'
            }`}
          >
            {isBlocked ? (
              <ShieldAlert className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            )}
            <div className="leading-snug">{errorMessage}</div>
          </div>
        )}

        {/* Campo E-mail */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            E-mail de Acesso
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Mail className="w-4 h-4" />
            </div>
            <input
              type="email"
              placeholder="seu.email@exemplo.com"
              {...register('email')}
              disabled={isSubmitting}
              className={`w-full pl-10 pr-4 py-2.5 bg-slate-950/70 border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all duration-200 ${
                errors.email
                  ? 'border-red-500/70 focus:border-red-500 focus:ring-1 focus:ring-red-500/40'
                  : 'border-slate-800 focus:border-nexus-yellow focus:ring-1 focus:ring-nexus-yellow/30'
              }`}
            />
          </div>
          {errors.email && (
            <p className="text-xs text-red-400 mt-1 font-medium">{errors.email.message}</p>
          )}
        </div>

        {/* Campo Senha */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Senha
            </label>
            <Link
              to="/auth/esqueci-senha"
              className="text-xs text-nexus-yellow hover:text-nexus-yellow-hover transition-colors font-medium"
            >
              Esqueceu a senha?
            </Link>
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Lock className="w-4 h-4" />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              {...register('senha')}
              disabled={isSubmitting}
              className={`w-full pl-10 pr-11 py-2.5 bg-slate-950/70 border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all duration-200 ${
                errors.senha
                  ? 'border-red-500/70 focus:border-red-500 focus:ring-1 focus:ring-red-500/40'
                  : 'border-slate-800 focus:border-nexus-yellow focus:ring-1 focus:ring-nexus-yellow/30'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
              className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.senha && (
            <p className="text-xs text-red-400 mt-1 font-medium">{errors.senha.message}</p>
          )}
        </div>

        {/* Botão de Submissão */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-3 px-4 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-ink font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all duration-200 transform active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Autenticando no NEXUS 2.0...</span>
            </>
          ) : (
            <>
              <LogIn className="w-4 h-4" />
              <span>Entrar na Plataforma</span>
            </>
          )}
        </button>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="h-px flex-1 bg-slate-800" /> ou <span className="h-px flex-1 bg-slate-800" />
        </div>
        <button
          type="button"
          onClick={onLicenca}
          className="w-full py-3.5 px-4 border border-nexus-yellow/40 text-nexus-yellow font-bold text-sm rounded-xl flex items-center justify-center gap-2 hover:bg-nexus-yellow/10"
        >
          <KeyRound className="w-4 h-4" />
          Entrar com número da licença
        </button>

        <p className="text-center text-sm text-slate-400">
          Ainda não é aluno?{' '}
          <Link to="/matricula-ead" className="font-semibold text-nexus-yellow hover:text-nexus-yellow-hover">
            Quero me matricular no EAD
          </Link>
        </p>

        <div className="pt-2 text-center text-xs text-slate-500">
          Protegido com tecnologia Argon2id e controle ativo de sessões.
        </div>
      </form>
    </AuthLayout>
  );
};
