import React, { useEffect, useState } from 'react';
import { CHAVE_AVISOS_SESSAO as CHAVE_SESSAO, useAuthStore } from '@/stores/authStore';
import { AvisoPopup, avisosApi } from '../api';
import { AvisoConteudo, LARGURAS } from './AvisoModal';

const vistosNaSessao = (): string[] => {
  try {
    return JSON.parse(sessionStorage.getItem(CHAVE_SESSAO) || '[]');
  } catch {
    return [];
  }
};

const marcarNaSessao = (id: string) => {
  try {
    sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify([...new Set([...vistosNaSessao(), id])]));
  } catch {
    /* armazenamento indisponível: o aviso pode reaparecer, sem prejuízo */
  }
};

/**
 * Fila de pop-ups de aviso exibida ao abrir a plataforma (montado no AppLayout).
 * Um aviso por vez; registra a visualização e, quando exigido, a confirmação de leitura.
 */
export const AvisosPopupHost: React.FC = () => {
  const { user, viaLicenca } = useAuthStore();
  const [fila, setFila] = useState<AvisoPopup[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const atual = fila[0];

  useEffect(() => {
    if (!user?.id || viaLicenca) return;
    let vivo = true;
    avisosApi
      .pendentes()
      .then((lista) => {
        const jaVistos = vistosNaSessao();
        if (vivo) setFila(lista.filter((a) => !jaVistos.includes(a.id)));
      })
      .catch(() => undefined);
    return () => {
      vivo = false;
    };
  }, [user?.id, viaLicenca]);

  useEffect(() => {
    if (atual) avisosApi.visualizado(atual.id).catch(() => undefined);
  }, [atual?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!atual) return null;

  const proximo = () => {
    marcarNaSessao(atual.id);
    setFila((f) => f.slice(1));
  };

  const confirmar = async () => {
    setOcupado(true);
    try {
      await avisosApi.confirmar(atual.id);
    } catch {
      /* registra de novo no próximo acesso */
    } finally {
      setOcupado(false);
      proximo();
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-3 pb-safe-4 sm:p-4" role="dialog" aria-modal="true"
      aria-label={atual.titulo}>
      <div className={`w-full ${LARGURAS[atual.largura]?.classe ?? 'max-w-2xl'}`}>
        <AvisoConteudo
          titulo={atual.titulo}
          conteudoHtml={atual.conteudo_html}
          midias={atual.midias}
          corDestaque={atual.cor_destaque}
          exigeConfirmacao={atual.exige_confirmacao}
          onFechar={proximo}
          onAdiar={proximo}
          onConfirmar={() => void confirmar()}
          ocupado={ocupado}
          contador={fila.length > 1 ? `Mais ${fila.length - 1} aviso${fila.length > 2 ? 's' : ''} a seguir` : undefined}
        />
      </div>
    </div>
  );
};
