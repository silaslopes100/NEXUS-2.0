import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowLeft, EyeOff, FileDown, Loader2, Lock, MoreVertical, Unlock, Users } from 'lucide-react';
import { AnexoEnviado, ConversaDetalhe, Mensagem, chatApi, erroApi } from '../api';
import { useIntervalo } from '../hooks/useIntervalo';
import { mesclarMensagens, rotuloDia, rotuloPerfil } from '../utils';
import { Avatar } from './Avatar';
import { CompositorMensagem } from './CompositorMensagem';
import { MensagemItem } from './MensagemItem';
import { MembrosPainel } from './MembrosPainel';

const INTERVALO_MSG_MS = 4_000;
const INTERVALO_DETALHE_MS = 20_000;
const PAGINA = 50;

interface Props {
  conversaId: string;
  meuId: string;
  isAdmin: boolean;
  onVoltar: () => void;
  onMudou: () => void;
  onOcultada: () => void;
}

export const ConversaJanela: React.FC<Props> = ({ conversaId, meuId, isAdmin, onVoltar, onMudou, onOcultada }) => {
  const [detalhe, setDetalhe] = useState<ConversaDetalhe | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[] | null>(null);
  const [temMaisAntigas, setTemMaisAntigas] = useState(true);
  const [carregandoAntigas, setCarregandoAntigas] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [painelMembros, setPainelMembros] = useState(false);
  const [acao, setAcao] = useState(false);

  const listaRef = useRef<HTMLDivElement>(null);
  const grudadoNoFimRef = useRef(true);
  const alturaAntesRef = useRef<number | null>(null);
  const mensagensRef = useRef<Mensagem[]>([]);
  mensagensRef.current = mensagens ?? [];

  const souMembro = !!detalhe?.membros.some((m) => m.id === meuId);

  const carregarDetalhe = useCallback(() => {
    chatApi.detalhe(conversaId).then(setDetalhe).catch((e) => setErro(erroApi(e, 'Conversa indisponível.')));
  }, [conversaId]);

  // Troca de conversa: estado limpo + primeira página.
  useEffect(() => {
    let vivo = true;
    setDetalhe(null);
    setMensagens(null);
    setErro(null);
    setTemMaisAntigas(true);
    setPainelMembros(false);
    grudadoNoFimRef.current = true;
    carregarDetalhe();
    chatApi.mensagens(conversaId, { limite: PAGINA })
      .then((ms) => {
        if (!vivo) return;
        setMensagens(ms);
        setTemMaisAntigas(ms.length === PAGINA);
      })
      .catch((e) => vivo && setErro(erroApi(e, 'Não foi possível carregar as mensagens.')));
    return () => { vivo = false; };
  }, [conversaId, carregarDetalhe]);

  // Marca como lida ao abrir e sempre que chegam mensagens com a aba visível.
  const ultimaId = mensagens?.[mensagens.length - 1]?.id;
  useEffect(() => {
    if (!ultimaId || !souMembro || document.hidden) return;
    chatApi.marcarLida(conversaId).then(onMudou).catch(() => undefined);
  }, [ultimaId, souMembro, conversaId, onMudou]);

  // Polling de mensagens novas.
  useIntervalo(() => {
    const atuais = mensagensRef.current;
    if (mensagens === null) return;
    const ultima = atuais[atuais.length - 1];
    chatApi.mensagens(conversaId, ultima ? { depois: ultima.criado_em, limite: 200 } : { limite: PAGINA })
      .then((novas) => novas.length && setMensagens((m) => mesclarMensagens(m ?? [], novas)))
      .catch(() => undefined);
  }, INTERVALO_MSG_MS, mensagens !== null);

  // Leitura dos outros membros / status (confirmação de leitura e encerramento).
  useIntervalo(carregarDetalhe, INTERVALO_DETALHE_MS, detalhe !== null);

  // Scroll: mantém no fim quando o usuário já está lá; preserva a posição ao carregar as antigas.
  useLayoutEffect(() => {
    const el = listaRef.current;
    if (!el || !mensagens) return;
    if (alturaAntesRef.current !== null) {
      el.scrollTop = el.scrollHeight - alturaAntesRef.current;
      alturaAntesRef.current = null;
    } else if (grudadoNoFimRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [mensagens]);

  const carregarAntigas = async () => {
    const primeira = mensagensRef.current[0];
    if (!primeira || carregandoAntigas || !temMaisAntigas) return;
    setCarregandoAntigas(true);
    try {
      const antigas = await chatApi.mensagens(conversaId, { antes: primeira.criado_em, limite: PAGINA });
      alturaAntesRef.current = listaRef.current?.scrollHeight ?? null;
      setTemMaisAntigas(antigas.length === PAGINA);
      setMensagens((m) => mesclarMensagens(m ?? [], antigas));
    } catch {
      /* tenta de novo no próximo scroll */
    } finally {
      setCarregandoAntigas(false);
    }
  };

  const aoRolar = () => {
    const el = listaRef.current;
    if (!el) return;
    grudadoNoFimRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (el.scrollTop < 60) void carregarAntigas();
  };

  const enviar = async (texto: string | null, anexo: AnexoEnviado | null) => {
    const msg = await chatApi.enviar(conversaId, texto, anexo);
    grudadoNoFimRef.current = true;
    setMensagens((m) => mesclarMensagens(m ?? [], [msg]));
    onMudou();
  };

  const executar = async (fn: () => Promise<unknown>) => {
    setMenu(false);
    setAcao(true);
    setErro(null);
    try {
      await fn();
    } catch (e) {
      setErro(erroApi(e));
    } finally {
      setAcao(false);
    }
  };

  const encerrarOuReabrir = () => executar(async () => {
    const novo = detalhe?.status === 'encerrada' ? await chatApi.reabrir(conversaId) : await chatApi.encerrar(conversaId);
    setDetalhe(novo);
    const atuais = mensagensRef.current;
    const novas = await chatApi.mensagens(conversaId, { depois: atuais[atuais.length - 1]?.criado_em, limite: 200 });
    setMensagens((m) => mesclarMensagens(m ?? [], novas));
    onMudou();
  });

  const ocultar = () => executar(async () => {
    if (!window.confirm('Excluir esta conversa da sua lista? Ela volta a aparecer se chegar uma nova mensagem.')) return;
    await chatApi.ocultar(conversaId);
    onOcultada();
  });

  const exportar = () => executar(async () => {
    const blob = await chatApi.exportar(conversaId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversa-${detalhe?.titulo ?? conversaId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // Confirmação de leitura (individual): o outro membro leu até quando?
  const leituraOutro = detalhe?.tipo === 'individual'
    ? detalhe.membros.find((m) => m.id !== meuId)?.ultima_leitura_em ?? null
    : null;

  const subtitulo = !detalhe ? '' : detalhe.tipo === 'grupo'
    ? `${detalhe.membros.length} participantes`
    : rotuloPerfil(detalhe.membros.find((m) => m.id !== meuId)?.perfil);

  const encerrada = detalhe?.status === 'encerrada';

  return (
    <div className="relative flex h-full min-h-0">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Cabeçalho */}
        <div className="flex items-center gap-3 border-b border-slate-800 px-3 py-2.5">
          <button type="button" onClick={onVoltar} aria-label="Voltar" className="rounded-lg p-1.5 text-slate-400 hover:text-white lg:hidden">
            <ArrowLeft size={18} />
          </button>
          <Avatar nome={detalhe?.titulo} grupo={detalhe?.tipo === 'grupo'}
            fotoUrl={detalhe?.tipo === 'individual' ? detalhe.membros.find((m) => m.id !== meuId)?.foto_url : null} />
          <button type="button" className="min-w-0 flex-1 text-left" onClick={() => setPainelMembros((v) => !v)}>
            <p className="truncate font-semibold text-white">{detalhe?.titulo ?? '…'}</p>
            <p className="truncate text-xs text-slate-400">
              {encerrada && <span className="mr-1.5 text-amber-300">Encerrada ·</span>}
              {subtitulo}
              {!souMembro && detalhe && <span className="ml-1.5 text-blue-300">· modo moderação</span>}
            </p>
          </button>
          {acao && <Loader2 size={16} className="animate-spin text-slate-400" />}
          <div className="relative">
            <button type="button" onClick={() => setMenu((v) => !v)} aria-label="Opções"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
              <MoreVertical size={18} />
            </button>
            {menu && detalhe && (
              <div className="absolute right-0 z-30 mt-1 w-56 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-2xl"
                onMouseLeave={() => setMenu(false)}>
                <MenuItem icon={<Users size={15} />} onClick={() => { setMenu(false); setPainelMembros(true); }}>
                  Participantes
                </MenuItem>
                {detalhe.pode_encerrar && (
                  <MenuItem icon={encerrada ? <Unlock size={15} /> : <Lock size={15} />} onClick={() => void encerrarOuReabrir()}>
                    {encerrada ? 'Reabrir conversa' : 'Finalizar conversa'}
                  </MenuItem>
                )}
                {souMembro && (
                  <MenuItem icon={<EyeOff size={15} />} onClick={() => void ocultar()}>Excluir para mim</MenuItem>
                )}
                {isAdmin && (
                  <MenuItem icon={<FileDown size={15} />} onClick={() => void exportar()}>Baixar conversa (PDF)</MenuItem>
                )}
              </div>
            )}
          </div>
        </div>

        {erro && (
          <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-200">{erro}</div>
        )}

        {/* Mensagens */}
        <div ref={listaRef} onScroll={aoRolar} className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5">
          {mensagens === null ? (
            <div className="flex justify-center py-12 text-slate-400"><Loader2 className="animate-spin" /></div>
          ) : (
            <>
              {carregandoAntigas && (
                <div className="flex justify-center pb-3 text-slate-500"><Loader2 size={16} className="animate-spin" /></div>
              )}
              {!temMaisAntigas && mensagens.length > 0 && (
                <p className="pb-3 text-center text-[11px] text-slate-600">
                  Início do histórico disponível (as conversas ficam guardadas por 90 dias).
                </p>
              )}
              {mensagens.length === 0 && (
                <p className="py-12 text-center text-sm text-slate-500">Nenhuma mensagem ainda. Diga olá! 👋</p>
              )}
              <div className="space-y-1.5">
                {mensagens.map((m, i) => {
                  const anterior = mensagens[i - 1];
                  const novoDia = !anterior || new Date(anterior.criado_em).toDateString() !== new Date(m.criado_em).toDateString();
                  const minha = m.remetente_id === meuId && m.tipo !== 'sistema';
                  const mostrarRemetente = detalhe?.tipo === 'grupo'
                    && (novoDia || anterior?.remetente_id !== m.remetente_id || anterior?.tipo === 'sistema');
                  return (
                    <React.Fragment key={m.id}>
                      {novoDia && (
                        <div className="sticky top-0 z-10 flex justify-center py-2">
                          <span className="rounded-full bg-slate-900/90 px-3 py-0.5 text-[11px] capitalize text-slate-400 ring-1 ring-slate-800">
                            {rotuloDia(m.criado_em)}
                          </span>
                        </div>
                      )}
                      <MensagemItem mensagem={m} minha={minha} mostrarRemetente={mostrarRemetente}
                        lida={minha && detalhe?.tipo === 'individual'
                          ? !!leituraOutro && new Date(leituraOutro) >= new Date(m.criado_em)
                          : undefined} />
                    </React.Fragment>
                  );
                })}
              </div>
            </>
          )}
        </div>

        <CompositorMensagem
          desabilitado={!detalhe || encerrada || !souMembro}
          motivoDesabilitado={!detalhe ? 'Carregando…' : encerrada
            ? 'Esta conversa foi finalizada.'
            : 'Você está visualizando como moderador (não participa desta conversa).'}
          onEnviar={enviar}
        />
      </div>

      {painelMembros && detalhe && (
        <MembrosPainel detalhe={detalhe} meuId={meuId} onFechar={() => setPainelMembros(false)}
          onAtualizado={(d) => { setDetalhe(d); onMudou(); }} />
      )}
    </div>
  );
};

const MenuItem: React.FC<{ icon: React.ReactNode; onClick: () => void; children: React.ReactNode }> = ({ icon, onClick, children }) => (
  <button type="button" onClick={onClick}
    className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800">
    <span className="text-slate-400">{icon}</span>{children}
  </button>
);
