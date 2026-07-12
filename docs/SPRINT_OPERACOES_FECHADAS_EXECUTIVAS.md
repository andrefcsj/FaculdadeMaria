# Sprint — Operações Fechadas Executivas

**Status:** Concluída  
**Data:** 12/07/2026

## Entregas

- menu Carteira de PUTs renomeado para Operações Abertas;
- Operações Fechadas restaurado no menu Premium;
- nova página executiva sem retorno ao layout legado;
- cards de lucro do mês, lucro acumulado, ROI médio realizado e total fechado;
- filtros de mês atual, ano atual, mês específico e histórico completo;
- tabela com todos os dados da abertura, posição e encerramento;
- edição em popup Premium;
- exclusão com confirmação explícita;
- reabertura com confirmação explícita;
- retorno imediato da posição reaberta à lista de abertas;
- recálculo automático a partir do status e resultado zerado;
- persistência da data, método, recompra e resultado do encerramento;
- compatibilidade CSV e PostgreSQL.

## Integridade

- resultado realizado é usado nos cards, não o prêmio estimado;
- ROI realizado usa resultado dividido pelo capital nominal;
- registros antigos sem data de fechamento permanecem identificados como tal;
- nenhuma data histórica é inventada;
- reabrir remove o resultado realizado e os metadados do encerramento;
- excluir remove operação e metadados somente após confirmação.

## Validação

- filtros e métricas testados;
- edição, reabertura e persistência testadas;
- menu e três ações testados;
- suíte completa executada antes do merge.
