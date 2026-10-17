# Petrobras — recuperação canônica end-to-end

Data: 16/09/2026. Referência financeira e de capital: 31/12/2025. Fechamento B3 efetivo: 30/12/2025.

Petrobras foi criada no banco local real pelo contrato 0016, com golden independente, snapshot V2 inicialmente `NOT_VALIDATED`, oito dimensões de QA `PASS` e elegibilidade canônica `true`. Os cinco emissores estão `RESOLVED`; o gate de prontidão está `READY`. O ranking permanece `INACTIVE` e a ferramenta `VALIDATION_REQUIRED`.

## Execução real e identidade

- Banco: `C:/Projetos/income-analytics/income_analytics.db`. A revisão Alembic permaneceu `0016_magic_formula_canonical_contract`; esta etapa não criou migração.
- Backup anterior às alterações: `tmp/petrobras-e2e-baseline/before.db`.
- Backup imediatamente anterior à gravação real: `tmp/petrobras-e2e-baseline/pre-real-write.db`.
- Issuer UUID: `d534bf40-ca22-4d9d-83b6-458f29b27399`; CVM `009512`; CNPJ `33.000.167/0001-01`; slug `petrobras`; nome `Petróleo Brasileiro S.A. Petrobras`.
- PETR3/ON e PETR4/PN são securities distintas (`BR:PETR3`, `BR:PETR4`) do mesmo UUID. Tickers não são a identidade do issuer; CVM e CNPJ permanecem atributos.
- FCA: referência `2025-01-01`, formulário `147760`, versão `1`, início de negociação `2018-05-14`, sem fim informado. ISINs `BRPETRACNOR9` e `BRPETRACNPR6` foram recuperados do COTAHIST; o CSV FCA não possui coluna ISIN. A fixture preserva a fonte de cada ISIN.

## Construção e fontes independentes

A fixture [petrobras_2025.json](../tests/golden/magic_formula/petrobras_2025.json) foi produzida exclusivamente por `MagicFormulaGoldenEvidenceBuilder`: RAW → evidence builders → golden V2 → serialização em arquivo → persistência no banco → fechamento → leitura em nova conexão → relocalização dos registros RAW. Somente após a verificação dos locators foi materializado o snapshot. Nenhum expected foi copiado ou recalibrado a partir do snapshot.

Esquema `MAGIC_FORMULA_GOLDEN_V2`, metodologia `MAGIC_FORMULA_STOCKS_V1`, fixture `READY_FOR_VALIDATION`, adapter `CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE`.
Hash canônico da fixture persistida: `6babdffc4cb398ed3b431c573286991308daf7eb9dc6410adfc529c7c4a43701`. A cópia versionada é byte a byte igual à saída serializada do builder.

| Arquivo RAW completo | SHA-256 |
|---|---|
| `data\cvm\dfp_cia_aberta_2025.zip` | `de8b7be1cdae032a402ab33916015c74fdc30f0bc64be3f38a4b5dd1d43f6d79` |
| `data\cvm\fca_cia_aberta_2025.zip` | `dbbbda515a98d402ff0b0fb2808d15f3d81b029e0c61de8b95655323604d1192` |
| `data\cotahist\COTAHIST_A2025.ZIP` | `6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d` |

As fontes completas locais foram usadas na recuperação real. Os [excertos de teste e manifesto](../tests/fixtures/cvm/petrobras_canonical_v2/README.md) preservam os registros originais; no COTAHIST, linhas não relacionadas são substituídas por linhas vazias para manter a numeração física original. Os testes conferem os hashes dos arquivos e dos registros. Esses ZIPs pequenos são explicitamente identificados como excertos, não como distribuições completas.

## Evidência contábil e reconciliação

O registry contábil aprovado não foi alterado. DFP consolidada, exercício encerrado em 31/12/2025; DRE de 01/01/2025 a 31/12/2025. Moeda BRL; escala CVM `MIL` → `THOUSAND`, multiplicador 1000. Cada componente mantém descrição original, código, regra, demonstração, escopo, período, referência, valor bruto, escala, multiplicador, valor normalizado e locator.

