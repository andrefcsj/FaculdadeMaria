# Sprint Funcional H — Importação de Mercado CSV

## Objetivo

Permitir que o Radar Premium receba uma cadeia de opções por CSV e envie as PUTs válidas ao Decision Engine, sem depender de API paga.

## Implementado

- formulário **Importar Mercado** no topo do Radar;
- upload de arquivos `.csv` de até 5 MB;
- leitura de CSV com separadores vírgula, ponto e vírgula, tabulação ou barra vertical;
- suporte a UTF-8 e Latin-1;
- reconhecimento de aliases em português e inglês;
- validação das colunas obrigatórias;
- descarte de CALLs, opções vencidas e linhas inválidas;
- normalização em `OptionOpportunity`;
- persistência temporária em `data/market/imported_options.json`;
- carregamento automático do mercado importado no Radar;
- aplicação do Decision Engine, Score, ranking e explicação;
- indicação da data/hora da última importação;
- mensagens resumidas de sucesso e erro;
- testes unitários do importador.

## Colunas obrigatórias

O importador reconhece nomes equivalentes, mas precisa dos seguintes dados:

- código da opção;
- ativo-objeto;
- vencimento;
- cotação do ativo-objeto;
- strike;
- prêmio/valor atual da opção.

A coluna de tipo é opcional; quando ausente, o sistema considera PUT. Bid, ask e volume são opcionais.

## Arquitetura

O importador foi isolado em `services/market_import_service.py`. O Decision Engine continua independente de Flask, arquivos e interface.

Para preservar o aplicativo existente sem reescrever o monólito, o conteúdo anterior de `app.py` foi mantido integralmente em `legacy_app.py`. O novo `app.py` tornou-se o ponto de entrada e adiciona apenas a extensão de importação ao aplicativo Flask existente. Esta separação é transitória e reduz risco de regressão.

## Limitações conhecidas

- nesta Sprint, somente CSV;
- dados importados são armazenados no filesystem do servidor;
- em hospedagem com disco efêmero, uma reinicialização ou novo deploy pode exigir nova importação;
- o arquivo não substitui uma fonte em tempo real;
- qualidade de ativos desconhecidos continua bloqueando elegibilidade, conforme estratégia oficial.

## Fora de escopo

- Excel;
- API/provider pago;
- execução de ordens;
- nota de corretagem PDF;
- rolagem automática.
