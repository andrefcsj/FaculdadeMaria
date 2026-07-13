# Sprint — Cards, Gestão de Notas e Encerramento Assistido

**Data:** 12/07/2026  
**Status:** Em revisão

## Dashboard

- `Saldo na Corretora` passa a ser o primeiro card;
- novo card `Prêmios` mostra o total líquido histórico das vendas registradas;
- `Prêmios no Mês` permanece como indicador periódico;
- `ROI Projetado` é removido;
- `Capital Alocado` passa a se chamar `Capital Comprometido`.

## Exclusão de notas

- cada nota importada possui ação de exclusão;
- o sistema exige confirmação explícita;
- após excluir, notas, gráficos, livro-caixa e saldo são recalculados;
- a operação vinculada não é excluída automaticamente;
- sem a nota, a operação permanece como registro manual e volta a ser a origem do caixa quando aplicável.

## Encerramento assistido por nota

Uma compra é apresentada como possível encerramento quando:

- existe exatamente uma operação aberta com o mesmo código;
- a posição aberta é uma venda;
- a nova negociação é uma compra;
- a quantidade comprada é igual à quantidade aberta.

O usuário deve confirmar o encerramento. Após a confirmação:

- a operação aberta é encerrada;
- a recompra unitária vem da nota;
- custos e IRRF da compra reduzem o resultado realizado;
- a nota é vinculada à mesma operação;
- carteira, histórico, caixa e indicadores são recalculados.

Encerramentos parciais, quantidades superiores ou múltiplas posições com o mesmo código exigem conferência manual e não são executados automaticamente.

## Integridade financeira

Quando uma nota de compra registra a recompra, o livro-caixa usa o débito líquido dessa nota e não adiciona novamente o débito manual do encerramento.

## Validação

- fechamento integral por nota;
- bloqueio de fechamento parcial;
- exclusão de nota;
- recálculo do caixa com notas de abertura e fechamento;
- suíte automatizada completa.