| Métrica / componente | Regra | Conta | Valor RAW | Multiplicador | BRL normalizado |
|---|---|---|---:|---:|---:|
| cash_and_equivalents | CASH_RULE_001 | 1.01.01 | 35608000 | 1000 | 35608000000 |
| ebit | EBIT_RULE_002 | 3.05 | 145628000 | 1000 | 145628000000 |
| financial_debt_long_term | DEBT_LT_RULE_001 | 2.02.01 | 316772000 | 1000 | 316772000000 |
| financial_debt_short_term | DEBT_ST_RULE_001 | 2.01.04 | 67253000 | 1000 | 67253000000 |
| net_fixed_assets | FIXED_ASSET_RULE_001 | 1.02.03 | 924624000 | 1000 | 924624000000 |
| operating_current_assets | NWC_ASSET_RULE_002 | 1.01.03 | 25461000 | 1000 | 25461000000 |
| operating_current_assets | NWC_ASSET_RULE_002 | 1.01.04 | 45173000 | 1000 | 45173000000 |
| operating_current_liabilities | NWC_LIABILITY_RULE_001 | 2.01.02 | 40948000 | 1000 | 40948000000 |

O snapshot usa o adapter de produção e o `IssuerMarketCapService`; o golden usa os builders independentes. O teste de independência proíbe chamadas ao adapter de produção, ao assembler de produção e à leitura de snapshots durante a construção do golden.

| Métrica | Golden independente = snapshot |
|---|---:|
| cash_and_equivalents | 35608000000 |
| earnings_yield | 0.191951287841490548453090749 |
| ebit | 145628000000 |
| enterprise_value | 758671648612.52 |
| financial_debt_long_term | 316772000000 |
| financial_debt_short_term | 67253000000 |
| financial_debt_total | 384025000000 |
| invested_capital | 954310000000 |
| market_cap | 410254648612.52 |
| net_debt | 348417000000 |
| net_fixed_assets | 924624000000 |
| net_working_capital | 29686000000 |
| operating_current_assets | 70634000000 |
| operating_current_liabilities | 40948000000 |
| return_on_capital | 0.1526003080759920780459179931 |

Igualdade exata com `Decimal`, inclusive EY e ROC, sem tolerância numérica ou preenchimento de métricas ausentes com zero. Financial Debt total é reconciliada pela soma de Debt ST e Debt LT.

## Capital e mercado por classe

| Security | Classe | Emitidas/integralizadas | Tesouraria | Outstanding | Preço BRL | Market cap BRL | Linha COTAHIST |
|---|---|---:|---:|---:|---:|---:|---:|
| PETR3 | ON | 7442231382 | 0 | 7442231382 | 32.57 | 242393476111.74 | line=1692376 |
| PETR4 | PN | 5446501379 | 0 | 5446501379 | 30.82 | 167861172500.78 | line=1692377 |

**Market cap total = R$ 410.254.648.612,52.** `OUTSTANDING = ISSUED_SHARES - TREASURY_SHARES`; unidade aprovada `UNIT`, multiplicador `1`. Todos os valores foram recuperados do RAW. Os anchors informados pelo usuário foram usados somente como assertions após a construção; não houve divergência nem ajuste de expected.

## Round-trip dos locators

Após serialização, persistência e fechamento, o golden foi relido e cada locator foi verificado nos arquivos oficiais completos. Resultado: **16/16 locators com exactly one applicable raw record**: oito contábeis, dois FCA, quatro capital e dois COTAHIST. Formulário, classe, validade, coluna de capital, período, valor, escala, ticker, linha, data, moeda e ISIN foram reconciliados. Duplicidade ou desvio gera `GOLDEN_EVIDENCE_DEFECT`.

