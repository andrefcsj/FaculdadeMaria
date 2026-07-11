# DECISION_ENGINE_SPEC — FaculdadeMaria

## 1. Status e autoridade do documento

Este documento é a especificação técnica oficial vigente do Decision Engine do FaculdadeMaria.

Ele substitui, para decisões futuras do motor, as orientações conceituais anteriores que conflitem com:

- `ARQUITETURA_V4.md`;
- `ESTRATEGIA_OPERACIONAL.md`;
- `PRODUCT_VISION.md`;
- `BACKLOG.md`;
- `REGRAS_DO_PROJETO.md`.

Documentos históricos de Sprint preservam o contexto temporal em que foram escritos, mas não definem a ordem vigente de evolução quando houver conflito com o backlog oficial e com esta especificação.

O Decision Engine é um mecanismo de apoio analítico, explicável, auditável e configurável. Ele não promete lucro, não afirma certeza de mercado e não transforma Score IA em garantia.

---

## 2. Estado atual oficial

O produto permanece funcionalmente baseado na aplicação Flask existente, com `legacy_app.py` preservando o monólito e `app.py` estendendo importação de mercado e Rolagem Inteligente.

Atualização vigente em 11/07/2026:

- as Sprints Funcionais A–I foram integradas;
- contratos, métricas, normalização, indicadores, segurança, qualidade, estratégia PUT, Score, ranking e explicação estão implementados;
- o Radar Premium está integrado ao Flask por camada de serviço;
- providers públicos B3 EOD e CVM estão integrados;
- a Rolagem Inteligente está disponível;
- o `motor_ia/` permanece legado isolado.

O inventário reduzido e as limitações descritas abaixo registram a fundação histórica da Sprint 1.1-R. Para o estado atual, prevalece esta atualização e os relatórios das Sprints posteriores.

O novo Decision Engine vive em:

```text
engine/
```

Estado atual integrado à `main`:

```text
engine/
|-- __init__.py
|-- errors.py
|-- telemetry.py
|-- version.py
|-- core/
|   |-- __init__.py
|   |-- context.py
|   `-- pipeline.py
`-- providers/
    |-- __init__.py
    `-- base.py
