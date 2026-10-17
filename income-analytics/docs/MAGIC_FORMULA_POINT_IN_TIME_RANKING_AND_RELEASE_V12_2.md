# Fórmula Mágica — ranking point-in-time e release V12.2

**Resultado: PASS · FEATURE_STATUS = RELEASED · MAGIC_FORMULA_FEATURE_READY_FOR_USE = YES**

O bloqueio temporal RC06 foi resolvido. A tela passa a consumir o snapshot canônico publicado `mf-f1ee50809c83979ba221d84e`, construído com dados que eram públicos até **30/12/2025**. O validador independente confirmou zero look-ahead. A política e suas fórmulas permaneceram inalteradas.

## Seleção temporal

A data histórica (`RANKING_AS_OF_DATE`) é 30/12/2025; a construção/auditoria ocorreu em 16/10/2026. A disponibilidade foi determinada pela data oficial de protocolo/recebimento da CVM. O contrato financeiro existente suporta DFP anual; por isso, ITR e DFP intermediárias não foram transformadas em FY/TTM. Documentos posteriores ao as-of e períodos intermediários não suportados foram rejeitados antes do cálculo de EY, ROC e ranks.

Foram avaliados 2.072 documentos candidatos de 307 empresas do universo congelado. O seletor escolheu 299 documentos anuais elegíveis: 298 relativos ao exercício encerrado em 31/12/2024 e um DFP de 31/12/2023, cada qual já protocolado até 30/12/2025. Rejeitou 332 documentos posteriores ao corte; rejeitou também candidatos intermediários por incompatibilidade com o contrato contábil. As seis amostras douradas passaram: PETR4, VALE3, WEGE3, CMIG4 e ABEV3 são ranqueáveis; CSNA3 permanece bloqueada porque não há evidência elegível de identidade ticker–emissor até o corte. Não se usou o diretório B3 de 2026 para preencher essa lacuna.

Cada uma das 165 linhas do ranking tem lineage de documento financeiro e hash, protocolo/disponibilidade, preço histórico e fonte/hash, ações e métricas. As 165 entradas ranqueadas passaram a validação temporal de preço e quantidade de ações. Entre os 11 bloqueios do universo elegível, sete decorrem de identidade de segurança sem prova point-in-time suficiente e quatro de dados financeiros consolidados ausentes. Quatro empresas adicionais têm denominador de capital investido não positivo e ficam como `METRIC_NON_RANKABLE`, preservando a fórmula atual; esses casos não recebem valores inventados.

## Ranking e integridade

| Medida | Antes (V11) | Depois (V12.2) |
|---|---:|---:|
| Empresas ranqueadas | 174 | 165 |
| Coverage metodológica | 74,07% | 67,90% |
| Coverage conservadora | 68,70% | 62,98% |
| Empresas com look-ahead | 174 | 0 |

`ranking_hash` V12.2: `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3`. O hash de conteúdo do snapshot é `18a8631490f3a340575df3234acc26065a467b701c9a999cd3eaed859bb82db7`. Duas reconstruções produziram os mesmos dois hashes. Os 165 EY, ROC e ranks globais foram calculados após congelar os inputs point-in-time, mantendo o mecanismo canônico de ranking e seus desempates.

A política `MF_BR_2027_V1` permaneceu inalterada: hash antes/depois `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`. S4, L3, exclusões metodológicas financeiras e screening também permaneceram como aprovados. Varejo tradicional e aviação seguem fora da metodologia e como filtros posteriores, que preservam o rank global.

O snapshot V11 `mf-783598cd7f717527425123eb` foi mantido para auditoria e invalidado com motivo `TEMPORAL_LOOKAHEAD`; a UI não o utiliza. O evento de publicação V12.2 é append-only. A leitura do snapshot publicado confirmou 165 resultados, com rank 1 no primeiro item e posições globais preservadas após filtros.

## Validação e produto

- Baseline V9.2: 273/273 PASS; todos os 273 IDs congelados aparecem como PASS na suíte final.
- Testes focados: 40/40 PASS, incluindo os 34 testes da feature e os seis testes V12.2.
- Suíte completa: 837/837 PASS, sem falhas, erros ou skips.
- Ruff: PASS nos arquivos alterados dentro do escopo.
- Read model/API e testes automatizados da página: PASS. Busca, filtros, detalhe com fontes e período contábil, e cards mobile são cobertos pelos testes de produto/UI.
- Performance de 100 leituras persistidas: p50 34,025 ms; p95 46,925 ms; máximo 52,696 ms (limite 250 ms): PASS. A requisição lê ranking persistido; não recalcula os fundamentos.
- Smoke manual no navegador: `NOT_RUN` por bloqueio da política de URL do navegador embutido. Os testes automatizados de UI/API passaram, condição de release permitida pela especificação.
- Manifesto: 837 IDs, 837 PASS; SHA-256 dos IDs `e157fd3ab890beeca6ae30c9c84d4ef1117edc644033c9ff5a72c88923225d14`.

## Estado final

`RC06_LOOKAHEAD = RESOLVED` · `MAGIC_FORMULA_TEMPORAL_INTEGRITY = PASS` · `MAGIC_FORMULA_FEATURE_READY_FOR_USE = YES` · `FEATURE_STATUS = RELEASED` · `RANKING_AVAILABLE_IN_INCOME = YES` · `LOOKAHEAD = 0`.

## Artefatos

- Evidências e decisões dos 23 gates: [release_gate.json](appendices/magic_formula_v12_2/release_gate.json)
- [Snapshot canônico](appendices/magic_formula_v12_2/ranking_snapshot.json) e [diff V11–V12.2](appendices/magic_formula_v12_2/ranking_diff_v11_v12_2.csv)
- [Seleção financeira point-in-time](appendices/magic_formula_v12_2/point_in_time_financial_selection.csv), [auditoria de ações](appendices/magic_formula_v12_2/point_in_time_shares_audit.csv) e [lineage do ranking](appendices/magic_formula_v12_2/ranking_input_lineage.csv)
- [Validação independente de look-ahead](appendices/magic_formula_v12_2/lookahead_validation.json), [coverage](appendices/magic_formula_v12_2/coverage_reconciliation.json) e [casos dourados](appendices/magic_formula_v12_2/golden_cases.json)
- [Manifesto de testes](appendices/magic_formula_v12_2/test_manifest.json), [relatório JUnit](appendices/magic_formula_v12_2/full_suite.xml) e [performance](appendices/magic_formula_v12_2/performance.json)
