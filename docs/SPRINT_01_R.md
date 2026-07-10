# Sprint 1.1-R - Reconciliacao da Infraestrutura do Decision Engine

## Status

Concluida tecnicamente na branch `sprint-1-1-r` e vinculada exclusivamente a Issue #1. Aguardando aprovacao arquitetural.

## Objetivo

Reconciliar o codigo real com a infraestrutura descrita em `ARQUITETURA_V4.md`, `DECISION_ENGINE_SPEC.md` e `SPRINT_01.md`, sem implementar funcionalidades da Sprint 2 ou posteriores.

## Arquivos criados

- `engine/__init__.py`
- `engine/errors.py`
- `engine/telemetry.py`
- `engine/version.py`
- `engine/core/__init__.py`
- `engine/core/context.py`
- `engine/core/pipeline.py`
- `engine/providers/__init__.py`
- `engine/providers/base.py`
- `tests/test_engine_architecture.py`
- `tests/test_engine_context.py`
- `tests/test_engine_dependencies.py`
- `tests/test_engine_errors.py`
- `tests/test_engine_provider_contract.py`
- `tests/test_engine_telemetry.py`

## Arquivos alterados

Nenhum arquivo Flask, rota, template, CSS, JavaScript, interface ou arquivo do legado `motor_ia/` foi alterado.

A documentacao da Sprint 1.1 original foi preservada. Este arquivo registra exclusivamente a Sprint corretiva 1.1-R.

## Implementacao

### Erros de dominio

`engine/errors.py` define a hierarquia oficial de excecoes do Decision Engine e permite serializacao por `code`, `message` e `details`.

### Telemetria local

`engine/telemetry.py` registra eventos, metricas e spans em memoria, sem rede, banco ou dependencia externa.

### Versao centralizada

`engine/version.py` concentra `ENGINE_VERSION`, `ENGINE_CODENAME` e `get_engine_version()`.

### Contexto

`DecisionContext` mantem metadata, traces e `TelemetryRecorder`. Cada trace registra tambem um evento local de telemetria.

### Pipeline

`DecisionPipeline` e `run_pipeline` executam somente orquestracao pass-through. A pipeline registra inicio, quantidade de candidatos, span, trace, fim e metadata de versao. Nao calcula indicador, score, ranking ou explicacao de negocio.

### Providers

`MarketDataProvider` define apenas contrato abstrato. `ProviderError` herda de `EngineProviderError`. Nenhuma chamada de rede foi implementada.

## Testes executados

Comando:

```txt
python -m unittest discover -s tests -v
```

Resultado final:

```txt
Ran 7 tests
OK
```

Cobertura da Sprint:

- versao centralizada;
- pipeline pass-through;
- contexto e trace com telemetria;
- erros estruturados;
- eventos, metricas e spans;
- hierarquia de erro de provider;
- ausencia de imports diretos proibidos em `engine/`.

## Decisoes arquiteturais

- `engine/` permanece desacoplado de Flask.
- `engine/` nao acessa PostgreSQL, SQLite ou CSV.
- `engine/` nao importa `yfinance` ou bibliotecas de rede.
- a pipeline permanece sem regra de negocio;
- o legado `motor_ia/` foi mantido intacto;
- nenhuma funcionalidade existente foi alterada.

## Riscos conhecidos

- A branch possui historico divergente de `main` por commits corretivos de gravacao, mas a comparacao de conteudo de `main` contra o ponto pre-Sprint resulta em zero arquivos diferentes.
- A infraestrutura ainda nao possui indicadores, score, ranking, scanner, providers reais ou integracao Flask por decisao explicita de escopo.

## Confirmacao de sincronizacao

O codigo implementado na branch e esta documentacao descrevem o mesmo estado: fundacao do Decision Engine presente, testada, sem regra de negocio e sem alteracao de funcionalidades existentes.

A Sprint 1.1-R termina aqui e nao autoriza inicio de qualquer Sprint posterior.
