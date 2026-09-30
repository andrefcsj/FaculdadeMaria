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

O Worker só aceita requisições sob `/faculdademaria/`. A middleware preserva o
prefixo em `url_for`, que é a base para migrar as rotas reais sem links que
escapem para a raiz de `www.radarpulse.com.br`.

Os endpoints que leem dados (`/api/operations`, `/api/config` e
`/api/closed-operations`) exigem o secret `PILOT_ACCESS_TOKEN` no cabeçalho
`Authorization: Bearer ...`. Isso é obrigatório antes de enviar qualquer dado
real de homologação ao D1.

`POST`, `PUT` e `DELETE /api/operations/<id>` usam a mesma proteção e permitem
validar a escrita de operações no banco-piloto. Eles não são ligados à produção
e não substituem ainda os formulários originais.

`/api/outbound-probe` valida o padrão de HTTP síncrono empregado atualmente por
integrações de mercado, sem utilizar tokens nem chamar nenhum fornecedor do
projeto.
