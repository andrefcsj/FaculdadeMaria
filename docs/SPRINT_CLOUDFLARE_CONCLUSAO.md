# Sprint CF-02 — Conclusão funcional da migração

Autorização: Andre, em 08/10/2026: “pode iniciar”, após apresentação dos itens 1 a 5.
Status: implementação e corte de endereço concluídos; desligamento do legado pendente. Branch: cloudflare-migration-prep.

## Escopo autorizado

1. Radar de novas oportunidades, scanner e integração de mercado, preservando as regras do Decision Engine.
2. Revisão de cálculos, probabilidade de exercício e memória fiscal.
3. Reconciliação de dados entre origem e destino, preservando os lançamentos feitos no Cloudflare.
4. Testes completos em base separada e backup/restauração.
5. Preparação do endereço www.radarpulse.com.br/faculdademaria/ e plano de reversão.

O corte de rota/DNS e desligamento do Render/Neon dependem de autorização final com resultados revisáveis. Não realizar importações de notas ou operações de teste na base do usuário. Manter a arquitetura gratuita de assets + Worker JavaScript + D1; os documentos da CF-01 sobre Flask/Python/R2 representam alternativas anteriores, substituídas pela decisão de manter o plano Free.

## Evidências iniciais

- Backup real do Cloudflare salvo em pasta local ignorada: 2 operações abertas, 27 fechamentos, 58 notas, 4 lotes, 7 eventos de caixa, 0 DARFs, 4.049 cotações de mercado.
- Pedido de backup do Render retornou HTTP 502. Não existe ainda evidência de reconciliação completa entre as bases.
- Menu Radar e Jade Lizard apontava para acompanhamento de posições, rolagem para simuladores gerais; não corresponde à implementação antiga.
- Probabilidade no cadastro usava spot/strike × 50, sem fundamento estatístico.
- Apuração fiscal não tinha compensação de perdas nem segregação comum/day trade.
- Restauração apagava e inseria em lotes separados de 100 statements: falha tardia podia deixar banco parcialmente restaurado.

## Validação

Em andamento: baseline Python, testes da API em SQLite isolado, paridade de cálculos, regressão no navegador desktop/mobile, reconciliação somente leitura e verificação da publicação.

## Resultado da implementação e publicação

Itens 1–4 implementados e validados; item 5 executado após a aprovação do corte. O desligamento de Render/Neon não foi executado.

- Radar agora consulta novas PUTs, aplica ROI alvo 4%, liquidez, spread, qualidade CVM, concentração e prazo; expõe fatores e dados insuficientes.
- Scanner usa ações disponíveis e cobertura existente; Jade utiliza códigos, bid/ask e vencimentos reais; rolagem compara custo de recompra e nova venda, sem lançar operações.
- Integrações SLDX, histórico observado, B3/COTAHIST, CVM/DFP e CSV. ZIPs são processados em Web Worker no navegador; o servidor faz consultas e cache em D1.
- Probabilidade substitui a regra spot/strike × 50 por distribuição lognormal com volatilidade observada. Ausência de histórico não gera probabilidade inventada.
- Memória gerencial fiscal separa operações comuns/day trade, prejuízos, IRRF e acumulado abaixo de R$ 10. Exercícios antigos de CALL sem custo fiscal suficiente aparecem para revisão, sem atribuir uma base presumida. Novos exercícios guardam o custo entregue e resultado fiscal.
- Nota e operação são salvas na mesma transação. Repetição não duplica; uma falha de cobertura não deixa nota órfã. Reabertura parcial preserva a posição original; reversão de PUT exercida verifica o lote e a cobertura.
- Restauração valida o backup completo e usa uma transação única, com rollback em falhas tardias. Backup inclui timestamps e cache de mercado.
- Calculadora rápida mostra strike menos prêmio (PUT) e strike mais prêmio (CALL), sem vencimento obrigatório.
- Caixa aplica o sinal de débito uma única vez, inclusive quando a nota já armazena valor negativo.
- Tabelas largas rolam dentro dos painéis no celular, sem alargar a página.

## Reconciliação concluída

O Render voltou a responder em 08/10/2026. Backup portátil PostgreSQL obtido e validado por hashes: 12 tabelas e 4 arquivos. A tabela de demonstração `playing_with_neon` foi preservada no ZIP original, sem importá-la como dados do sistema.

- Origem: 1 aberta, 24 fechamentos, 51 notas, 6 eventos de caixa, 4 lotes, 0 DARFs.
- Destino: 2 abertas, 27 fechamentos, 58 notas, 7 eventos de caixa, 4 lotes, 0 DARFs.
- Nenhum registro financeiro original ausente. Acréscimos correspondem aos lançamentos posteriores do piloto.
- Redução de 100 ações BBAS3 e 100 BBDC4 corresponde às duas CALLs exercidas no piloto. Custos e quantidades originais dos lotes foram preservados.
- Cotações manuais e preferências atualizadas no Cloudflare foram mantidas. Duas preferências originais de operações já fechadas (53 e 54), ausentes no destino, foram recuperadas com `INSERT OR IGNORE`, sem substituir configurações novas.
- Comparação do backup antes/depois desta Sprint: nenhum lançamento financeiro adicionado, removido ou alterado; apenas as duas preferências originais recuperadas. Consultas de mercado atualizam exclusivamente o cache de mercado.

Relatórios e backups: `tmp/migration-2026-10-08/`, fora do Git. Auditoria reproduzível: `scripts/audit_cloudflare_backup.cjs`; conversão da origem: `scripts/convert_render_backup.cjs`.

## Validação final

- 164 testes Python aprovados. Atualizado um teste desatualizado que esperava “Novos Aportes” no menu: agora verifica o link existente e seu rótulo “Aportes”. O produto legado não foi alterado.
- 24 testes JavaScript aprovados em SQLite/memória, incluindo autenticação, importação atômica, cobertura, fechamentos parciais, exercício, reabertura, restauração com mais de 4.050 cotações e reconciliação.
- Paridade com Python: 18 casos de métricas/score, 6 probabilidades e 4 competências fiscais aprovados.
- Navegador isolado: 1440 px e 390 px, login, nove telas, calculadora, Radar, scanner e fiscal; sem erros JavaScript e sem página alargada.
- Fontes reais no piloto: SLDX BBAS3 (695 opções), histórico BBAS3 (128 preços), B3 de 07/10/2026 (4.781 opções vigentes para o universo), CVM 2025 (15 perfis). Fluxo CVM/B3 executado pelo navegador, com 120 cards de Radar e 80 do scanner, sem erros JavaScript. Esses dados representam a consulta registrada, não garantia de cotação intraday.
- Publicação no domínio do piloto e backup final confirmados por HTTP 200.

Plano de endereço e reversão: `docs/CLOUDFLARE_CORTE_E_REVERSAO.md`. Não declarar migração 100% encerrada antes do corte aprovado e da confirmação do endereço principal.

## Corte aprovado e executado

Andre autorizou ativar o endereço principal em 08/10/2026: “pode sim. vlw”. Publicação no www concluída e conferida em desktop/celular; backups financeiros iguais antes/depois e rota de contabilidade preservada. O endereço principal já é `https://www.radarpulse.com.br/faculdademaria/`. A configuração padrão de publicação inclui a rota ativa; a reversão de rota usa `wrangler.pilot-only.jsonc`. Render e Neon permanecem ativos, aguardando a etapa de desligamento.
