# Magic Formula — Ranking Engine Validation Gate

Data: 17/09/2026. Execução restrita a `VALIDATION_SAMPLE`, com os cinco emissores canônicos existentes.

**Decisão: PASS para o engine nesta amostra de validação.** Pré-gate, cálculo de produção, QA independente, determinismo, persistência/read-back e testes passaram. A ferramenta continua `VALIDATION_REQUIRED` e a publicação do ranking `INACTIVE`. Esta validação não demonstra suficiência de um universo publicável.

## Pré-gate e amostra congelada

O banco canônico real `income_analytics.db` foi consultado novamente antes de qualquer rank. Petrobras, WEG, Suzano, Rumo e Telefônica permaneceram RESOLVED e elegíveis, com snapshot V2 validado, QA formal PASS vinculado, adapter aprovado e referência compatível. O gate canônico existente retornou cinco resolvidos, nenhuma exclusão e nenhum achado crítico. Não houve expansão do universo, download, leitura de RAW para cálculo, rematerialização ou alteração dos fundamentos.

`VALIDATED_RESOLVED_ISSUERS = 5`, `MULTISECTOR_GOLDEN_GATE = PASS`, `OPEN_DEFECTS = 0` no escopo desta validação. Se qualquer emissor falha, a execução bloqueia a amostra inteira com `RankingGateBlocked` e reason codes; não produz ranking parcial.

- Sample ID: `ec8ca4f4-5370-41bf-b757-47d9fc1e24ca`.
- Digest da amostra congelada: `d4a7ff4c7cc3bce074d4390bd4c9cc5c60e314760713f364b02aba84a17df9d0`.
- Universe type: `VALIDATION_SAMPLE`.
- Reference date: `2025-12-31`.
- Methodology: `MAGIC_FORMULA_STOCKS_V1`.
- Adapter: `CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE`.
- A seleção inicial foi persistida como artefato FROZEN antes do cálculo. Cada input contém issuer UUID, snapshot ID, QA ID, digest do snapshot e os cinco valores aprovados: EBIT, EV, Invested Capital, EY e ROC.
- Depois do congelamento, todas as consultas de elegibilidade recebem `snapshot_id` explícito. Nenhum snapshot mais recente pode substituir silenciosamente o selecionado. Mudança do input ou do QA bloqueia a execução.

| Issuer | UUID | Fundamentals snapshot | Formal QA PASS |
|---|---|---|---|
| Suzano | `66ed46ae-3438-4bc9-a945-c4b7ba9df9b0` | `5efdb7bf-4433-45f9-b06c-38e09bd7baa5` | `a8334600-73b8-4adc-bd56-2ab5ea277df1` |
| Petrobras | `d534bf40-ca22-4d9d-83b6-458f29b27399` | `6d5dd506-9023-4862-81eb-067cb0bc3cf2` | `f2ed0dc5-f34a-41c7-b162-cb389187a2f3` |
| Telefônica Brasil | `e8e1f3bd-eab1-4ed0-a503-ced7d797d03e` | `d97ee807-7299-41b2-9026-d6ec7f926d70` | `09afeef3-23da-4d37-96fa-0dd7a216bfb7` |
| Rumo | `e9b5b58f-ba9f-4708-8b45-c70315d588b9` | `a827520a-f34b-4cb9-87ae-83d0b94a09ba` | `ec0a71e2-b3c8-4bb5-808c-120221cffe25` |
| WEG | `eb89bcc0-8295-45c6-91c7-8832ce58d76f` | `56cffb48-edf2-493c-a775-de1aacab5685` | `c5dcc8c5-f45f-431d-b1b9-5d53538d1482` |

## Input financeiro aprovado

Valores consumidos exclusivamente dos snapshots V2. As razões EY e ROC já persistidas foram ordenadas com `Decimal`; os fundamentos e razões não foram recalculados a partir de RAW.