```

A fundação atual oferece:

- erros estruturados;
- telemetria local em memória;
- versão centralizada;
- contexto de execução;
- pipeline pass-through;
- contrato abstrato de provider;
- testes de arquitetura e isolamento.

A pipeline da fundação histórica não implementava:

- indicadores;
- qualidade do ativo;
- filtros de segurança;
- métricas funcionais de PUT;
- Score IA;
- ranking;
- explicação financeira final;
- provider real;
- integração Flask/Radar;
- aprendizado.

O pacote legado:

```text
motor_ia/
```

permanece isolado e não é o caminho oficial de evolução do novo motor.

Regra:

> O novo caminho oficial é `engine/`. Não corrigir, integrar, remover ou refatorar `motor_ia/` sem Sprint específica e autorização explícita.

---

## 3. Objetivo do Decision Engine

O Decision Engine transforma dados de mercado, contratos de oportunidade, contexto operacional e regras de estratégia em análises:

- comparáveis;
- reproduzíveis;
- explicáveis;
- auditáveis;
- alinhadas ao perfil operacional oficial.

O motor deve ajudar a responder perguntas como:

- Qual PUT merece atenção agora?
- O ativo é aceitável para aquisição por exercício?
- O preço líquido de aquisição é atrativo?
- O prêmio compensa o risco assumido?
- O capital está sendo usado com eficiência?
- A opção possui liquidez suficiente?
- O strike oferece margem de segurança adequada?
- Os dados são completos e confiáveis?
- Existe oportunidade objetivamente melhor?
- Uma PUT aberta deveria ser mantida, encerrada ou rolada quando a funcionalidade existir?
- Por que a IA atribuiu determinada nota?
- Por que a melhor decisão pode ser não operar?

---

## 4. Perfil operacional oficial

A prioridade inicial do produto é a venda sistemática de PUTs na B3.

Perfil do Product Owner:

- vendedor sistemático de PUT;
- geração de renda recorrente;
- aquisição de ativos por exercício;
- foco em ativos de qualidade;
- horizonte de longo prazo.

### 4.1 Exercício

O exercício não é falha automática.

Uma PUT exercida pode ser considerada coerente ou bem-sucedida quando:

- o ativo é adequado à estratégia;
- o preço líquido de aquisição é atrativo;
- o risco assumido é aceitável;
- a concentração resultante é compatível com a carteira;
- as premissas da entrada permanecem válidas.

Referência operacional:

```text
Preço líquido de aquisição = Strike - Prêmio recebido
```

### 4.2 Estratégias futuras

CALL coberta e Wheel continuam compatíveis com a arquitetura futura, mas não possuem precedência sobre a prioridade operacional atual de venda de PUT.

Sua implementação depende de backlog e Sprint específicos.

---

## 5. Hierarquia oficial de decisão

Toda análise deve considerar, nesta ordem conceitual:

1. qualidade do ativo;
2. segurança da operação;
3. preço líquido de aquisição;
4. relação risco x retorno;
5. eficiência do capital;
6. liquidez;
7. probabilidade de exercício, quando houver metodologia e dados válidos;
8. prêmio recebido.

O maior prêmio nunca deve ser o principal critério.

ROI nominal elevado também não é prova de boa oportunidade.

### 5.1 Princípio de não compensação indevida

Fatores positivos não podem compensar ilimitadamente falhas estruturais.

Exemplos:

```text
Ativo inelegível + prêmio alto != boa oportunidade
```

```text
Dado crítico ausente + ROI alto != análise confiável
```

```text
Liquidez inadequada + Score alto != prioridade operacional
```

### 5.2 Gates de elegibilidade

Quando aplicável, critérios críticos devem funcionar como gates de elegibilidade, e não apenas como pesos.

Gates candidatos:

- ativo explicitamente inelegível;
- dado crítico ausente;
- preço não confiável;
- liquidez abaixo do mínimo obrigatório;
- spread operacional excessivo;
- risco incompatível com limites configurados;
- concentração incompatível com a política futura de carteira;
- vencimento fora de limites obrigatórios;
- inconsistência contratual.

Regra central:

> O Score IA não pode resgatar uma oportunidade que falhou em gate obrigatório.

Todo gate deve produzir motivo rastreável e explicável.

---

## 6. Arquitetura do motor

O Decision Engine é um módulo de domínio independente.

Ele deve permanecer desacoplado de:

- Flask;
- rotas;
- templates;
- PostgreSQL;
- SQLite;
- CSV;
- `yfinance`;
- bibliotecas de rede no core.

### 6.1 Relação com Flask

Fluxo alvo:

```text
Flask route
  -> camada de serviço
    -> Decision Engine
      -> contratos
      -> normalização
      -> métricas
      -> indicadores
      -> qualidade do ativo
      -> gates/filtros
      -> avaliação da estratégia
      -> Score IA
      -> ranking
      -> explicação
    -> view model
  -> template Radar
```

Responsabilidades do Flask:

- receber requisição HTTP;
- ler parâmetros de apresentação;
- chamar serviço de aplicação;
- renderizar resultados;
- tratar erro de apresentação.

Não pertencem ao Flask:

- calcular Score IA;
- calcular indicadores;
- aplicar ranking de negócio;
- consultar provider do motor diretamente;
- construir regra de elegibilidade;
- gerar conclusão técnica do domínio.

### 6.2 Relação com persistência

O Decision Engine não acessa banco ou CSV diretamente.

Dados devem chegar por:

- contratos;
- serviços;
- interfaces de repositório externas ao motor.

### 6.3 Relação com providers

Providers concretos encapsulam integrações externas.

O domínio depende de contratos substituíveis.

Requisitos futuros:

- timeout;
- erro estruturado;
- timestamp;
- identificação de fonte;
- tratamento de rate limit;
- testes com mock;
- fallback planejado;
- nenhuma dependência direta do Flask.

---

## 7. Pipeline alvo

A evolução oficial segue o caminho crítico do backlog.

```text
Contratos de oportunidade
  -> Snapshot normalizado
  -> Métricas operacionais de PUT
  -> Indicadores técnicos
  -> Qualidade do ativo
  -> Gates e filtros de segurança
  -> Avaliador de venda de PUT
  -> Score IA explicável
  -> Ranking ajustado ao perfil
  -> Explicação
  -> Serviço de Radar
  -> Radar Premium
