# SPRINT_PROVIDER_B3_EOD_MANUAL_INTRADAY.md

**Projeto:** FaculdadeMaria  
**Status:** Concluída — aguardando aprovação para merge  
**Data:** 11/07/2026  
**Branch:** `sprint/provider-b3-eod-manual-intraday`

## Objetivo

Preparar o Radar para dados públicos EOD da B3, permitindo confirmação manual de preços intraday sem acoplar o Decision Engine a um provider específico.

## Entregas concluídas

- Provider para arquivos COTAHIST em TXT ou ZIP.
- Leitura de PUTs, ativo subjacente, fechamento, bid, ask, strike, vencimento, negócios e volume.
- Normalização para o contrato oficial `OptionOpportunity`.
- Atualização manual de prêmio, bid e ask sem alterar os dados estruturais da série.
- Integração do resultado normalizado ao Decision Engine.
- Bloqueio automático de ativos sem qualidade aprovada.
- Universo Pessoal de Ativos Elegíveis para Exercício.
- Cadastro iniciado vazio, sem recomendações ou aprovações implícitas.
- Validação de notas e elegibilidade.
- Universo pessoal preenchido com 15 ações definidas pelo Product Owner.
- Download automático do último COTAHIST diário disponível.
- Radar Premium conectado aos dados reais EOD.
- Formulário de confirmação manual de prêmio, bid e ask.
- Recálculo do Radar após confirmação do preço intraday.

## Validação

- 68 testes automatizados aprovados.
- Validação integrada com arquivo real: 2.189 séries de PUT identificadas em 13 ativos monitorados no pregão analisado.
- Nenhum ativo foi classificado ou recomendado automaticamente.

## Próxima evolução

- Alimentar notas reais de qualidade dos ativos para substituir o estado conservador de dados insuficientes.

## Merge

Nenhum merge foi realizado.
