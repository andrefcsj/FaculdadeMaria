# Sprint — Importação de ativos à vista e cancelamento da nota

Data: 2026-09-09

## Correções

- O cadastro de operação reconhece `equity_purchase` e `equity_sale` da nota. Essas negociações reutilizam o serviço de importação da carteira, sem criar PUT/CALL e sem exigir strike ou vencimento.
- O popup mostra preço unitário e unidades reais para ativos à vista, preservando o código completo (por exemplo, LFTB11). Os valores importados ficam somente para conferência; o registro usa os dados da nota.
- Cancelar, fechar pelo X, Escape ou fundo descarta formulário, arquivo selecionado, negociação atual, progresso e confirmação de encerramento. Respostas atrasadas de leitura, consulta e prévia não repovoam a tela.
- Notas mistas continuam sendo salvas negociação a negociação. Ao passar para uma opção, strike e vencimento voltam a ser obrigatórios.

## Validação

- Suíte Python: 293 testes aprovados; sintaxe Python validada.
- Chromium/Playwright: importação de 37 unidades sem strike, quatro formas de cancelamento, leitura atrasada, nota mista e consulta antiga para o mesmo código após reimportação.
- Teste de menu desatualizado alinhado à navegação existente; sua falha foi reproduzida no commit original.

Para executar os testes de navegador, disponibilize `playwright` no Node, instale Chromium (`npx playwright install chromium`) e execute `node --test tests/new_operation_modal.test.cjs`.

## Escopo

Não altera regras de preço médio fiscal nem registros já persistidos. A venda à vista mantém a validação de quantidade livre na carteira e a prevenção de duplicidade existentes.
