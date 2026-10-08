# CF-02 — Corte de endereço e reversão

Preparação em 08/10/2026. A execução do corte e o desligamento do legado aguardam a aprovação final de Andre, conforme o escopo desta Sprint.

## Resultado disponível para revisão

Piloto: https://free-pilot.radarpulse.com.br/faculdademaria/?v=70

O código e os dados financeiros já estão no Cloudflare Free. A rota final foi preparada em `cloudflare/free-pilot/wrangler.cutover.jsonc`, sem aplicá-la. O www atualmente possui a rota abrangente `www.radarpulse.com.br/*`, atendida por `contabilidade-mensal`; `/faculdademaria/` redireciona e termina em 404. A nova rota específica de FaculdadeMaria deve coexistir com essa rota abrangente, preservando o restante do domínio.

## Corte, após aprovação

1. Baixar novo backup do piloto e da origem; comparar com os relatórios desta Sprint. A base ativa é D1: não substituir pelos dados antigos do Render.
2. Publicar somente a configuração preparada:

   ```bash
   npx wrangler deploy --config cloudflare/free-pilot/wrangler.cutover.jsonc
   ```

3. Conferir `/faculdademaria`, `/faculdademaria/`, login, arquivos e consultas no www, inclusive celular; verificar que a raiz do www continua atendida pelo sistema de contabilidade.
4. Validar uma nova sessão no endereço principal e a igualdade do backup financeiro. Manter o piloto como endereço de acesso alternativo.
5. Somente depois dessa conferência e da autorização de desligamento, retirar Render/Neon de serviço. Guardar os backups completos; nenhuma exclusão de projeto é parte do corte de rota.

## Reversão de rota

Reimplantar o código validado com a configuração que contém apenas o domínio do piloto:

```bash
npx wrangler deploy --config cloudflare/free-pilot/wrangler.jsonc
```

Confirmar a remoção somente da rota específica vinculada ao Worker FaculdadeMaria. A rota abrangente de contabilidade deve continuar igual ao snapshot anterior. O acesso ao piloto permanece. Reverter a rota não exige restaurar o banco.

## Reversão de código

A versão do Worker imediatamente anterior à CF-02, com o segredo de mercado configurado, é `9816fa81-13f7-49fc-8d7c-99af1a375ea7`. O histórico e os backups foram guardados localmente em `tmp/migration-2026-10-08/` (ignorado pelo Git).

```bash
npx wrangler rollback 9816fa81-13f7-49fc-8d7c-99af1a375ea7 --config cloudflare/free-pilot/wrangler.jsonc
```

A tabela aditiva `market_snapshots` pode permanecer: o código anterior a ignora. Não executar restauração financeira só para reverter código. Se houver incidente nos dados, congelar gravações, salvar a base atual e testar a recuperação em SQLite separado antes de propor a restauração de D1.