```

A ordem acima é conceitual. Cada etapa depende de Sprint autorizada.

### 7.1 Core

Responsável por:

- orquestração;
- contexto;
- traces;
- telemetria;
- encadeamento de etapas;
- tratamento estruturado de falhas.

O core não contém:

- fórmula de indicador;
- regra específica de Score;
- ranking de negócio;
- acesso a provider concreto;
- persistência.

### 7.2 Contracts

Responsável por estruturas estáveis de entrada e saída.

Primeiro contrato completo de oportunidade deve contemplar, conforme disponibilidade:

- ativo;
- código da opção;
- tipo da opção;
- vencimento;
- cotação atual;
- strike;
- prêmio;
- bid;
- ask;
- volume;
- negócios;
- liquidez;
- volatilidade implícita;
- timestamp;
- fonte;
- confiança do dado.

### 7.3 Market

Responsável por:

- normalizar dados;
- validar timestamp;
- identificar fonte;
- marcar campos ausentes;
- distinguir ausência de dado de baixa liquidez;
- preservar rastreabilidade.

### 7.4 Metrics

Responsável por métricas puras e auditáveis.

Métricas iniciais de PUT:

- preço líquido de aquisição;
- desconto em relação ao mercado;
- ROI bruto;
- ROI líquido;
- ROI anualizado;
- distância percentual do strike;
- dias até vencimento;
- retorno por dia;
- capital nominal comprometido;
- eficiência do capital;
- retorno sobre margem apenas quando margem real ou premissa explícita estiver disponível.

### 7.5 Indicators

Responsável por sinais técnicos, sem decidir sozinho se uma oportunidade é boa.

Indicadores iniciais previstos:

- MM21;
- MM200;
- IFR14;
- Bandas de Bollinger;
- ATR;
- volatilidade histórica.

Volatilidade implícita é dado de opção quando disponível; não deve ser inventada.

### 7.6 Asset Quality

Responsável por avaliar adequação do ativo ao perfil de aquisição por exercício e longo prazo.

Dimensões candidatas:

- elegibilidade configurável;
- liquidez do ativo base;
- histórico de negociação;
- tendência estrutural;
- volatilidade;
- deterioração relevante;
- concentração de carteira;
- eventos relevantes quando houver fonte válida;
- adequação ao horizonte de longo prazo.

A definição final de critérios objetivos e configuráveis depende de Sprint específica.

### 7.7 Filters e Gates

Responsáveis por segurança e elegibilidade.

Devem:

- produzir status;
- registrar motivo;
- ser auditáveis;
- distinguir descarte de dado insuficiente;
- permitir modo diagnóstico futuro.

### 7.8 Strategies

A prioridade inicial é `PUT selling`.

O avaliador de PUT deve considerar:

- qualidade do ativo;
- aceitabilidade do exercício;
- preço líquido;
- segurança;
- risco;
- retorno;
- liquidez;
- prazo;
- contexto técnico;
- eficiência do capital;
- confiança dos dados.

### 7.9 Score

O Score IA é uma síntese explicável de 0 a 100.

Ele deve ser:

- configurável;
- testável;
- reproduzível;
- auditável;
- separado por estratégia quando necessário;
- composto por fatores rastreáveis;
- acompanhado por confiança dos dados separada.

O Score não é:

- recomendação absoluta;
- garantia de lucro;
- substituto de gate de segurança;
- mecanismo para esconder dado ausente.

### 7.10 Ranking

O ranking só ordena oportunidades após a avaliação de elegibilidade.

Separação mínima:

- elegíveis;
- em observação;
- não elegíveis;
- dados insuficientes.

Ordem conceitual para oportunidades elegíveis:

1. aderência ao perfil operacional e elegibilidade;
2. qualidade do ativo;
3. segurança;
4. Score IA;
5. atratividade do preço líquido;
6. risco ajustado ao retorno;
7. eficiência do capital;
8. liquidez;
9. confiança dos dados;
10. critérios de desempate configuráveis.

O prêmio e o ROI nominal não possuem precedência automática.

Critérios de desempate candidatos:

- maior confiança dos dados;
- melhor liquidez;
- menor risco relativo;
- melhor adequação ao perfil;
- menor concentração incremental;
- melhor proximidade da faixa operacional desejada.

### 7.11 Probability e Risk

Camada futura.

Não deve inventar probabilidade.

Enquanto não houver metodologia validada, dados suficientes e testes:

- probabilidade deve permanecer ausente ou explicitamente indisponível;
- risco pode ser representado por fatores determinísticos e alertas;
- confiança da análise deve permanecer separada.

### 7.12 Explain

Toda oportunidade relevante deve poder apresentar:

- resumo;
- principais fatores positivos;
- principais fatores negativos;
- principal risco;
- impacto de dados ausentes;
- motivo da nota;
- motivo da elegibilidade ou descarte;
- conclusão técnica;
- alternativa melhor quando objetivamente identificada.

O motor deve poder concluir:

> Nenhuma oportunidade atual atende aos critérios mínimos.

### 7.13 Learning

Aprendizado é fase futura.

Não implementar Machine Learning antes de:

- base histórica suficiente;
- critérios validados;
- governança de dados;
- comparação expectativa x resultado;
- aprovação explícita.

Nenhum peso pode mudar automaticamente sem auditoria.

---

## 8. Estrutura alvo conceitual

```text
engine/
|-- __init__.py
|-- errors.py
|-- telemetry.py
|-- version.py
|-- config.py                    # futuro, Sprint específica
|-- core/
|   |-- __init__.py
|   |-- context.py
|   |-- pipeline.py
|   `-- contracts.py             # caminho crítico
|-- market/
|   |-- __init__.py
|   |-- snapshot.py
|   `-- normalizer.py
|-- providers/
|   |-- __init__.py
|   |-- base.py
|   `-- providers concretos      # futuros
|-- metrics/
|   `-- options.py
|-- indicators/
|   |-- trend.py
|   |-- momentum.py
|   `-- volatility.py
|-- asset_quality/
|   `-- evaluator.py
|-- filters/
|   `-- safety.py
|-- strategies/
|   `-- put_selling.py
|-- score/
|   |-- calculator.py
|   `-- classes.py
|-- ranking/
|   `-- sorter.py
|-- probability/
|   `-- risk.py                  # futuro
|-- explain/
|   `-- explainer.py
`-- learning/                    # futuro
```