| Tipo | Locator | Registros aplicáveis |
|---|---|---:|
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPA / 1.01.01 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / DRE / 3.05 / 2025-01-01 / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPP / 2.02.01 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPP / 2.01.04 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPA / 1.02.03 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPA / 1.01.03 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPA / 1.01.04 /  / 2025-12-31` | 1 |
| accounting | `dfp_cia_aberta_2025.zip / 009512 / 2025-12-31 / CONSOLIDATED / BPP / 2.01.02 /  / 2025-12-31` | 1 |
| security | `fca_cia_aberta_2025.zip / fca_cia_aberta_valor_mobiliario_2025.csv / 33.000.167/0001-01 / 2025-01-01 / 147760 / PETR3` | 1 |
| security | `fca_cia_aberta_2025.zip / fca_cia_aberta_valor_mobiliario_2025.csv / 33.000.167/0001-01 / 2025-01-01 / 147760 / PETR4` | 1 |
| capital | `dfp_cia_aberta_2025.zip:dfp_cia_aberta_composicao_capital_2025.csv / 33.000.167/0001-01 / 2025-12-31 / ON / ISSUED_SHARES / QT_ACAO_ORDIN_CAP_INTEGR` | 1 |
| capital | `dfp_cia_aberta_2025.zip:dfp_cia_aberta_composicao_capital_2025.csv / 33.000.167/0001-01 / 2025-12-31 / ON / TREASURY_SHARES / QT_ACAO_ORDIN_TESOURO` | 1 |
| capital | `dfp_cia_aberta_2025.zip:dfp_cia_aberta_composicao_capital_2025.csv / 33.000.167/0001-01 / 2025-12-31 / PN / ISSUED_SHARES / QT_ACAO_PREF_CAP_INTEGR` | 1 |
| capital | `dfp_cia_aberta_2025.zip:dfp_cia_aberta_composicao_capital_2025.csv / 33.000.167/0001-01 / 2025-12-31 / PN / TREASURY_SHARES / QT_ACAO_PREF_TESOURO` | 1 |
| market | `COTAHIST_A2025.ZIP / COTAHIST_A2025.TXT / line=1692376 / date=20251230 / ticker=PETR3 / close=32.57` | 1 |
| market | `COTAHIST_A2025.ZIP / COTAHIST_A2025.TXT / line=1692377 / date=20251230 / ticker=PETR4 / close=30.82` | 1 |

Os separadores são apresentados como `/` na tabela para legibilidade; os locators originais com `|`, juntamente com os digests dos registros, estão em `tmp/petrobras-e2e-baseline/real/recovery-result.json` e na fixture.

## Snapshot, QA e read-back

- Snapshot: `6d5dd506-9023-4862-81eb-067cb0bc3cf2`.
- QA formal: `f2ed0dc5-f34a-41c7-b162-cb389187a2f3`, vinculado exatamente ao snapshot acima.
- Digest do snapshot vinculado ao QA: `3c6da14e4025943664abae691fac6ce4440bd50384094d14ba98b82ca515131f`.
- Estado inicialmente persistido: `NOT_VALIDATED`; após QA: coluna canônica `validation_status = PASS`. Nenhuma segunda decisão em `metrics_json`.
- A inserção do QA projeta o resultado na coluna de validação atomicamente pelo trigger existente. Somente o status mudou: demais campos, métricas e lineage permaneceram iguais ao snapshot inicialmente gravado.

| Dimensão persistida | Resultado |
|---|---|
| ACCOUNTING | PASS |
| SECURITY | PASS |
| CAPITAL | PASS |
| MARKET | PASS |
| MARKET_CAP | PASS |
| DERIVED | PASS |
| LINEAGE | PASS |
| SNAPSHOT_READBACK | PASS |

`FINAL_QA_STATUS = PASS`. Todas as decisões contêm evidência e vínculo ao mesmo snapshot. Os arquivos `snapshot-initial.json`, `snapshot-readback.json` e `qa-readback.json`, no diretório de auditoria `tmp/petrobras-e2e-baseline/real`, registram a transição.

O writer usa sessões fechadas e `NullPool`; o engine foi descartado. A validação e os read-backs usam conexões novas e encerradas explicitamente. Após o término completo do processo de recuperação, outro processo Python abriu conexões independentes, leu issuer/golden/snapshot/QA/validation, executou a policy e comparou o banco com o backup. `PRAGMA integrity_check = ok`, sem violações de foreign key. Resultado salvo em `tmp/petrobras-e2e-baseline/independent-readback.json`: `READBACK_STATUS = PASS`.

## Resolução, elegibilidade e regressão dos quatro

`RESOLVED` resulta da projeção canônica; não foi inserido como flag para completar o universo. Não houve rematerialização dos quatro emissores anteriores. Todos os registros anteriores das quatro tabelas canônicas foram preservados integralmente: quatro issuers, quatro goldens, nove snapshots (incluindo legados) e quatro decisões formais de QA.

| Issuer | Snapshot | QA | Resolução | Elegível |
|---|---|---|---|---|
| weg | `56cffb48-edf2-493c-a775-de1aacab5685` | `c5dcc8c5-f45f-431d-b1b9-5d53538d1482` | RESOLVED | true |
| suzano | `5efdb7bf-4433-45f9-b06c-38e09bd7baa5` | `a8334600-73b8-4adc-bd56-2ab5ea277df1` | RESOLVED | true |
| rumo | `a827520a-f34b-4cb9-87ae-83d0b94a09ba` | `ec0a71e2-b3c8-4bb5-808c-120221cffe25` | RESOLVED | true |
| telefonica | `d97ee807-7299-41b2-9026-d6ec7f926d70` | `09afeef3-23da-4d37-96fa-0dd7a216bfb7` | RESOLVED | true |
| petrobras | `6d5dd506-9023-4862-81eb-067cb0bc3cf2` | `f2ed0dc5-f34a-41c7-b162-cb389187a2f3` | RESOLVED | true |

Para WEG, Suzano, Rumo e Telefônica, issuer UUID, métricas, lineage, decisões e hashes dos arquivos golden permaneceram exatamente iguais. Comparação por linha completa do banco, além de SHA-256 dos quatro arquivos golden. EBIT, Cash, Debt ST/LT/total, NWC, Invested Capital, Market Cap, EV, EY e ROC não mudaram.

`VALIDATED_RESOLVED_ISSUERS = 5`; `MULTISECTOR_GOLDEN_GATE = PASS`; `RANKING_GATE = READY`. O gate canônico confirma cinco resolvidos, zero exclusões e zero achados críticos. O mínimo permanece cinco. `ranked_issuers = 0`, `TOOL_STATUS = VALIDATION_REQUIRED`, `RANKING_STATUS = INACTIVE`. A API e o serviço de ranking não foram ativados; nenhuma ordenação financeira foi executada nesta recuperação.

## Defeito corrigido e testes

Foi comprovada uma lacuna no QA de market cap: a parcela explicitamente persistida de uma classe podia divergir enquanto o total permanecia correto. O QA agora verifica a parcela de cada classe contra quantidade e preço independentes do golden. O caso PETRO-E2E-009 altera as duas parcelas em +1/-1, conserva o total e recebe `FAIL`. Para V2 anteriores sem parcela explícita, o QA reconcilia os componentes já existentes; seus artefatos não foram alterados.

Testes PETRO-E2E-001 a 008 cobrem golden/snapshot/QA ausentes, dimensão REVIEW_REQUIRED, QA de outro snapshot, validação não PASS, adapter e data incompatíveis. PETRO-E2E-009 cobre parcelas divergentes; 010 prova que métrica ausente não vira zero. PETRO-E2E-011 a 020 cobrem builder/schema, UUID comum, locators determinísticos, market cap, oito dimensões persistidas, read-back, resolução, elegibilidade e preservação dos quatro com gate de cinco. Sete verificações adicionais cobrem checksums, quatro tipos de locator adulterado, duplicidade contábil e independência do builder.

Antes da gravação real: ensaio completo em cópia do banco, suíte relevante com 118 testes e, após a última verificação adicional, 27 testes Petrobras. Após a gravação real:

```text
python -m pytest tests/application tests/infrastructure/test_b3_cotahist_market_data.py -q -p no:cacheprovider --basetemp=tmp/pytest-petrobras-post-real --junitxml=tmp/petrobras-e2e-baseline/post-real-tests.xml
TESTS_PASSED = 119
TESTS_FAILED = 0
```

JUnit e resultados de lint estão em `tmp/petrobras-e2e-baseline`. Os testes rodam em bancos temporários. Guardas legadas de ranking são testadas para bloqueio; nenhum ranking do universo real foi chamado.

`CHANGED_FILES_LINT = PASS`: sete arquivos Python, zero apontamentos. `PRE_EXISTING_LINT = 20`, no escopo Magic Formula previamente reportado: 17 em `scripts/rematerialize_magic_formula_v2.py`, dois na migração 0015 e um em `magic_formula_golden_validation.py`. Nenhum foi corrigido nesta etapa; isto não declara o restante do projeto livre de lint.

## Worktree e estado final

O worktree já possuía 17 arquivos rastreados modificados e 609 entradas não rastreadas na captura inicial. A lista completa e os hashes iniciais estão em `tmp/petrobras-e2e-baseline/git-status-before.txt` e `hashes-before.json`. Nenhum reset ou commit foi feito.

Arquivos preexistentes alterados nesta fase:

- `src/income_analytics/application/magic_formula_formal_qa.py`
- `src/income_analytics/application/magic_formula_golden_evidence_builder.py`
- `src/income_analytics/application/magic_formula_market_evidence.py`
- `src/income_analytics/infrastructure/magic_formula_snapshot_repository.py`

Novos arquivos de implementação/evidência desta fase:

- `scripts/recover_petrobras_canonical.py`
- `src/income_analytics/infrastructure/magic_formula_raw_verification.py`
- `tests/application/test_petrobras_canonical_e2e.py`
- `tests/fixtures/cvm/petrobras_canonical_v2/COTAHIST_A2025.ZIP`
- `tests/fixtures/cvm/petrobras_canonical_v2/README.md`
- `tests/fixtures/cvm/petrobras_canonical_v2/dfp_cia_aberta_2025.zip`
- `tests/fixtures/cvm/petrobras_canonical_v2/fca_cia_aberta_2025.zip`
- `tests/fixtures/cvm/petrobras_canonical_v2/manifest.json`
- `tests/golden/magic_formula/petrobras_2025.json`
- `docs/MAGIC_FORMULA_PETROBRAS_CANONICAL_E2E_REPORT.md`

As demais alterações são o banco local autorizado e os backups/logs de auditoria sob `tmp/petrobras-e2e-baseline`. Registry, fórmula Greenblatt, V1/V2 anteriores, mínimo do gate e ativação da ferramenta não foram alterados.

```text
PETROBRAS_E2E_STATUS = PASS
PETROBRAS_ISSUER_ID = d534bf40-ca22-4d9d-83b6-458f29b27399
PETROBRAS_GOLDEN_STATUS = READY_FOR_VALIDATION
PETROBRAS_GOLDEN_SCHEMA = MAGIC_FORMULA_GOLDEN_V2
PETROBRAS_V2_SNAPSHOT = 6d5dd506-9023-4862-81eb-067cb0bc3cf2
PETROBRAS_FORMAL_QA = PASS
PETROBRAS_VALIDATION_STATUS = PASS
PETROBRAS_READBACK_STATUS = PASS
PETROBRAS_STATUS = RESOLVED
PETROBRAS_RANKING_ELIGIBLE = true
VALIDATED_RESOLVED_ISSUERS = 5
MULTISECTOR_GOLDEN_GATE = PASS
RANKING_GATE = READY
OPEN_DEFECTS = 0
TESTS_PASSED = 119
TESTS_FAILED = 0
CHANGED_FILES_LINT = PASS
PRE_EXISTING_LINT = 20 (inalterados; escopo Magic Formula)
TOOL_STATUS = VALIDATION_REQUIRED
RANKING_STATUS = INACTIVE
RECOMMENDED_NEXT_ACTION = Revisar as evidências e definir a próxima etapa de ativação separadamente, mantendo o ranking inativo.
```
