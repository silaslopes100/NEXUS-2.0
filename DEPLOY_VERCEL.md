# Deploy do NEXUS 2.0 no Vercel

O repositório contém dois aplicativos que devem ser conectados ao mesmo
repositório Git como projetos Vercel separados:

1. **Frontend** — diretório raiz `nexus-frontend`, preset Vite, comando de build
   `npm run build` e diretório de saída `dist`. O arquivo `vercel.json` nessa
   pasta encaminha rotas do React Router para o `index.html`.
2. **API** — diretório raiz `nexus-backend`, preset FastAPI/Python. O Vercel
   detecta a aplicação FastAPI em `app/main.py` e instala dependências de
   `requirements.txt`.

## Variáveis de ambiente

Configure os valores sensíveis apenas no painel do Vercel, nos ambientes
Production e Preview conforme necessário. Não versione nem copie valores de
`nexus-backend/.env`.

### Projeto da API

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `ENVIRONMENT` | Sim | Use `production` em Production e Preview no Vercel. |
| `JWT_SECRET` | Sim | Segredo aleatório forte, distinto para Production e Preview. |
| `PG_DSN` ou `DATABASE_URL` | Sim | Connection string do PostgreSQL no Neon. Prefira a URL com pooling para funções serverless. |
| `CORS_ORIGINS` | Sim | Origens exatas do frontend, sem barra final e separadas por vírgula; por exemplo `https://<frontend>.vercel.app` e seu domínio próprio, se houver. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | Se usados | Configuração do serviço de e-mail para fluxos que enviam mensagens. |

Antes do deploy, habilite **Enable access to System Environment Variables** no
projeto da API. Quando a Vercel expõe `VERCEL=1`, a aplicação recusa iniciar em
Production ou Preview se `ENVIRONMENT` não for `production`; com as variáveis
de sistema desabilitadas, essa proteção não detecta o deploy. Esse valor também
ativa as validações de segurança, banco e CORS: confira as variáveis necessárias
em cada ambiente antes de publicar. Use banco, segredo e origens adequados ao
Preview, sem compartilhar dados de produção inadvertidamente.

Crie dois **Vercel Blobs privados**, conectando um exclusivamente a Production
e outro exclusivamente a Preview no projeto da API. A conexão injeta
`BLOB_STORE_ID` e disponibiliza autenticação OIDC para o SDK Python; não copie
credenciais para o repositório. Fotos e arquivos acadêmicos usam o Blob no modo
`production`; em desenvolvimento local continuam usando o diretório local.
Antes de trocar uma conexão existente, avalie os arquivos já armazenados: as
referências no banco não transferem os objetos entre stores automaticamente.
Após alterar variáveis ou conexões, gere novos deployments dos ambientes afetados.
O limite de upload é 4 MB para que o multipart permaneça abaixo do limite de
requisição das funções Vercel.

### Projeto do frontend

Configure `VITE_API_BASE_URL` com a URL pública da API, sem barra final, por
exemplo `https://<api>.vercel.app`. Como o valor é incorporado ao build do Vite,
configure-o também nos ambientes e gere um novo deploy após alterá-lo.

### Pagamentos (Financeiro & Logística)

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `PAYMENT_ENV` | Sim | `sandbox` ou `producao`: ambiente dos gateways usado nas novas cobranças. |
| `PAYMENT_SECRETS_KEY` | Sim | Chave Fernet que criptografa as credenciais dos gateways no banco. Gere com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Trocar a chave obriga a recadastrar as credenciais. |
| `PUBLIC_API_URL` | Sim | URL pública da API, sem barra final. Base das URLs de webhook (`{PUBLIC_API_URL}/financeiro/webhooks/{gateway}/{ambiente}`). |
| `CRON_SECRET` | Sim | Segredo aleatório. A Vercel envia `Authorization: Bearer <CRON_SECRET>` ao chamar o cron (`/financeiro/cron/reconciliar` e `/chat/cron/rotacionar`). |
| `CHAT_BLOB_READ_WRITE_TOKEN` | Sim (chat) | Token read-write de um Blob store **público** criado só para os anexos do chat (separado do store privado dos materiais). O navegador envia os arquivos direto a esse store; as URLs têm caminho aleatório e só são entregues aos membros da conversa. Sem ele, os anexos ficam em disco (apenas desenvolvimento). |

**Chat:** aplique `scripts/migrations/024_chat.sql`. O cron diário
`/chat/cron/rotacionar` move as mensagens com mais de 48h para
`chat_mensagens_historico` e apaga do histórico (e do Blob) o que passou de 90 dias.

As credenciais de cada gateway (API Key do Asaas, token do PagBank, access
token do Mercado Pago e tokens de webhook) **não** vão em variáveis de
ambiente: são cadastradas pelo admin na tela **Gateways de Pagamento** e ficam
criptografadas na tabela `gateways_config`.

