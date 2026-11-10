import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { ModulePlaceholderPage } from '@/pages/dashboard/ModulePlaceholderPage';
import { useAuthStore } from '@/stores/authStore';

const WHATSAPP_URL = 'https://wa.me/551119366880';

export const ComprasEadPage: React.FC = () => {
  const { user } = useAuthStore();
  const [aberto, setAberto] = useState(!!user?.aluno_desistente);

  return (
    <>
      <ModulePlaceholderPage />
      {aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="regularizacao-titulo"
            className="w-full max-w-md space-y-4 rounded-2xl border border-amber-500/30 bg-slate-900 p-6 text-center shadow-2xl"
          >
            <AlertTriangle className="mx-auto text-amber-300" size={32} />
            <h2 id="regularizacao-titulo" className="text-lg font-bold text-white">
              Regularize sua situação
            </h2>
            <p className="text-sm text-slate-300">
              Você já tem cadastro, mas precisa regularizar sua situação, entre em contato conosco
              pelo WhatsApp (11)1936-6880
            </p>
            <div className="flex flex-col-reverse justify-center gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => setAberto(false)}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-slate-800"
              >
                Fechar
              </button>
              <a
                href={WHATSAPP_URL}
                target="_blank"
                rel="noreferrer"
                className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                Abrir WhatsApp
              </a>
            </div>
          </section>
        </div>
      )}
    </>
  );
};
