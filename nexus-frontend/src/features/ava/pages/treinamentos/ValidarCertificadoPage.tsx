import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BadgeCheck, Loader2, Search, ShieldX } from 'lucide-react';
import { ValidacaoCertificado, treinamentosApi } from '../../treinamentosApi';

/** Página pública: confere a autenticidade de um certificado pelo código impresso nele. */
export const ValidarCertificadoPage: React.FC = () => {
  const { codigo = '' } = useParams();
  const navigate = useNavigate();
  const [digitado, setDigitado] = useState(codigo);
  const [resultado, setResultado] = useState<ValidacaoCertificado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!codigo) return;
    setCarregando(true);
    setErro(null);
    treinamentosApi
      .validar(codigo)
      .then(setResultado)
      .catch(() => setErro('Não foi possível consultar agora. Tente novamente em instantes.'))
      .finally(() => setCarregando(false));
  }, [codigo]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-nexus-page p-4 text-slate-100">
      <div className="w-full max-w-lg space-y-6 rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-widest text-nexus-yellow">NEXUS 2.0 · ETADEMP</p>
          <h1 className="mt-2 text-2xl font-extrabold text-white">Validação de certificado</h1>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); if (digitado.trim()) navigate(`/certificados/validar/${digitado.trim().toUpperCase()}`); }}
          className="flex gap-2">
          <input value={digitado} onChange={(e) => setDigitado(e.target.value)} placeholder="Código do certificado" maxLength={16}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 font-mono uppercase tracking-wider text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
          <button type="submit" className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
            <Search size={16} /> Validar
          </button>
        </form>

        {carregando && <div className="flex justify-center text-blue-400"><Loader2 className="animate-spin" /></div>}
        {erro && <p className="text-center text-sm text-amber-300">{erro}</p>}

        {resultado && !carregando && (
          resultado.valido ? (
            <div className="space-y-3 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5">
              <p className="flex items-center gap-2 font-bold text-emerald-300"><BadgeCheck size={20} /> Certificado autêntico</p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
                <dt className="text-slate-400">Nome</dt><dd className="font-semibold text-white">{resultado.nome}</dd>
                <dt className="text-slate-400">{resultado.categoria || 'Treinamento'}</dt><dd className="text-white">{resultado.treinamento}</dd>
                {resultado.carga_horaria ? <><dt className="text-slate-400">Carga horária</dt><dd className="text-white">{resultado.carga_horaria}h</dd></> : null}
                {resultado.concluido_em && <><dt className="text-slate-400">Concluído em</dt><dd className="text-white">{new Date(resultado.concluido_em).toLocaleDateString('pt-BR')}</dd></>}
                <dt className="text-slate-400">Código</dt><dd className="font-mono text-white">{resultado.codigo}</dd>
              </dl>
            </div>
          ) : (
            <p className="flex items-center gap-2 rounded-2xl border border-red-500/40 bg-red-500/10 p-5 text-sm font-semibold text-red-200">
              <ShieldX size={20} /> Nenhum certificado encontrado com o código {resultado.codigo}.
            </p>
          )
        )}
      </div>
    </div>
  );
};
