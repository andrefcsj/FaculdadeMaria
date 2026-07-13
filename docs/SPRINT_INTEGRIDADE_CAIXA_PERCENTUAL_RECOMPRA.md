# Sprint — Integridade do Caixa e Percentual da Recompra

**Data:** 12/07/2026  
**Status:** Em revisão

## Objetivo

Eliminar lançamentos financeiros duplicados derivados de notas de corretagem e exibir no encerramento a parcela do prêmio preservada após a recompra.

## Correção do livro-caixa

Problema identificado:

- a operação era adicionada uma vez de forma incondicional;
- operações sem vínculo reconhecido eram adicionadas novamente;
- a nota importada também gerava o crédito real.

Regra corrigida:

- com nota vinculada, somente o crédito ou débito líquido da nota entra no caixa;
- sem nota, somente o valor calculado da operação manual entra no caixa;
- vínculo é reconhecido pelo ID da operação ou pelo código da opção;
- notas repetidas com a mesma identidade documental e negociação são deduplicadas;
- encerramentos posteriores continuam gerando recompra ou exercício normalmente.

As linhas do extrato são calculadas a cada carregamento. Portanto, duplicações causadas pela regra antiga desaparecem automaticamente após a implantação, sem excluir a operação nem a nota válida.

## Percentual de lucro da recompra

O modal passa a mostrar `Lucro sobre o prêmio` ao lado de `Resultado final`.

Fórmula:

`(prêmio unitário recebido - recompra unitária) / prêmio unitário recebido × 100`

Exemplo:

- prêmio unitário: `R$ 0,33`;
- recompra unitária: `R$ 0,06`;
- prêmio preservado: `81,82%`.

O resultado financeiro continua considerando quantidade, tamanho do contrato, custos e IRRF conforme as regras existentes.

## Validação

- operação vinculada à nota aparece uma única vez;
- vínculo legado divergente é recuperado pelo código da opção;
- notas repetidas não multiplicam o caixa;
- recompra posterior permanece debitada;
- suíte automatizada completa.
