# Ambiente-piloto Cloudflare

Este diretório contém exclusivamente a prova de conectividade da migração.

- Worker: `faculdademaria-pilot`;
- banco D1: `faculdademaria-pilot`;
- URL provisória: `https://faculdademaria-pilot.radarpulse.com.br`;
- subdomínio próprio, sem alterar `www.radarpulse.com.br` ou acessar dados de produção.

O endpoint `/health` confirma que o Worker e o D1 estão ativos. A aplicação Flask só será introduzida após a camada de persistência ter sido adaptada e testada.

As migrações D1 ficam em `migrations/`. A primeira cria somente a estrutura das tabelas do sistema, sem importar dados operacionais.

## Importação auditável de dados locais

O utilitário `tools/export_local_data.py` converte os CSVs locais em SQL para
o D1, mas não acessa credenciais, não conecta ao Cloudflare e não executa o
arquivo produzido. A saída deve ficar fora do Git e ser revisada antes de uma
importação de homologação:

```bash
python3 cloudflare/pilot/tools/export_local_data.py \
  --data-dir data \
  --output cloudflare/pilot/generated/import.sql

npx wrangler d1 execute faculdademaria-pilot --remote \
  --file cloudflare/pilot/generated/import.sql
```

O SQL não inclui `BEGIN`/`COMMIT`: a API de importação do D1 gerencia a
execução e rejeita transações SQL explícitas nesse formato.

O comando acima só poderá ser usado depois de comparar os dados e confirmar a
origem correta (CSV ou base PostgreSQL de produção). Nesta fase nenhum dado
real é enviado automaticamente.
