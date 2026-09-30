# Piloto Flask no Cloudflare Workers

Este Worker valida a camada WSGI usada pelo projeto FaculdadeMaria antes da
migração das rotas e da persistência reais. Ele é propositalmente isolado e
não recebe tráfego do domínio de produção nem altera dados de produção.

## Publicação

Com `uv` e `pywrangler` instalados:

```bash
uv run pywrangler deploy
```

O endpoint `/health` confirma que Flask está sendo atendido pelo runtime Python
do Cloudflare Workers.

`/api/d1-health` confirma a ponte entre o handler Flask síncrono e o binding
assíncrono do D1. Os endpoints `/api/operations` e `/api/config` usam a primeira
camada de leitura reutilizável. Durante a homologação, o banco permanece vazio;
dados reais só serão copiados por uma importação explicitamente auditada.

`/api/pdf-compatibility` gera um PDF em memória com ReportLab e o abre com
PyPDF. Ele existe apenas como teste de compatibilidade do runtime.
