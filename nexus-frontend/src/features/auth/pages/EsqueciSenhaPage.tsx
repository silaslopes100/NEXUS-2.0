import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle2, AlertCircle, Loader2, Send } from 'lucide-react';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { esqueciSenhaSchema, EsqueciSenhaFormData } from '@/features/auth/schemas';
import { authApi } from '@/features/auth/api';

export const EsqueciSenhaPage: React.FC = () => {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sentEmail, setSentEmail] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EsqueciSenhaFormData>({
    resolver: zodResolver(esqueciSenhaSchema),
    defaultValues: {
      email: '',
    },
  });

  const onSubmit = async (data: EsqueciSenhaFormData) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await authApi.esqueciSenha({ email: data.email });
      setSentEmail(data.email);
      setSuccessMessage(
        response.message ||
          'Se o e-mail estiver cadastrado, as instruções e o código de redefinição foram enviados.'
      );
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail ||
          'Ocorreu um erro ao processar a solicitação. Tente novamente em instantes.'
      );
    }
  };

  return (
    <AuthLayout
      title="Recuperação de Senha"
      subtitle="Informe o e-mail cadastrado para receber as instruções de redefinição."
    >
      {successMessage ? (
        <div className="space-y-6 animate-fadeIn text-center sm:text-left">
          <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="text-sm leading-relaxed">
              <p className="font-semibold text-emerald-300">E-mail enviado com sucesso!</p>
              <p className="mt-1 text-xs text-emerald-200/90">
                Enviamos o código de validação para <strong className="text-white">{sentEmail}</strong>.
                Verifique sua caixa de entrada e spam.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 space-y-2">
            <p>
              💡 <strong>Já está com o token em mãos?</strong>
            </p>
            <p>
              Clique no botão abaixo para prosseguir com a definição da sua nova senha de acesso.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              to="/auth/redefinir-senha"
              className="flex-1 py-2.5 px-4 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-sm rounded-xl text-center shadow-lg transition-colors"
            >
              Inserir Código e Redefinir Senha
            </Link>
            <Link
              to="/auth/login"
              className="py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm rounded-xl text-center border border-slate-700 transition-colors flex items-center justify-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              Voltar ao Login
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          {errorMessage && (
            <div className="p-4 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 flex items-start gap-3 text-sm">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="leading-snug">{errorMessage}</div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              E-mail Cadastrado
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

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all duration-200 transform active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Enviando instruções...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Enviar Link de Recuperação</span>
              </>
            )}
          </button>

          <div className="pt-2 text-center">
            <Link
              to="/auth/login"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Lembrou sua senha? Voltar para o Login
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
