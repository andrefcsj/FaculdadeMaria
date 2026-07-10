# Product Vision — FaculdadeMaria

## 1. Status

Este documento define a visão oficial de produto do FaculdadeMaria.

Ele deve orientar decisões de:

- arquitetura;
- produto;
- experiência do usuário;
- Decision Engine;
- Radar de Oportunidades;
- priorização de backlog;
- integração de dados;
- explicabilidade da IA;
- evolução visual.

Em caso de conflito entre conveniência de curto prazo e esta visão, a decisão deve ser submetida ao Product Owner.

---

## 2. Visão do produto

O FaculdadeMaria é um sistema profissional para gestão e análise de operações com opções da B3.

Seu propósito é ajudar o usuário a tomar decisões melhores, mais disciplinadas, mais explicáveis e mais consistentes dentro de uma estratégia sistemática de longo prazo.

O produto não existe para maximizar prêmio isoladamente.

O produto existe para combinar:

- qualidade do ativo;
- segurança da operação;
- preço líquido de aquisição;
- risco x retorno;
- eficiência do capital;
- liquidez;
- probabilidade de exercício;
- prêmio recebido;
- contexto da carteira;
- explicabilidade.

---

## 3. Problema que o FaculdadeMaria resolve

O investidor de opções enfrenta decisões fragmentadas entre:

- corretora;
- planilhas;
- sites de cotação;
- gráficos;
- dados de opções;
- histórico próprio;
- cálculo manual de ROI;
- avaliação subjetiva de risco;
- acompanhamento de rolagens;
- gestão de margem;
- análise de exercício.

O FaculdadeMaria deve reduzir essa fragmentação e transformar dados dispersos em uma visão operacional clara.

O sistema deve responder, com transparência, perguntas como:

- Qual PUT merece atenção agora?
- Eu aceitaria realmente ser sócio desse ativo?
- O preço líquido de aquisição é atrativo?
- O prêmio compensa o risco?
- O capital está sendo usado com eficiência?
- A opção possui liquidez suficiente?
- O strike oferece margem de segurança adequada?
- O exercício seria aceitável dentro da estratégia?
- Existe oportunidade melhor no mesmo ativo ou em outro ativo?
- Uma PUT aberta deveria ser mantida, encerrada ou rolada?
- Por que a IA atribuiu determinada nota?

---

## 4. Perfil operacional oficial

O produto deve respeitar `docs/ESTRATEGIA_OPERACIONAL.md`.

O perfil oficial do Product Owner é:

- vendedor sistemático de PUT;
- geração de renda recorrente;
- aquisição de ativos por exercício;
- foco em ativos de qualidade;
- horizonte de longo prazo.

O exercício não deve ser tratado automaticamente como falha.

Uma operação pode ser bem-sucedida mesmo com exercício quando o preço líquido de aquisição for tecnicamente interessante e o ativo for adequado à estratégia.

---

## 5. Proposta de valor

### 5.1 Gestão profissional

Centralizar operações abertas, encerradas, histórico, patrimônio, resultados, vencimentos, risco e acompanhamento operacional.

### 5.2 Inteligência explicável

Transformar dados de mercado e critérios operacionais em análises auditáveis, reproduzíveis e compreensíveis.

### 5.3 Seleção de oportunidades

Comparar oportunidades de forma multidimensional, evitando priorização cega pelo maior prêmio.

### 5.4 Disciplina operacional

Reduzir decisões impulsivas e tornar explícitos os critérios que justificam uma entrada, manutenção, encerramento ou rolagem.

### 5.5 Eficiência do capital

Avaliar retorno não apenas pelo prêmio nominal, mas também pelo capital comprometido, margem, prazo e risco assumido.

### 5.6 Experiência Premium

Apresentar informação complexa de forma visualmente clara, elegante, rápida e acionável.

---

## 6. Norte estratégico

O produto deve evoluir em direção a cinco capacidades principais.

### 6.1 Gestão

- operações abertas;
- operações encerradas;
- histórico;
- carteira;
- desempenho;
- relatórios;
- backup;
- configurações.

### 6.2 Decision Engine

- contratos de dados;
- indicadores;
- filtros;
- estratégia de venda de PUT;
- score;
- ranking;
- risco;
- explicação;
- aprendizado futuro.

### 6.3 Radar de Oportunidades

- descoberta e comparação de oportunidades;
- priorização;
- filtros operacionais;
- Score IA;
- nota de 0 a 10;
- pontos positivos;
- pontos de atenção;
- conclusão técnica;
- alternativas melhores.

### 6.4 Inteligência de Rolagem

- lucro capturado;
- prêmio restante;
- custo de recompra;
- nova oportunidade;
- crédito ou débito líquido;
- mudança de strike;
- mudança de vencimento;
- impacto da margem;
- retorno incremental;
- mudança de risco.

### 6.5 Aprendizado e feedback

- registrar decisões;
- comparar expectativa e resultado;
- medir qualidade histórica do score;
- identificar critérios mais úteis;
- ajustar parâmetros com auditoria;
- evitar caixa-preta.

---

## 7. Visão da experiência Premium

A experiência visual deve transmitir:

