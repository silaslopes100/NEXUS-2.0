import React, { useEffect, useRef, useState } from 'react';
import {
  CalendarDays, Clock, CreditCard, HeartPulse, Home, IdCard, Loader2, Mail, Phone, Smartphone, UserRound,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { formatCep, formatPhone, onlyDigits } from '@/features/alunos/profileSchema';
import { lookupAddressByCep } from '@/features/alunos/viacep';
import { mascaraCpf } from '@/features/admin/components/UsuarioFormModal';
import { UsuarioFicha } from '@/types/admin';
import { Campo, DadoItem, SecaoEditavel } from './SecaoEditavel';
import {
  ESTADO_CIVIL, SEXO, UFS, formatarCep, formatarCpf, formatarData, formatarTelefone, inputCls, ouNull, vazio,
} from './fichaUtils';

interface Props {
  ficha: UsuarioFicha;
  /** Sem ela as seções ficam somente leitura (ficha vista por Polo/Escola). */
  aoSalvar?: (mensagem: string) => void;
}

const SelectUf: React.FC<{ value: string; onChange: (v: string) => void; id?: string }> = ({ value, onChange, id }) => (
  <select id={id} className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
    <option value="">—</option>
    {UFS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
  </select>
);

// ---------- Identificação ----------

const SecaoIdentificacao: React.FC<Props> = ({ ficha, aoSalvar }) => {
  const [f, setF] = useState({ nome: '', sobrenome: '', email: '', cpf: '', telefone: '', celular: '' });
  return (
    <SecaoEditavel
      titulo="Identificação"
      icone={<CreditCard className="w-4 h-4" />}
      aoEditar={() => setF({
        nome: ficha.nome || '', sobrenome: ficha.sobrenome || '', email: ficha.email || '',
        cpf: mascaraCpf(ficha.cpf || ''), telefone: formatPhone(ficha.telefone || ''),
        celular: formatPhone(ficha.celular || ''),
      })}
      aoSalvar={aoSalvar && (async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'identificacao', {
          nome: f.nome.trim(), sobrenome: f.sobrenome.trim(), email: f.email.trim(),
          cpf: ouNull(onlyDigits(f.cpf)), telefone: ouNull(onlyDigits(f.telefone)), celular: ouNull(onlyDigits(f.celular)),
        });
        aoSalvar('Identificação atualizada.');
      })}
      leitura={
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <DadoItem icon={<Mail className="w-3 h-3" />} label="E-mail" value={vazio(ficha.email)} />
          <DadoItem icon={<CreditCard className="w-3 h-3" />} label="CPF" value={formatarCpf(ficha.cpf)} />
          <DadoItem icon={<Phone className="w-3 h-3" />} label="Telefone" value={formatarTelefone(ficha.telefone)} />
          <DadoItem icon={<Smartphone className="w-3 h-3" />} label="Celular" value={formatarTelefone(ficha.celular)} />
          <DadoItem icon={<Clock className="w-3 h-3" />} label="Último acesso" value={formatarData(ficha.ultimo_login_em, true)} />
          <DadoItem icon={<CalendarDays className="w-3 h-3" />} label="Cadastro" value={formatarData(ficha.criado_em)} />
          <DadoItem icon={<CalendarDays className="w-3 h-3" />} label="Última alteração" value={formatarData(ficha.atualizado_em, true)} />
        </div>
      }
      edicao={
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Campo label="Nome" obrigatorio>
            <input className={inputCls} required value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} />
          </Campo>
          <Campo label="Sobrenome">
            <input className={inputCls} value={f.sobrenome} onChange={(e) => setF({ ...f, sobrenome: e.target.value })} />
          </Campo>
          <Campo label="E-mail" obrigatorio>
            <input type="email" className={inputCls} required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
          </Campo>
          <Campo label="CPF">
            <input className={inputCls} inputMode="numeric" placeholder="000.000.000-00" value={f.cpf}
              onChange={(e) => setF({ ...f, cpf: mascaraCpf(e.target.value) })} />
          </Campo>
          <Campo label="Telefone">
            <input className={inputCls} inputMode="tel" placeholder="(00) 0000-0000" value={f.telefone}
              onChange={(e) => setF({ ...f, telefone: formatPhone(e.target.value) })} />
          </Campo>
          <Campo label="Celular">
            <input className={inputCls} inputMode="tel" placeholder="(00) 00000-0000" value={f.celular}
              onChange={(e) => setF({ ...f, celular: formatPhone(e.target.value) })} />
          </Campo>
        </div>
      }
    />
  );
};