| Issuer | EBIT | Enterprise Value | Invested Capital |
|---|---:|---:|---:|
| Suzano | 10649009000.0000000000 | 143209011142.6000000000 | 79203044000.0000000000 |
| Petrobras | 145628000000.0000000000 | 758671648612.5200000000 | 954310000000.0000000000 |
| Telefônica Brasil | 9859278000.0000000000 | 119088912251.2000000000 | 49591361000.0000000000 |
| Rumo | 4579664000.0000000000 | 43497107954.0800000000 | 23734112000.0000000000 |
| WEG | 7998741000.0000000000 | 201827535650.2300000000 | 26470527000.0000000000 |

## Metodologia e política de empates

EY = EBIT / EV e ROC = EBIT / Invested Capital permanecem as definições aprovadas. O engine ordena as razões aprovadas de forma decrescente e aplica ranks densos: valores iguais têm o mesmo rank, sem saltos. `magic_formula_score = EY_rank + ROC_rank`; menor score é melhor. Nenhum peso, percentil, score 0–100, fator adicional ou ajuste subjetivo foi introduzido.

Política técnica explícita: `DENSE_EY_ROC_AND_SCORE; DISPLAY_SCORE_ASC_ISSUER_UUID_ASC`.

- `final_rank`: rank denso do score crescente. Scores iguais compartilham o rank final.
- `final_display_order`: posição sequencial de exibição, ordenada por score crescente e, apenas em empate, UUID estável do issuer crescente.
- Não há desempate econômico adicional aprovado. UUID, ticker e nome não alteram score nem atribuem superioridade financeira; ticker e nome não são usados para ordenação.

## Resultado da execução real

O `MagicFormulaStockRankingService.rank_validation_sample` executou o motor de produção sobre a amostra congelada. Este modo explícito de validação não muda o bloqueio da entrada pública `rank`, que continua exigindo disponibilidade da ferramenta. Nenhum endpoint foi alterado ou publicado.

Valores abaixo em razão decimal integral, sem arredondamento usado no cálculo. A ordem não foi escrita previamente como expected: foi produzida pelo engine e reconstruída pelo QA independente.

| Issuer | Snapshot ID | EY | EY rank | ROC | ROC rank | Score | Final rank | Display order |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Petrobras | `6d5dd506-9023-4862-81eb-067cb0bc3cf2` | 0.1919512878414905484530907490 | 1 | 0.1526003080759920780459179931 | 4 | 5 | 1 | 1 |
| Telefônica Brasil | `d97ee807-7299-41b2-9026-d6ec7f926d70` | 0.08278921869068170061794465638 | 3 | 0.1988103936086771242273427422 | 2 | 5 | 1 | 2 |
| Rumo | `a827520a-f34b-4cb9-87ae-83d0b94a09ba` | 0.1052866320407959569016255136 | 2 | 0.1929570400611575440446223562 | 3 | 5 | 1 | 3 |
| WEG | `56cffb48-edf2-493c-a775-de1aacab5685` | 0.03963156451487339329340703427 | 5 | 0.3021753590323305614580321729 | 1 | 6 | 2 | 4 |
| Suzano | `5efdb7bf-4433-45f9-b06c-38e09bd7baa5` | 0.07435990874482246800090195486 | 4 | 0.1344520167684464248621555505 | 5 | 9 | 3 | 5 |

**Empate encontrado:** Petrobras, Telefônica e Rumo têm score 5 e final rank 1. Aparecem nessa sequência somente pelos UUIDs estáveis. WEG tem score 6 e final rank 2; Suzano tem score 9 e final rank 3. Não houve empate individual de EY ou ROC nesta amostra.

## QA independente e determinismo

O caminho `independent_rank_qa` recebe apenas issuer UUID, EY aprovado e ROC aprovado. Para cada razão, calcula `1 + quantidade de valores distintos estritamente maiores`. Depois soma os ranks, calcula o rank denso do score e a ordem técnica. Não chama o RankingService nem seu método de cálculo.

