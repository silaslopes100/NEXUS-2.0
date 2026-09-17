# Checklist de Implementação - NEXUS 2.0 (Backend & Frontend)

Documento oficial de acompanhamento do plano técnico e status de entrega dos 18 módulos do ecossistema educacional unificado **NEXUS 2.0**.

---

## 1. Infraestrutura, Segurança & Banco de Dados

- [x] **PostgreSQL / NeonDB DDL**: Schema relacional normalizado (seção 3 do plano técnico) com UUIDs, timestamptz e rastreabilidade legada.
- [x] **Segurança de Senhas**: Criptografia em Argon2id (`argon2-cffi`) com suporte a *lazy rehash* de senhas legadas em `bcrypt`.
- [x] **Autenticação JWT & Sessões**: `access_token` JWT em memória (15 min) + `refresh_token` rotativo de uso único (7 dias).
- [x] **Proteção de Força Bruta**: Bloqueio temporário (429) após 5 tentativas falhas em 15 minutos via `login_tentativas`.
- [x] **Auditoria Contínua**: Registro unificado de ações administrativas e autenticação em `logs_auditoria` com `dados_antes`/`dados_depois`.
- [x] **Controle de Acesso (RBAC)**: Dependências reutilizáveis `require_role([...])` e `require_permissao(...)` com bypass de administrador.

---

## 2. Status dos 18 Módulos de Negócio (100% Concluídos)

| # | Módulo | Tabelas Envolvidas | Backend (`app/modules/`) | Frontend (`src/`) | Testes Automatizados | Status |
|---|---|---|---|---|---|---|
| **01** | **Autenticação & Sessões** | `usuarios`, `perfis`, `permissoes`, `usuario_permissoes`, `refresh_tokens`, `password_reset`, `login_tentativas` | [app/modules/auth/](app/modules/auth/) | [src/features/auth/](src/features/auth/) | `test_auth.py` | ✅ Concluído |
| **02** | **Administração Geral & Auditoria** | `configuracoes`, `logs_auditoria`, `etl_sync_runs`, `etl_erros`, `usuarios` | [app/modules/admin/](app/modules/admin/) | [src/features/admin/](src/features/admin/) | `test_admin.py` | ✅ Concluído |
| **03** | **Polos & Escolas** | `polos`, `escolas` | [app/modules/polos_escolas/](app/modules/polos_escolas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **04** | **Professores & Docência** | `professores`, `professor_disciplinas`, `professor_materiais`, `atas_aula` | [app/modules/professores/](app/modules/professores/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **05** | **Alunos & Matrículas** | `alunos`, `alunos_desistentes` | [app/modules/alunos/](app/modules/alunos/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **06** | **Cursos & Matrizes** | `cursos` | [app/modules/cursos_disciplinas/](app/modules/cursos_disciplinas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **07** | **Disciplinas & Conteúdos AVA** | `disciplinas`, `disciplina_conteudos` | [app/modules/cursos_disciplinas/](app/modules/cursos_disciplinas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **08** | **Turmas & Calendários** | `turmas`, `calendarios_oficiais` | [app/modules/turmas/](app/modules/turmas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **09** | **Matrículas & Cursos EAD** | `matriculas_ead`, `compras_disciplina_ead`, `avisos_liberacao_ead`, `turma_alunos` | [app/modules/ead/](app/modules/ead/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **10** | **Grades, Notas & Histórico** | `notas`, `historico_unificado` | [app/modules/notas_historico/](app/modules/notas_historico/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **11** | **Certificados & Diplomas** | `certificados` | [app/modules/certificados/](app/modules/certificados/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **12** | **Presenças & Frequência** | `presencas` | [app/modules/presencas/](app/modules/presencas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **13** | **Licenças & Estoque** | `estoque_licencas`, `licencas_atribuidas` | [app/modules/licencas/](app/modules/licencas/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **14** | **Financeiro & Vendas** | `pedidos_licenca`, `pagamentos` | [app/modules/financeiro/](app/modules/financeiro/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **15** | **Cupons de Desconto** | `cupons` | [app/modules/cupons/](app/modules/cupons/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **16** | **Logística & Livros** | `pedidos_livros`, `pedidos_livros_itens` | [app/modules/pedidos_livros/](app/modules/pedidos_livros/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **17** | **Transferências Acadêmicas** | `solicitacoes_transferencia` | [app/modules/transferencias/](app/modules/transferencias/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |
| **18** | **Comunicação, Chat & Feed** | `conversas`, `conversa_membros`, `mensagens`, `feed_posts`, `lembretes`, `notificacoes` | [app/modules/comunicacao/](app/modules/comunicacao/) | Rotas & Sidebar Integrados | `test_modules_all.py` | ✅ Concluído |

---

## 3. Frontend NEXUS 2.0 (`nexus-frontend/`)

- [x] **Estrutura Separada**: Diretório isolado [nexus-frontend/](nexus-frontend/) com Vite 6 + React 18 + TailwindCSS + TypeScript.
- [x] **Zustand Auth Store**: Sessão 100% em memória (access_token, perfil, permissões), sem armazenamento vulnerável em `localStorage`.
- [x] **Axios Interceptor**: Auto-refresh transparente em requisições que retornam HTTP 401, com fila de sincronismo e logout seguro em caso de expiração.
- [x] **Guards de Rota**: `<RequireRole roles={[...]}>` e `<RequirePermissao permissao="..." />` para proteção de todas as áreas do sistema.
- [x] **Sidebar Dinâmica Multi-Perfil**: Menu lateral vertical retrátil renderizado dinamicamente para os 5 papéis (`admin`, `polo`, `escola`, `professor`, `aluno`), com badges de status e itens dos 18 módulos.
- [x] **Telas de Autenticação**: `LoginPage`, `EsqueciSenhaPage` e `RedefinirSenhaPage` com validações Zod e mensagens em PT-BR.
- [x] **Painel Administrativo Completo**:
  - `UsuariosInternosPage`: CRUD com seleção de perfil e checkboxes de permissões `p_*`.
  - `LogsAuditoriaPage`: Tabela filtrável com comparação lado a lado de `dados_antes` vs `dados_depois`.
  - `ConfiguracoesPage`: Edição de parâmetros chave/valor JSONB.
  - `ExecucoesBatchPage`: Monitoramento das execuções do ETL com detalhes de erros.
- [x] **Identidade Visual**: Logomarca oficial NEXUS 2.0 em SVG estilizado e paleta de cores temática.

## 4. Validação Integrada

- [x] **Suíte Backend**: `66 passed, 1 skipped` usando `.venv/Scripts/python.exe -m pytest -q`.
- [x] **Build Frontend**: `npm run build` concluído com TypeScript e Vite sem erros.
- [x] **API Local**: Uvicorn respondendo em `http://127.0.0.1:8000` e documentação HTTP `200`.
- [x] **Dev Server**: Vite disponível em `http://localhost:3000/` com proxy para a API local.
