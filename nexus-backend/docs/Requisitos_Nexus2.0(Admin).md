# CONTEXTO

Você é um engenheiro de software sênior especializado em Python, FastAPI, PostgreSQL e arquitetura em camadas (Router → Service → Repository). Sua tarefa é criar DO ZERO o módulo `admin` do projeto **NEXUS 2.0**, um sistema SaaS multi-tenant de gestão educacional teológica (ETADEMP).

O módulo `admin` é o coração administrativo do sistema e deve atender a **todos** os requisitos da Dashboard Interativa descrita abaixo, além de manter as boas práticas já adotadas no projeto (FastAPI, Pydantic v2, psycopg, Argon2id, auditoria, paginação, filtros).

# STACK E CONVENÇÕES

- **Linguagem:** Python 3.11+
- **Framework:** FastAPI
- **ORM/DB:** PostgreSQL com `psycopg` (cursor via context manager `get_db_cursor`)
- **Validação:** Pydantic v2 (`BaseModel`, `Field`, `ConfigDict`)
- **Autenticação:** JWT (módulo `app.modules.auth`)
- **Hash de senha:** Argon2id (`hash_password` em `app.core.security`)
- **Estrutura de pastas:** `app/modules/admin/{router,service,repository,schemas,dependencies}.py`
- **Idioma:** português (nomes de campos, mensagens, comentários)
- **Estilo:** type hints obrigatórios, docstrings em português, `from __future__ import annotations`
- **Paginação:** sempre `limit`/`offset` com `total` no retorno
- **Auditoria:** toda operação de escrita registra em `logs_auditoria` com `dados_antes`/`dados_depois`
- **Multi-tenancy:** filtrar por `polo_id`/`escola_id` quando o usuário logado não for `admin` ou `secretario_geral`

# PERFIS DE USUÁRIO

Criar/suportar os seguintes perfis:
- `admin` — acesso total
- `secretario_geral` — visão global, sem configurar sistema
- `coordenador_ead` — gestão EAD
- `coordenador_polo` — gestão do próprio polo
- `secretario_escola` — gestão da própria escola
- `professor` — aulas, atas, anexos, presença
- `monitor` — apoio ao professor, chat
- `aluno` — acesso ao próprio histórico
- `financeiro` — vendas, boletos
- `logistica` — pedidos de livros

Permissões granulares (chaves): `p_dashboard`, `p_alunos`, `p_polos`, `p_escolas`, `p_cursos`, `p_modulos`, `p_licencas`, `p_ead`, `p_financeiro`, `p_logistica`, `p_chat`, `p_certificados`, `p_config`, `p_auditoria`, `p_usuarios`, `p_relatorios`.

# ⚠️ REGRAS DE NEGÓCIO CRÍTICAS

## RN-01 — Cadastro unificado do Responsável/Coordenador de Polo
Os dados de cadastro do **Responsável do Polo** devem ser **os mesmos** do **Coordenador do Polo**. **NÃO** deve existir cadastro separado na sessão "Usuários e Staff". Isso evita confusão e duplicidade para o usuário.

**Implicações:**
- Ao criar um Polo, os campos `responsavel`, `cpf`, `email`, `endereco` e `senha` cadastrados são automaticamente usados para criar o **usuário coordenador** com perfil `coordenador_polo`.
- O usuário coordenador aparece em "Usuários e Staff" apenas como **reflexo** (read-only ou com edição controlada), nunca como um cadastro independente.
- Ao editar o Polo, os dados do responsável/coordenador são sincronizados automaticamente (nome, CPF, e-mail, senha).
- Ao excluir o Polo, o usuário coordenador vinculado também é desativado/excluído.
- A sessão "Usuários e Staff" deve **ocultar** usuários cujo perfil seja `coordenador_polo` e que já tenham vínculo com um polo, OU exibi-los com aviso "Gerenciado via cadastro do Polo".
- **O mesmo raciocínio se aplica ao Secretário de Escola:** os dados de cadastro da Escola (responsável, CPF, e-mail, endereço, senha) criam automaticamente o usuário `secretario_escola`. Não deve haver cadastro duplicado em "Usuários e Staff".

