# Otimização sistêmica de performance — Income Analytics

**Resultado: FAIL (parcialmente otimizado; release gate incompleto).** A auditoria reproduziu lentidão real em endpoints analíticos e encontrou trabalho quadrático em projeções históricas. Foram aplicadas otimizações de projeção, dashboard/read model, FX em lote e carregamento de rotas do frontend. As 43 verificações focadas passaram, Ruff passou e a versão final foi iniciada; o health check respondeu 200. No runtime atual, holdings caiu de p95 14.9 s para 25.06 ms em cinco chamadas warm, com uma leitura SQL (~0.8 ms). A suíte completa não coletou por módulos ausentes no checkout. Os analíticos continuam acima da meta, portanto a otimização sistêmica não está completa.

## Baseline e volume

Os dados vêm da base local real (`income_analytics.db`, 10,092,544 bytes; aproximadamente 9.6 MiB). Inventário observado: 1,402 eventos, 27,377 preços, 1,345 taxas FX, 84 ativos, 2,286 linhas de importação B3, 133 taxas de benchmark e 14 observações de benchmark. O dashboard carregava um histórico embutido com 1,402 linhas (~184 KB) que o frontend não consome; o payload era 246,867 bytes.

Gargalos mais significativos: (1) evolução patrimonial reconstruía todos os pontos históricos e varria/reordenava preços repetidamente; (2) `holdings` recalculava `performance()` para cada classe, chegando a p95 14.9 s; (3) análises de riqueza/performance recalculavam séries com milhares de eventos e/ou preços, com alguns endpoints acima de 1.5 s e cold performance-comparison em 9.7 s. O `health` do processo antigo também ficou sem resposta por mais de 3 s.

## Alterações

- Projeções de carteira e cobertura de performance percorrem eventos/preços em ordem cronológica e mantêm estado incremental, evitando varreduras integrais repetidas por data.
- `PortfolioSession` mantém índices em memória por ativo e cache de FX por moeda/data, com invalidação nos caminhos de escrita; o valuation mantém a regra temporal de não usar cotação posterior à data avaliada.
- Evolução patrimonial agrega datas solicitadas primeiro e projeta só os buckets apresentados.
- O dashboard persiste resposta compacta sem `portfolio.history`; GET lê o snapshot e deixa de reconstruí-lo. Holdings corrente também lê o read model. `as_of` continua sendo computado.
- A comparação de performance memoiza períodos repetidos dentro da mesma montagem. Atualização de FX usa upsert em lote numa transação.
- As rotas de Fórmula Mágica carregam apenas o endpoint correspondente, removendo chamadas sequenciais redundantes ao endpoint genérico.
- Instrumentação SQL/request opt-in via `INCOME_ANALYTICS_PERF_LOG=1`; sem variável, não ativa os logs detalhados.

## Medições disponíveis

Tempos em ms, medidos contra a base real. A tabela pós representa código carregado antes das últimas alterações de holdings e memoização; não é benchmark final da árvore atual.

| Jornada/endpoint | Antes p95 | Depois p95 medido | Meta | Estado |
|---|---:|---:|---:|---|
| Dashboard `/api/portfolio/dashboard` | 68.41 | 29.69 warm | 250 | Dentro warm; primeiro carregamento variou |
| Operações `/api/operations/history` | 206.47 | 63.14 | 250 | Dentro |
| Rendimentos `/api/settings/paid-income` | 7.56 | 7.56 | 250 | Dentro |
| Evolução `/portfolio/history?period_months=12` | >35,000 (baseline bloqueou) | 229.14 | 250 | Dentro no código anterior |
| Entender `/analytics/wealth-explanation` | n/d | 9,544.7 latest max | 500 | Acima; variou com chamadas concorrentes |
| Evolução `/analytics/wealth-evolution` | >35,000 | 5,469.2 latest max | 500 | Melhorou versus timeout, ainda acima |
| Performance `/portfolio/performance` | n/d | 10,625.2 latest max | 500 | Acima; variou com chamadas concorrentes |
| Comparação `/analytics/performance-comparison` | n/d | 10,830.7 latest max | 500 | Altamente variável; uma repetição warm foi 432.6 ms |
| Fórmula Mágica stocks | n/d | 79.78 | 250 | Dentro |
| Holdings `/api/portfolio/holdings` | 14,892.10 | 25.06 warm | 250 | Dentro |

O baseline teve cinco amostras para endpoints comuns e três para analíticos. Com o runtime final, o profiler registrou 0 ms de SQL nos endpoints analíticos; o custo observado ficou em projeção/cálculo em memória. Outras requisições locais concorreram durante essa coleta, produzindo grande variação, por isso reportamos o máximo mais recente e não o chamamos de p95 estável. Para algumas rotas não havia medição “antes” equivalente; não foi inventado valor. `screen_benchmarks_before_after.csv` explicita os itens sem medição de tela/render.

## Banco, rede e semântica

Não foram adicionados nem removidos índices: as medições apontaram custo dominante em trabalho de projeção em memória, chamadas repetidas à camada de aplicação e payload; não houve benefício demonstrado para novo índice. O snapshot é procurado pela chave primária e FX pelo índice existente. Nenhuma chamada a provedor externo ocorre nos GETs normais auditados; refresh continua em sua rota explícita/background. B3/Magic Formula continuam lendo snapshots publicados. Não houve alteração intencional de regras financeiras.

Verificações compararam a projeção otimizada com a projeção de referência nas datas representativas e cobriram limites temporais de cotação, snapshot GET sem rebuild e upsert FX. A equivalência do dashboard compactado foi verificada. Os testes focados passaram (43). Não há evidência concluída de reconciliação independente de cada métrica financeira ponta a ponta; o gate correspondente permanece parcial.

## Pendências de release

- Repetir as medições sob carga controlada e capturar a primeira abertura de cada tela, pois primeiros requests e tarefas concorrentes de startup produziram outliers.
- Completar profile SQL por request, profile de escrita com tempos antes/depois, e benchmark de navegação/render real. O browser local foi bloqueado pela política do browser; não foi contornado.
- Isolar carga concorrente e perfilar/otimizar os analíticos que continuam acima de 500 ms; avaliar o payload de 219 KB da listagem de execuções de refresh.
- Corrigir as referências a `scripts.discover_magic_formula_universe`, `scripts.audit_magic_formula_investable_universe_v6` e pacote `spikes` ausentes antes de executar suíte completa.

## Arquivos de evidência

Veja [apêndices de performance](appendices/performance_v1/). O comando reproduzível é `python scripts/performance_audit.py --help` (usa apenas GETs e grava os resultados no diretório de apêndices).
