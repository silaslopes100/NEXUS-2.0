import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ImagePlus, Loader2, Search, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { ACEITA_IMAGENS, avaAdminApi } from '../../api';
import { botaoPrimario, botaoSecundario, campo, rotulo } from '../editor/estilos';
import {
  CATEGORIA,
  CategoriaTreinamento,
  PERFIS_ALVO,
  PerfilAlvo,
  Treinamento,
  TreinamentoPayload,
  Unidade,
  treinamentosAdminApi,
} from '../../treinamentosApi';

interface Props {
  treinamento?: Treinamento | null;
  onFechar: () => void;
  onSalvo: (t: Treinamento, novo: boolean) => void;
}

/** Seleção múltipla com busca (polos ou escolas). */
const SeletorUnidades: React.FC<{ titulo: string; opcoes: Unidade[]; selecionados: string[]; onChange: (ids: string[]) => void }> = ({
  titulo, opcoes, selecionados, onChange,
}) => {
  const [busca, setBusca] = useState('');
  const filtradas = useMemo(() => {
    const t = busca.trim().toLowerCase();
    return (t ? opcoes.filter((o) => o.nome.toLowerCase().includes(t)) : opcoes).slice(0, 200);
  }, [busca, opcoes]);
  const marcar = (id: string) => onChange(selecionados.includes(id) ? selecionados.filter((x) => x !== id) : [...selecionados, id]);
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <span className="text-xs font-semibold text-slate-300">{titulo}</span>
        <span className="text-[11px] text-slate-500">{selecionados.length} selecionado(s)</span>
      </div>
      <div className="relative border-b border-slate-800">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar…"
          className="w-full bg-transparent py-2 pl-8 pr-3 text-xs text-white placeholder-slate-500 focus:outline-none" />
      </div>
      <ul className="max-h-40 overflow-y-auto py-1">
        {filtradas.map((o) => (
          <li key={o.id}>
            <label className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800/60">
              <input type="checkbox" checked={selecionados.includes(o.id)} onChange={() => marcar(o.id)} /> {o.nome}
            </label>
          </li>
        ))}
        {filtradas.length === 0 && <li className="px-3 py-2 text-xs text-slate-500">Nada encontrado.</li>}
      </ul>
    </div>
  );
};