**Exemplo prático:**
POST /admin/polos
{
"nome": "Polo São Paulo Centro",
"responsavel": "João Silva",
"cpf": "123.456.789-00",
"email": "joao@polosp.com.br",
"endereco": "Rua X, 123 - SP",
"senha": "senhaSegura123"
}
→ Cria registro em polos
→ Cria usuário em usuarios com perfil coordenador_polo, vinculado ao polo
→ NÃO é necessário chamar POST /admin/usuarios


## RN-02 — Multi-tenancy e visibilidade
- `admin` e `secretario_geral` veem tudo
- `coordenador_polo` vê apenas dados do próprio polo
- `secretario_escola` vê apenas dados da própria escola
- Filtros de listagem aplicam escopo automaticamente conforme perfil

## RN-03 — Regras do EAD
- 2 matérias por mês, seguindo calendário oficial
- Matéria anterior permanece liberada até abertura da próxima
- Se não finalizar no prazo: reprovado, só libera nova matéria com novo pagamento
- Preço por matéria EAD: R$ 45,00
- Upsell opcional do livro físico
- Pop-ups e e-mails avisando data de liberação

## RN-04 — Churn / Alunos Desistentes
- > 1 ano sem movimentação/compra → status "desistente", desvinculado do polo
- Reingresso: taxa R$ 100,00 ou 2 licenças cobradas do polo de destino
- EAD: pop-up "Você já tem cadastro, mas precisa regularizar sua situação, entre em contato pelo WhatsApp (11) 1936-6880"
- Etiqueta "aluno revalidado"
- Só entra em turmas que comecem do zero
- Coordenador solicita ao Secretário Geral, que gera nova matrícula

## RN-05 — Certificados
- Exige entrega dos 2 estágios: Teologia do Ministério + Homilética
- Exige histórico completo (todas as matérias)
- Data de emissão condicionada às duas regras acima

## RN-06 — Chat
- PROIBIDO chat aluno↔aluno
- Admin pode baixar conversas particulares
- Segmentar fluxo em grupo ou individual

## RN-07 — Presença
- Percentual = (presenças / total_aulas_previstas) * 100
- Total de aulas previstas é definido por matéria
- Presença alimentada pelo professor via lista de chamada

# REQUISITOS FUNCIONAIS (DASHBOARD INTERATIVA)

## 1. Visualizadores (cards clicáveis com contagem)
Implementar endpoints de contagem + listagem paginada com filtros para:

### 1.1 Alunos Ativos
- Endpoint de contagem + listagem
- Filtros: `data_inicio`, `data_fim`, `polo_id`, `escola_id`, `pais`, `estado`, `curso_id`, `semestre` (1º, 2º, 3º), `ano`
- Ao clicar em um aluno: abrir card com perfil + histórico + presenças

### 1.2 Quantidade de Matrículas (último filtro)
- Filtros: `data_inicio`, `data_fim`, `mes`, `semestre`, `ano`, `polo_id`, `escola_id`
- **Botão para gerar PDF:** Ranking de Polos por ordem de novas licenças/livros adquiridos

### 1.3 Polos Ativos
- Listagem de todos os polos
- Ao clicar em um polo: card com detalhes (responsável, endereço, total alunos, licenças, escolas vinculadas)

### 1.4 Escolas Ativas
- Listagem de todas as escolas (com filtro por polo)
- Ao clicar em uma escola: card com detalhes (responsável, endereço, alunos, polo vinculado)

### 1.5 Professores Ativos
- Filtros: `data_inicio`, `data_fim`
- Ao clicar em um professor: card com:
  - Perfil
  - **Botão de anexos** (materiais de aula — sempre mostrar data da aula + matéria)
  - **Botão de Atas** (atas oficiais das aulas lecionadas)
  - **Lista de chamada** (presença por aluno, % de presença por matéria — base: total de aulas previstas)

