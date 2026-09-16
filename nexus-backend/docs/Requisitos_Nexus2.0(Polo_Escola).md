# CONTEXTO

Você é um engenheiro de software sênior especializado em Python, FastAPI, PostgreSQL e arquitetura em camadas (Router → Service → Repository). Sua tarefa é criar DO ZERO o módulo `polos_escolas` do projeto **NEXUS 2.0**, um sistema SaaS multi-tenant de gestão educacional teológica (ETADEMP).

Este módulo é responsável por toda a **gestão operacional de Polos e Escolas**, incluindo:
- Dashboards gerenciais (KPIs, gráficos, funil de vendas, treemap, drill-down)
- Gestão de licenças (estoque, distribuição, venda, devolução, conversão)
- Relatórios hierárquicos dinâmicos
- Financeiro (histórico, boletos)
- Gestão de alunos e professores vinculados ao polo
- Gestão pedagógica (feed, lembretes, calendário)
- Área de treinamentos
- Gerenciamento de perfil

# STACK E CONVENÇÕES

- **Linguagem:** Python 3.11+
- **Framework:** FastAPI
- **ORM/DB:** PostgreSQL com `psycopg` (cursor via `get_db_cursor`)
- **Validação:** Pydantic v2 (`BaseModel`, `Field`, `ConfigDict`)
- **Autenticação:** JWT (módulo `app.modules.auth`)
- **Hash de senha:** Argon2id (`hash_password`)
- **Estrutura:** `app/modules/polos_escolas/{router,service,repository,schemas,dependencies}.py`
- **Idioma:** português
- **Estilo:** type hints obrigatórios, docstrings em português, `from __future__ import annotations`
- **Paginação:** `limit`/`offset` com `total` no retorno
- **Auditoria:** toda escrita registra em `logs_auditoria`
- **Multi-tenancy:** filtrar por `polo_id`/`escola_id` conforme perfil
- **Proibido:** usar `dict` em memória como fallback de banco; usar `except Exception: pass`

# PERFIS DE USUÁRIO ENVOLVIDOS

- `admin` — acesso total
- `secretario_geral` — visão global
- `coordenador_polo` — gestão do próprio polo
- `secretario_escola` — gestão da própria escola
- `professor` — aulas, atas, anexos, presença
- `monitor` — apoio ao professor, chat
- `aluno` — acesso ao próprio histórico

Permissões granulares: `p_dashboard_polo`, `p_licencas`, `p_alunos_polo`, `p_professores_polo`, `p_escolas`, `p_financeiro_polo`, `p_chat_polo`, `p_pedagogico`, `p_treinamentos`, `p_perfil`.

# ⚠️ REGRAS DE NEGÓCIO CRÍTICAS

## RN-01 — Cadastro unificado do Responsável/Coordenador de Polo
Os dados de cadastro do **Responsável do Polo** devem ser **os mesmos** do **Coordenador do Polo**. **NÃO** deve existir endpoint separado `/polos/{id}/coordenador`. O cadastro do coordenador é feito automaticamente ao criar o Polo.

**Implicações:**
- `POST /polos` cria o Polo **e** o usuário `coordenador_polo` em uma única transação
- `PUT /polos/{id}` sincroniza dados do coordenador (nome, CPF, e-mail, senha se enviada)
- `DELETE /polos/{id}` desativa o usuário coordenador vinculado
- O coordenador **não** aparece como cadastro independente em "Usuários e Staff"
- Mesmo raciocínio para **Secretário de Escola** ao criar Escola

## RN-02 — Fluxo de Licenças (crítico)
Implementar o fluxo completo de licenças:

### 2.1 Compra de Licenças (Fornecedor → Polo)
- Polo compra lote (ex: 100 licenças)
- Sistema credita no **Estoque do Polo**
- Status: `disponivel_polo`

