# ETL legado MySQL → NeonDB — Mapeamento e Premissas

Fonte: dicionário de dados do legado (banco `teo-eadetademp`, 62 tabelas) e plano técnico NEXUS 2.0.

## Como rodar

```bash
cd nexus-backend
# 1) crie o .env a partir do exemplo e preencha as credenciais
copy .env.example .env

# 2) valide conexoes e colunas sem tocar no destino
.venv\Scripts\python.exe -m batch.legacy_sync.main --mode=full --dry-run

# 3) carga inicial (cria schema + migra tudo + gera relatorio_baseline.md)
.venv\Scripts\python.exe -m batch.legacy_sync.main --mode=full

# 4) atualizacao diaria (agendar ~03:00 America/Sao_Paulo)
.venv\Scripts\python.exe -m batch.legacy_sync.main --mode=incremental

# opcional: rodar apenas um mapper
.venv\Scripts\python.exe -m batch.legacy_sync.main --mode=full --only=UsuarioMapper
```

Agendamento sugerido no Windows: Agendador de Tarefas chamando o passo 4; em servidor Linux, `cron`/systemd timer; alternativa gerenciada via GitHub Actions com `schedule`.

## Regras gerais da migração

- Toda tabela nova com origem no legado mantém `legacy_table`, `legacy_id`, `synced_at`
  e `UNIQUE (legacy_table, legacy_id)` → o batch é **idempotente** (`ON CONFLICT DO UPDATE`).
- Conexão ao MySQL é **somente leitura** (SELECT); crie um usuário dedicado com grant `SELECT`.
- Erro por linha é isolado (savepoint/registro) e gravado em `etl_erros` — o batch nunca para.
- Cada execução fica em `etl_sync_runs` (modo, totais, status).
- `--dry-run` compara as colunas esperadas (dicionário) com as colunas reais do MySQL.

## Mapeamento tabela a tabela

| Destino | Origem (MySQL) | Regra / premissa |
|---|---|---|
| `perfis` | `role` + seed | Garante os 5 padrões (admin, polo, escola, professor, aluno); importa linhas da `role` |
| `polos` | `users` (distinto por `users.polo`) | Polo vive dentro do user; legacy_id = valor de `users.polo`; responsável = user de menor id do polo |
| `escolas` | `users` (distinto por `users.escola`) | legacy_id = valor de `users.escola`; `polo_id` vindo de `users.polo` |
| `usuarios` | `users` | Perfil por `role_id` ou heurística por flags (`is_pedag/is_exec/is_secret`→admin, `is_instructor`→professor, `is_vendedor`→polo, polo→polo, escola→escola, resto→aluno). e-mail/CPF duplicados → `NULL` (unicidade parcial). Senha migrada como `legacy_bcrypt` p/ lazy rehash |
| `professores` | `users` (is_instructor/vendedor) | chave_pix e valor_hora_aula são campos novos → NULL |
| `alunos` | `users` (não staff/instrutor/vendedor) | matrícula = `users.codigo` ou `legacy-<id>`; modalidade polo se tem polo/escola; `revalidacao` preenchida → status `desistente` |
| `cursos` | `pacotes` | Em produção, a tabela que descreve os cursos (título/modalidade/preço/status) é `pacotes`. A tabela `course` do dicionário não corresponde ao schema real e foi descontinuada no mapper |
| `disciplinas` | `section` | semestre = `section.order`; `qtd_aulas_prevista` = count de lessons da section |
| `disciplina_conteudos` | `lesson` | conteúdo do AVA; tipo_midia/url de `lesson_type`/`video_type`/`video_url`/`linkMeet` |
| `calendarios_oficiais` | `section` (`datainicio`/`datafinal`) | calendário global por curso/disciplina |
| `turmas` | — | **sem origem legado confiável**; tabela criada vazia (dado novo do sistema) |
| `matriculas_ead` | `enrol` | `user_id`/`course_id` TEXT podem ter vários ids → usa o primeiro; classificação Polo×EAD a revisar com a equipe |
| `notas` | `quiz` | origem='ava'; valor = resultado (0–10) |
| `historico_unificado` | computado | pós-pass: `nota_final = MAX(notas.valor)` por (aluno, disciplina); status aprovado ≥ 6.0 |
| `presencas` | `presenca` | aula assistida (progress>0) = presente; % = presentes / aulas previstas |
| `licencas_atribuidas` | `licences` | atribuição por polo; vínculo course/pacote → `disciplina_id` NULL (revisar) |
| `estoque_licencas` | — | sem 1:1 no legado; inicia vazio (novo módulo Vendas controla) |
| `pedidos_livros` (+itens) | `p_livros` | status int→string ajustável (`PEDIDO_STATUS`); polo do pedido via usuário→polo |
| `pagamentos` | `pagamento`, `pagseguro_transaction`, `offline_payment` | gateway preservado (asaas/pagseguro); mapeamento de status int ajustável (`STATUS_INT`) |
| `conversas` | `message_thread` | 1 conversa por `message_thread_code` (dedup) |
| `conversa_membros` | `message_thread` (sender/receiver) | sem tracking; `ON CONFLICT (conversa_id, usuario_id) DO NOTHING` |
| `mensagens` | `message` | conversa resolvida pelo thread_code; remetente inexistente → NULL |
| `certificados` | `certificates` | datas dos 2 estágios são campos novos → NULL |
| `cupons` | `coupons` | `discount_percentage` varchar → NUMERIC |
| `configuracoes` | `settings`, `frontend_settings`, `customize` | chave prefixada com a origem (`settings.<key>`) |
| `feed_posts` | `blogs` | autorização de postagem é do módulo Notificações |
| `lembretes` | `noticeboard` | só os ativos |

## Premissas que exigem confirmação da equipe

1. **Perfil por flags** (usuarios): a heurística assume que `is_pedag`/`is_exec`/`is_secret`
   são equipe central (admin). Confirmar com a operação.
2. **Polo/Escola extraídos de `users`**: os backups (`polos_backup_moraro_*`,
   `users_polo_backup_*`, etc.) foram ignorados por serem ponto-no-tempo.
3. **`enrol` → `matriculas_ead`**: todas as linhas vão para a mesma tabela; a separação
   Polo vs EAD será refinada.
4. **Status int** (`users.status`, `p_livros.status`, `pagseguro.status`): sem dicionário
   no legado; os mapeamentos usados estão em constantes ajustáveis nos mappers.
5. **`estoque_licencas` vazio e `disciplina_id` NULL em licenças**: o saldo de estoque
   por disciplina não existia no legado — validar antes de liberar.
6. **e-mails/CPFs duplicados** ficam `NULL` (não bloqueiam login); listados como aviso
   na execução para auditoria manual.