- confiança;
- clareza;
- sofisticação;
- controle;
- velocidade;
- profissionalismo.

### 7.1 Princípios visuais

- hierarquia clara de informação;
- pouco ruído visual;
- uso consistente de espaço;
- tipografia legível;
- componentes reutilizáveis;
- indicadores com significado;
- cores usadas com propósito;
- responsividade;
- estados vazios elegantes;
- carregamento perceptível e não confuso;
- mensagens de erro úteis.

### 7.2 Radar Premium

O primeiro grande resultado visual do novo Decision Engine deverá ser um Radar capaz de apresentar, quando as camadas funcionais estiverem prontas:

- ativo;
- opção;
- vencimento;
- cotação atual;
- strike;
- prêmio;
- preço líquido de aquisição;
- desconto sobre mercado;
- ROI bruto;
- ROI líquido;
- ROI anualizado;
- volatilidade implícita;
- liquidez;
- distância do strike;
- risco;
- nota de 0 a 10;
- Score IA de 0 a 100;
- classe da oportunidade;
- pontos positivos;
- pontos de atenção;
- conclusão técnica;
- ação de comparação;
- indicação de possível rolagem quando aplicável.

O Radar deve ser bonito, mas a estética nunca pode mascarar incerteza, baixa liquidez, dados ausentes ou risco elevado.

---

## 8. Usuário principal

O usuário principal inicial é o próprio Product Owner, com estratégia real de venda sistemática de PUT na B3.

Isso permite:

- validar decisões com operações concretas;
- ajustar critérios com contexto real;
- evitar produto genérico;
- desenvolver explicabilidade orientada ao uso prático.

A arquitetura, entretanto, deve permanecer preparada para futura expansão de perfis e configurações.

---

## 9. Princípios de produto

### 9.1 Segurança antes de velocidade

Nenhuma aceleração justifica quebrar funcionalidades existentes ou comprometer a integridade da `main`.

### 9.2 Explicabilidade antes de complexidade

Uma regra simples e auditável é preferível a uma caixa-preta sofisticada sem justificativa.

### 9.3 Dados reais antes de aparência de precisão

O sistema não deve inventar volatilidade, liquidez, margem, probabilidade ou cotação.

### 9.4 Qualidade antes de prêmio

O maior prêmio nunca deve ser o principal critério de decisão.

### 9.5 Modularidade antes de acoplamento

O Decision Engine deve permanecer independente de Flask, banco e interface.

### 9.6 Evolução incremental

Cada Sprint deve produzir uma base verificável para a próxima.

### 9.7 Visual Premium com conteúdo confiável

A interface deve ser excelente, mas sempre sustentada por contratos, testes e regras consistentes.

---

## 10. Métricas de sucesso do produto

A evolução do FaculdadeMaria deve ser avaliada por indicadores como:

- redução de decisões manuais repetitivas;
- tempo para comparar oportunidades;
- clareza da justificativa do score;
- percentual de oportunidades com dados completos;
- qualidade da liquidez das oportunidades priorizadas;
- diferença entre retorno esperado e realizado;
- frequência de exercício em preço líquido considerado aceitável;
- eficiência do capital;
- qualidade das rolagens sugeridas;
- estabilidade do sistema;
- ausência de regressões;
- confiança do Product Owner nas recomendações.

---

## 11. Marcos de produto

### Marco A — Fundação confiável

- arquitetura oficial;
- Decision Engine independente;
- erros estruturados;
- telemetria;
- contratos básicos;
- testes;
- estratégia operacional formalizada.

Status atual: fundação inicial concluída.

### Marco B — Primeira inteligência operacional

- contrato completo de oportunidade;
- métricas de PUT;
- qualidade do ativo;
- filtros de segurança;
- indicadores essenciais;
- Score IA inicial;
- explicação básica.

### Marco C — Primeiro resultado visual Premium

- serviço de Radar;
- integração controlada via camada de serviço;
- tela Premium;
- filtros;
- ranking;
- score;
- explicação;
- estados vazios e de erro.

### Marco D — Inteligência de rolagem

- leitura de PUTs abertas;
- comparação com novas oportunidades;
- impacto de margem;
- recomendação explicável.

### Marco E — Motor auditável e evolutivo

- histórico de decisões;
- comparação com resultados;
- calibração;
- feedback;
- aprendizado futuro com governança.

---

## 12. O que o produto não deve se tornar

O FaculdadeMaria não deve se tornar:

- sistema de promessa de lucro;
- gerador cego de sinais;
- ranking de maior prêmio;
- caixa-preta;
- recomendador sem contexto;
- ferramenta que esconde risco;
- sistema excessivamente acoplado a um único provider;
- aplicação visualmente sofisticada, porém tecnicamente frágil.

---

## 13. Definição de sucesso

O FaculdadeMaria será bem-sucedido quando conseguir transformar dados de mercado, operações do usuário e regras operacionais em decisões:

- mais claras;
- mais consistentes;
- mais comparáveis;
- mais explicáveis;
- mais seguras;
- mais eficientes em capital;
- visualmente profissionais.

A ambição do produto é unir gestão, inteligência e experiência Premium sem sacrificar transparência, manutenção ou segurança.