### 2.2 Distribuição para Escolas (Polo → Escola)
- Polo transfere N licenças para Escola
- Sistema **debita** do Estoque do Polo e **credita** no Estoque da Escola
- **Regra:** não permitir transferir mais do que o Polo possui
- Status: `disponivel_escola`

### 2.3 Venda para Alunos (Escola → Aluno)
- Escola matricula aluno e atribui 1 licença
- Sistema **debita** do Estoque da Escola e **vincula** ao ID do Aluno
- Status: `vendida_ativa`
- **Cálculo automático:** `Não Vendidas = Recebidas - Ativas em Alunos`

### 2.4 Devolução Escola → Polo
- Escola devolve N licenças não usadas
- Sistema **debita** do Estoque da Escola e **credita** no Estoque do Polo
- Status: `devolvida_polo`
- Impacto: `Qtd Não Vendida` da Escola zera; `Qtd Não Vendida no Polo` aumenta

### 2.5 Devolução Aluno → Escola
- Aluno cancela curso
- Sistema **remove vínculo** e **devolve** para Estoque da Escola
- Status volta a `disponivel_escola`

## RN-03 — Cálculos de KPI (obrigatórios)

### Dashboard do Polo:
- Total de Licenças Compradas = soma de compras
- Total de Licenças Vendidas para Alunos = soma de licenças ativas em alunos
- Total de Licenças Não Vendidas = (47 nas escolas + 42 no polo)
- Taxa de Conversão Global = `(Vendidas / Compradas) * 100`
- Taxa de Distribuição = `(Distribuídas para Escolas / Compradas) * 100`

### Dashboard da Escola:
- Licenças Recebidas do Polo
- Licenças Vendidas (Alunos)
- Licenças Não Vendidas (Estoque)
- Taxa de Conversão = `(Vendidas / Recebidas) * 100`
- Taxa de Ociosidade = `(Não Vendidas / Recebidas) * 100`

## RN-04 — Alertas Visuais
- **Vermelho:** escolas com > 50% de ociosidade
- **Amarelo:** polos com > 40% de estoque próprio
- **Laranja:** escolas que não venderam nenhuma licença após um período
- **Alerta Escola:** ociosidade > 50% → "Atenção: Mais da metade das licenças da escola estão paradas. Considere devolver ao Polo ou promover uma ação de matrícula."
- **Alerta Escola:** conversão < 20% → "Baixa conversão. Verifique se há alunos com matrículas pendentes."

## RN-05 — Churn / Troca de Polo
- Troca de polo sem nova matrícula (se < 1 ano sem movimentação)
- > 1 ano sem movimentação/entrega → status "desistente", desvinculado do polo
- Reingresso: taxa R$ 100,00 ou 2 licenças cobradas do polo de destino
- Etiqueta "aluno revalidado", só entra em turmas do zero
- Coordenador solicita ao Secretário Geral

## RN-06 — Migração de Modalidade
- Polo ↔ EAD e EAD ↔ Polo
- Solicitação feita por Coordenadores de Polo e Secretários de Escola
- Nomear como "Migração de Modalidade"

## RN-07 — Presença
- Percentual = `(presenças / total_aulas_previstas) * 100`
- Total de aulas previstas é definido por matéria
- Alimentado pelo professor via lista de chamada

## RN-08 — Gestão Pedagógica
- Feed de notícias (apenas professores, coordenadores, diretores, admin)
- Lembretes (pop-ups de aviso)
- Calendário de liberação de matérias EAD (Coordenador EAD)

## RN-09 — Multi-tenancy
- `admin`/`secretario_geral`: veem tudo
- `coordenador_polo`: apenas dados do próprio polo
- `secretario_escola`: apenas dados da própria escola

# REQUISITOS FUNCIONAIS

## 1. Dashboard Principal do Polo

