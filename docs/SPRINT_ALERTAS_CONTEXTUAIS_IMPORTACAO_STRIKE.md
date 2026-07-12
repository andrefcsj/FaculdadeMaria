# Sprint — Alertas Contextuais e Importação de Strike

**Data:** 12/07/2026  
**Status:** Em revisão

## Objetivo

Tornar a leitura do painel Atenção Necessária tecnicamente precisa e recuperar automaticamente strike e vencimento após a importação de nota BTG/Necton.

## Alertas contextuais

- `Exercício — Crítico`: cotação da ação no strike ou abaixo dele;
- `Exercício — Acompanhar`: cotação até 2% acima do strike;
- `Exercício — Observar`: cotação entre 2% e 5% acima do strike;
- `Vencimento — Acompanhar`: até 7 dias, sem transformar sozinho a operação em crítica;
- `Vencimento — Observar`: entre 8 e 15 dias;
- `Concentração`: mantém a política de atenção em 25% e limite em 35%;
- `Dados — Observar`: cotação ausente.

Cada operação pode mostrar mais de um motivo, com severidade calculada pelo motivo mais importante. Uma PUT fora do dinheiro não é classificada como crítica apenas pela proximidade do vencimento.

## Importação BTG/Necton

Após selecionar uma negociação da nota, o popup executa imediatamente a consulta do código da opção. Quando o contrato existir no mercado B3/CSV carregado ou em operação já cadastrada, o sistema preenche:

- ativo subjacente;
- strike;
- vencimento;
- cotação disponível.

Quando a fonte não possuir o contrato, o sistema informa claramente que o strike deve ser conferido manualmente. O código da opção, isoladamente, não contém o strike numérico.

## Validação

- testes de PUT fora do dinheiro com vencimento curto;
- teste de PUT no strike ou dentro do dinheiro;
- teste do fluxo de consulta após importar a nota;
- suíte automatizada completa.
