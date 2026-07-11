# SPRINT_PROVIDER_B3_EOD_MANUAL_INTRADAY.md

**Projeto:** FaculdadeMaria  
**Status:** Em andamento  
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

## Validação

- 68 testes automatizados aprovados.
- Nenhum ativo foi classificado ou recomendado automaticamente.

## Próximas etapas da Sprint

- Cadastrar os ativos escolhidos pelo Product Owner.
- Conectar upload/atualização do arquivo B3 ao Radar Premium.
- Adicionar formulário de confirmação manual intraday.
- Validar a experiência completa antes do encerramento.

## Merge

Nenhum merge foi realizado.
