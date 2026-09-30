# Sprint CF-01 — Preparação segura para migração ao Cloudflare

**Status:** Em andamento  
**Branch:** `cloudflare-migration-prep`  
**Objetivo:** preparar uma migração reversível para Cloudflare, sem alterar a produção atual no Render.

## Regra de segurança

O serviço atual no Render continua sendo a produção durante toda esta sprint. Nenhum DNS de produção, `render.yaml`, credencial de produção ou base de dados será alterado nesta etapa.

O corte só poderá ser considerado depois de todos os critérios abaixo terem sido homologados em um endereço de teste e com um backup real restaurado.

## Inventário confirmado em 30/09/2026

- Aplicação monolítica Flask/Python, iniciada por `app.py` e apoiada por `legacy_app.py`.
- Produção atual configurada em `render.yaml` com Gunicorn e Python 3.12.13.
- 68 rotas HTTP identificadas, incluindo APIs de criação, edição, exclusão, importação, backup e restauração.
- 165 referências a URLs absolutas iniciadas em `/` foram identificadas em templates e JavaScript. Elas precisam passar a respeitar o prefixo `/faculdademaria/`; esse ajuste será tratado como uma migração específica, com testes de regressão, e não como substituição cega de texto.
- Interface renderizada no servidor com Jinja (`templates/`) e arquivos estáticos em `static/`.
- Persistência híbrida:
  - PostgreSQL/Neon quando `DATABASE_URL` está configurada;
  - CSV/JSON local e SQLite como caminhos alternativos ou complementares;
  - arquivos de mercado e preferências em `data/`.
- Integrações externas: SLDX, B3/CVM e Yahoo Finance.
- Recursos sensíveis à plataforma: importação de PDF (`pypdf`), geração de DARF PDF (`reportlab`), ZIP de backup/restauração e gravação atômica de arquivos.

## Decisão arquitetural inicial

O destino de teste será um **Cloudflare Python Worker com Flask**, não Cloudflare Pages isoladamente. O Worker atenderá a aplicação e os assets; a rota de produção final será avaliada sob o prefixo:

`https://www.radarpulse.com.br/faculdademaria/`

O projeto não deve depender de armazenamento local no Worker. A proposta de destino é:

| Uso atual | Destino candidato | Condição para aprovar |
| --- | --- | --- |
| Dados relacionais operacionais | D1 | esquema, importação e testes de escrita/leitura aprovados |
| Backups e arquivos persistentes | R2 | upload, download e restauração aprovados |
| Segredos (`SLDX_API_TOKEN`, PIN administrativo) | Secrets do Worker | nunca versionados nem expostos ao navegador |
| Dados de mercado temporários | D1 ou R2, conforme acesso | expiração e atualização validadas |
| PostgreSQL/Neon | mantido somente durante transição | desligado apenas após a migração completa de dados |

## Itens que exigem protótipo obrigatório

1. Compatibilidade de `pypdf` e `reportlab` no Python Workers.
2. Acesso do Flask a D1/R2 no runtime Python.
3. Ajuste do prefixo `/faculdademaria/` em todos os links, redirecionamentos, formulários e chamadas JavaScript absolutas.
4. Substituição das escritas em `data/` por persistência remota.
5. Chamadas externas e atualização concorrente de cotações sem `ThreadPoolExecutor` do ambiente atual.
6. Backup completo e restauração com dados reais em ambiente de teste.

## Critérios de aceite antes do corte

- Suíte oficial executada com Python 3.12.13 e dependências do projeto.
- Dashboard, operações, carteira, caixa, DARF, notas, Radar, importação CSV e backup/restauração homologados.
- Teste de caminho completo em `/faculdademaria/`, inclusive URLs internas e arquivos estáticos.
- Dados de teste restaurados e conferidos contra a origem.
- Segredos configurados no Cloudflare; nenhum segredo em Git.
- Render permanece disponível durante o período de validação.
- Troca de DNS/rota executada apenas com autorização explícita do Product Owner.

## Bloqueio atual de ambiente local

A máquina disponível possui apenas Python 3.9.6. O repositório fixa Python 3.12.13 e usa recursos indisponíveis no 3.9 (`dataclass(..., slots=True)`), além de depender de pacotes ainda não instalados (`Flask`, `python-dotenv` e `pytest`).

Resultado da tentativa de baseline: a suíte não é executável neste interpretador. Antes de homologar código, será necessário disponibilizar Python 3.12.13 em ambiente isolado e instalar `requirements-dev.txt`.
