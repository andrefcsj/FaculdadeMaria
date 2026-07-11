# Sprint Funcional I — Rolagem Inteligente

## Objetivo

Entregar a primeira Central de Rolagem Inteligente para PUTs abertas, alinhada à estratégia operacional oficial.

## Escopo entregue

- detecção de PUTs abertas cadastradas;
- tela Premium acessível pelo menu lateral;
- entrada manual do preço de recompra da posição atual;
- entrada manual dos dados da nova PUT candidata;
- cálculo de lucro capturado e prêmio restante;
- cálculo do crédito ou débito líquido da rolagem;
- comparação do preço líquido atual com o novo preço líquido acumulado;
- comparação do ROI atual com o ROI acumulado após a rolagem;
- recomendação explicável entre manter, fechar e reavaliar ou rolar;
- pontos positivos e pontos de atenção;
- testes unitários do motor de rolagem.

## Regras preservadas

- nenhuma cotação é inventada;
- custos permanecem explícitos e opcionais;
- a rolagem não é recomendada apenas para adiar prejuízo;
- crédito, strike, preço líquido e retorno precisam demonstrar melhoria objetiva;
- a meta oficial de ROI permanece em 4%;
- execução de ordens não faz parte desta Sprint.

## Como experimentar

1. Cadastre ou mantenha ao menos uma PUT com status `Aberta`.
2. Acesse `Rolagem Inteligente` no menu lateral.
3. Selecione a PUT aberta.
4. Consulte na corretora o preço atual de recompra.
5. Informe uma nova PUT candidata, vencimento, strike, prêmio e cotação do ativo.
6. Clique em `Analisar manter, fechar ou rolar`.
7. Confira a conclusão, os cálculos e os alertas.

## Limitações

- dados da nova PUT são informados manualmente nesta versão;
- a simulação não executa nem grava uma ordem de rolagem;
- margem real e impacto tributário detalhado não são estimados;
- a qualidade do ativo não é recalculada nesta tela.

## Arquivos principais

- `engine/roll/analysis.py`
- `engine/roll/__init__.py`
- `templates/rolagem_inteligente.html`
- `tests/test_roll_analysis.py`
- `app.py`
- `templates/base.html`
