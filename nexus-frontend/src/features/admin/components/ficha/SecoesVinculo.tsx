import React, { useEffect, useState } from 'react';
import {
  AlertTriangle, ArrowLeftRight, Award, BarChart3, BookOpen, Building2, CalendarDays, ClipboardCheck,
  Clock, CreditCard, GraduationCap, KeyRound, MapPin, Shield, Users as UsersIcon, Wallet,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { PERMISSOES_LABELS } from '@/features/admin/components/UsuarioFormModal';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { tipoLabel, TipoTransferencia } from '@/features/transferencias/api';
import { ResumoMetricasUsuario, UsuarioFicha } from '@/types/admin';
import { Campo, DadoItem, MetricaCard, SecaoEditavel } from './SecaoEditavel';
import { MODALIDADE, fmtBRL, fmtNum, formatarData, inputCls, ouNull, rotuloStatus, statusBadge, vazio } from './fichaUtils';

type Opcao = { id: string; nome: string };

/** Polos (uma vez) e escolas do polo escolhido, para os selects das seções. */
function usePolosEscolas(ativo: boolean, poloId: string) {
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  useEffect(() => {
    if (!ativo || polos.length) return;
    polosEscolasApi.listarPolos({ limit: 200 }).then((r) => setPolos(r?.items ?? [])).catch(() => setPolos([]));
  }, [ativo, polos.length]);
  useEffect(() => {
    if (!ativo || !poloId) {
      setEscolas([]);
      return;
    }
    let vivo = true;
    polosEscolasApi.listarEscolasDoPolo(poloId)
      .then((r) => vivo && setEscolas(r?.items ?? []))
      .catch(() => vivo && setEscolas([]));
    return () => {
      vivo = false;
    };
  }, [ativo, poloId]);
  return { polos, escolas };
}

const SelectsUnidade: React.FC<{
  poloId: string; escolaId: string; onChange: (polo: string, escola: string) => void; ativo: boolean;
}> = ({ poloId, escolaId, onChange, ativo }) => {
  const { polos, escolas } = usePolosEscolas(ativo, poloId);
  return (
    <>
      <Campo label="Polo">
        <select className={inputCls} value={poloId} onChange={(e) => onChange(e.target.value, '')}>
          <option value="">Sem polo</option>
          {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      </Campo>
      <Campo label="Escola">
        <select className={inputCls} value={escolaId} disabled={!poloId} onChange={(e) => onChange(poloId, e.target.value)}>
          <option value="">Sem escola</option>
          {escolas.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
        </select>
      </Campo>
    </>
  );
};

// ---------- Acesso & permissões ----------

const SecaoAcesso: React.FC<{ ficha: UsuarioFicha; aoSalvar: (m: string) => void }> = ({ ficha, aoSalvar }) => {
  const [editando, setEditando] = useState(false);
  const [f, setF] = useState({ perfil_nome: '', polo_id: '', escola_id: '', permissoes: [] as string[] });
  const [perfis, setPerfis] = useState<string[]>([]);
  const [chaves, setChaves] = useState<string[]>(Object.keys(PERMISSOES_LABELS));

  useEffect(() => {
    if (!editando || perfis.length) return;
    adminApi.listPerfis().then((r) => setPerfis(r.map((p) => p.nome))).catch(() => setPerfis([]));
    adminApi.listPermissoes().then((r) => r.length && setChaves(r.map((p) => p.chave).sort())).catch(() => undefined);
  }, [editando, perfis.length]);

  const alternar = (chave: string) =>
    setF((a) => ({
      ...a,
      permissoes: a.permissoes.includes(chave) ? a.permissoes.filter((p) => p !== chave) : [...a.permissoes, chave],
    }));

  return (
    <SecaoEditavel
      titulo="Acesso & permissões"
      icone={<KeyRound className="w-4 h-4" />}
      aoEditar={() => {
        setF({
          perfil_nome: ficha.perfil_nome || '', polo_id: ficha.polo_id || '', escola_id: ficha.escola_id || '',
          permissoes: [...(ficha.permissoes || [])],
        });
        setEditando(true);
      }}
      aoSalvar={async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'acesso', {
          perfil_nome: f.perfil_nome, polo_id: ouNull(f.polo_id), escola_id: ouNull(f.escola_id),
          permissoes: f.permissoes,
        });
        setEditando(false);
        aoSalvar('Acesso e permissões atualizados.');
      }}
      leitura={
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <DadoItem icon={<Shield className="w-3 h-3" />} label="Perfil" value={<span className="capitalize">{vazio(ficha.perfil_nome)}</span>} />
            <DadoItem icon={<MapPin className="w-3 h-3" />} label="Polo" value={vazio(ficha.polo_nome)} />
            <DadoItem icon={<Building2 className="w-3 h-3" />} label="Escola" value={vazio(ficha.escola_nome)} />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(ficha.permissoes || []).length === 0 && <span className="text-xs text-slate-500">Sem permissões extras.</span>}
            {(ficha.permissoes || []).map((p) => (
              <span key={p} className="px-2 py-0.5 rounded-full text-[11px] bg-slate-800 border border-slate-700 text-slate-300">
                {PERMISSOES_LABELS[p]?.label ?? p}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-slate-500">
            Para inativar ou bloquear o acesso, use o botão “Inativar” no topo da ficha.
          </p>
        </div>
      }
      edicao={
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Campo label="Perfil" obrigatorio>
              <select className={inputCls} value={f.perfil_nome} onChange={(e) => setF({ ...f, perfil_nome: e.target.value })}>
                {!perfis.includes(f.perfil_nome) && f.perfil_nome && <option value={f.perfil_nome}>{f.perfil_nome}</option>}
                {perfis.map((p) => <option key={p} value={p} className="capitalize">{p}</option>)}
              </select>
            </Campo>
            <SelectsUnidade ativo={editando} poloId={f.polo_id} escolaId={f.escola_id}
              onChange={(polo_id, escola_id) => setF({ ...f, polo_id, escola_id })} />
          </div>
          <fieldset>
            <legend className="text-xs font-semibold text-slate-300 mb-2">Permissões</legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {chaves.map((chave) => (
                <label key={chave} className="flex items-start gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 cursor-pointer">
                  <input type="checkbox" className="mt-0.5 accent-yellow-400" checked={f.permissoes.includes(chave)} onChange={() => alternar(chave)} />
                  <span>
                    <span className="block text-xs font-semibold text-white">{PERMISSOES_LABELS[chave]?.label ?? chave}</span>
                    {PERMISSOES_LABELS[chave]?.desc && <span className="block text-[11px] text-slate-500">{PERMISSOES_LABELS[chave].desc}</span>}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      }
    />
  );
};

// ---------- Vínculo de aluno ----------

const SecaoAluno: React.FC<{
  ficha: UsuarioFicha; resumo: ResumoMetricasUsuario | null; aoSalvar: (m: string) => void;
  aoSolicitarTransferencia: () => void;
}> = ({ ficha, resumo, aoSalvar, aoSolicitarTransferencia }) => {
  const aluno = ficha.aluno!;
  const m = resumo?.aluno;
  const [f, setF] = useState({ numero_matricula: '', data_nascimento: '' });
  const pendente = aluno.transferencia_pendente;
  const freq = m?.frequencia_pct;
  return (
    <SecaoEditavel
      titulo="Vínculo de aluno"
      icone={<GraduationCap className="w-4 h-4" />}
      aoEditar={() => setF({
        numero_matricula: aluno.numero_matricula || '',
        data_nascimento: aluno.data_nascimento || ficha.dados.data_nascimento || '',
      })}
      aoSalvar={async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'vinculo-aluno', {
          numero_matricula: f.numero_matricula.trim(), data_nascimento: ouNull(f.data_nascimento),
        });
        aoSalvar('Vínculo de aluno atualizado.');
      }}
      acoesExtras={
        !pendente && aluno.status === 'ativo' ? (
          <button
            type="button"
            onClick={aoSolicitarTransferencia}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-lg flex items-center gap-1.5"
          >
            <ArrowLeftRight className="w-3.5 h-3.5" /> Solicitar transferência
          </button>
        ) : null
      }
      aviso={
        pendente ? (
          <p role="status" className="mb-4 flex items-start gap-2 text-xs text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
            <ArrowLeftRight className="w-4 h-4 shrink-0" />
            <span>
              Transferência pendente: <strong>{tipoLabel[pendente.tipo as TipoTransferencia] ?? pendente.tipo}</strong>
              {pendente.escola_destino_nome || pendente.polo_destino_nome
                ? ` para ${[pendente.polo_destino_nome, pendente.escola_destino_nome].filter(Boolean).join(' · ')}`
                : ''}
              {pendente.criado_em ? `, aberta em ${formatarData(pendente.criado_em)}` : ''}. Aguardando análise em Transferências.
            </span>
          </p>
        ) : null
      }
      leitura={
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <DadoItem icon={<CreditCard className="w-3 h-3" />} label="Nº de matrícula" value={vazio(aluno.numero_matricula)} />
            <DadoItem icon={<BookOpen className="w-3 h-3" />} label="Modalidade" value={aluno.modalidade ? MODALIDADE[aluno.modalidade] ?? aluno.modalidade : '—'} />
            <DadoItem label="Situação" value={
              <span className={`px-2 py-0.5 rounded-full text-[11px] border ${statusBadge(aluno.status)}`}>{rotuloStatus(aluno.status)}</span>
            } />
            <DadoItem icon={<CalendarDays className="w-3 h-3" />} label="Nascimento" value={formatarData(aluno.data_nascimento)} />
            <DadoItem icon={<MapPin className="w-3 h-3" />} label="Polo" value={vazio(aluno.polo_nome)} />
            <DadoItem icon={<Building2 className="w-3 h-3" />} label="Escola" value={vazio(aluno.escola_nome)} />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricaCard icon={<UsersIcon className="w-4 h-4" />} label="Turmas" value={m ? m.turmas_total : '—'} />
            <MetricaCard
              icon={<BarChart3 className="w-4 h-4" />}
              label={m?.media_notas != null ? `Média de notas (${m.total_notas} avaliações)` : 'Média de notas'}
              value={m?.media_notas != null ? fmtNum(m.media_notas, 1) : '—'}
              accent="text-blue-400"
            />
            <MetricaCard
              icon={<ClipboardCheck className="w-4 h-4" />}
              label={`Frequência (RN07${m?.frequencia_minima_pct != null ? `, mínimo ${fmtNum(m.frequencia_minima_pct)}%` : ''})`}
              value={freq != null ? `${fmtNum(freq, 1)}%` : '—'}
              accent="text-emerald-400"
              selo={m?.frequencia_em_risco ? (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500/15 border border-red-500/30 text-red-300">
                  <AlertTriangle className="w-3 h-3" aria-hidden /> Em risco
                </span>
              ) : null}
            />
            <MetricaCard icon={<Award className="w-4 h-4" />} label="Certificados" value={m ? m.certificados_total : '—'} accent="text-amber-400" />
          </div>
        </div>
      }
      edicao={
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Campo label="Nº de matrícula" obrigatorio>
              <input className={inputCls} required maxLength={50} value={f.numero_matricula}
                onChange={(e) => setF({ ...f, numero_matricula: e.target.value })} />
            </Campo>
            <Campo label="Data de nascimento">
              <input type="date" className={inputCls} max={new Date().toISOString().slice(0, 10)} value={f.data_nascimento}
                onChange={(e) => setF({ ...f, data_nascimento: e.target.value })} />
            </Campo>
          </div>
          <p className="text-[11px] text-slate-500">
            Polo, escola e modalidade mudam pelo fluxo de transferência (botão “Solicitar transferência”).
          </p>
        </div>
      }
    />
  );
};

// ---------- Vínculo de professor ----------

const SecaoProfessor: React.FC<{ ficha: UsuarioFicha; resumo: ResumoMetricasUsuario | null; aoSalvar: (m: string) => void }> = ({
  ficha, resumo, aoSalvar,
}) => {
  const prof = ficha.professor!;
  const m = resumo?.professor;
  const [editando, setEditando] = useState(false);
  const [f, setF] = useState({ polo_id: '', escola_id: '', valor_hora_aula: '', chave_pix: '', status: 'ativo' as 'ativo' | 'inativo' });
  return (
    <SecaoEditavel
      titulo="Vínculo de professor"
      icone={<BookOpen className="w-4 h-4" />}
      aoEditar={() => {
        setF({
          polo_id: prof.polo_id || '', escola_id: prof.escola_id || '',
          valor_hora_aula: prof.valor_hora_aula != null ? String(prof.valor_hora_aula) : '',
          chave_pix: prof.chave_pix || '', status: prof.status === 'inativo' ? 'inativo' : 'ativo',
        });
        setEditando(true);
      }}
      aoSalvar={async () => {
        const valor = f.valor_hora_aula.replace(',', '.').trim();
        await adminApi.salvarSecaoFicha(ficha.id, 'vinculo-professor', {
          polo_id: ouNull(f.polo_id), escola_id: ouNull(f.escola_id),
          valor_hora_aula: valor ? Number(valor) : null, chave_pix: ouNull(f.chave_pix), status: f.status,
        });
        setEditando(false);
        aoSalvar('Vínculo de professor atualizado.');
      }}
      leitura={
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <DadoItem icon={<MapPin className="w-3 h-3" />} label="Polo" value={vazio(prof.polo_nome)} />
            <DadoItem icon={<Building2 className="w-3 h-3" />} label="Escola" value={vazio(prof.escola_nome)} />
            <DadoItem icon={<Wallet className="w-3 h-3" />} label="Hora-aula" value={fmtBRL(prof.valor_hora_aula)} />
            <DadoItem label="Chave PIX" value={vazio(prof.chave_pix)} />
            <DadoItem label="Situação" value={
              <span className={`px-2 py-0.5 rounded-full text-[11px] border ${statusBadge(prof.status)}`}>{rotuloStatus(prof.status)}</span>
            } />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricaCard icon={<UsersIcon className="w-4 h-4" />} label="Turmas" value={m ? m.turmas_total : '—'} />
            <MetricaCard icon={<BookOpen className="w-4 h-4" />} label="Disciplinas" value={m ? m.disciplinas_total : '—'} accent="text-blue-400" />
            <MetricaCard icon={<ClipboardCheck className="w-4 h-4" />} label="Aulas registradas" value={m ? m.aulas_registradas : '—'} accent="text-emerald-400" />
            <MetricaCard
              icon={<Clock className="w-4 h-4" />}
              label="Horas ministradas / previstas"
              value={m ? `${fmtNum(m.horas_ministradas, 1)}h / ${fmtNum(m.horas_previstas, 1)}h` : '—'}
              accent="text-amber-400"
            />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-300 mb-2">Turmas e disciplinas vinculadas</h3>
            {prof.vinculos.length === 0 ? (
              <p className="text-xs text-slate-500">Nenhuma disciplina vinculada em Turmas.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 text-left">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Turma</th>
                      <th className="px-3 py-2 font-semibold">Disciplina</th>
                      <th className="px-3 py-2 font-semibold text-right">Carga</th>
                      <th className="px-3 py-2 font-semibold text-right">Aulas (ministradas/previstas)</th>
                      <th className="px-3 py-2 font-semibold text-right">Horas ministradas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {prof.vinculos.map((v) => (
                      <tr key={v.professor_disciplina_id} className={v.ativo ? '' : 'opacity-60'}>
                        <td className="px-3 py-2 text-slate-200">{vazio(v.turma_nome)}</td>
                        <td className="px-3 py-2 text-white font-semibold">{vazio(v.disciplina_nome)}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{v.carga_horaria != null ? `${fmtNum(v.carga_horaria)}h` : '—'}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{v.aulas_ministradas}/{v.aulas_previstas ?? '—'}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{fmtNum(v.horas_ministradas, 1)}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      }
      edicao={
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <SelectsUnidade ativo={editando} poloId={f.polo_id} escolaId={f.escola_id}
            onChange={(polo_id, escola_id) => setF({ ...f, polo_id, escola_id })} />
          <Campo label="Valor da hora-aula (R$)">
            <input className={inputCls} inputMode="decimal" placeholder="0,00" value={f.valor_hora_aula}
              onChange={(e) => setF({ ...f, valor_hora_aula: e.target.value.replace(/[^\d.,]/g, '') })} />
          </Campo>
          <Campo label="Chave PIX">
            <input className={inputCls} maxLength={255} value={f.chave_pix} onChange={(e) => setF({ ...f, chave_pix: e.target.value })} />
          </Campo>
          <Campo label="Situação no Corpo Docente">
            <select className={inputCls} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as 'ativo' | 'inativo' })}>
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </Campo>
        </div>
      }
    />
  );
};

// ---------- Resumo da unidade (perfis polo/escola) ----------

const SecaoUnidade: React.FC<{ ficha: UsuarioFicha; resumo: ResumoMetricasUsuario }> = ({ ficha, resumo }) => {
  const u = resumo.unidade!;
  return (
    <SecaoEditavel
      titulo={`Unidade gerida (${ficha.escola_nome || ficha.polo_nome || '—'})`}
      icone={<UsersIcon className="w-4 h-4" />}
      leitura={
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricaCard icon={<Building2 className="w-4 h-4" />} label="Escolas" value={u.escolas} />
          <MetricaCard icon={<UsersIcon className="w-4 h-4" />} label="Alunos ativos" value={u.alunos} accent="text-blue-400" />
          <MetricaCard icon={<BookOpen className="w-4 h-4" />} label="Professores" value={u.professores} accent="text-emerald-400" />
          <MetricaCard icon={<ClipboardCheck className="w-4 h-4" />} label="Aulas" value={u.aulas} accent="text-amber-400" />
          <MetricaCard icon={<GraduationCap className="w-4 h-4" />} label="Turmas" value={u.turmas} accent="text-purple-400" />
        </div>
      }
    />
  );
};

export const SecoesVinculo: React.FC<{
  ficha: UsuarioFicha;
  resumo: ResumoMetricasUsuario | null;
  aoSalvar: (m: string) => void;
  aoSolicitarTransferencia: () => void;
}> = ({ ficha, resumo, aoSalvar, aoSolicitarTransferencia }) => (
  <>
    <SecaoAcesso ficha={ficha} aoSalvar={aoSalvar} />
    {ficha.aluno && (
      <SecaoAluno ficha={ficha} resumo={resumo} aoSalvar={aoSalvar} aoSolicitarTransferencia={aoSolicitarTransferencia} />
    )}
    {ficha.professor && <SecaoProfessor ficha={ficha} resumo={resumo} aoSalvar={aoSalvar} />}
    {resumo?.unidade && <SecaoUnidade ficha={ficha} resumo={resumo} />}
  </>
);
