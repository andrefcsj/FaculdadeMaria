# Sprint Funcional J — Operações Abertas Premium

## Entregas

- coluna `Prob. de Exercício`;
- estimativa estatística baseada em volatilidade histórica, sem inventar dados;
- indicação clara quando a estimativa estiver indisponível;
- edição em modal Premium com dados preenchidos;
- salvamento assíncrono sem navegar para outra página;
- fechamento automático do modal após salvar;
- compatibilidade com PostgreSQL e CSV;
- rota antiga de edição redirecionada para Operações Abertas.

## Observação

A probabilidade exibida é uma estimativa estatística de encerramento dentro do dinheiro, baseada em volatilidade histórica e modelo lognormal. Não representa garantia de exercício.

## Testes

Foram adicionados testes determinísticos para limites, sensibilidade ao strike e histórico insuficiente.
