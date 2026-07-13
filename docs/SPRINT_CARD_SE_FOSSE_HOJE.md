# Sprint — Card “Se Fosse Hoje”

**Data:** 12/07/2026  
**Status:** Em revisão

## Objetivo

Adicionar ao Dashboard Executivo uma leitura direta das opções abertas mais próximas do vencimento, preservando integralmente o visual aprovado.

## Conteúdo do card

- `Opção`: código da opção aberta;
- `Dias`: dias restantes até o vencimento;
- `Seu Valor`: prêmio unitário registrado no cadastro;
- `Valor Atual`: cotação unitária da opção disponível no mercado carregado;
- `Situação`: se a opção seria ou não exercida considerando a cotação atual da ação e o strike.

São exibidas até cinco opções abertas, ordenadas pelo menor prazo.

## Fontes do Valor Atual

Ordem de prioridade:

1. preço manual confirmado;
2. B3 COTAHIST EOD;
3. CSV de mercado importado.

Se nenhuma fonte contiver o contrato, o card apresenta `Indisponível`. Nenhuma cotação é inventada.

## Regras de exercício

- PUT: seria exercida se a cotação da ação estiver no strike ou abaixo;
- CALL: seria exercida se a cotação da ação estiver no strike ou acima;
- sem cotação ou strike: situação não calculada.

## Ajustes em Atenção Necessária

- concentração deixa de gerar alertas;
- PUT ou CALL dentro do dinheiro só gera criticidade quando faltarem 10 dias ou menos;
- vencimento e ausência de dados continuam sendo motivos independentes.

## Validação

- cenários de prazo e exercício;
- prioridade das cotações reais;
- ordenação por vencimento;
- suíte automatizada completa.