A estrutura é conceitual e não autoriza criação automática de módulos.

---

## 9. Métricas operacionais de PUT

### 9.1 Preço líquido de aquisição

```text
preco_liquido = strike - premio
```

Premissas devem ser explícitas.

### 9.2 Desconto em relação ao mercado

Conceitualmente:

```text
desconto = (cotacao_atual - preco_liquido) / cotacao_atual
```

Unidade e arredondamento devem ser definidos na Sprint de implementação.

### 9.3 ROI bruto

A fórmula exata depende da definição oficial de capital comprometido.

A Sprint funcional deve registrar a base usada e impedir ambiguidade entre:

- capital nominal;
- margem real;
- capital líquido;
- caixa reservado.

### 9.4 ROI líquido

Custos e tributos não podem ser inventados.

Quando indisponíveis:

- informar ausência;
- não apresentar precisão fictícia;
- usar premissa somente se explicitamente configurada.

### 9.5 ROI anualizado

Deve:

- declarar convenção de dias;
- tratar DTE zero ou inválido;
- evitar anualização enganosa;
- permanecer reproduzível.

### 9.6 Eficiência do capital

Deve comparar retorno com o capital realmente comprometido quando esse dado existir.

Retorno sobre margem só pode ser tratado como real quando houver margem real.

---

## 10. Indicadores previstos

### MM21