A comparação verifica issuer, EY, ROC, EY rank, ROC rank, score, final rank, display order e sinalização de empate, campo por campo. Os IDs de snapshot/QA, digests e versões são validados separadamente no repositório antes da persistência. Testes bloqueiam explicitamente chamadas ao cálculo de produção durante o QA e adulteram o resultado para provar a detecção.

- `INDEPENDENT_QA_STATUS = PASS`.
- Digest do resultado independente: `679e3bd8602ae8fe0bcbbc60196b07f5ff12a52fbb47eff945c984c2b3d3aed1`.
- Execuções reais comparadas: `13`; resultados lógicos distintos: `1`.
- As execuções usam a ordem original, inversão e 11 permutações com novas instâncias/conexões do repositório. Os testes também percorrem as 120 permutações possíveis dos cinco inputs.
- `DETERMINISM_STATUS = PASS`.

## Persistência, lineage e read-back

- Ranking snapshot ID: `921b4bfa-d99c-464f-a0ac-2668be1daefb`.
- Created at: `2026-09-17T08:51:12.956153+00:00`.
- Status persistido: `PASS`.
- Banco próprio: `data/magic_formula/validation_rankings.db`.
- Tabela: `magic_formula_ranking_artifacts`; um registro `FROZEN_SAMPLE` e um `RANKING_SNAPSHOT`, ambos com JSON e digest SHA-256 semântico. Triggers proíbem UPDATE e DELETE; o writer somente insere novos artefatos.
- O banco separado evita alterações de schema ou dados no banco canônico de fundamentos. Esta é persistência SQLite real, não cache em memória. Não houve nova migração no banco canônico.
- Lineage por item: final rank → score → ranks EY/ROC → razões aprovadas → fundamentals snapshot ID/digest → Formal QA PASS ID → versões de adapter e metodologia. Não há cópia da evidência DFP/FCA/COTAHIST no ranking.

Cada gravação fez COMMIT e fechou a conexão. O artefato foi relido em conexão nova e comparado semanticamente. Depois do encerramento do processo de execução, outro processo Python abriu novas conexões, releu amostra e ranking, conferiu os fundamentos referenciados, repetiu o QA independente e executou `PRAGMA integrity_check = ok` no banco dos artefatos.

`RANKING_SNAPSHOT_READBACK = PASS`; `LINEAGE_STATUS = PASS`. Evidência: `tmp/ranking-engine-validation/independent-readback.json`. O resultado completo está em `tmp/ranking-engine-validation/real/ranking-validation-result.json`.

## Coverage e exclusões

| Campo | Valor |
|---|---:|
| total_considered | 5 |
| resolved | 5 |
| eligible | 5 |
| ranked | 5 |
| excluded | 0 |
| unresolved | 0 |

`COVERAGE_STATUS = PASS`; `EXCLUDED_ISSUERS = []`. Estes números se referem somente aos cinco integrantes da amostra de validação.

Casos negativos retornam reason codes explícitos, incluindo `ISSUER_NOT_RESOLVED`, `ISSUER_NOT_RANKING_ELIGIBLE`, `MISSING_VALIDATED_SNAPSHOT`, `QA_NOT_PASS`, `QA_SNAPSHOT_MISMATCH`, `ADAPTER_VERSION_MISMATCH`, `MISSING_OR_INVALID_EARNINGS_YIELD`, `MISSING_OR_INVALID_RETURN_ON_CAPITAL`, `NON_POSITIVE_ENTERPRISE_VALUE` e `NON_POSITIVE_INVESTED_CAPITAL`. Métrica ausente não é convertida em zero.

Os controles negativos Petrobras retiram golden, snapshot ou QA apenas de fixtures de teste. Petrobras real e os outros quatro emissores não foram alterados.

## Testes e self-QA

