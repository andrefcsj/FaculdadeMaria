# FaculdadeMaria — piloto Cloudflare Free

Versão leve para manter o sistema dentro do plano gratuito:

- Worker JavaScript de baixo consumo de CPU, ligado ao D1;
- interface estática servida como asset;
- autenticação com PIN via secret e cookie assinado;
- operações, dashboard e backup manual no navegador;
- sem Python, PDF, R2 ou armazenamento de arquivos no servidor.

## Secrets necessários

```bash
npx wrangler secret put ADMIN_PIN --name faculdademaria-free-pilot
npx wrangler secret put SESSION_SECRET --name faculdademaria-free-pilot
```

## Publicação

```bash
npx wrangler deploy
```

O endereço de teste é `https://free-pilot.radarpulse.com.br/faculdademaria/`.
