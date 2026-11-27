import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, ArrowLeftRight, BookOpen, Building2, CalendarDays, CreditCard, Eye, FileText,
  GraduationCap, Loader2, MapPin, RefreshCw,
} from 'lucide-react';
import { UserAvatar } from '@/components/avatar/UserAvatar';
import { alunosGestaoApi } from '@/features/alunos/api';
import { BoletimModal } from '@/features/alunos/components/BoletimModal';
import { DadoItem, SecaoEditavel } from '@/features/admin/components/ficha/SecaoEditavel';
import { SecoesPessoais } from '@/features/admin/components/ficha/SecoesPessoais';
import {
  MODALIDADE, formatarData, mensagemErro, rotuloStatus, statusBadge, vazio,
} from '@/features/admin/components/ficha/fichaUtils';
import { tipoLabel, TipoTransferencia } from '@/features/transferencias/api';
import { UsuarioFicha } from '@/types/admin';

type VoltarPara = { to: string; rotulo: string };

/** Destino do "Voltar": a lista de Alunos informa via state; sem ela, volta para a lista da área. */
const voltarDoEstado = (state: unknown, padrao: VoltarPara): VoltarPara => {
  const voltar = (state as { voltar?: Partial<VoltarPara> } | null)?.voltar;
  return voltar && typeof voltar.to === 'string' && voltar.to.startsWith('/') && typeof voltar.rotulo === 'string'
    ? { to: voltar.to, rotulo: voltar.rotulo }
    : padrao;
};

const SecaoVinculoAluno: React.FC<{ ficha: UsuarioFicha }> = ({ ficha }) => {
  const aluno = ficha.aluno!;
  const pendente = aluno.transferencia_pendente;
  return (
    <SecaoEditavel
      titulo="Vínculo de aluno"
      icone={<GraduationCap className="w-4 h-4" />}
      aviso={
        pendente ? (
          <p role="status" className="mb-4 flex items-start gap-2 text-xs text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
            <ArrowLeftRight className="w-4 h-4 shrink-0" />
            <span>
              Transferência pendente: <strong>{tipoLabel[pendente.tipo as TipoTransferencia] ?? pendente.tipo}</strong>
              {pendente.escola_destino_nome || pendente.polo_destino_nome
                ? ` para ${[pendente.polo_destino_nome, pendente.escola_destino_nome].filter(Boolean).join(' · ')}`
                : ''}
              {pendente.criado_em ? `, aberta em ${formatarData(pendente.criado_em)}` : ''}.
            </span>
          </p>
        ) : null
      }
      leitura={
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <DadoItem icon={<CreditCard className="w-3 h-3" />} label="Nº de matrícula" value={vazio(aluno.numero_matricula)} />
          <DadoItem icon={<BookOpen className="w-3 h-3" />} label="Modalidade" value={aluno.modalidade ? MODALIDADE[aluno.modalidade] ?? aluno.modalidade : '—'} />
          <DadoItem label="Situação" value={
            <span className={`px-2 py-0.5 rounded-full text-[11px] border ${statusBadge(aluno.status)}`}>{rotuloStatus(aluno.status)}</span>
          } />
          <DadoItem icon={<CalendarDays className="w-3 h-3" />} label="Nascimento" value={formatarData(aluno.data_nascimento || ficha.dados.data_nascimento)} />
          <DadoItem icon={<MapPin className="w-3 h-3" />} label="Polo" value={vazio(aluno.polo_nome)} />
          <DadoItem icon={<Building2 className="w-3 h-3" />} label="Escola" value={vazio(aluno.escola_nome)} />
        </div>
      }
    />
  );
};

/**
 * Ficha cadastral do aluno vista por Polo e Escola: somente leitura e restrita à
 * própria unidade (o backend valida). Edição continua com o admin em /admin/usuarios.
 */
export const AlunoFichaPage: React.FC = () => {
  const { alunoId } = useParams<{ alunoId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const area = location.pathname.startsWith('/escola') ? 'escola' : 'polo';
  const voltar = voltarDoEstado(location.state, { to: `/${area}/alunos`, rotulo: 'Voltar para alunos' });

  const [ficha, setFicha] = useState<UsuarioFicha | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [boletimAberto, setBoletimAberto] = useState(false);

  const carregar = useCallback(async () => {
    if (!alunoId) return;
    setCarregando(true);
    setErro(null);
    try {
      setFicha(await alunosGestaoApi.ficha(alunoId));
    } catch (err) {
      setFicha(null);
      setErro(mensagemErro(err, 'Não foi possível carregar a ficha do aluno.'));
    } finally {
      setCarregando(false);
    }
  }, [alunoId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (carregando && !ficha) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-nexus-yellow mr-3" />
        Carregando ficha cadastral...
      </div>
    );
  }

  if (erro || !ficha) {
    return (
      <div className="max-w-3xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <p role="alert" className="text-sm text-slate-300">{erro || 'Aluno não encontrado.'}</p>
        <button
          onClick={() => navigate(voltar.to)}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
        >
          {voltar.rotulo}
        </button>
      </div>
    );
  }

  const nomeCompleto = `${ficha.nome} ${ficha.sobrenome || ''}`.trim();

  return (
    <div className="space-y-6 max-w-6xl">
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
            <UserAvatar
              usuarioId={ficha.id}
              fotoUrl={ficha.foto_url}
              nome={nomeCompleto}
              className="w-16 h-16 shrink-0 rounded-2xl object-cover border border-slate-700 text-xl"
            />
            <div className="min-w-0">
              <h1 className="text-2xl font-extrabold text-white tracking-tight break-words">{nomeCompleto}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${statusBadge(ficha.status)}`}>
                  {rotuloStatus(ficha.status)}
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border border-slate-700 bg-slate-800 text-slate-300">
                  <Eye className="w-3 h-3" /> Somente leitura
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {ficha.aluno && (
              <button
                onClick={() => setBoletimAberto(true)}
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors flex items-center gap-1.5"
              >
                <FileText className="w-3.5 h-3.5" /> Histórico escolar
              </button>
            )}
            <button
              onClick={() => void carregar()}
              className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
              title="Recarregar"
              aria-label="Recarregar ficha"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${carregando ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <p className="mt-5 text-xs text-slate-400">
          Alterações cadastrais são feitas pela administração. Para mudar polo, escola ou modalidade, use Transferências.
        </p>
      </div>

      <SecoesPessoais ficha={ficha} />
      {ficha.aluno && <SecaoVinculoAluno ficha={ficha} />}

      {boletimAberto && alunoId && (
        <BoletimModal alunoId={alunoId} podeEditar={false} onClose={() => setBoletimAberto(false)} />
      )}
    </div>
  );
};