### 1.1 Endpoint de KPIs Globais
`GET /polos/{polo_id}/dashboard/kpis`
Retorna:
```json
{
  "total_licencas_compradas": 100,
  "total_licencas_vendidas_alunos": 11,
  "total_licencas_nao_vendidas": 89,
  "total_nao_vendidas_escolas": 47,
  "total_nao_vendidas_polo": 42,
  "taxa_conversao_global": 11.0,
  "taxa_distribuicao": 58.0
}
1.2 Gráfico de Barras Empilhadas (Funil)
GET /polos/{polo_id}/dashboard/funil
Retorna dados por Polo/Campus com 5 séries:

Compradas (cinza)

Distribuídas para Escolas (azul)

Vendidas para Alunos (verde)

Não Vendidas nas Escolas (vermelho)

Não Vendidas no Polo (amarelo)

1.3 Treemap (Polo > Escola > Status)
GET /polos/{polo_id}/dashboard/treemap
Retorna hierarquia com tamanho proporcional à quantidade de licenças.

1.4 Tabela Matriz Drill-down
GET /polos/{polo_id}/dashboard/drilldown
Retorna estrutura hierárquica:

Nível 1: Polo (expandir)

Nível 2: Escola (expandir)

Nível 3: Aluno (detalhe)

Colunas: Qtd Comprada, Qtd Vendida, Qtd Não Vendida, % Ociosidade

1.5 Filtros do Dashboard
?periodo_mes=&periodo_ano=&polo_id=&status_licenca=ativa|expirada|devolvida

1.6 Alertas
GET /polos/{polo_id}/dashboard/alertas
Retorna lista de alertas conforme RN-04.

2. Relatório Dinâmico Hierárquico (Drill-down)
GET /polos/{polo_id}/relatorios/drilldown

Colunas obrigatórias: Nível, Campo, Descrição, Fórmula

Domínio:

Nível: Polo, Escola, Aluno

Campo: nome do campo representado

Descrição: descrição informativa

Fórmula: resultado (soma, ou dado do banco)

Rodapé (totais):

Total de Licenças Vendidas por Escola (soma)

Total de Licenças Não Vendidas por Escola

Total de Licenças Não Vendidas por Polo = Compradas - Vendidas pelas Escolas

3. Fluxo de Licenças (endpoints)
3.1 Compra (Fornecedor → Polo)
POST /polos/{polo_id}/licencas/compra
Body: { "quantidade": 100, "fornecedor": "...", "valor_unitario": 0.0, "data": "..." }

3.2 Distribuição (Polo → Escola)
POST /polos/{polo_id}/licencas/distribuir
Body: { "escola_id": "...", "quantidade": 11 }
Validação: quantidade <= estoque_polo

3.3 Venda (Escola → Aluno)
POST /escolas/{escola_id}/licencas/vender
Body: { "aluno_id": "...", "quantidade": 1 }
Validação: quantidade <= estoque_escola

3.4 Devolução (Escola → Polo)
POST /escolas/{escola_id}/licencas/devolver
Body: { "quantidade": 6 }

3.5 Devolução (Aluno → Escola)
POST /alunos/{aluno_id}/licencas/devolver
Remove vínculo e devolve ao estoque da escola.

3.6 Extrato de Movimentações
GET /polos/{polo_id}/licencas/movimentacoes?limit=&offset=

4. Dashboard da Escola
4.1 KPIs
GET /escolas/{escola_id}/dashboard/kpis
{
  "licencas_recebidas": 11,
  "licencas_vendidas": 5,
  "licencas_nao_vendidas": 6,
  "taxa_conversao": 45.4,
  "taxa_ociosidade": 54.6
}
4.2 Donut Chart (Vendidas vs. Não Vendidas)
GET /escolas/{escola_id}/dashboard/donut

4.3 Top Alunos
GET /escolas/{escola_id}/dashboard/top-alunos?limit=10

4.4 Tabela Drill-down de Alunos
GET /escolas/{escola_id}/dashboard/alunos
Colunas: Nome, Qtd Licenças, Data Venda/Ativação, Status

4.5 Evolução Temporal
GET /escolas/{escola_id}/dashboard/evolucao?meses=12

4.6 Filtros
?periodo_mes=&periodo_ano=&status_licenca=ativa|expirada|cancelada&aluno_nome=

4.7 Alertas
GET /escolas/{escola_id}/dashboard/alertas

5. Financeiro
5.1 Histórico de Compras
GET /polos/{polo_id}/financeiro/compras?data_inicio=&data_fim=&limit=&offset=

5.2 Download de 2ª Via de Boleto
GET /polos/{polo_id}/financeiro/boletos/{boleto_id}/pdf
Retorna PDF do boleto.

5.3 Lista de Boletos
GET /polos/{polo_id}/financeiro/boletos?data_inicio=&data_fim=

6. Alunos
6.1 Gestão de Alunos do Polo
GET /polos/{polo_id}/alunos?q=&escola_id=&status=&limit=&offset=
Colunas obrigatórias: Quantidade de presenças, Porcentagem de presença

6.2 Editar Aluno
PUT /polos/{polo_id}/alunos/{aluno_id}

6.3 Incluir Notas
POST /polos/{polo_id}/alunos/{aluno_id}/notas

6.4 Emitir Histórico
GET /polos/{polo_id}/alunos/{aluno_id}/historico/pdf

6.5 Cadastrar Aluno
POST /polos/{polo_id}/alunos
Body: nome, sobrenome, cpf, email, data_nascimento, escola_id (opcional), modalidade (polo/escola/ead)

6.6 Requisição de Troca de Polo
POST /polos/{polo_id}/alunos/{aluno_id}/troca-polo
Body: { "polo_destino_id": "..." }
Validação: aluno < 1 ano sem movimentação

6.7 Requisição de Migração de Modalidade
POST /polos/{polo_id}/alunos/{aluno_id}/migracao-modalidade
Body: { "modalidade_destino": "ead" }

6.8 Listar Requisições Pendentes
GET /polos/{polo_id}/requisicoes?tipo=troca_polo|migracao&status=pendente

6.9 Alunos Desistentes (Churn)
GET /polos/{polo_id}/alunos/desistentes

6.10 Escolas (gestão no Polo)
POST /polos/{polo_id}/escolas — cria Escola e usuário secretario_escola (RN-01)

7. Professores
7.1 Dashboard de Professores
GET /polos/{polo_id}/professores/dashboard
Retorna: quantidade de aulas / horas de aulas dadas no período filtrado

7.2 Lista de Professores
GET /polos/{polo_id}/professores?data_inicio=&data_fim=&limit=&offset=

7.3 Card do Professor
GET /polos/{polo_id}/professores/{professor_id}
Retorna: perfil + links para anexos, atas, lista de chamada

7.4 Anexos de Materiais
GET /professores/{professor_id}/anexos?data_inicio=&data_fim=
Sempre mostrar data da aula + matéria

7.5 Atas Oficiais
GET /professores/{professor_id}/atas

7.6 Lista de Chamada
GET /professores/{professor_id}/chamada?materia_id=
Retorna presença por aluno + % de presença por matéria

7.7 Gestão de Professor
PUT /professores/{professor_id}
Campos: perfil, matérias que lecionará, polo, escola, data início, qtd aulas, horas totais por matéria, PIX, valor hora/aula, conteúdo programático

7.8 Cadastro de Professor
POST /polos/{polo_id}/professores
Cria usuário professor e registro de professor em uma transação

7.9 Gestão Pedagógica
POST /pedagogico/feed — postagens (apenas prof/coord/dir/admin)

GET /pedagogico/feed — listar feed

POST /pedagogico/lembretes — criar lembrete

GET /pedagogico/lembretes — listar lembretes

POST /pedagogico/calendario-ead — definir datas de liberação

GET /pedagogico/calendario-ead — listar calendário

8. Área de Treinamentos de Docentes
GET /treinamentos — listar treinamentos disponíveis
POST /treinamentos/{id}/inscrever — inscrever professor
GET /professores/{id}/treinamentos — treinamentos do professor

9. Gerenciamento de Perfil
GET /perfil — dados do próprio usuário
PUT /perfil — editar informações
POST /perfil/foto — upload de foto
PUT /perfil/senha — alterar senha

REQUISITOS NÃO FUNCIONAIS
Auditoria: toda escrita registra logs_auditoria

Paginação: obrigatória em todas as listagens

Filtros: data_inicio, data_fim, mes, ano, status

PDFs: usar reportlab ou fpdf2 (escolher um)

Transações: operações compostas atômicas (criar polo+coordenador, escola+secretário, professor+usuário)

Validações: CPF único, e-mail único, senha ≥ 8, quantidade de licenças não-negativa

Erros: HTTPException com mensagens em português

Testes: InMemoryPolosEscolasRepository

Performance: índices em polo_id, escola_id, status, criado_em

ESTRUTURA DE ARQUIVOS
app/modules/polos_escolas/
├── __init__.py
├── router.py
├── service.py
├── repository.py
├── schemas.py
├── dependencies.py
├── dashboard.py       # Cálculos de KPI e agregações
├── licencas.py        # Lógica de fluxo de licenças
└── pdf.py             # Geração de PDFs (boletos, históricos, relatórios)
BANCO DE DADOS
Já existentes (assumir): usuarios, perfis, permissoes, usuario_permissoes, logs_auditoria, configuracoes, polos, escolas

Novas (criar em schema.sql):
-- Estoque de licenças por local
CREATE TABLE licencas_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    materia_id UUID,
    quantidade_disponivel INT DEFAULT 0,
    quantidade_vendida INT DEFAULT 0,
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CHECK (polo_id IS NOT NULL OR escola_id IS NOT NULL)
);

-- Movimentações de licenças (extrato)
CREATE TABLE licencas_movimentacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(30) NOT NULL, -- 'compra_fornecedor', 'distribuicao_polo_escola', 'venda_aluno', 'devolucao_escola_polo', 'devolucao_aluno_escola'
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    aluno_id UUID REFERENCES usuarios(id),
    materia_id UUID,
    quantidade INT NOT NULL,
    valor_unitario DECIMAL(10,2),
    status VARCHAR(30) DEFAULT 'ativa', -- ativa, expirada, devolvida, cancelada
    actor_id UUID REFERENCES usuarios(id),
    observacao TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Licenças vinculadas a alunos
CREATE TABLE licencas_alunos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID REFERENCES usuarios(id),
    escola_id UUID REFERENCES escolas(id),
    polo_id UUID REFERENCES polos(id),
    materia_id UUID,
    movimentacao_id UUID REFERENCES licencas_movimentacoes(id),
    status VARCHAR(30) DEFAULT 'ativa',
    ativada_em TIMESTAMPTZ DEFAULT now(),
    expirada_em TIMESTAMPTZ,
    cancelada_em TIMESTAMPTZ
);

-- Compras de licenças (financeiro)
CREATE TABLE compras_licencas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id),
    fornecedor VARCHAR(255),
    quantidade INT NOT NULL,
    valor_unitario DECIMAL(10,2),
    valor_total DECIMAL(10,2),
    data_compra DATE NOT NULL,
    boleto_id UUID,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Boletos
CREATE TABLE boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    polo_id UUID REFERENCES polos(id),
    compra_id UUID REFERENCES compras_licencas(id),
    valor DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pendente',
    data_vencimento DATE,
    asaas_id VARCHAR(255),
    url_pdf TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Professores (vínculo com polo/escola)
CREATE TABLE professores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id),
    polo_id UUID REFERENCES polos(id),
    escola_id UUID REFERENCES escolas(id),
    materias JSONB,
    data_inicio DATE,
    quantidade_aulas INT,
    horas_totais INT,
    valor_hora_aula DECIMAL(10,2),
    pix VARCHAR(255),
    conteudo_programatico TEXT,
    status VARCHAR(20) DEFAULT 'ativo',
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Aulas
CREATE TABLE aulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_id UUID REFERENCES professores(id),
    materia_id UUID,
    escola_id UUID REFERENCES escolas(id),
    polo_id UUID REFERENCES polos(id),
    data_aula DATE NOT NULL,
    conteudo TEXT,
    total_aulas_previstas INT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Anexos de aula
CREATE TABLE anexos_aula (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID REFERENCES aulas(id),
    nome VARCHAR(255),
    url TEXT,
    tipo VARCHAR(50),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Atas
CREATE TABLE atas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aula_id UUID REFERENCES aulas(id),
    professor_id UUID REFERENCES professores(id),
    conteudo TEXT,
    url_pdf TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Presenças
CREATE TABLE presencas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID REFERENCES usuarios(id),
    aula_id UUID REFERENCES aulas(id),
    materia_id UUID,
    presente BOOLEAN DEFAULT false,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Requisições de troca
CREATE TABLE requisicoes_troca (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID REFERENCES usuarios(id),
    tipo VARCHAR(30) NOT NULL, -- 'troca_polo', 'migracao_modalidade'
    polo_origem_id UUID REFERENCES polos(id),
    polo_destino_id UUID REFERENCES polos(id),
    modalidade_destino VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pendente',
    solicitado_por UUID REFERENCES usuarios(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Feed de notícias
CREATE TABLE feed_noticias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    autor_id UUID REFERENCES usuarios(id),
    titulo VARCHAR(255),
    conteudo TEXT,
    tags JSONB,
    polo_id UUID REFERENCES polos(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Lembretes
CREATE TABLE lembretes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id),
    titulo VARCHAR(255),
    mensagem TEXT,
    data_expiracao DATE,
    lido BOOLEAN DEFAULT false,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Calendário EAD
CREATE TABLE calendario_ead (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    materia_id UUID,
    data_liberacao DATE NOT NULL,
    semestre INT,
    ano INT,
    criado_por UUID REFERENCES usuarios(id),
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Treinamentos
CREATE TABLE treinamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo VARCHAR(255),
    descricao TEXT,
    url_conteudo TEXT,
    carga_horaria INT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE treinamentos_inscricoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treinamento_id UUID REFERENCES treinamentos(id),
    professor_id UUID REFERENCES professores(id),
    status VARCHAR(20) DEFAULT 'inscrito',
    concluido_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_licencas_estoque_polo ON licencas_estoque(polo_id);
CREATE INDEX idx_licencas_estoque_escola ON licencas_estoque(escola_id);
CREATE INDEX idx_licencas_mov_polo ON licencas_movimentacoes(polo_id);
CREATE INDEX idx_licencas_mov_escola ON licencas_movimentacoes(escola_id);
CREATE INDEX idx_licencas_mov_tipo ON licencas_movimentacoes(tipo);
CREATE INDEX idx_licencas_alunos_aluno ON licencas_alunos(aluno_id);
CREATE INDEX idx_professores_polo ON professores(polo_id);
CREATE INDEX idx_aulas_professor ON aulas(professor_id);
CREATE INDEX idx_aulas_data ON aulas(data_aula);
CREATE INDEX idx_presencas_aluno ON presencas(aluno_id);
ENTREGÁVEIS
schemas.py — Pydantic v2 (Request/Response) com validações

repository.py — PolosEscolasRepositoryInterface + PostgresPolosEscolasRepository + InMemoryPolosEscolasRepository

service.py — regras de negócio, validações, auditoria, transações

router.py — endpoints organizados por seção

dependencies.py — get_polos_escolas_service, require_permission(perm), guards por perfil

dashboard.py — cálculos de KPI, agregações, drill-down

licencas.py — lógica de fluxo de licenças (compra, distribuição, venda, devolução)

pdf.py — PDFs (boletos, históricos, relatórios de drill-down)

schema.sql — tabelas novas + índices

CRITÉRIOS DE ACEITE
□ RN-01: criar polo gera coordenador sem duplicidade
□ RN-01: criar escola gera secretário sem duplicidade
□ RN-02: fluxo completo de licenças (compra → distribuição → venda → devolução)
□ RN-02: não permite distribuir mais que estoque do polo
□ RN-02: não permite vender mais que estoque da escola
□ RN-03: KPIs calculados corretamente (conversão, distribuição, ociosidade)
□ RN-04: alertas visuais retornados pela API
□ RN-05: Churn > 1 ano marcado como desistente
□ RN-06: migração de modalidade registrada
□ RN-07: presença calculada corretamente
□ RN-08: feed, lembretes, calendário EAD funcionais
□ Dashboard do Polo com KPIs + funil + treemap + drill-down
□ Relatório drill-down com colunas Nível/Campo/Descrição/Fórmula
□ Dashboard da Escola com donut + top alunos + evolução
□ Financeiro com histórico + download de boleto
□ Gestão de alunos com presença
□ Cadastro de aluno no polo
□ Requisições de troca e migração
□ Professores com anexos, atas, chamada
□ Treinamentos
□ Gerenciamento de perfil
□ Auditoria em toda escrita
□ Paginação em todas as listagens
□ Multi-tenancy aplicada
□ InMemoryRepository testado
INSTRUÇÕES FINAIS
Comece pelo schemas.py — contratos primeiro

repository.py — interface + Postgres + InMemory

licencas.py — fluxo de licenças (RN-02)

dashboard.py — KPIs e agregações (RN-03, RN-04)

service.py — regras de negócio

router.py — endpoints

dependencies.py — guards

pdf.py — geração de PDFs

schema.sql — banco

Comente # RN-01:, # RN-02: etc. onde cada regra é aplicada

Não use except Exception: pass — trate erros corretamente

Não use dict em memória como fallback — banco é a fonte de verdade

Use transações para operações compostas

Gere o código agora, começando pelo schemas.py.

---

## 📌 Resumo das Mudanças no Prompt

| Item | O que foi incluído |
|---|---|
| **RN-01** | Cadastro unificado do Coordenador/Secretário (sem endpoint separado) |
| **RN-02** | Fluxo completo de licenças (5 etapas) |
| **RN-03** | Fórmulas de KPI (conversão, distribuição, ociosidade) |
| **RN-04** | Alertas visuais com limiares específicos |
| **RN-05** | Churn (> 1 ano, R$ 100,00 / 2 licenças) |
| **RN-06** | Migração de modalidade |
| **RN-07** | Presença (% por matéria) |
| **RN-08** | Feed, lembretes, calendário EAD |
| **RN-09** | Multi-tenancy |
| **Arquitetura** | 9 arquivos separados (não mais tudo em `__init__.py`) |
| **Endpoints** | ~50 endpoints organizados por seção |
| **Banco** | 18 tabelas novas + índices |
| **Proibições** | `dict` em memória, `except Exception: pass` |
| **PDFs** | Boletos, históricos, relatórios |
| **Testes** | InMemoryRepository |

---

## 🎯 Como Usar

### Opção 1 — Executar em LLM
Cole o prompt e peça **um arquivo por vez** (evita truncamento).

### Opção 2 — Dividir em fases
| Fase | Arquivos |
|---|---|
| 1 | `schemas.py` + `schema.sql` |
| 2 | `repository.py` + `licencas.py` |
| 3 | `dashboard.py` + `service.py` |
| 4 | `router.py` + `dependencies.py` |
| 5 | `pdf.py` |

### Opção 3 — Usar como spec para a equipe
Entregue como documento técnico de requisitos.

---

Quer que eu **execute o prompt agora** e gere o `schemas.py` completo do módulo `polos_escolas`? Se sim, me confirme:
- Biblioteca de PDF: `reportlab` ou `fpdf2`?
- Posso assumir os nomes de tabelas sugeridos?
- Quer em **parte única** ou **por fases**?