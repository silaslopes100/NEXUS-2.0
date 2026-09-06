import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail, AlertCircle, Loader2, LogIn, ShieldAlert } from 'lucide-react';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { loginSchema, LoginFormData } from '@/features/auth/schemas';
import { authApi } from '@/features/auth/api';
import { useAuthStore } from '@/stores/authStore';

export const LoginPage: React.FC = () => {
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
      if (from && !from.startsWith('/auth')) {
        navigate(from, { replace: true });
        return;
      }

      switch (userRole) {
        case 'admin':
          navigate('/admin/dashboard', { replace: true });
          break;
        case 'polo':
          navigate('/polo/dashboard', { replace: true });
          break;
        case 'escola':
          navigate('/escola/dashboard', { replace: true });
          break;
        case 'professor':
          navigate('/professor/dashboard', { replace: true });
          break;
        case 'aluno':
          navigate('/aluno/dashboard', { replace: true });
          break;
        default:
          navigate('/admin/dashboard', { replace: true });
          break;
      }
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
          className="w-full py-3 px-4 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all duration-200 transform active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
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

        <div className="pt-2 text-center text-xs text-slate-500">
          Protegido com tecnologia Argon2id e controle ativo de sessões.
        </div>
      </form>
    </AuthLayout>
  );
};
