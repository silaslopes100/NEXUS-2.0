import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { avaliacoesApi } from '@/features/avaliacoes/api';
import { RealizarAvaliacao } from '@/features/avaliacoes/components/RealizarAvaliacao';

/** Prova online do aluno de Polo/Escola (licença ativa). O aluno EAD faz a avaliação dentro do AVA. */
export const RealizarAvaliacaoPage: React.FC = () => {
  const { avaliacaoId = '' } = useParams();
  const navigate = useNavigate();
  return (
    <RealizarAvaliacao
      chave={avaliacaoId}
      iniciar={() => avaliacoesApi.iniciar(avaliacaoId)}
      rotuloVoltar="Voltar às disciplinas"
      onVoltar={() => navigate('/aluno/disciplinas')}
    />
  );
};
