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