Uso: tendência de curto prazo.

### MM200

Uso: tendência estrutural.

Ativo abaixo da MM200 pode exigir alerta, mas nenhuma regra fixa deve ser implementada sem Sprint específica.

### IFR14

Uso: momentum e regiões extremas.

Sobrevenda não é automaticamente oportunidade.

### Bandas de Bollinger

Uso: posição relativa do preço e regime de volatilidade.

### ATR

Uso: amplitude e risco de oscilação.

Distância do strike pode ser comparada ao ATR em Sprint futura.

### Volatilidade implícita

Uso: expectativa implícita no prêmio quando o dado estiver disponível.

IV alta pode elevar prêmio e risco simultaneamente.

### Liquidez e volume

Devem apoiar executabilidade e confiança do preço.

O motor deve distinguir:

- falta de dado;
- baixa liquidez;
- preço stale;
- spread excessivo.

---

## 11. Análise padrão de PUT

Sempre que os dados estiverem disponíveis, a saída deve contemplar:

- ativo;
- vencimento;
- strike;
- prêmio;
- preço líquido de aquisição;
- desconto em relação ao mercado;
- ROI bruto;
- ROI líquido;
- ROI anualizado;
- volatilidade implícita;
- liquidez;
- distância do strike;
- risco;
- nota de 0 a 10;
- Score IA de 0 a 100;
- confiança dos dados;
- pontos positivos;
- pontos de atenção;
- conclusão técnica.

A ausência de dado deve ser explícita.

---

## 12. Rolagem

Quando houver PUT aberta e a funcionalidade estiver implementada, a análise deve considerar automaticamente:

- lucro capturado;
- prêmio restante;
- custo de recompra;
- nova oportunidade;
- crédito ou débito líquido;
- novo strike;
- novo vencimento;
- novo preço líquido;
- impacto da margem;
- mudança de risco;
- retorno esperado;
- eficiência incremental do capital.

Não recomendar rolagem apenas para:

- adiar prejuízo;
- ocultar deterioração;
- aumentar risco sem compensação;
- prolongar capital ineficiente.

---

## 13. Confiança dos dados

Confiança é dimensão separada da qualidade da oportunidade.

Uma oportunidade pode ser:

- boa com alta confiança;
- boa com baixa confiança;
- ruim com alta confiança;
- impossível de concluir por insuficiência de dados.

Fatores candidatos de confiança:

- completude;
- frescor;
- consistência;
- fonte;
- timestamp;
- coerência bid/ask;
- disponibilidade de volume e negócios.

Regra:

> Score alto com confiança baixa deve gerar interpretação limitada e alerta explícito.

---

## 14. Contratos conceituais

### 14.1 Entrada de oportunidade

```text
id
ativo
opcao
tipo_opcao
vencimento
cotacao_atual
strike
premio
bid
ask
volume
negocios
liquidez
volatilidade_implicita
timestamp
fonte
```

### 14.2 Saída analisada

```text
id
ativo
opcao
estrategia
status_elegibilidade
motivos_elegibilidade
preco_atual
strike
premio
preco_liquido
vencimento
dias_para_vencimento
roi_bruto
roi_liquido
roi_anualizado
desconto_mercado
distancia_strike
indicadores
qualidade_ativo
filtros
risco
score
nota_0_10
classe
ranking
explicacao
pontos_positivos
pontos_atencao
alertas
fonte_dados
timestamp
confianca_dados
```

Os contratos podem evoluir, mas mudanças devem preservar compatibilidade ou possuir estratégia explícita de migração.

---

## 15. Testabilidade e reproduzibilidade

Todo componente deve permitir testes com dados controlados.

Regras:

- mesma entrada + mesma configuração = mesma saída analítica;
- rede real não é requisito de teste unitário;
- providers concretos devem permitir mock;
- dados ausentes devem ser testados;
- valores zero e inválidos devem ser testados;
- DTE deve ser testado;
- arredondamentos devem ser definidos;
- gates devem possuir testes positivos e negativos;
- Score deve expor fatores;
- ranking deve ser determinístico para mesmas entradas.

