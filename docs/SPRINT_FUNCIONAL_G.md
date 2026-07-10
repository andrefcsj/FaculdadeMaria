# Sprint Funcional G — Radar ligado às operações reais

## Status
Implementada em branch própria.

## Resultado
O Radar Premium deixa de depender exclusivamente dos dados demonstrativos e passa a tentar carregar operações PUT abertas reais já cadastradas no app.

## Implementado
- serviço `services/radar_service.py` com suporte a operações reais já carregadas pelo app;
- fallback seguro para dados demonstrativos quando não houver dados reais mínimos;
- tela `templates/radar_oportunidades.html` atualizada para substituir a prévia por operações reais quando existirem;
- indicação visual da fonte dos dados;
- testes do serviço do Radar com operação real e fallback.

## Mantido fora do escopo
- provider real de mercado;
- cotação externa;
- corretora;
- execução de ordens;
- rolagem;
- Machine Learning.

## Observação
A tela ainda não executa compra/venda nem busca oportunidades externas. Ela usa as operações abertas cadastradas no próprio sistema e prepara o caminho para a próxima etapa: aplicar o Score IA completo diretamente no servidor com dados reais.
