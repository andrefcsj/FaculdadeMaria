# Sprint — Confiança dos Dados e Datas Brasileiras

**Data:** 12/07/2026  
**Status:** Em revisão

## Objetivo

Separar visualmente a qualidade da oportunidade da confiabilidade dos dados no Radar e padronizar datas visíveis no formato brasileiro `DD/MM/AAAA`.

## Entregas

- fonte e modalidade de cada cotação;
- data de referência e idade do dado;
- classificação de frescor: atual, atenção, defasado ou não confirmado;
- confiança informada em nível e percentual;
- alertas explícitos antes de qualquer decisão com dado antigo ou incompleto;
- filtros Jinja centralizados para data, data/hora e competência brasileiras;
- datas brasileiras em Dashboard, operações fechadas, rolagem, notas, aportes e DARFs;
- rótulos brasileiros nos gráficos de caixa e DARFs.

## Regras preservadas

- a nota da oportunidade não foi alterada pela apresentação de confiança;
- o Decision Engine permanece determinístico;
- dados continuam armazenados em ISO para compatibilidade e ordenação;
- campos técnicos HTML de data continuam usando o valor ISO exigido pelo navegador;
- confirmação humana no BTG continua obrigatória para preços intraday.

## Validação

- testes unitários de formatação brasileira;
- testes de confiança, fonte, idade e frescor do Radar;
- suíte automatizada completa;
- validação de sintaxe Python e JavaScript.
