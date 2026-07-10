# Sprint Funcional F — Serviço de Radar e primeira tela visual

## Status

- Issue: #27
- Branch: `sprint-funcional-f-radar-screen`
- Natureza: primeira entrega visual do Radar

## Resultado

Foi criada a primeira tela visual do Radar de Oportunidades, acessível pelo menu já existente `🔥 Radar de Oportunidades`.

A tela apresenta uma prévia demonstrativa/controlada com:

- ranking de PUTs;
- Score IA;
- ROI alvo de 4%;
- preço líquido;
- desconto;
- DTE;
- resumo curto do motivo da operação;
- operação elegível;
- operação em observação;
- operação descartada.

## Serviço criado

Foi criado `services/radar_service.py`, que monta oportunidades demonstrativas usando o novo Decision Engine:

- contrato de oportunidade;
- métricas de PUT;
- filtros de segurança;
- qualidade do ativo;
- avaliador de estratégia;
- Score IA;
- ranking;
- resumo curto.

O serviço não busca dados externos, não acessa banco e não acessa CSV.

## Tela criada

Foi atualizada `templates/radar_oportunidades.html`.

A tela é visual e pronta para o Product Owner ver no app, mas ainda usa dados demonstrativos até a integração com operações reais/provider.

## Fora de escopo preservado

- provider real;
- cotação real;
- banco;
- CSV;
- corretora;
- rolagem;
- Machine Learning;
- execução de ordens.

## Próximo passo

Sprint Funcional G — conectar o Radar às operações reais cadastradas e reduzir dados demonstrativos.
