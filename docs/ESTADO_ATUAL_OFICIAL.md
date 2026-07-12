# Estado Atual Oficial — FaculdadeMaria

**Data da auditoria:** 12/07/2026  
**Fonte:** código integrado, testes automatizados e documentação de Sprints

## Estado consolidado

O FaculdadeMaria possui atualmente:

- Decision Engine independente do Flask;
- contrato normalizado de oportunidades;
- métricas auditáveis para venda de PUT;
- filtros determinísticos de segurança e liquidez;
- avaliação de qualidade de ativos;
- Score IA explicável;
- ranking aderente ao perfil operacional;
- explicações técnicas rastreáveis;
- provider público B3 COTAHIST EOD;
- provider CVM para qualidade fundamentalista;
- confirmação manual de preços intraday;
- importação de cadeia de opções por CSV;
- Radar de Oportunidades Premium;
- Scanner Inteligente separado do Radar;
- análise de rolagem com manter, fechar ou rolar;
- Dashboard Executivo Premium;
- alertas operacionais por gravidade;
- cadastro, edição e fechamento de operações sem saída da página;
- central executiva de operações fechadas com filtros, edição, exclusão e reabertura;
- suporte explícito a exercício como parte da estratégia.

## Limitações vigentes

- mercado automático é EOD, não tempo real;
- preços intraday dependem de confirmação manual;
- dados importados no filesystem podem ser perdidos em hospedagem efêmera;
- não existe integração automática com a corretora;
- não existe envio de ordens;
- notas BTG/Necton são importadas, mas outros layouts de corretora não são suportados;
- CI automatizada executa sintaxe e suíte completa no GitHub.
- Configurações possui limpeza protegida por mês, ano ou reset operacional completo.
- livro-caixa registra aportes, retiradas e saldo contábil da corretora;
- DARFs pagos possuem cadastro manual, filtros e gráfico evolutivo.

## Última Sprint integrada

`FM-OPS-010 — Importação de notas de corretagem BTG/Necton`

Upload de PDF no cadastro, extração, conferência humana obrigatória, prevenção de duplicidade e central financeira de notas.

## Próxima recomendação

`FM-TAX-010 — Histórico de DARFs pagos`.

## Governança

Os relatórios individuais de Sprint registram o estado existente no momento em que foram escritos. Para decisões atuais, prevalecem este documento, o Backlog Oficial e o código integrado na `main`.