export const TreinamentoFormDrawer: React.FC<Props> = ({ treinamento: t, onFechar, onSalvo }) => {
  const [titulo, setTitulo] = useState(t?.titulo ?? '');
  const [descricao, setDescricao] = useState(t?.descricao ?? '');
  const [categoria, setCategoria] = useState<CategoriaTreinamento>(t?.categoria ?? 'treinamento');
  const [carga, setCarga] = useState(t?.carga_horaria != null ? String(t.carga_horaria) : '');
  const [perfis, setPerfis] = useState<PerfilAlvo[]>(t?.perfis_alvo ?? ['polo', 'escola', 'professor']);
  const [restringir, setRestringir] = useState(!!(t?.polos.length || t?.escolas.length));
  const [polos, setPolos] = useState<string[]>(t?.polos.map((p) => p.id) ?? []);
  const [escolas, setEscolas] = useState<string[]>(t?.escolas.map((e) => e.id) ?? []);
  const [certificado, setCertificado] = useState(t?.certificado_ativo ?? true);
  const [sequencial, setSequencial] = useState(t?.sequencial ?? false);
  const [inicio, setInicio] = useState(t?.data_inicio ?? '');
  const [fim, setFim] = useState(t?.data_fim ?? '');
  const [capa, setCapa] = useState(t?.capa_url ?? '');
  const [enviandoCapa, setEnviandoCapa] = useState(false);
  const [unidades, setUnidades] = useState<{ polos: Unidade[]; escolas: Unidade[] }>({ polos: [], escolas: [] });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const inputCapa = useRef<HTMLInputElement>(null);

  useEffect(() => {
    treinamentosAdminApi.unidades().then(setUnidades).catch(() => undefined);
  }, []);

  const enviarCapa = async (f: File) => {
    setEnviandoCapa(true);
    setErro(null);
    try {
      setCapa((await avaAdminApi.enviarArquivo(f)).url);
    } catch (e) {
      setErro(mensagemErro(e, 'Falha no envio da capa.'));
    } finally {
      setEnviandoCapa(false);
    }
  };

  const salvar = async () => {
    setSalvando(true);
    setErro(null);
    const payload: TreinamentoPayload = {
      titulo: titulo.trim(), descricao: descricao.trim() || null, capa_url: capa || null, categoria,
      carga_horaria: carga ? Number(carga) : null, perfis_alvo: perfis,
      polo_ids: restringir ? polos : [], escola_ids: restringir ? escolas : [],
      certificado_ativo: certificado, sequencial, data_inicio: inicio || null, data_fim: fim || null,
      publicado: t?.publicado ?? false,
    };
    try {
      const salvo = t ? await treinamentosAdminApi.atualizar(t.id, payload) : await treinamentosAdminApi.criar(payload);
      onSalvo(salvo, !t);
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const alternarPerfil = (p: PerfilAlvo) => setPerfis((l) => (l.includes(p) ? l.filter((x) => x !== p) : [...l, p]));

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onMouseDown={onFechar}>
      <aside className="flex h-full w-full max-w-2xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-lg font-bold text-white">{t ? 'Editar treinamento' : 'Novo treinamento'}</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={18} /></button>
        </header>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-6 py-5">
          <section className="grid gap-4 sm:grid-cols-[180px_1fr]">
            <button type="button" onClick={() => inputCapa.current?.click()} disabled={enviandoCapa}
              className="group relative aspect-video overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-blue-900/60 to-slate-950">
              {capa ? <img src={urlArquivo(capa)} alt="Capa" className="h-full w-full object-cover" /> : (
                <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-xs text-slate-400"><ImagePlus size={20} /> Capa</span>
              )}
              {enviandoCapa && <span className="absolute inset-0 flex items-center justify-center bg-black/60"><Loader2 className="animate-spin text-white" /></span>}
            </button>
            <input ref={inputCapa} type="file" hidden accept={ACEITA_IMAGENS}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) void enviarCapa(f); e.target.value = ''; }} />
            <div className="space-y-3">
              <label className="block">
                <span className={rotulo}>Título</span>
                <input value={titulo} maxLength={255} onChange={(e) => setTitulo(e.target.value)} className={campo} autoFocus
                  placeholder="Ex.: Boas-vindas aos novos Polos" />
              </label>
              <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
                {(Object.keys(CATEGORIA) as CategoriaTreinamento[]).map((c) => (
                  <button key={c} type="button" onClick={() => setCategoria(c)}
                    className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold ${categoria === c ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
                    {CATEGORIA[c].rotulo}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <label className="block">
            <span className={rotulo}>Descrição</span>
            <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} rows={4} maxLength={20000} className={campo}
              placeholder="O que o participante vai aprender e por que é importante." />
          </label>

          <div className="grid gap-3 sm:grid-cols-3">
            <label>
              <span className={rotulo}>Carga horária (h)</span>
              <input type="number" min={0} value={carga} onChange={(e) => setCarga(e.target.value)} className={campo} placeholder="Ex.: 4" />
            </label>
            <label>
              <span className={rotulo}>Início (opcional)</span>
              <input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} className={campo} />
            </label>
            <label>
              <span className={rotulo}>Término (opcional)</span>
              <input type="date" value={fim} onChange={(e) => setFim(e.target.value)} className={campo} />
            </label>
          </div>

          <section className="space-y-3 rounded-2xl border border-slate-800 p-4">
            <p className="text-sm font-bold text-white">Público</p>
            <div className="flex flex-wrap gap-2">
              {PERFIS_ALVO.map((p) => (
                <label key={p.valor} className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                  perfis.includes(p.valor) ? 'border-nexus-yellow bg-nexus-yellow/10 text-white' : 'border-slate-700 text-slate-300'}`}>
                  <input type="checkbox" checked={perfis.includes(p.valor)} onChange={() => alternarPerfil(p.valor)} /> {p.rotulo}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={restringir} onChange={(e) => setRestringir(e.target.checked)} />
              Somente para polos ou escolas específicos
            </label>
            {restringir && (
              <div className="grid gap-3 sm:grid-cols-2">
                <SeletorUnidades titulo="Polos" opcoes={unidades.polos} selecionados={polos} onChange={setPolos} />
                <SeletorUnidades titulo="Escolas" opcoes={unidades.escolas} selecionados={escolas} onChange={setEscolas} />
              </div>
            )}
            {restringir && (
              <p className="text-[11px] text-slate-500">
                Escolhendo um polo, as escolas e os professores daquele polo também veem o treinamento.
              </p>
            )}
          </section>

          <div className="flex flex-wrap gap-5 text-sm text-slate-200">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={certificado} onChange={(e) => setCertificado(e.target.checked)} /> Emitir certificado ao concluir
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={sequencial} onChange={(e) => setSequencial(e.target.checked)} /> Aulas em ordem obrigatória
            </label>
          </div>

          {erro && <p role="alert" className="text-sm text-red-300">{erro}</p>}
        </div>

        <footer className="flex justify-end gap-2 border-t border-slate-800 px-6 py-4">
          <button type="button" onClick={onFechar} className={botaoSecundario}>Cancelar</button>
          <button type="button" onClick={() => void salvar()}
            disabled={salvando || !titulo.trim() || perfis.length === 0 || (restringir && polos.length + escolas.length === 0)}
            className={botaoPrimario}>
            {salvando && <Loader2 size={14} className="animate-spin" />} {t ? 'Salvar' : 'Criar e montar conteúdo'}
          </button>
        </footer>
      </aside>
    </div>
  );
};
