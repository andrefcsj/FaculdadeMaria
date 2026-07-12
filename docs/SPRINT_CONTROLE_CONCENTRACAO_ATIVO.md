# Sprint — Controle de Concentração por Ativo

**Data:** 12/07/2026  
**Status:** Em revisão

## Objetivo

Impedir que retorno ou prêmio atraentes escondam exposição excessiva a um único ativo na estratégia sistemática de venda de PUTs.

## Política

- concentração calculada sobre o capital total da estratégia;
- atenção a partir de 25% por ativo;
- limite máximo de 35% por ativo;
- somente PUTs abertas compõem a exposição atual;
- o Radar considera o capital nominal da nova posição para calcular a concentração projetada;
- oportunidade acima do limite é bloqueada pelo filtro já existente de qualidade do ativo.

## Entregas

- serviço central e determinístico de concentração;
- contexto da carteira real conectado ao Decision Engine;
- concentração projetada em cada card do Radar;
- leitura visual equilibrada, atenção ou alta;
- composição do Dashboard calculada sobre o capital total;
- alertas de concentração no painel Atenção Necessária;
- Resumo Executivo destacando ativos acima do limite;
- testes unitários e de integração.

## Integridade

Nenhum preço, capital ou posição é inferido. Na ausência do capital total, o sistema informa que a concentração não pôde ser calculada.