RANK-001..004 verificam EY DESC, ROC DESC, soma de ranks e score ASC. RANK-005..010 verificam resolução, elegibilidade, razões ausentes, EV e IC inválidos. RANK-011..014 verificam empates, separação de ordem técnica, permutações e QA independente. RANK-015..018 verificam QA de outro snapshot, exclusão V1, persistência/read-back e lineage.

A fixture artificial A (EY alto/ROC baixo), B (ambos intermediários) e C (EY baixo/ROC alto) produz score 4 para os três. Também há testes de empates individuais, adulteração de resultado/lineage, mudança do QA congelado, amostra parcial/duplicada, imutabilidade e ausência dos artefatos Petrobras.

```text
python -m pytest tests/application tests/infrastructure/test_b3_cotahist_market_data.py -q -p no:cacheprovider --basetemp=tmp/pytest-ranking-engine-full --junitxml=tmp/ranking-engine-validation/tests.xml
TESTS_PASSED = 145
TESTS_FAILED = 0
```

Foram 26 testes específicos do ranking e 119 regressões existentes. A suíte completa foi executada após a criação do artefato real. JUnit em `tmp/ranking-engine-validation/tests.xml`.

`CHANGED_FILES_LINT = PASS`: cinco arquivos Python, zero apontamentos. `PRE_EXISTING_LINT = 20` no escopo Magic Formula anteriormente reportado (17 no rematerializador legado, dois na migração 0015 e um em golden validation), todos inalterados. Isso não declara o restante do projeto livre de lint.

Backup anterior à etapa: `tmp/ranking-engine-validation/before.db`. Comparação integral das quatro tabelas canônicas antes/depois: igualdade exata, incluindo os dez snapshots, cinco issuers, cinco goldens e cinco QA. SHA-256 dos cinco arquivos golden também permaneceu igual. Não houve alteração de fundamentos, de decisões QA, de golden, da fórmula ou do mínimo do gate.

Único arquivo preexistente alterado nesta etapa: `src/income_analytics/application/magic_formula_stocks.py`. Novos arquivos: módulo `magic_formula_ranking_validation.py`, repositório `magic_formula_ranking_repository.py`, script `validate_magic_formula_ranking.py`, testes `test_magic_formula_ranking_engine.py` e este relatório, além dos artefatos e logs. O estado anterior do worktree e hashes estão no diretório de auditoria. Nenhum reset ou commit foi feito.

## Decisão final

```text
RANKING_ENGINE_GATE = PASS
VALIDATION_SAMPLE_STATUS = PASS
RANKING_ENGINE_STATUS = PASS
INDEPENDENT_QA_STATUS = PASS
DETERMINISM_STATUS = PASS
RANKING_SNAPSHOT_READBACK = PASS
UNIVERSE_TYPE = VALIDATION_SAMPLE
REFERENCE_DATE = 2025-12-31
METHODOLOGY_VERSION = MAGIC_FORMULA_STOCKS_V1
ADAPTER_VERSION = CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE
RANKED_ISSUERS = 5
EXCLUDED_ISSUERS = []
TIES_FOUND = 1 grupo: Petrobras, Telefônica e Rumo; score 5; final rank 1
TIE_POLICY_STATUS = PASS
LINEAGE_STATUS = PASS
COVERAGE_STATUS = PASS
OPEN_DEFECTS = 0
TESTS_PASSED = 145
TESTS_FAILED = 0
CHANGED_FILES_LINT = PASS
PRE_EXISTING_LINT = 20 (inalterados; escopo Magic Formula)
VALIDATED_RESOLVED_ISSUERS = 5
MULTISECTOR_GOLDEN_GATE = PASS
TOOL_STATUS = VALIDATION_REQUIRED
RANKING_STATUS = INACTIVE
RECOMMENDED_NEXT_ACTION = PUBLISHABLE UNIVERSE GATE
```

A próxima fase é avaliar o universo publicável. Os cinco casos sustentam esta validação de cálculo, integração, determinismo e auditabilidade; não autorizam publicação da ferramenta.
