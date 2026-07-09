# Sprint 1.1 - Infraestrutura do Decision Engine

## Objetivo da Sprint

Fortalecer a fundacao do pacote `engine` antes da implementacao de indicadores, score, ranking ou qualquer regra de negocio.

Esta sprint adiciona infraestrutura tecnica para:

- excecoes especificas do Decision Engine;
- telemetria local em memoria;
- versao centralizada do motor;
- testes basicos dos novos contratos de infraestrutura.

Nao foram implementados indicadores, score, ranking, scanner, IA, regras de estrategia ou integracao com Flask.

## Arquivos Criados

### `engine/errors.py`

Define a hierarquia oficial de excecoes do Decision Engine.

Classes criadas:

- `DecisionEngineError`
- `EngineConfigurationError`
- `EngineContractError`
- `EnginePipelineError`
- `EngineProviderError`
- `EngineTelemetryError`

Objetivo:

- evitar uso futuro de `ValueError` ou `RuntimeError` genericos;
- permitir erros serializaveis com `code`, `message` e `details`;
- criar uma base consistente para diagnostico e exibicao segura de falhas.

### `engine/telemetry.py`

Define estruturas locais para eventos, metricas e spans da pipeline.

Classes criadas:

- `TelemetryEvent`
- `TelemetryMetric`
- `TelemetrySpan`
- `TelemetryRecorder`

Objetivo:

- registrar eventos da pipeline;
- registrar metricas simples em memoria;
- medir duracao de blocos com spans locais;
- preparar futura integracao com logs estruturados ou ferramentas externas, sem adicionar dependencias agora.

### `engine/version.py`

Centraliza a versao publica do Decision Engine.

Campos e funcoes:

- `ENGINE_VERSION`
- `ENGINE_CODENAME`
- `get_engine_version()`

Objetivo:

- evitar versoes espalhadas pelo codigo;
- permitir que Radar, relatorios e diagnosticos exibam a versao do motor;
- preparar futuras releases do pacote `engine`.

## Arquivos Atualizados

### `engine/__init__.py`

Passou a exportar:

- `DecisionEngineError`
- `ENGINE_VERSION`
- `get_engine_version`

### `engine/providers/base.py`

`ProviderError` agora herda de `EngineProviderError`, mantendo compatibilidade com o nome existente e alinhando providers a hierarquia oficial de erros.

### `engine/core/context.py`

`DecisionContext` agora possui um `TelemetryRecorder`.

Cada trace adicionado pela pipeline tambem registra um evento de telemetria em memoria.

### `engine/core/pipeline.py`

A pipeline continua sem regra de negocio.

Mudancas feitas:

- registra evento de inicio;
- registra metrica de quantidade de candidatos recebidos;
- mede a execucao da pipeline com um span local;
- registra evento de fim;
- adiciona resumo de telemetria ao metadata;
- atualiza `pipeline_version` para `sprint-1.1`;
- adiciona `engine_version` ao metadata.

### `tests/test_engine_architecture.py`

Testes atualizados para cobrir:

- versao centralizada;
- erros estruturados;
- telemetria em memoria;
- metadata da pipeline Sprint 1.1;
- preservacao da independencia em relacao ao Flask.

## Decisoes Arquiteturais

### Erros especificos do dominio

O Decision Engine passa a ter uma hierarquia propria de excecoes. Isso evita que futuras implementacoes usem excecoes genericas e facilita tratamento por camada.

### Telemetria sem integracao externa

A telemetria foi criada como estrutura local, sem `logging`, sem rede e sem dependencia externa.

Isso permite evoluir para logs estruturados ou sistemas de observabilidade no futuro, mantendo a Sprint 1.1 simples e testavel.

### Sem acoplamento com Flask ou banco

Nenhum modulo novo importa Flask, PostgreSQL, SQLite, CSV, `yfinance` ou bibliotecas de rede.

O pacote `engine` segue importavel de forma independente.

### Versao centralizada

A versao do motor fica em um unico ponto (`engine/version.py`) e tambem e exposta no metadata da pipeline.

### Pipeline ainda sem negocio

A pipeline apenas percorre etapas, registra traces e telemetria, e devolve contratos estruturados.

Ela ainda nao calcula indicadores, score, ranking ou explicacoes reais.

## Testes Executados

Comando executado:

```txt
python -m unittest discover -s tests -v
```

Resultado esperado da Sprint 1.1:

```txt
OK
```

Tambem foi validado que o pacote `engine` nao possui imports diretos de Flask, banco ou bibliotecas externas de rede.

## Pendencias para Sprint 2

Itens que ficam propositalmente fora desta sprint:

- implementar indicadores tecnicos;
- implementar calculos de MM21, MM200, IFR14, Bollinger, ATR ou volatilidade;
- implementar score;
- implementar ranking;
- implementar scanner ou descoberta automatica de opcoes;
- conectar o Decision Engine a rotas Flask;
- alterar templates;
- persistir historico de decisoes;
- integrar provedores reais com chamadas de rede;
- criar explicacoes finais em linguagem natural.

## Criterio de Conclusao

A Sprint 1.1 e considerada concluida quando:

- `engine/errors.py` existe e possui excecoes especificas;
- `engine/telemetry.py` existe e registra eventos, metricas e spans em memoria;
- `engine/version.py` centraliza a versao do motor;
- a pipeline continua sem regra de negocio;
- os testes passam;
- nenhum arquivo Flask ou template foi alterado.