// ---------- Dados pessoais ----------

const SecaoDadosPessoais: React.FC<Props> = ({ ficha, aoSalvar }) => {
  const d = ficha.dados;
  const novo = () => ({
    data_nascimento: d.data_nascimento || '', rg: d.rg || '', rg_orgao_emissor: d.rg_orgao_emissor || '',
    rg_uf: d.rg_uf || '', sexo: d.sexo || '', estado_civil: d.estado_civil || '',
    naturalidade_cidade: d.naturalidade_cidade || '', naturalidade_uf: d.naturalidade_uf || '',
    nacionalidade: d.nacionalidade || 'brasileira',
  });
  const [f, setF] = useState(novo);
  const rg = [d.rg, d.rg_orgao_emissor, d.rg_uf].filter(Boolean).join(' · ');
  const naturalidade = [d.naturalidade_cidade, d.naturalidade_uf].filter(Boolean).join(' / ');
  return (
    <SecaoEditavel
      titulo="Dados pessoais"
      icone={<IdCard className="w-4 h-4" />}
      aoEditar={() => setF(novo())}
      aoSalvar={aoSalvar && (async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'dados-pessoais', {
          data_nascimento: ouNull(f.data_nascimento), rg: ouNull(f.rg), rg_orgao_emissor: ouNull(f.rg_orgao_emissor),
          rg_uf: ouNull(f.rg_uf), sexo: ouNull(f.sexo), estado_civil: ouNull(f.estado_civil),
          naturalidade_cidade: ouNull(f.naturalidade_cidade), naturalidade_uf: ouNull(f.naturalidade_uf),
          nacionalidade: ouNull(f.nacionalidade),
        });
        aoSalvar('Dados pessoais atualizados.');
      })}
      leitura={
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <DadoItem icon={<CalendarDays className="w-3 h-3" />} label="Nascimento" value={formatarData(d.data_nascimento)} />
          <DadoItem label="RG · órgão · UF" value={rg || '—'} />
          <DadoItem label="Sexo" value={d.sexo ? SEXO[d.sexo] ?? d.sexo : '—'} />
          <DadoItem label="Estado civil" value={d.estado_civil ? ESTADO_CIVIL[d.estado_civil] ?? d.estado_civil : '—'} />
          <DadoItem label="Naturalidade" value={naturalidade || '—'} />
          <DadoItem label="Nacionalidade" value={vazio(d.nacionalidade)} className="capitalize" />
        </div>
      }
      edicao={
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Campo label="Data de nascimento">
            <input type="date" className={inputCls} max={new Date().toISOString().slice(0, 10)} value={f.data_nascimento}
              onChange={(e) => setF({ ...f, data_nascimento: e.target.value })} />
          </Campo>
          <Campo label="Sexo">
            <select className={inputCls} value={f.sexo} onChange={(e) => setF({ ...f, sexo: e.target.value })}>
              <option value="">—</option>
              {Object.entries(SEXO).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Campo>
          <Campo label="Estado civil">
            <select className={inputCls} value={f.estado_civil} onChange={(e) => setF({ ...f, estado_civil: e.target.value })}>
              <option value="">—</option>
              {Object.entries(ESTADO_CIVIL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Campo>
          <Campo label="RG">
            <input className={inputCls} maxLength={20} value={f.rg} onChange={(e) => setF({ ...f, rg: e.target.value })} />
          </Campo>
          <Campo label="Órgão emissor">
            <input className={inputCls} maxLength={20} placeholder="SSP" value={f.rg_orgao_emissor}
              onChange={(e) => setF({ ...f, rg_orgao_emissor: e.target.value.toUpperCase() })} />
          </Campo>
          <Campo label="UF do RG">
            <SelectUf value={f.rg_uf} onChange={(v) => setF({ ...f, rg_uf: v })} />
          </Campo>
          <Campo label="Naturalidade (cidade)">
            <input className={inputCls} maxLength={120} value={f.naturalidade_cidade}
              onChange={(e) => setF({ ...f, naturalidade_cidade: e.target.value })} />
          </Campo>
          <Campo label="UF de naturalidade">
            <SelectUf value={f.naturalidade_uf} onChange={(v) => setF({ ...f, naturalidade_uf: v })} />
          </Campo>
          <Campo label="Nacionalidade">
            <input className={inputCls} maxLength={60} value={f.nacionalidade}
              onChange={(e) => setF({ ...f, nacionalidade: e.target.value })} />
          </Campo>
        </div>
      }
    />
  );
};

// ---------- Endereço ----------

const SecaoEndereco: React.FC<Props> = ({ ficha, aoSalvar }) => {
  const d = ficha.dados;
  const novo = () => ({
    cep: formatCep(d.cep || ''), logradouro: d.logradouro || '', numero: d.numero || '',
    complemento: d.complemento || '', bairro: d.bairro || '', cidade: d.cidade || '', uf: d.uf || '',
  });
  const [f, setF] = useState(novo);
  const [cepStatus, setCepStatus] = useState<{ carregando: boolean; msg: string }>({ carregando: false, msg: '' });
  const controle = useRef<AbortController | null>(null);

  useEffect(() => () => controle.current?.abort(), []);

  const mudarCep = (valor: string) => {
    const cep = formatCep(valor);
    setF((atual) => ({ ...atual, cep }));
    controle.current?.abort();
    setCepStatus({ carregando: false, msg: '' });
    const digitos = onlyDigits(cep);
    if (digitos.length !== 8) return;
    const ctrl = new AbortController();
    controle.current = ctrl;
    setCepStatus({ carregando: true, msg: 'Consultando CEP...' });
    lookupAddressByCep(digitos, ctrl.signal)
      .then((r) => {
        if (ctrl.signal.aborted) return;
        setF((atual) => ({
          ...atual,
          logradouro: r.logradouro || atual.logradouro,
          bairro: r.bairro || atual.bairro,
          cidade: r.cidade || atual.cidade,
          uf: r.uf || atual.uf,
        }));
        setCepStatus({ carregando: false, msg: 'Endereço preenchido pelo CEP. Confira e informe o número.' });
      })
      .catch((err: Error) => {
        if (!ctrl.signal.aborted) setCepStatus({ carregando: false, msg: err.message });
      });
  };

  const linha1 = [d.logradouro, d.numero, d.complemento].filter(Boolean).join(', ');
  const linha2 = [d.bairro, [d.cidade, d.uf].filter(Boolean).join('/')].filter(Boolean).join(' — ');
  return (
    <SecaoEditavel
      titulo="Endereço"
      icone={<Home className="w-4 h-4" />}
      aoEditar={() => {
        setF(novo());
        setCepStatus({ carregando: false, msg: '' });
      }}
      aoSalvar={aoSalvar && (async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'endereco', {
          cep: ouNull(onlyDigits(f.cep)), logradouro: ouNull(f.logradouro), numero: ouNull(f.numero),
          complemento: ouNull(f.complemento), bairro: ouNull(f.bairro), cidade: ouNull(f.cidade), uf: ouNull(f.uf),
        });
        aoSalvar('Endereço atualizado.');
      })}
      leitura={
        linha1 || linha2 || d.cep ? (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <DadoItem label="CEP" value={formatarCep(d.cep)} />
            <DadoItem label="Endereço" value={linha1 || '—'} className="sm:col-span-3" />
            <DadoItem label="Bairro · cidade" value={linha2 || '—'} className="sm:col-span-4" />
          </div>
        ) : (
          <p className="text-xs text-slate-500">Endereço não informado.</p>
        )
      }
      edicao={
        <div className="grid grid-cols-1 sm:grid-cols-6 gap-3">
          <Campo label="CEP" className="sm:col-span-2">
            <div className="relative">
              <input className={inputCls} inputMode="numeric" placeholder="00000-000" value={f.cep}
                onChange={(e) => mudarCep(e.target.value)} aria-describedby="cep-status" />
              {cepStatus.carregando && <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400 absolute right-3 top-2.5" />}
            </div>
          </Campo>
          <p id="cep-status" role="status" className="sm:col-span-4 self-end text-[11px] text-slate-400 pb-2">{cepStatus.msg}</p>
          <Campo label="Logradouro" className="sm:col-span-4">
            <input className={inputCls} value={f.logradouro} onChange={(e) => setF({ ...f, logradouro: e.target.value })} />
          </Campo>
          <Campo label="Número" className="sm:col-span-2">
            <input className={inputCls} maxLength={20} value={f.numero} onChange={(e) => setF({ ...f, numero: e.target.value })} />
          </Campo>
          <Campo label="Complemento" className="sm:col-span-2">
            <input className={inputCls} value={f.complemento} onChange={(e) => setF({ ...f, complemento: e.target.value })} />
          </Campo>
          <Campo label="Bairro" className="sm:col-span-2">
            <input className={inputCls} value={f.bairro} onChange={(e) => setF({ ...f, bairro: e.target.value })} />
          </Campo>
          <Campo label="Cidade" className="sm:col-span-1">
            <input className={inputCls} value={f.cidade} onChange={(e) => setF({ ...f, cidade: e.target.value })} />
          </Campo>
          <Campo label="UF" className="sm:col-span-1">
            <SelectUf value={f.uf} onChange={(v) => setF({ ...f, uf: v })} />
          </Campo>
        </div>
      }
    />
  );
};

