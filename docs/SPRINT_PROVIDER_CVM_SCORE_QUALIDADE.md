# SPRINT_PROVIDER_CVM_SCORE_QUALIDADE.md

**Projeto:** FaculdadeMaria  
**Status:** Concluída — aguardando aprovação para merge  
**Data:** 11/07/2026  
**Branch:** `sprint/provider-cvm-score-qualidade`

## Objetivo

Automatizar a qualidade dos ativos com dados públicos oficiais, sem exigir leitura manual do Product Owner e sem permitir que prêmio ou ROI substituam qualidade.

## Fonte

- Demonstrações Financeiras Padronizadas (DFP) da CVM.
- Download anual automático pelo Portal de Dados Abertos da CVM.
- Mapeamento explícito por CNPJ para os 15 ativos monitorados.

## Modelos

### Empresas

- lucro líquido;
- ROE;
- fluxo de caixa operacional;
- lucro positivo em dois exercícios;
- relação patrimônio/ativos.

### Instituições financeiras e holdings

- lucro líquido;
- ROE;
- lucro positivo em dois exercícios;
- estabilidade/crescimento do patrimônio.

## Segurança

- Campos ausentes reduzem a confiança.
- Dados essenciais ausentes impedem a criação da nota.
- Score permanece separado da confiança dos dados.
- Critérios e justificativas ficam explícitos.
- O maior prêmio não resgata ativo ou operação reprovada.

## Validação

- 70 testes automatizados aprovados.
- Verificação de sintaxe aprovada.
- 15 emissores processados com dados reais do DFP.
- Validação integrada: 2.189 PUTs processadas; 5 em observação e 2.184 descartadas no pregão usado para teste.

## Merge

Nenhum merge foi realizado.
