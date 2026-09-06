import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Lock, KeyRound, Eye, EyeOff, CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { redefinirSenhaSchema, RedefinirSenhaFormData } from '@/features/auth/schemas';
import { authApi } from '@/features/auth/api';

export const RedefinirSenhaPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const tokenParam = searchParams.get('token') || '';

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RedefinirSenhaFormData>({
    resolver: zodResolver(redefinirSenhaSchema),
    defaultValues: {
      token: tokenParam,
      nova_senha: '',
      confirmar_senha: '',
    },
  });

  useEffect(() => {
    if (tokenParam) {
      setValue('token', tokenParam);
    }
  }, [tokenParam, setValue]);

  const onSubmit = async (data: RedefinirSenhaFormData) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await authApi.redefinirSenha({
        token: data.token,
        nova_senha: data.nova_senha,
      });

      setSuccessMessage(
        response.message || 'Sua senha foi redefinida com sucesso! Você já pode entrar com a nova senha.'
      );
    } catch (err: any) {
      if (err.response?.status === 400) {
        setErrorMessage(
          err.response?.data?.detail || 'Token de recuperação inválido ou já utilizado/expirado.'
        );
      } else if (err.response?.data?.detail) {
        setErrorMessage(
          typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : 'Erro ao redefinir a senha.'
        );
      } else {
        setErrorMessage('Não foi possível conectar ao servidor. Tente novamente.');
      }
    }
  };

  return (
    <AuthLayout
      title="Criar Nova Senha"
      subtitle="Defina sua nova credencial de acesso segura para o NEXUS 2.0."
    >
      {successMessage ? (
        <div className="space-y-6 animate-fadeIn">
          <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="text-sm leading-relaxed">
              <p className="font-semibold text-emerald-300">Senha alterada com sucesso!</p>
              <p className="mt-1 text-xs text-emerald-200/90">{successMessage}</p>
            </div>
          </div>

          <button
            onClick={() => navigate('/auth/login')}
            className="w-full py-3 px-4 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-sm rounded-xl shadow-lg flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <span>Ir para o Login</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {errorMessage && (
            <div className="p-4 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 flex items-start gap-3 text-sm">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="leading-snug">{errorMessage}</div>
            </div>
          )}

          {/* Campo Token */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Token de Validação
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                type="text"
                placeholder="Cole o token recebido no e-mail"
                {...register('token')}
                disabled={isSubmitting}
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-950/70 border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all duration-200 ${
                  errors.token
                    ? 'border-red-500/70 focus:border-red-500 focus:ring-1 focus:ring-red-500/40'
                    : 'border-slate-800 focus:border-nexus-yellow focus:ring-1 focus:ring-nexus-yellow/30'
                }`}
              />
            </div>
            {errors.token && (
              <p className="text-xs text-red-400 mt-1 font-medium">{errors.token.message}</p>
            )}
          </div>

          {/* Campo Nova Senha */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Nova Senha
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Mínimo 6 caracteres"
                {...register('nova_senha')}
                disabled={isSubmitting}
                className={`w-full pl-10 pr-11 py-2.5 bg-slate-950/70 border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all duration-200 ${
                  errors.nova_senha
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
            {errors.nova_senha && (
              <p className="text-xs text-red-400 mt-1 font-medium">{errors.nova_senha.message}</p>
            )}
          </div>

          {/* Campo Confirmar Senha */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Confirmar Nova Senha
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="Repita a nova senha"
                {...register('confirmar_senha')}
                disabled={isSubmitting}
                className={`w-full pl-10 pr-11 py-2.5 bg-slate-950/70 border rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all duration-200 ${
                  errors.confirmar_senha
                    ? 'border-red-500/70 focus:border-red-500 focus:ring-1 focus:ring-red-500/40'
                    : 'border-slate-800 focus:border-nexus-yellow focus:ring-1 focus:ring-nexus-yellow/30'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                tabIndex={-1}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.confirmar_senha && (
              <p className="text-xs text-red-400 mt-1 font-medium">
                {errors.confirmar_senha.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all duration-200 transform active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer mt-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Atualizando senha com Argon2id...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>Salvar Nova Senha</span>
              </>
            )}
          </button>

          <div className="pt-2 text-center">
            <Link
              to="/auth/login"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors font-medium"
            >
              Voltar para a tela de login
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
