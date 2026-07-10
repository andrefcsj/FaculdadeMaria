# Changelog de Desenvolvimento — FaculdadeMaria

## 1. Status

Este documento registra mudanças relevantes de desenvolvimento, arquitetura, governança e produto do FaculdadeMaria.

Ele não substitui:

- histórico do Git;
- Pull Requests;
- Issues;
- relatórios técnicos de Sprint.

Seu objetivo é oferecer uma visão cronológica e legível da evolução oficial do projeto.

---

## 2. Convenções

Categorias utilizadas:

- `Added`: adicionado.
- `Changed`: alterado.
- `Fixed`: corrigido.
- `Validated`: validado.
- `Deprecated`: marcado como legado.
- `Security`: segurança ou integridade.
- `Docs`: documentação e governança.

Somente mudanças oficialmente integradas à `main` devem ser tratadas como estado vigente.

Mudanças em branch podem ser registradas como `Em revisão`.

---

## 2026-07-10 — Sprint de Organização Oficial

Status: `Em revisão`

Issue: `#7`

Branch:

```text
sprint-organizacao-oficial
```

### Added

- `docs/PRODUCT_VISION.md`;
- `docs/BACKLOG.md`;
- `docs/REGRAS_DO_PROJETO.md`;
- `docs/CHANGELOG_DESENVOLVIMENTO.md`.

### Changed

- organização do caminho crítico até o primeiro Radar Premium;
- formalização de prioridades `P0` a `P3`;
- criação de identificadores oficiais de backlog;
- consolidação das regras permanentes do projeto.

### Direção de produto

Foi registrado como primeiro grande resultado visual futuro:

- Radar Premium;
- Score IA explicável;
- preço líquido;
- ROI bruto, líquido e anualizado;
- risco;
- liquidez;
- distância do strike;
- pontos positivos;
- pontos de atenção;
- conclusão técnica.

### Escopo funcional

Nenhuma funcionalidade foi alterada nesta Sprint documental.

---

## 2026-07-10 — Correção documental pós-merge da Estratégia Operacional

Status: `Em revisão`

Issue: `#5`

Branch:

```text
fix-docs-estrategia-operacional-closure
```

### Fixed

- sincronização de `docs/SPRINT_DOCS_ESTRATEGIA_OPERACIONAL.md` com o estado real pós-merge;
- registro do PR #4 como mergeado;
- registro do commit de merge `7ee1a5a6598182bd1ba313c1e582dc036e1d3614`;
- registro da Issue #3 como encerrada.

### Validated

- diff líquido restrito ao relatório documental;
- 7 testes aprovados;
- nenhuma regressão funcional.

---

## 2026-07-10 — Estratégia Operacional e Reconciliação Arquitetural

Status: `Integrado`

Issue: `#3`

Pull Request: `#4`

Commit de merge:

```text
7ee1a5a6598182bd1ba313c1e582dc036e1d3614
```

### Added

- `docs/ESTRATEGIA_OPERACIONAL.md`;
- `docs/SPRINT_DOCS_ESTRATEGIA_OPERACIONAL.md`.

### Changed

- `docs/ARQUITETURA_V4.md` reconciliado com o estado real pós-Sprint 1.1-R;
- `engine/` registrado como fundação oficial do novo Decision Engine;
- `motor_ia/` registrado como legado isolado;
- estratégia operacional tornada leitura obrigatória para evolução do Decision Engine.

### Docs

Formalizados:

- venda sistemática de PUT;
- geração de renda recorrente;
- aquisição por exercício;
- foco em ativos de qualidade;
- horizonte de longo prazo;
- exercício não tratado como falha automática;
- qualidade e segurança antes de prêmio;
- preço líquido de aquisição;
- análise de rolagem;
- postura crítica da IA;
- governança de backlog.

### Validated

- 7 testes aprovados;
- nenhuma alteração funcional;
- diff restrito a `docs/`.

---

## 2026-07-10 — Encerramento da Sprint 1.1-R

Status: `Integrado`

Issue: `#1`

Pull Request: `#2`

Commit de merge:

```text
6e3416402e83a281dad4ab4a399ae3d4c059235b
```

### Added

Fundação oficial do novo Decision Engine:

- `engine/__init__.py`;
- `engine/errors.py`;
- `engine/telemetry.py`;
- `engine/version.py`;
- `engine/core/__init__.py`;
- `engine/core/context.py`;
- `engine/core/pipeline.py`;
- `engine/providers/__init__.py`;
- `engine/providers/base.py`.

Testes:

- `tests/test_engine_architecture.py`;
- `tests/test_engine_context.py`;
- `tests/test_engine_dependencies.py`;
- `tests/test_engine_errors.py`;
- `tests/test_engine_provider_contract.py`;
- `tests/test_engine_telemetry.py`.

Documentação:

- `docs/SPRINT_01_R.md`;
- `docs/SPRINT_01_R_ENCERRAMENTO.md`.

### Added — Infraestrutura

- hierarquia estruturada de erros;
- telemetria local em memória;
- versão centralizada do motor;
- contexto de execução;
- pipeline pass-through;
- contrato abstrato de provider.

### Validated

Comando:

```bash
python -m unittest discover -s tests -v
```

Resultado:

```text
Ran 7 tests
OK
```

### Preserved

Permaneceram inalterados:

- Flask;
- `app.py`;
- rotas;
- templates;
- interface;
- banco;
- CSV;
- persistência;
- `motor_ia/`;
- funcionalidades existentes.

### Architecture

O novo `engine/` passou a representar a fundação oficial do futuro Decision Engine.

---

## 2026-07-09 — Abertura da Sprint 1.1-R

Status: `Concluído posteriormente`

### Contexto

Foi identificada divergência entre a documentação da Sprint 1.1 e o código real disponível na `main`.

### Decisão

Criar uma Sprint corretiva exclusiva para reconciliar a infraestrutura do Decision Engine sem implementar funcionalidades futuras.

### Escopo protegido

Ficaram explicitamente fora de escopo:

- indicadores;
- score;
- ranking;
- scanner;
- integração Flask;
- providers reais;
- Machine Learning;
- refatoração do legado `motor_ia/`.

---

## Estado oficial atual do produto

Versão oficial do produto:

```text
FaculdadeMaria v4.3 - Score IA Inteligente
```

Versão interna atual do Decision Engine:

```text
1.1.0
```

O produto permanece funcionalmente baseado no monólito Flask existente, com a fundação independente do novo Decision Engine integrada.

---

## Próximas mudanças esperadas

Dependem de Sprints específicas e autorização do Product Owner.

Prioridades de caminho crítico:

1. contratos completos de oportunidade;
2. métricas operacionais de PUT;
3. normalização de dados;
4. indicadores técnicos puros;
5. qualidade do ativo;
6. filtros de segurança;
7. avaliador de PUT;
8. Score IA explicável;
9. ranking;
10. serviço de Radar;
11. Radar Premium v1.

A ordem oficial de execução deve ser confirmada pelo backlog e pela Sprint autorizada.