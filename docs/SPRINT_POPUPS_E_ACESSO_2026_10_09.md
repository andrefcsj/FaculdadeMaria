# CF-03 — Importação, janelas móveis e acesso

Autorização de Andre em 09/10/2026: fechar o popup ao concluir a última negociação da nota, permitir movimentar todos os popups e alterar o PIN de acesso.

Branch: `cloudflare-migration-prep`. Sem merge na main e sem notas/operações de teste na base real.

## Mudanças

- A importação mantém a janela aberta quando ainda existe negociação pendente. Somente após todas serem registradas (ou reconhecidas como duplicadas), fecha o popup, limpa PDF e formulário e mostra Operações Abertas com confirmação da conclusão.
- Erros mantêm a janela e os dados preenchidos. O índice selecionado permanece disponível para repetir a negociação que falhou, sem reaplicar as anteriores.
- Todos os dez tipos de popup do sistema podem ser movidos pelo cabeçalho com mouse, toque ou caneta. Botões e campos continuam recebendo seus próprios cliques; clique duplo no cabeçalho centraliza a janela. A posição também volta ao centro ao reabrir ou redimensionar a tela.
- O cabeçalho permanece acessível mesmo quando parte da janela é arrastada para fora da tela. O fundo não fica desfocado, permitindo consultar informações da página atrás.
- Confirmações e edição de valores antes exibidas em janelas nativas do navegador passam para um dialog do aplicativo. Mantidos confirmar, cancelar, Escape e valores retornados; cancelamento não grava alterações.
- O PIN foi atualizado exclusivamente no secret `ADMIN_PIN` do Worker; não é armazenado nos arquivos versionados.

## Validação

- Regressão em SQLite isolado e navegador Chromium, 1440 px e 390 px: PDF sintético pesquisável com duas vendas; primeira mantém a janela, última fecha, limpa e navega para abertas.
- Falha controlada no envio da última negociação mantém dados e janela; nova tentativa conclui sem duplicar. PDF inválido mantém a janela sem criar notas/operações.
- Arraste e recentralização dos nove popups preexistentes e do novo diálogo de confirmação/valor. Teste de arraste por toque no celular. Nenhum erro JavaScript.
- Sem desfoque no backdrop de todas as janelas; confirmar valor preserva a entrada e Escape devolve cancelamento.
- 24 testes de API/domínio aprovados. Sintaxe e diff validados.
- Teste reproduzível: `scripts/test_popup_workflow.cjs`, usando Playwright e Node com `node:sqlite`. O script gera o próprio PDF em `tmp/` e usa a mesma versão fixada de PDF.js do aplicativo.

## Publicação e dados

Atualização publicada no www e no piloto. Novo PIN aceito (HTTP 200) e anterior rejeitado (HTTP 401). Login manual e automático pelo link conferidos no navegador em 1440 px e 390 px, junto com arraste, ausência de desfoque e cancelamento. Nenhum erro JavaScript. Backups da base ativa antes/depois comparados: nenhuma operação, nota, lote, movimentação, DARF, preferência, cotação manual ou configuração adicionada, removida ou alterada. Evidências em `tmp/popup-2026-10-09/` (fora do Git).