### 1.6 Emissão de Certificados
- Lista de alunos formados com certificado emitido
- Ao clicar: card com:
  - Data de entrega dos 2 estágios (Teologia do Ministério + Homilética)
  - Data de emissão do certificado (condicionada ao histórico completo)

## 2. Licenças / Estoque
- Dashboard com quantidade de licenças/livros por matéria ("Estoque Geral")
- Lista de matérias com licenças disponíveis + em estoque para distribuir aos polos
- **Diminuição automática** do estoque quando polo adquire licença/livro
- **Edição manual** pelo Secretário (adição/subtração) com auditoria
- Histórico de movimentações (entrada, saída, ajuste)

## 3. Cursos e Módulos
- CRUD de cursos (nome, descrição, carga horária, grade curricular)
- Dentro do curso: gerenciar/editar/criar módulos (matérias)
- Módulo: nome, ordem, conteúdo, carga horária, matérias vinculadas

## 4. EAD

### 4.1 Matrículas Manuais
- Aluno EAD = sem vínculo com polo
- Acesso direto ao AVA
- Preço por matéria: **R$ 45,00**
- Upsell opcional do livro físico

### 4.2 Gestão Pedagógica EAD
- Campo de busca + listagem de alunos EAD
- Colunas: último acesso, progresso na matéria atual
- Inserção de materiais adicionais
- **Feed de notícias** (postagens de professores, coordenadores, diretores, admin — conteúdo teológico, artigos, novidades)
- **Lembretes** (pop-ups de aviso)
- **Calendário de liberação de matérias** (Coordenador EAD define datas conforme grade curricular)

### 4.3 Histórico de Matrículas EAD
- Lista de matrículas manuais + compras no site oficial (www.etadempcom.br)
- **Liberação automática** da matrícula ao comprar no EAD
- Regra: **2 matérias por mês**, seguindo calendário oficial
- Matéria anterior permanece liberada para finalização até abertura da próxima
- Se não finalizar: aluno **reprovado** e só libera nova matéria com **novo pagamento**
- **Pop-ups e e-mails** avisando data de liberação da próxima matéria
- Curso único (sem distinção Polo x EAD no histórico) — diferença só no preço

## 5. Polos (gestão)
- CRUD de polos
- Ao criar polo, cadastrar **Coordenador de Polo** com: nome, CPF, e-mail, endereço, senha
- Criação automática do usuário com perfil `coordenador_polo` (**ver RN-01**)
- **NÃO** permitir cadastro duplicado do Coordenador em "Usuários e Staff"

## 6. Escolas (gestão)
- CRUD de escolas (também disponível no usuário Polo)
- Ao criar escola, cadastrar **Secretário de Escola** com: nome, CPF, e-mail, endereço, senha
- Criação automática do usuário com perfil `secretario_escola` (**ver RN-01**)
- **NÃO** permitir cadastro duplicado do Secretário em "Usuários e Staff"

## 7. Financeiro

### 7.1 Vendas
- Dashboard com filtros: `data_inicio`, `data_fim`, `mes`, `ano`, `polo_id`, `escola_id`, `modalidade` (polo/escola/ead)
- Download em PDF do relatório

### 7.2 Boletos (integração AsaaS — preparar)
- Geração de boletos via API do AsaaS
- Histórico de boletos gerados (salvar no momento da compra do polo)
- Estrutura pronta para receber a API (interface + stub)

## 8. Logística

### 8.1 Novos Pedidos
- Lista de pedidos de livros pendentes de envio feitos pelos polos

### 8.2 Histórico de Pedidos
- Lista de todos os pedidos já feitos
- Filtros: `data_inicio`, `data_fim`, `mes`, `semestre`, `ano`, `polo_id`, `escola_id` (polo/escola opcionais)

## 9. Alunos

### 9.1 Gestão de Alunos
- Admin/Secretaria: vê todos os alunos
- Polo/Escola: vê apenas vinculados
- Editar informações do aluno
- Incluir notas das avaliações + emitir histórico
- **Colunas obrigatórias:** "Quantidade de presenças" e "Porcentagem de presença" (puxadas da lista de chamada do professor)