Telemetria temporal pode variar e deve ser tratada separadamente da saída analítica reproduzível.

---

## 16. Tratamento de falhas

Falhas externas não devem derrubar a aplicação sem tratamento.

Categorias:

- contrato inválido;
- dado ausente;
- dado inconsistente;
- provider indisponível;
- timeout;
- rate limit;
- configuração inválida;
- etapa parcial indisponível.

A resposta deve:

- usar erros estruturados;
- preservar causa útil;
- evitar vazamento indevido;
- produzir alerta acionável;
- limitar conclusão quando necessário.

---

## 17. Caminho crítico vigente

A ordem vigente é definida pelo `BACKLOG.md` e por Sprints autorizadas.

Sequência recomendada atual:

### Sprint Funcional A — Contratos e métricas de PUT

- `FM-ENG-010`;
- `FM-PUT-010`;
- parte de `FM-DATA-010`.

### Sprint Funcional B — Indicadores e segurança

- `FM-ENG-020`;
- `FM-RISK-010`;
- `FM-RISK-030`.

### Sprint Funcional C — Qualidade do ativo e estratégia PUT

- `FM-ASSET-010`;
- `FM-PUT-020`;
- `FM-CAP-010`.

### Sprint Funcional D — Score e explicação

- `FM-SCORE-010`;
- `FM-EXPLAIN-010`;
- `FM-EXPLAIN-040`.

### Sprint Funcional E — Ranking e serviço de Radar

- `FM-RANK-010`;
- `FM-SVC-010`.

### Sprint Visual F — Radar Premium v1

- `FM-UI-010`;
- parte de `FM-UI-020`.

A presença neste documento não autoriza implementação automática.

---

## 18. Relação com versões do produto

A versão oficial do produto permanece definida pela fonte própria do projeto.

A versão interna do Decision Engine é independente do número de versão do produto.

Não realizar bump de versão automaticamente por mudança documental ou por início de Sprint.

Releases futuras dependem de decisão explícita e critérios de conclusão.

---

## 19. Princípios permanentes

### Desacoplado

Sem dependência direta de Flask ou persistência.

### Modular

Contratos, métricas, indicadores, qualidade, filtros, estratégia, Score, ranking e explicação em responsabilidades separadas.

### Explicável

Nenhuma nota sem fatores rastreáveis.

### Conservador com dados incompletos

Não inventar dados.

### Orientado a qualidade

Prêmio alto não supera ativo inadequado ou risco incompatível.

### Seguro

Gates críticos não são compensados por Score.

### Reproduzível

Mesma entrada e configuração geram mesma saída analítica.

### Auditável

Decisões, descartes e fatores devem poder ser explicados.

### Evolutivo

Arquitetura preparada para múltiplos providers e aprendizado futuro sem caixa-preta.

### Compatível

Preservar dashboard, operações, histórico, configurações, backup, exportações e fluxos existentes até Sprint específica de integração.

### Premium com conteúdo real

A interface futura deve ser sofisticada sem mascarar risco, dado ausente ou confiança baixa.

---

## 20. Fora de escopo automático

Esta especificação não autoriza, por si só:

- criação de indicador;
- criação de Score;
- criação de ranking;
- provider real;
- alteração Flask;
- nova rota;
- template;
- CSS;
- JavaScript;
- persistência;
- integração de `motor_ia/`;
- Machine Learning;
- execução automática de operações.

Cada item depende de Sprint autorizada.

---

## 21. Conclusão

O Decision Engine é o núcleo analítico futuro do FaculdadeMaria.

Sua evolução deve transformar dados e regras operacionais em análises:

- confiáveis;
- compreensíveis;
- auditáveis;
- alinhadas ao perfil de venda sistemática de PUT;
- orientadas à qualidade do ativo e à segurança;
- sensíveis ao preço líquido, risco e eficiência do capital;
- transparentes sobre confiança dos dados.

A melhor oportunidade não é necessariamente a de maior prêmio, maior ROI ou maior Score isolado.

A melhor oportunidade é a que permanece elegível, consistente e explicável dentro da estratégia operacional oficial.
