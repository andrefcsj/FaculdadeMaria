# Estratégia Operacional Oficial do FaculdadeMaria

## 1. Status do documento

Este documento define a política operacional padrão e oficial do projeto FaculdadeMaria.

Ele deve ser lido integralmente antes de qualquer evolução relacionada a:

- Decision Engine;
- análise de oportunidades com opções;
- score e ranking;
- filtros de elegibilidade;
- análise de risco;
- rolagem;
- explicabilidade da IA;
- eficiência do capital;
- seleção e priorização de oportunidades.

Documentos complementares obrigatórios:

- `PRODUCT_VISION.md`;
- `BACKLOG.md`;
- `REGRAS_DO_PROJETO.md`;
- `DECISION_ENGINE_SPEC.md`;
- `ARQUITETURA_V4.md`.

Em caso de conflito entre uma nova funcionalidade e esta política, a implementação deve ser interrompida e submetida à validação do Product Owner.

---

## 2. Estratégia operacional oficial

O FaculdadeMaria não é um sistema para especulação.

Seu objetivo é auxiliar operações sistemáticas de venda de opções na B3 utilizando Inteligência Artificial explicável, auditável e orientada à qualidade da decisão.

O perfil operacional oficial do Product Owner é:

- vendedor sistemático de PUT;
- geração de renda recorrente;
- aquisição de ativos por meio do exercício;
- foco em ativos de qualidade;
- horizonte de longo prazo.

### 2.1 Tratamento do exercício

O exercício não deve ser tratado como falha.

O exercício faz parte da estratégia.

Uma PUT exercida pode representar uma operação bem-sucedida quando o preço líquido de aquisição for tecnicamente atrativo e o ativo estiver alinhado com os critérios de qualidade e horizonte de longo prazo.

A referência operacional é:

```text
Preço líquido de aquisição = Strike - Prêmio recebido
```

O Decision Engine deve avaliar o exercício dentro do contexto completo da operação, e não como evento automaticamente negativo.

---

## 3. Critérios de decisão

Toda análise deverá priorizar, nesta ordem conceitual:

1. Qualidade do ativo.
2. Segurança da operação.
3. Preço líquido de aquisição.
4. Relação risco x retorno.
5. Eficiência do capital.
6. Liquidez.
7. Probabilidade de exercício.
8. Prêmio recebido.

O maior prêmio nunca deverá ser o principal critério.

Quando existir conflito entre prêmio elevado e operação consistente, o sistema deverá priorizar a alternativa mais robusta, explicável e compatível com o perfil operacional oficial.

---

## 4. Análise padrão das PUTs

Toda análise de PUT deverá apresentar, sempre que os dados estiverem disponíveis:

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
- conclusão técnica.

### 4.1 Premissas e transparência

Sempre que algum campo depender de premissa, estimativa ou dado ausente, isso deverá ser informado explicitamente.

O sistema não deve inventar:

- volatilidade implícita;
- liquidez;
- custos;
- margem;
- probabilidade;
- cotação;
- prêmio;
- vencimento.

Dados incompletos devem reduzir a confiança da análise, gerar alerta ou impedir conclusão definitiva.

### 4.2 Qualidade antes de retorno nominal

Uma oportunidade não deve ser priorizada apenas porque apresenta:

- ROI alto;
- prêmio alto;
- volatilidade alta;
- strike próximo do dinheiro.

Esses fatores devem ser interpretados em conjunto com qualidade do ativo, segurança, liquidez, preço líquido e risco.

---

## 5. Rolagem

Sempre que existir uma PUT aberta, o sistema deverá analisar automaticamente a possibilidade de rolagem assim que essa funcionalidade estiver implementada.

A análise deverá considerar:

- lucro capturado;
- prêmio restante;
- novas oportunidades;
- impacto da margem;
- risco;
- retorno esperado.

Também deverá comparar, quando possível:

- operação atual;
- custo de recompra;
- nova operação;
- crédito ou débito líquido da rolagem;
- novo strike;
- novo vencimento;
- novo preço líquido de aquisição;
- mudança de risco;
- mudança de eficiência do capital.

Quando existir uma operação claramente superior, o sistema deverá recomendar a rolagem e explicar tecnicamente o motivo.

O sistema não deve recomendar rolagem apenas para:

- adiar reconhecimento de prejuízo;
- ocultar deterioração do ativo;
- aumentar risco sem compensação;
- prolongar exposição ineficiente de capital.

---

## 6. Estilo das respostas

O sistema e o assistente não devem concordar automaticamente com o Product Owner.

Quando existir uma alternativa melhor, ela deverá ser apresentada.

Decisões deverão ser questionadas quando houver fundamento técnico.

Toda recomendação deverá explicar o motivo.

As respostas deverão ser:

- objetivas;
- técnicas;
- fundamentadas;
- críticas quando necessário;
- transparentes sobre incertezas;
- livres de promessa de lucro.

---

## 7. Decision Engine

Toda evolução do Decision Engine deverá respeitar esta estratégia operacional.

Antes de implementar uma funcionalidade relacionada à análise de opções, deverá ser verificado se ela está alinhada com esta política.

