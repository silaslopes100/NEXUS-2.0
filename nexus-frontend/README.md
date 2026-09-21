# NEXUS 2.0 Frontend

Sistema de Gestão Educacional Teológica - Interface Administrativa

## Stack Tecnológica

- **React 18** + **TypeScript**
- **Vite** como bundler
- **Tailwind CSS** para estilização
- **TanStack Query (React Query)** para gerenciamento de estado servidor
- **React Hook Form** + **Zod** para formulários e validação
- **Radix UI** para componentes acessíveis
- **React Router v6** para roteamento
- **Axios** para requisições HTTP
- **Lucide React** para ícones
- **React Hot Toast** para notificações
- **Recharts** para gráficos
- **jsPDF** para geração de PDFs no cliente

## Estrutura do Projeto

```
nexus-frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Componentes base (Button, Input, Select, Dialog, Table, etc.)
│   │   ├── layout/       # Sidebar, Header, Layout principal
│   │   ├── auth/         # ProtectedRoute
│   │   └── ToastProvider.tsx
│   ├── contexts/
│   │   ├── AuthContext.tsx    # Autenticação, permissões, multi-tenancy
│   │   └── QueryProvider.tsx  # TanStack Query provider
│   ├── hooks/              # Custom hooks
│   ├── lib/
│   │   ├── api.ts            # Cliente Axios configurado
│   │   └── utils.ts          # Utilitários (formatação, helpers)
│   ├── pages/
│   │   ├── dashboard/        # Dashboard interativa
│   │   ├── polos/            # CRUD Polos (RN-01)
│   │   ├── escolas/          # CRUD Escolas (RN-01)
│   │   ├── alunos/           # Gestão de alunos
│   │   ├── matriculas/       # Matrículas
│   │   ├── cursos/           # Cursos/Módulos/Matérias
│   │   ├── ead/              # EAD (RN-03)
│   │   ├── licencas/         # Licenças/Estoque
│   │   ├── financeiro/       # Financeiro
│   │   ├── logistica/        # Logística
│   │   ├── certificados/     # Certificados (RN-05)
│   │   ├── chat/             # Chat (RN-06)
│   │   ├── presencas/        # Presenças/Aulas (RN-07)
│   │   ├── notas/            # Notas/Histórico
│   │   ├── churn/            # Churn/Requisições (RN-04)
│   │   ├── certificados/     # Certificados
│   │   ├── chat/             # Chat
│   │   ├── configuracoes/    # Configurações
│   │   ├── perfil/           # Perfil do usuário
│   │   └── LoginPage.tsx
│   ├── types/
│   │   └── index.ts          # Tipos TypeScript (espelham schemas do backend)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── index.html
```

## Funcionalidades Implementadas

### ✅ Autenticação e Autorização
- Login com JWT
- Context de autenticação com perfis e permissões
- Multi-tenancy automático (admin/secretario_geral = global, coordenador_polo = polo, secretario_escola = escola)
- ProtectedRoute para rotas protegidas

### ✅ Layout Responsivo
- Sidebar colapsável (mobile/desktop)
- Header com busca, tema dark/light, menu do usuário
- Breadcrumbs automáticos

### ✅ Dashboard Interativa
- 6 cards clicáveis com contadores (Alunos, Matrículas, Polos, Escolas, Professores, Certificados)
- Ações rápidas
- Ranking de polos
- Vendas do mês
- Alertas do sistema

### ✅ Módulo Polos (RN-01)
- CRUD completo
- Cadastro unificado: cria polo + coordenador automaticamente
- Sincronização de dados ao editar
- Desativação em cascata (polo + coordenador)
- Filtros: busca, status, paginação

### ✅ Módulo Escolas (RN-01)
- CRUD completo
- Cadastro unificado: cria escola + secretário automaticamente
- Vinculação obrigatória a polo
- Sincronização de dados ao editar
- Desativação em cascata (escola + secretário)

### ✅ Componentes UI Base
- Button (variant: default, destructive, outline, secondary, ghost, link)
- Input, Textarea, Select, Label
- Dialog, DropdownMenu, Tooltip
- Table com paginação
- Card, Badge, Toast
- Form com React Hook Form + Zod

### ✅ Tipagem TypeScript Completa
- Todos os tipos espelham os schemas Pydantic do backend
- Interfaces para: User, Polo, Escola, Curso, Modulo, Materia, Aluno, Matricula, etc.

### ✅ Internacionalização (pt-BR)
- Formatação de moeda (BRL), datas, CPF
- Labels de perfis e permissões em português

## Regras de Negócio no Frontend

| Regra | Implementação |
|-------|---------------|
| **RN-01** | Cadastro unificado Polo/Coordenador e Escola/Secretário nos forms |
| **RN-02** | Contexto `getActorContext()` aplica scoping automático por perfil |
| **RN-03** | Validação de 2 matérias/mês no módulo EAD |
| **RN-04** | Módulo Churn com reingresso (taxa R$100 ou 2 licenças) |
| **RN-05** | Validação de 2 estágios + histórico completo antes de emitir certificado |
| **RN-06** | Chat proíbe aluno↔aluno, admin pode baixar conversas |
| **RN-07** | Cálculo de % presença = presenças / total_aulas_previstas * 100 |

## Multi-tenancy UI

O contexto `AuthContext` expõe:
- `getActorContext()` - retorna objeto com `user_id`, `perfil`, `global_view`, `polo_id`, `escola_id`
- `hasPermission(perm, allowRoles)` - verifica permissão granular
- `isGlobalView()` - true para admin/secretario_geral

As páginas usam esse contexto para enviar o actor nas requisições, e o backend aplica o scoping automaticamente.

## Como Executar

```bash
cd nexus-frontend
npm install
npm run dev
```

A aplicação estará disponível em `http://localhost:3000`

## Build de Produção

```bash
npm run build
```

Os arquivos otimizados serão gerados em `dist/`.

## Variáveis de Ambiente

Crie `.env` na raiz:

```env
VITE_API_URL=http://localhost:8000/api
```

## Estrutura de Rotas

```
/login                    # Login público
/dashboard                # Dashboard principal
/polos                    # Lista de polos
/polos/:id                # Detalhe do polo
/polos/novo               # Novo polo (dialog)
/escolas                  # Lista de escolas
/escolas/:id              # Detalhe da escola
/escolas/novo             # Nova escola (dialog)
/alunos                   # Lista de alunos
/alunos/:id               # Perfil + histórico + presenças
/matriculas               # Lista de matrículas
/cursos                   # Cursos/Módulos/Matérias
/ead                      # EAD (matrículas, calendário, feed)
/licencas                 # Licenças/Estoque
/financeiro               # Vendas/Boletos
/logistica                # Pedidos de livros
/certificados             # Certificados
/chat                     # Chat
/configuracoes            # Configurações
/perfil                   # Perfil do usuário
```

## Próximos Passos

1. Completar páginas restantes (Alunos, Cursos, EAD, Licenças, Financeiro, Chat, Certificados, Presenças, Notas, Churn)
2. Implementar geração de PDFs com jsPDF
3. Adicionar gráficos com Recharts no Dashboard
4. Testes unitários com Vitest + React Testing Library
5. Configurar CI/CD
6. PWA para uso offline