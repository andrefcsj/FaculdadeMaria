# CF-02 — Corte de endereço e reversão

Corte autorizado por Andre em 08/10/2026 (“pode sim. vlw”) e executado no mesmo dia. O desligamento do Render/Neon permanece pendente; a autorização desta etapa foi para ativar o endereço principal.

## Resultado disponível para revisão

Endereço principal ativo: https://www.radarpulse.com.br/faculdademaria/?v=70

Piloto alternativo: https://free-pilot.radarpulse.com.br/faculdademaria/?v=70

A rota `www.radarpulse.com.br/faculdademaria*` está ativa no Worker FaculdadeMaria. A rota abrangente `www.radarpulse.com.br/*` continua atendida por `contabilidade-mensal`. Antes do corte, `/faculdademaria/` terminava em 404. A configuração padrão `cloudflare/free-pilot/wrangler.jsonc` agora inclui o endereço principal, para que futuras publicações o preservem; `wrangler.cutover.jsonc` contém a mesma configuração. A raiz do www permanece igual à anterior.

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
npx wrangler deploy --config cloudflare/free-pilot/wrangler.pilot-only.jsonc
```

Confirmar a remoção somente da rota específica vinculada ao Worker FaculdadeMaria. A rota abrangente de contabilidade deve continuar igual ao snapshot anterior. O acesso ao piloto permanece. Reverter a rota não exige restaurar o banco.

## Reversão de código

A versão do Worker imediatamente anterior à CF-02, com o segredo de mercado configurado, é `9816fa81-13f7-49fc-8d7c-99af1a375ea7`. O histórico e os backups foram guardados localmente em `tmp/migration-2026-10-08/` (ignorado pelo Git).

```bash
npx wrangler rollback 9816fa81-13f7-49fc-8d7c-99af1a375ea7 --config cloudflare/free-pilot/wrangler.jsonc
```

A tabela aditiva `market_snapshots` pode permanecer: o código anterior a ignora. Não executar restauração financeira só para reverter código. Se houver incidente nos dados, congelar gravações, salvar a base atual e testar a recuperação em SQLite separado antes de propor a restauração de D1.

## Evidência do corte concluído

- Worker publicado: `6764c209-f02f-48b8-8d5a-5d9474afbce0`.
- Sem barra final: HTTP 302 para o endereço canônico com barra; com barra: HTTP 200.
- Nova sessão com PIN manual no desktop e entrada automática pelo link no celular; nove telas e calculadora conferidas, sem erros JavaScript.
- Backups autenticados pelo www comparados ao backup imediatamente anterior: nenhum registro financeiro, preferência, cotação manual ou configuração adicionado, removido ou alterado.
- Rota geral de contabilidade idêntica ao snapshot anterior; raiz do www HTTP 200 e HTML igual ao anterior.
- Evidências em `tmp/migration-2026-10-08/cutover-*` e `cloudflare-routes-after.json` (fora do Git). O novo pedido de backup do Render retornou 502; o backup completo validado antes do corte permanece guardado. A base ativa D1 foi salva imediatamente antes e depois da troca.
- Render/Neon não foram desligados nem excluídos.
