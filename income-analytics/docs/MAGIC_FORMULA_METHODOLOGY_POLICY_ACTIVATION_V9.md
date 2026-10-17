# Magic Formula methodology policy activation V9

## Resultado

A política permanece `MF_BR_2027_V1_DRAFT` com `ACTIVATION_STATUS = BLOCKED`. O gate crítico falhou: os 31 testes da diferença V7/V8 não podem ser identificados nominalmente nos artefatos preservados.

## Baseline congelada

MAGIC_FORMULA_METHODOLOGY_POLICY_ACTIVATION_V9 = FAIL

SOURCE_CANDIDATES=360; STRUCTURAL_FINANCIAL_EXCLUDED=35; OUTSIDE_BASELINE_REVIEW=18; BASELINE_COMPANIES=307.
- Empresas: 307; snapshot `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` (0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9); referência 2025-12-30.
- Status: {"BUYABLE_SECURITY_REVIEW": 19, "ELIGIBLE_COMPLETE": 180, "ELIGIBLE_DATA_BLOCKED": 63, "INELIGIBLE_STRUCTURAL": 0, "LIQUIDITY_FAIL": 45, "LIQUIDITY_REVIEW": 0}.
- Cobertura metodológica: 74.07% (180/243); conservadora: 68.70% (180/262).
- S4: maior `traded_days_ratio_30d`; desempate por volume financeiro mediano e chave estável; mercado 010. L3: 15 de 30 pregões. Sem mínimo de market cap.
- S4: selecionadas=288; em REVIEW=19; determinístico=YES; pronto para ativação=YES.
- L3: PASS=243; FAIL=45; REVIEW=19; determinístico=YES; pronto=YES.
- Varejo e aviação não são exclusões metodológicas; utilities preservadas; screening separado. ASAI3 = CASH_AND_CARRY; exceção legada depreciada.
- As 19 revisões continuam `BUYABLE_SECURITY_REVIEW`, sem seleção presumida ou elegibilidade para ranking.
- REVIEW_TOTAL=19; BUYABLE_SECURITY_REVIEW=19; LIQUIDITY_REVIEW=0; sem nova busca; stop rule aplicada=YES.

## Reconciliação dos testes

V7 reportou 274; o inventário atual V8 coletou 243; delta = -31. `test_reconciliation.csv` enumera os IDs V8, mas os artefatos V7 guardam somente a contagem e não preservam os 274 IDs. A diferença de 31 não pode ser atribuída com evidência a remoção obsoleta, renomeação, merge, substituição ou perda acidental. Os 31 slots `V7_NODEID_UNAVAILABLE_*` são placeholders explícitos, não nomes inventados. `NOT_DISCOVERED=31`, `UNEXPLAINED=31`; GATE_01=FAIL.

## Backlog de dados

Os 63 casos `ELIGIBLE_DATA_BLOCKED` foram carregados sem recuperação adicional: P0=32, P1=14, P2=17. A prioridade usa somente disponibilidade de componentes/fontes, nunca valores ou ranks de EY/ROC.
- TOTAL_ELIGIBLE_DATA_BLOCKED=63; RECOVERY_EXECUTED_IN_V9=NO.

## Gates

| Gate | Resultado | Evidência |
|---|---|---|
| GATE_01_TEST_RECONCILIATION | FAIL | 31 V7 tests cannot be mapped because no V7 nodeid inventory is preserved; NOT_DISCOVERED=31. |
| GATE_02_REGRESSION | PASS | V8 Magic Formula suite collected 243 tests; V9 policy suite separately passes 30 tests. |
| GATE_03_RUFF | PASS | Scoped Ruff check passed for methodology modules and V9 policy tests. |
| GATE_04_POLICY_DETERMINISM | PASS | Canonical SHA-256 policy fingerprint 96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac. |
| GATE_05_S4_DETERMINISM | PASS | Selections copied from frozen V8 outputs and ordered by issuer code; repeated signatures match. |
| GATE_06_L3_DETERMINISM | PASS | V8 L3 statuses retained with market 010, 30 sessions and >=15 sessions threshold. |
| GATE_07_STATUS_RECONCILIATION | PASS | Status sum=307; counts recomputed from V8 universe. |
| GATE_08_COVERAGE_RECONCILIATION | PASS | Methodological=74.0740740741%; conservative=68.7022900763%; denominators recomputed. |
| GATE_09_SCREENING_SEPARATION | PASS | Screening preferences are absent from methodology policy payload/hash; defaults false; screening follows canonical rank. |
| GATE_10_SNAPSHOT_IMMUTABILITY | PASS | Snapshot ed8a9235-ee14-4a97-93fd-0dbcd87113fb / 0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9; manifest byte hash unchanged. |
| GATE_11_NO_RANKING_CALCULATED | PASS | V8 manifest confirms ranking_calculated=false; V9 only copies eligibility universe. |
| GATE_12_NO_TOP30_PUBLISHED | PASS | V8 manifest confirms top_30_published=false; V9 produced no ranking outputs. |
| GATE_13_IDEMPOTENCY | PASS | Dry-run signatures match: c7873ffd0f778c10a7c539e80a7ea66f3e80afcacc0e307a0bd5599a07d6df29. |
| GATE_14_NO_DATA_SNOOPING | PASS | S4/L3/status outputs derive from V8 frozen evidence and policy rules; no EY/ROC/rank/portfolio values consumed. |

## Fingerprint e fronteira de execução

- Policy hash: `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`; fingerprint não inclui preferências pessoais.
- Dry run determinístico: YES; run 1 = `c7873ffd0f778c10a7c539e80a7ea66f3e80afcacc0e307a0bd5599a07d6df29`; run 2 = `c7873ffd0f778c10a7c539e80a7ea66f3e80afcacc0e307a0bd5599a07d6df29`.
- ARTIFACT_CHECKSUMS_EQUAL=YES (duas execuções produziram hashes iguais para todos os artefatos auxiliares).
- Snapshot alterado: NO. EY rank, ROC rank, combined rank: NO. Top 30: NO.
- Como nem todos os gates passaram, `MF_BR_2027_V1` não foi ativada. Corrigir a reconciliação com um inventário V7 verificável antes de reexecutar.

Artefatos auxiliares: `docs/appendices/magic_formula_methodology_v9/`.
