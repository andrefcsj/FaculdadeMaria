# Sprint Funcional J — Operações Abertas Premium

## Objetivo

Evoluir a página de Operações Abertas com estimativa explicável de exercício e edição em modal, mantendo o usuário na mesma tela.

## Entregas

- coluna `Prob. de Exercício`;
- estimativa estatística baseada em cotação, strike, prazo e volatilidade histórica anualizada;
- ausência explícita de estimativa quando os dados ou a fonte não forem suficientes;
- classificação visual baixa, moderada ou alta;
- tooltip com metodologia e volatilidade usada;
- modal Premium de edição com dados pré-preenchidos;
- salvamento assíncrono pela API interna;
- fechamento automático do modal e atualização da própria página;
- rota antiga de edição redirecionada para Operações Abertas;
- preservação das ações de fechar e excluir;
- testes unitários da função pura de probabilidade.

## Metodologia da estimativa

A probabilidade exibida representa uma estimativa estatística de a opção terminar dentro do dinheiro no vencimento. O cálculo usa:

- cotação atual do ativo;
- strike;
- dias até o vencimento;
- volatilidade histórica anualizada de seis meses;
- modelo lognormal com deriva zero.

A estimativa não é garantia de exercício e não utiliza volatilidade inventada. Se o histórico ou a cotação estiverem indisponíveis, a interface exibe `--` e `Indisponível`.

## Compatibilidade

A persistência existente em PostgreSQL ou CSV foi preservada. A antiga rota `/editar/<id>` continua válida, mas agora redireciona para a tela principal, evitando quebra de links antigos.

## Arquivos alterados

- `app.py`
- `services/exercise_probability_service.py`
- `templates/operacoes_abertas.html`
- `static/op_abertas.js`
- `tests/test_exercise_probability_service.py`
