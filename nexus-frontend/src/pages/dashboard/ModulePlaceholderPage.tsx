import React from 'react';
import { useLocation } from 'react-router-dom';
import { Layers, Database, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export const ModulePlaceholderPage: React.FC = () => {
  const location = useLocation();
  const { perfil } = useAuthStore();

  const getModuleDetails = (pathname: string) => {
    const map: Record<string, { title: string; desc: string; table: string; category: string }> = {
      '/admin/usuarios': {
        title: 'Usuários & Staff Central',
        desc: 'Gerenciamento de contas unificadas com hash Argon2id e controle de acessos.',
        table: 'usuarios',
        category: 'Autenticação & Segurança',
      },
      '/admin/perfis-permissoes': {
        title: 'Perfis & Permissões Granulares',
        desc: 'Gestão de RBAC (admin, polo, escola, professor, aluno) e chaves de permissão p_* do legado.',
        table: 'perfis / permissoes / usuario_permissoes',
        category: 'Segurança & RBAC',
      },
      '/admin/polos-escolas': {
        title: 'Polos & Escolas Parceiras',
        desc: 'Controle de unidades regionais, endereços, responsáveis e filiais vinculadas.',
        table: 'polos / escolas',
        category: 'Estrutura & Unidades',
      },
      '/admin/professores': {
        title: 'Corpo Docente & Professores',
        desc: 'Controle de instrutores, valor de hora-aula, chaves PIX e alocação de turmas.',
        table: 'professores / professor_disciplinas',
        category: 'Gestão de Docentes',
      },
      '/admin/cursos': {
        title: 'Cursos & Matrizes Curriculares',
        desc: 'Cadastro de pacotes, modalidades (presencial, híbrido, EAD) e semestres.',
        table: 'cursos',
        category: 'Gestão Curricular',
      },
      '/admin/disciplinas': {
        title: 'Disciplinas & Conteúdos AVA',
        desc: 'Grade de matérias, aulas, vídeos, materiais complementares e links Meet.',
        table: 'disciplinas / disciplina_conteudos',
        category: 'Ambiente Virtual (AVA)',
      },
      '/admin/turmas-calendarios': {
        title: 'Turmas & Calendários Oficiais',
        desc: 'Montagem de turmas por polo, períodos de liberação e encerramento de disciplinas.',
        table: 'turmas / calendarios_oficiais',
        category: 'Planejamento Acadêmico',
      },
      '/admin/alunos': {
        title: 'Alunos & Matrículas',
        desc: 'Cadastro unificado de discentes, geração de RA/matrícula e controle de desistentes.',
        table: 'alunos / alunos_desistentes',
        category: 'Secretaria Acadêmica',
      },
      '/admin/ead': {
        title: 'Matrículas & Cursos EAD',
        desc: 'Gestão de matrículas automatizadas e avulsas em disciplinas digitais.',
        table: 'matriculas_ead / compras_disciplina_ead',
        category: 'Educação a Distância',
      },
      '/admin/notas-historico': {
        title: 'Notas & Histórico Unificado',
        desc: 'Lançamento de notas do AVA, consolidação final e histórico escolar.',
        table: 'notas / historico_unificado',
        category: 'Desempenho & Avaliação',
      },
      '/admin/presencas': {
        title: 'Presenças & Diário de Classe',
        desc: 'Controle de presença por aula ministrada e cálculo de frequência global.',
        table: 'presencas / atas_aula',
        category: 'Frequência Acadêmica',
      },
      '/admin/certificados': {
        title: 'Certificados & Diplomas',
        desc: 'Emissão de certificados digitais e validação de estágios supervisionados.',
        table: 'certificados',
        category: 'Certificação Digital',
      },
      '/admin/licencas': {
        title: 'Estoque & Atribuição de Licenças',
        desc: 'Controle quantitativo de licenças por disciplina e saldo por polo/escola.',
        table: 'estoque_licencas / licencas_atribuidas',
        category: 'Licenciamento Educacional',
      },
      '/admin/financeiro': {
        title: 'Vendas & Gateway Asaas',
        desc: 'Pedidos de licença, cobranças PIX/Boleto/Cartão e conciliação de pagamentos.',
        table: 'pedidos_licenca / pagamentos',
        category: 'Financeiro & Vendas',
      },
      '/admin/cupons': {
        title: 'Cupons de Desconto',
        desc: 'Códigos promocionais com vigência e percentuais para checkout.',
        table: 'cupons',
        category: 'Comercial & Marketing',
      },
      '/admin/pedidos-livros': {
        title: 'Logística & Pedidos de Livros',
        desc: 'Gestão de remessas físicas de material didático para polos e unidades.',
        table: 'pedidos_livros / pedidos_livros_itens',
        category: 'Logística & Suprimentos',
      },
      '/admin/transferencias': {
        title: 'Transferências de Alunos',
        desc: 'Solicitações de mudança de polo de origem para polo de destino.',
        table: 'solicitacoes_transferencia',
        category: 'Movimentação Acadêmica',
      },
      '/chat': {
        title: 'Chat & Mensageria Interna',
        desc: 'Comunicação direta em tempo real entre alunos, professores e coordenação.',
        table: 'conversas / conversa_membros / mensagens',
        category: 'Comunicação',
      },
      '/feed': {
        title: 'Feed, Notificações & Lembretes',
        desc: 'Mural de avisos institucionais, postagens e lembretes por perfil.',
        table: 'feed_posts / lembretes / notificacoes',
        category: 'Comunicação & Avisos',
      },
      '/admin/auditoria': {
        title: 'Logs de Auditoria & Configurações',
        desc: 'Rastreamento completo de acessos, alterações de dados e parâmetros do sistema.',
        table: 'logs_auditoria / configuracoes',
        category: 'Segurança & Governança',
      },
    };

    return (
      map[pathname] || {
        title: 'Módulo NEXUS 2.0',
        desc: 'Módulo integrado em preparação para o ecossistema NEXUS 2.0.',
        table: 'Tabelas migradas via NeonDB',
        category: 'Módulo do Sistema',
      }
    );
  };

  const details = getModuleDetails(location.pathname);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-nexus-yellow/10 to-transparent pointer-events-none" />
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-blue/20 border border-nexus-blue/40 text-nexus-yellow text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-nexus-yellow" />
              {details.category}
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-3">
              {details.title}
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
              {details.desc}
            </p>
          </div>

          <div className="px-4 py-2 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Backend Conectado</span>
          </div>
        </div>
      </div>

      {/* Info Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center gap-3 text-nexus-yellow mb-3">
            <Database className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Estrutura de Banco
            </h3>
          </div>
          <p className="text-xs text-slate-400 mb-2">Tabelas mapeadas no PostgreSQL:</p>
          <code className="text-xs text-slate-200 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 block font-mono">
            {details.table}
          </code>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center gap-3 text-blue-400 mb-3">
            <ShieldCheck className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Autenticação Ativa
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Sessão autenticada como <strong className="text-white uppercase">{perfil?.nome || 'Usuário'}</strong>. Permissões validadas pelo guard de rota.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center gap-3 text-emerald-400 mb-3">
            <Layers className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Status da Interface
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Estrutura de menu e rotas integrada. Pronto para receber os componentes da feature.
          </p>
        </div>
      </div>
    </div>
  );
};
