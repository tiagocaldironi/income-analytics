# Income Analytics — Analytics Engine Performance V1.1

**Resultado:** `FAIL` no gate sistêmico; os quatro endpoints analíticos estão otimizados e cumprem o orçamento individual aquecido de 500 ms. O gate sistêmico permanece bloqueado pelos dois testes de `finding_engine_v2` descritos abaixo.

## Ambiente e método

Medição final realizada em 17/10/2026, em um processo Uvicorn dedicado (`127.0.0.1:8011`), com jobs de inicialização em background desabilitados somente para esse ambiente (`INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS=1`). Não houve refresh, importação, provider externo nem navegação paralela. Cada endpoint recebeu uma chamada fria seguida de dez chamadas aquecidas sequenciais. O p95 usa nearest-rank; com dez amostras, ele coincide com a maior amostra aquecida. Todos os 44 requests analíticos retornaram HTTP 200 e tiveram payload estável entre chamadas.

| Endpoint | Frio | Mediana aquecida | p95 aquecido | Payload |
| --- | ---: | ---: | ---: | ---: |
| `wealth-evolution` | 667,31 ms | 432,06 ms | 495,72 ms | 42.535 B |
| `wealth-explanation` | 263,49 ms | 264,64 ms | 341,77 ms | 16.609 B |
| `portfolio/performance` | 184,35 ms | 178,12 ms | 297,14 ms | 1.675 B |
| `performance-comparison` | 344,99 ms | 34,96 ms | 104,23 ms | 1.612 B |

Em relação às medianas aquecidas do benchmark controlado antes da otimização, as reduções medidas foram 63,4%, 87,6%, 90,9% e 46,1%, respectivamente. Os valores de antes e depois, hashes e amostras estão em `docs/appendices/performance_v1_1/`.

## Causa raiz e mudanças

O custo estava no processamento histórico em Python, não no SQL. O profile antes da mudança mostrou reconstruções repetidas da posição e replay de eventos por data; por exemplo, `FinancialEffectFactory.from_event` foi chamado 40.982 vezes em `wealth-evolution`, 96.598 vezes em `wealth-explanation` e 89.954 vezes em `portfolio/performance`. No profile final, esses números caíram para 1.344, 6.726 e 4.036. A projeção cronológica agora ordena e avança o ledger uma vez por série e aplica 1.346 eventos na execução de `wealth-evolution`.

Outros trabalhos repetidos também foram removidos: a série histórica de preços é indexada para lookup cronológico, as taxas de câmbio são indexadas por par/data e consultadas por busca binária, coverage reutiliza a grade de valuation e TWR reaproveita os estados projetados. `wealth-explanation` conserva projeções de boundaries dentro do request. Não foi introduzido cache entre requests, nem alterada a semântica financeira.

O profile final ainda mostra projeção de renda fixa e valuation de moeda como trabalho relevante, mas os endpoints permanecem dentro do orçamento individual. A fase não inicia outra rodada ampla de otimização.

## Integridade financeira e regressões

Os quatro payloads antes/depois são **idênticos byte a byte**, com os mesmos tamanhos e hashes. `TWR_SEMANTICS_CHANGED=NO` e `MAGIC_FORMULA_CHANGED=NO`.

No processo dedicado final, `dashboard` teve p95 aquecido de 13,32 ms e `holdings` de 13,57 ms; ambos responderam HTTP 200 em 11 chamadas. A raiz web e `/static/js/app.js` também retornaram 200. O dashboard retornou 101.112 bytes nesta carteira e execução; a referência anterior era aproximadamente 92 KB, então o tamanho foi registrado para acompanhamento, sem evidência isolada de regressão causada por esta mudança. Ver `system_regression_benchmark.json`.

O teste estrutural de escala mediu 14,22 ms para 1x (1.408 eventos, 27.384 preços e 21 datas), 33,27 ms para 2x e 66,80 ms para 4x. O crescimento observado foi próximo de linear, com 4x levando 4,7x o tempo de 1x.

O ensaio concorrente no endpoint de performance, com dez lotes para cada nível, observou p95 de 595,73 ms para concorrência 1, 945,45 ms para concorrência 2 e 965,16 ms para concorrência 4. Isso identifica degradação de cauda sob concorrência. O orçamento de 500 ms foi medido e aprovado no teste sequencial individual; a especificação não define gate de concorrência separado.

## Qualidade e gate

Os 49 testes focados passaram. A suíte completa coletou e executou 857 testes com `PYTHONPATH=src;.`: 855 passaram e dois falharam em `tests/application/test_finding_engine_v2.py`:

- `test_missing_history_is_unknown_without_future_price_fallback`: esperado `UNKNOWN`, observado `WORSENING`.
- `test_no_undated_asset_price_fallback`: cobertura esperada `0`, observada `1`.

Esses testes são de `finding_engine_v2`, fora do escopo analítico e sem alterações correspondentes nesta fase. O problema de coleta inicial foi configuração de `PYTHONPATH`; os módulos investigados existem no checkout e nenhum módulo falso foi criado. Ruff e `git diff --check` passaram. Browser smoke não foi executado; a validação HTTP e os contratos de resposta foram executados.

| Gate | Resultado |
| --- | --- |
| ANPERF_01–10: benchmark, profile, causa raiz, replay, preço, FX e reuse | PASS |
| ANPERF_11–14: quatro endpoints dentro de 500 ms | PASS |
| ANPERF_15–16: regressões de holdings e dashboard | PASS |
| ANPERF_17–19: payloads e semântica financeira preservados | PASS |
| ANPERF_20: escala aceitável | PASS |
| ANPERF_21: suíte coleta com ambiente configurado | PASS |
| ANPERF_22: suíte completa | FAIL — 2 falhas fora do escopo |
| ANPERF_23–24: Ruff e HTTP runtime | PASS |

**`ANALYTICS_ENGINE_OPTIMIZED=YES`** · **`ALL_ANALYTICS_WARM_P95_UNDER_500MS=YES`** · **`SYSTEM_PERFORMANCE_RELEASE_GATE=FAIL`**

O único bloqueio do gate sistêmico é a suíte com duas falhas fora do escopo. O ponto de desempenho restante medido é a degradação de cauda concorrente descrita acima. Não foi iniciada outra rodada ampla.

## Artefatos

Profiles `.pstats`, CSVs por função, call counts, benchmarks, payloads dourados, comparação de correção, evidência de escala/concorrência, auditoria de coleta, manifesto de testes e gate estão em [`docs/appendices/performance_v1_1/`](appendices/performance_v1_1/).