### 9.2 Cadastrar Aluno
- Nome, Sobrenome, CPF, E-mail, Data de nascimento
- É aluno de Polo? (sim/não)
- Pertence a alguma Escola? (opcional)
- É aluno EAD? (sim/não)
- Edição e gerenciamento

### 9.3 Requisição de Troca de Polo ou Modalidade
- Visualizar solicitações feitas pelos polos
- Troca de polo: sem nova matrícula
- **Regra Churn:** > 1 ano sem movimentação/entrega → status "desistente" e desvinculado do polo
- Troca Polo↔EAD ou EAD↔Polo (nomear como "Migração de Modalidade")
- Solicitação feita por Coordenadores de Polo e Secretários de Escola

### 9.4 Alunos Desistentes (Churn)
- Lista de alunos > 1 ano sem movimentação/compra
- Reingresso: taxa de matrícula **R$ 100,00** (ou 2 licenças cobradas do polo de destino)
- EAD: pop-up "Você já tem cadastro, mas precisa regularizar sua situação, entre em contato pelo WhatsApp (11) 1936-6880"
- Etiqueta **"aluno revalidado"**
- Só entra em **turmas que comecem do zero**
- Regra válida para Polo e EAD
- Coordenador solicita ao Secretário Geral, que localiza o aluno neste campo e gera nova matrícula

## 10. Chat
- Canal interno: alunos ↔ professores, coordenação, monitores, secretaria
- Funcionalidades: finalizar chats, marcar mensagens como lidas, excluir chat (apenas Admin)
- **Grupos** e **individuais**
- Admin pode **baixar conversas particulares** (aluno ↔ professor/coordenador/secretário/monitor)
- **PROIBIDO** chat entre alunos

## 11. Configurações
- Pagamentos: meios e regras
- Sobre: regras padrão de CRMs, SaaS e Hubs
- Gerenciamento de Perfil: editar informações, foto, senha de acesso

# REQUISITOS NÃO FUNCIONAIS

- **Auditoria:** toda escrita registra `logs_auditoria` (usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip, criado_em)
- **Paginação:** obrigatória em todas as listagens
- **Filtros:** sempre aceitar `data_inicio`, `data_fim`, `mes`, `semestre`, `ano`, `polo_id`, `escola_id` quando fizer sentido
- **PDFs:** usar `reportlab` ou `fpdf2` (escolher um)
- **Transações:** operações compostas (ex: criar polo + usuário) devem ser atômicas
- **Validações:** CPF único, e-mail único, senha ≥ 6 caracteres, perfil existente
- **Erros:** usar `HTTPException` com mensagens claras em português
- **Testes:** criar `InMemoryAdminRepository` para testes unitários
- **Performance:** índices nas colunas de filtro (data, polo_id, escola_id, status)

# ESTRUTURA DE ARQUIVOS

Criar do zero os seguintes arquivos:
app/modules/admin/
├── init.py
├── router.py # Rotas HTTP FastAPI
├── service.py # Regras de negócio
├── repository.py # Acesso a dados (Interface + Postgres + InMemory)
├── schemas.py # Pydantic v2
├── dependencies.py # Injeção de dependência + guards
└── pdf.py # Geração de PDFs (ranking, relatórios)

# BANCO DE DADOS

Criar migrations SQL (ou script `schema.sql`) com as tabelas:

**Já existentes (assumir):**
- `usuarios`, `perfis`, `permissoes`, `usuario_permissoes`
- `logs_auditoria`, `configuracoes`
- `etl_sync_runs`, `etl_erros`

**Novas:**
- `polos`, `escolas`
- `cursos`, `modulos`, `materias`
- `matriculas`, `matriculas_ead`
- `licencas_estoque`, `licencas_movimentacoes`
- `ead_calendario`, `feed_noticias`, `lembretes`
- `aulas`, `presencas`, `anexos_aula`, `atas`
- `certificados`
- `chat_mensagens`, `chat_grupos`, `chat_participantes`
- `vendas`, `boletos`, `pedidos_livros`
- `alunos_churn`, `requisicoes_troca`
- `notas_alunos`, `historico_alunos`

