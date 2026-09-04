# ETL / sincronizacao entre o sistema legado (MySQL) e o NEXUS 2.0 (PostgreSQL / NeonDB).
# Estrutura:
#   config.py            - credenciais via .env
#   source_mysql.py      - leitura do MySQL legado (somente SELECT)
#   target_postgres.py   - escrita no NeonDB (upserts idempotentes)
#   schema.py            - DDL do destino
#   etl_sync_log.py      - bookkeeping (etl_sync_runs / etl_erros)
#   registry.py          - cache legacy_id -> uuid
#   run_full_load.py     - carga inicial (baseline)
#   run_incremental.py   - atualizacao diaria
#   main.py              - CLI
#   mappers/             - transformacao linha legado -> linha nova