// ---------- Contato de emergência ----------

const SecaoContatoEmergencia: React.FC<Props> = ({ ficha, aoSalvar }) => {
  const d = ficha.dados;
  const novo = () => ({
    nome: d.contato_emergencia_nome || '', parentesco: d.contato_emergencia_parentesco || '',
    telefone: formatPhone(d.contato_emergencia_telefone || ''),
  });
  const [f, setF] = useState(novo);
  return (
    <SecaoEditavel
      titulo="Contato de emergência"
      icone={<HeartPulse className="w-4 h-4" />}
      aoEditar={() => setF(novo())}
      aoSalvar={aoSalvar && (async () => {
        await adminApi.salvarSecaoFicha(ficha.id, 'contato-emergencia', {
          contato_emergencia_nome: ouNull(f.nome), contato_emergencia_parentesco: ouNull(f.parentesco),
          contato_emergencia_telefone: ouNull(onlyDigits(f.telefone)),
        });
        aoSalvar('Contato de emergência atualizado.');
      })}
      leitura={
        d.contato_emergencia_nome || d.contato_emergencia_telefone ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <DadoItem icon={<UserRound className="w-3 h-3" />} label="Nome" value={vazio(d.contato_emergencia_nome)} />
            <DadoItem label="Parentesco" value={vazio(d.contato_emergencia_parentesco)} />
            <DadoItem icon={<Phone className="w-3 h-3" />} label="Telefone" value={formatarTelefone(d.contato_emergencia_telefone)} />
          </div>
        ) : (
          <p className="text-xs text-slate-500">Nenhum contato de emergência informado.</p>
        )
      }
      edicao={
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Campo label="Nome">
            <input className={inputCls} value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} />
          </Campo>
          <Campo label="Parentesco">
            <input className={inputCls} maxLength={60} placeholder="Mãe, cônjuge..." value={f.parentesco}
              onChange={(e) => setF({ ...f, parentesco: e.target.value })} />
          </Campo>
          <Campo label="Telefone">
            <input className={inputCls} inputMode="tel" placeholder="(00) 00000-0000" value={f.telefone}
              onChange={(e) => setF({ ...f, telefone: formatPhone(e.target.value) })} />
          </Campo>
        </div>
      }
    />
  );
};

export const SecoesPessoais: React.FC<Props> = (props) => (
  <>
    <SecaoIdentificacao {...props} />
    <SecaoDadosPessoais {...props} />
    <SecaoEndereco {...props} />
    <SecaoContatoEmergencia {...props} />
  </>
);
