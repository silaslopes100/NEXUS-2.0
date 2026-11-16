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
| `ENVIRONMENT` | Sim | Use `production` no Vercel. |
| `JWT_SECRET` | Sim | Segredo aleatório forte, exclusivo da produção. |
| `PG_DSN` ou `DATABASE_URL` | Sim | Connection string do PostgreSQL no Neon. Prefira a URL com pooling para funções serverless. |
| `CORS_ORIGINS` | Sim | Origens exatas do frontend, sem barra final e separadas por vírgula; por exemplo `https://<frontend>.vercel.app` e seu domínio próprio, se houver. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | Se usados | Configuração do serviço de e-mail para fluxos que enviam mensagens. |

Crie um **Vercel Blob privado** e conecte-o ao projeto da API. A conexão injeta
`BLOB_STORE_ID` e a autenticação OIDC para o SDK Python; não cadastre tokens de
Blob manualmente. Os endpoints de fotos mantêm a validação e autenticação da API
e leem/gravam nesse Blob em produção. Em desenvolvimento continuam usando o
diretório local.
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
| `CRON_SECRET` | Sim | Segredo aleatório. A Vercel envia `Authorization: Bearer <CRON_SECRET>` ao chamar o cron. |

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
leitura autenticados de fotos e os fluxos de e-mail configurados. Teste também
os domínios Preview separadamente; cada origem necessária deve constar em
`CORS_ORIGINS`.