O arquivo `nexus-backend/vercel.json` agenda `GET /financeiro/cron/reconciliar`
uma vez por dia (limite do plano Hobby). No plano Pro, reduza o intervalo (por
exemplo `*/30 * * * *`). O cron reprocessa webhooks com erro e consulta nos
gateways as cobranças pendentes.

## Banco e dados existentes

Antes do primeiro deploy, confirme que o PostgreSQL está acessível pelo Vercel,
que o esquema e as migrações existentes foram aplicados e que o usuário da
aplicação tem as permissões necessárias. Não execute as migrações às cegas em um
banco com dados.

Para editar polos com dados fiscais, o banco da API deve ter a migração
[`018_polos_fiscal_gateway_clientes.sql`](./nexus-backend/scripts/migrations/018_polos_fiscal_gateway_clientes.sql).
Antes de aplicá-la, confirme o banco e o esquema corretos, faça backup e verifique
as migrações anteriores, incluindo a 016, que cria `webhook_eventos`. A 018 também
cria `gateway_clientes` e um índice de webhooks; se qualquer etapa falhar, sua
transação é revertida. Aplique-a pelo procedimento de migração do ambiente e
confirme as quatro colunas fiscais em `polos` antes de tentar novamente.

A listagem e o cadastro de Disciplinas leem a coluna `disciplinas.preco`: aplique
[`019_disciplinas_preco.sql`](./nexus-backend/scripts/migrations/019_disciplinas_preco.sql)
antes de publicar essa versão da API, ou a tela de Disciplinas falhará.

Calendário Acadêmico, carga horária, cronograma, tipos de ata e frequência (RN01–RN07)
dependem de [`029_calendario_carga_horaria.sql`](./nexus-backend/scripts/migrations/029_calendario_carga_horaria.sql):
aplique-a antes de publicar a API, ou cursos, turmas, Diário de Aulas e a Dashboard
falharão.
- Ela cria `calendarios_academicos` e `aulas_previstas`.
- Acrescenta colunas em `cursos`, `turmas` e `aulas_ministradas`.
- Instala o trigger que recalcula a carga do curso a partir das disciplinas.
- Cria o "Calendário Padrão" (aulas aos sábados, recesso em julho e dezembro) e
  vincula a ele os cursos existentes. Revise esse calendário na tela
  **Calendários Acadêmicos** antes de gerar cronogramas.

Depois da 029, aplique [`030_remover_calendarios_oficiais.sql`](./nexus-backend/scripts/migrations/030_remover_calendarios_oficiais.sql).
Ela apaga a tabela antiga `calendarios_oficiais` e a coluna `turmas.calendario_oficial_id`, que a API
não usa mais. É irreversível: faça backup antes se quiser guardar esses registros.

A ficha cadastral do usuário depende de [`033_ficha_cadastral.sql`](./nexus-backend/scripts/migrations/033_ficha_cadastral.sql):
aplique-a antes de publicar a API, ou a ficha em **Usuários** falhará. Ela acrescenta em `usuarios`
nascimento, documentos, naturalidade, contato de emergência e os campos de inativação, e copia
para `usuarios.data_nascimento` o nascimento já cadastrado em `alunos`. Nada é apagado.

O cadastro de turmas depende de [`034_turmas_cadastro.sql`](./nexus-backend/scripts/migrations/034_turmas_cadastro.sql):
aplique-a antes de publicar a API, ou Turmas, Disciplinas e o AVA falharão.
- Ela acrescenta em `turmas` código, modalidade, turno, horário, vagas, local, responsável e
  cancelamento, e em `disciplinas` o prazo EAD.
- Gera o código das turmas existentes e marca como EAD as turmas do polo "EAD".
- **Muda o início e o fim** das turmas abertas para a vigência do calendário do curso. Depois de
  aplicar, regere o cronograma das turmas na tela da turma.

O gateway **Simulador** (`fake`) existe só no sandbox, para testes sem chaves reais.
Ele é recusado em `producao`, e só o admin pode simular pagamentos.

Arquivos em `nexus-backend/uploads/profile_photos/` não são publicados com o
repositório. Se houver fotos existentes, migre-as para o Blob privado mantendo
os nomes registrados em `usuarios.foto_url` antes de apontar o frontend para a
API nova.

As rotinas em `nexus-backend/batch/` são scripts de execução separada e não
viram processos persistentes ao publicar a API como função Vercel. Planeje sua
execução fora do ciclo de requisição.

## Verificação

Após configurar os dois projetos, valide `/health` na URL da API, navegação
direta para uma rota interna do frontend, login, acesso ao PostgreSQL, envio e
leitura autenticados de fotos e arquivos acadêmicos e os fluxos de e-mail
configurados. `/health` deve informar `environment: production` tanto em
Production quanto em Preview. Confira que os arquivos de teste chegam ao Blob
correspondente e remova-os após o teste. Teste também os domínios Preview
separadamente; cada origem necessária deve constar em `CORS_ORIGINS`.