Caso não esteja, a implementação deverá ser interrompida e submetida à validação do Product Owner.

### 7.1 Princípios obrigatórios do motor

O Decision Engine deverá:

- tratar o exercício como parte possível e legítima da estratégia;
- diferenciar prêmio alto de oportunidade de qualidade;
- avaliar preço líquido de aquisição;
- considerar risco e eficiência do capital;
- incorporar liquidez como fator operacional relevante;
- preservar explicabilidade;
- evitar caixa-preta;
- expor fatores positivos e negativos;
- permitir auditoria da decisão;
- preservar compatibilidade com o restante do sistema.

### 7.2 Prioridade analítica

A oportunidade ideal não será necessariamente:

- a de maior prêmio;
- a de maior ROI nominal;
- a de maior volatilidade;
- a mais próxima do dinheiro.

A qualidade da oportunidade deverá resultar de uma análise multidimensional alinhada ao perfil operacional oficial.

### 7.3 Confiança separada da qualidade

O motor deve evoluir para distinguir:

- qualidade da oportunidade;
- confiança dos dados usados na análise.

Uma oportunidade aparentemente boa com dados incompletos não deve receber a mesma interpretação de uma oportunidade igualmente boa com dados confiáveis.

---

## 8. Backlog oficial

`docs/BACKLOG.md` existe e passa a ser o registro oficial de ideias, prioridades e dependências futuras do projeto.

Qualquer nova ideia que possa melhorar os itens abaixo deverá ser registrada no backlog oficial:

- seleção de oportunidades;
- análise de risco;
- rolagem;
- explicabilidade da IA;
- eficiência do capital;
- qualidade das recomendações;
- experiência Premium;
- robustez operacional.

### 8.1 Regra de registro automático

Sempre que surgir uma ideia relevante:

1. registrar no `BACKLOG.md`;
2. atribuir identificador;
3. indicar prioridade inicial;
4. registrar dependências quando conhecidas;
5. não implementar automaticamente.

### 8.2 Regra de governança

Nenhuma ideia de backlog pode ser implementada fora de Sprint autorizada.

O backlog organiza possibilidades e prioridades; não substitui o escopo formal de uma Sprint.

### 8.3 Ideias estratégicas já registradas

Entre as ideias oficiais já registradas estão:

- qualidade do ativo antes do prêmio;
- preço líquido como eixo central;
- análise automática de rolagem;
- alternativa melhor obrigatória;
- penalização de ROI alto causado por risco extremo;
- confiança de dados separada do Score IA;
- exercício avaliado pelo preço líquido;
- eficiência do capital;
- comparação entre strikes;
- comparação entre ativos;
- explicação de por que não operar;
- alertas de concentração;
- Radar com foco em qualidade;
- trilha visual da decisão.

---

## 9. Governança e compatibilidade

Este documento complementa a arquitetura oficial e a especificação técnica do Decision Engine.

Ele não autoriza alteração automática de:

- Flask;
- rotas;
- templates;
- interface;
- banco de dados;
- CSV;
- `motor_ia/` legado;
- funcionalidades existentes.

Toda implementação deverá seguir o fluxo oficial consolidado em `REGRAS_DO_PROJETO.md`.

Resumo:

1. leitura integral de `docs/`;
2. comparação entre documentação e código;
3. interrupção em caso de divergência;
4. Sprint autorizada;
5. branch própria;
6. testes e regressão;
7. documentação atualizada;
8. relatório técnico;
9. aprovação do Product Owner;
10. merge somente após autorização explícita.

---

## 10. Critério de conformidade

Uma evolução do Decision Engine só poderá ser considerada alinhada a esta política quando:

- respeitar o perfil de vendedor sistemático de PUT;
- não tratar exercício automaticamente como falha;
- priorizar qualidade do ativo e segurança;
- calcular ou considerar preço líquido de aquisição;
- avaliar risco x retorno;
- considerar eficiência do capital;
- considerar liquidez;
- manter explicabilidade;
- documentar premissas;
- preservar compatibilidade;
- passar pelos testes e validações da Sprint correspondente.

---

## 11. Relação com o Radar Premium

O Radar Premium é o primeiro grande resultado visual futuro do Decision Engine, conforme `PRODUCT_VISION.md` e `BACKLOG.md`.

Ele deverá apresentar informação operacional de forma clara e sofisticada, sem esconder:

- risco;
- liquidez baixa;
- dados ausentes;
- confiança baixa;
- premissas.

A experiência visual deve reforçar a qualidade da decisão, não substituir o raciocínio técnico.

---

## 12. Conclusão

O FaculdadeMaria é um sistema profissional de apoio à gestão e análise de operações com opções da B3.

Sua inteligência deve ser orientada por:

- disciplina;
- qualidade;
- segurança;
- eficiência de capital;
- explicabilidade;
- experiência Premium.

O Decision Engine é o núcleo analítico do projeto e deverá evoluir de acordo com esta política operacional.

O objetivo não é maximizar prêmio isoladamente.

O objetivo é melhorar a qualidade das decisões dentro de uma estratégia sistemática, racional e de longo prazo.