Usar `UUID` como PK, `TIMESTAMPTZ` para datas, `JSONB` para campos flexíveis, FKs com `ON DELETE` apropriado, índices nas colunas de filtro.

**Importante:** as tabelas `polos` e `escolas` devem ter FK `usuario_id` apontando para `usuarios(id)`, representando o vínculo 1:1 entre o polo/escola e seu responsável/coordenador (ver RN-01).

# ENTREGÁVEIS

Gerar código **completo e funcional** para:

1. **`schemas.py`** — todos os Pydantic models (Request/Response) com validações
2. **`repository.py`** — `AdminRepositoryInterface` (Protocol) + `PostgresAdminRepository` (completo) + `InMemoryAdminRepository` (testes)
3. **`service.py`** — `AdminService` com toda a lógica de negócio, validações, auditoria e transações
4. **`router.py`** — todos os endpoints FastAPI organizados por seção, com `response_model`, `summary`, `status_code` e dependências de permissão
5. **`dependencies.py`** — `get_admin_service`, `require_admin_user`, `require_permission(perm_key)`, guards por perfil
6. **`pdf.py`** — geração de PDFs (ranking de polos, relatórios de vendas, histórico)
7. **`schema.sql`** — todas as tabelas novas com índices e constraints

# CRITÉRIOS DE ACEITE

- [ ] Todos os endpoints retornam os schemas corretos
- [ ] Toda escrita gera log de auditoria
- [ ] Filtros funcionam combinados (data + polo + escola + modalidade)
- [ ] Paginação retorna `total`, `items`, `limit`, `offset`
- [ ] PDFs são gerados corretamente
- [ ] **RN-01:** Criar polo gera automaticamente o usuário coordenador sem duplicidade em "Usuários e Staff"
- [ ] **RN-01:** Editar polo sincroniza dados do coordenador
- [ ] **RN-01:** Criar escola gera automaticamente o usuário secretário sem duplicidade
- [ ] **RN-01:** Listagem de "Usuários e Staff" oculta ou marca usuários gerenciados via Polo/Escola
- [ ] Regras do EAD (2 matérias/mês, reprovação, novo pagamento) estão implementadas
- [ ] Regras de Churn (> 1 ano, taxa R$ 100,00 / 2 licenças, etiqueta "revalidado") estão implementadas
- [ ] Chat proíbe aluno↔aluno
- [ ] Admin pode baixar conversas particulares
- [ ] Presença calcula % corretamente (presenças / total_aulas * 100)
- [ ] Certificado exige 2 estágios + histórico completo
- [ ] Estoque de licenças diminui automaticamente e aceita ajuste manual auditado
- [ ] Multi-tenancy: coordenador_polo só vê dados do próprio polo
- [ ] Testes com InMemoryAdminRepository passam

# INSTRUÇÕES FINAIS

1. **Comece pelo `schemas.py`** — defina todos os contratos antes de implementar.
2. **Depois `repository.py`** — interface primeiro, depois Postgres, depois InMemory.
3. **Em seguida `service.py`** — regras de negócio, validações, auditoria.
4. **Depois `router.py`** — endpoints organizados por seção com tags.
5. **Por fim `dependencies.py` e `pdf.py`**.
6. **Inclua `schema.sql`** ao final.
7. **Comente o código em português** explicando regras não óbvias (RN-01, Churn, EAD, certificados).
8. **Não omita nenhuma funcionalidade** — se for grande, divida em partes, mas entregue tudo.
9. **Use `TODO:` apenas para integrações externas** (AsaaS, envio de e-mail) — o resto deve estar completo.
10. **Se algo não estiver claro nos requisitos, assuma a interpretação mais razoável e documente a decisão no código.**
11. **Destaque no código, com comentário `# RN-01:`, todos os pontos onde a regra de cadastro unificado do Coordenador de Polo / Secretário de Escola é aplicada.**

Gere o código agora, começando pelo `schemas.py`.