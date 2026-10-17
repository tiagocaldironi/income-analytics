# Magic Formula — reconstituição da baseline e ativação V9.2

**Resultado: PASS.** A política `MF_BR_2027_V1` foi ativada após todos os 15 gates atuais passarem. A lacuna histórica V7 foi aceita e registrada como não resolvível; isso não afirma que os testes V7 foram reconciliados.

## Limitação histórica aceita

V7 reportava 274 testes, mas não há IDs históricos nem revisão V7 verificável. A investigação está encerrada (`FURTHER_V7_TEST_HUNT=CLOSED`). A reconciliação é `UNRESOLVABLE`; não se afirma que todos os testes V7 foram reconciliados nem que não houve perda histórica. Os 243 IDs reconstruídos da coleta V8 são apenas evidência de apoio, não um inventário histórico verificado.

## Baseline atual verificável

- Coletados/executados/passaram: **273 / 273 / 273**; falharam: **0**; skipped: **0**.
- Node IDs preservados: sim, ordenados; hash dos IDs `6d1d3d164f7fa19725ef96c88e3e520ed299fdf5dad36f3744615cbc490b6700`.
- Manifest hash: `4cf27ecae75b948c6e87615ef82a0c885f80220622bb22662b7ae0a07f4790a6`; gerado em `2026-10-13T21:05:09-03:00`.
- Manifest determinístico: sim; hash idêntico em duas coletas independentes.
- Versão da baseline: `MF_BR_2027_V1_ACTIVATION_BASELINE`.

## Regressões críticas

Cobertura atual: **30/30**, sem área descoberta. O mapa liga cada área aos IDs atuais executados; não tenta equivalência com testes V7 desconhecidos.

## Metodologia e universo congelado

Exclusão estrutural financeira ativa; varejo e aviação são filtros de screening, sem exclusão metodológica; utilities não receberam nova exclusão; market cap mínimo é `NONE`; mercado `010`. ASAI3 permanece `CASH_AND_CARRY` sem exceção metodológica. Screening não integra o fingerprint.

S4 foi recomputado sobre 307 grupos de candidatos (com a resolução de identidade V8 onde a evidência antiga era incompleta): **288** papéis selecionados e **19** em review, reconciliando ticker, ISIN e estado com o resultado V9 congelado. O critério primário é frequência negociada em 30 sessões, com volume financeiro mediano como desempate e chave estável como desempate final. S4 não consulta disponibilidade de preço, EY, ROC, ranks, preferências nem posições da carteira.

L3 foi recalculado a partir da seleção S4, com janela de 30 pregões e mínimo de 15 (50%); PASS **243**, FAIL **45**, REVIEW **19**. Todos os status reconciliam com a baseline V9 congelada. Review é estado definido e permanece fora do universo rankable.

Baseline **307**; status: structural ineligible 0, liquidity fail 45, buyable security review 19, liquidity review 0, data blocked 63, complete 180; soma 307.

Coverage metodológica: **74.07%** (180/243); conservadora: **68.70%** (180/262). 63 elegíveis bloqueadas por dados permanecem elegíveis. Backlog preservado: P0 32, P1 14, P2 17, total 63; nenhuma recuperação executada.

Snapshot preservado: `ed8a9235-ee14-4a97-93fd-0dbcd87113fb`, digest `0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9`. Nenhum ranking EY/ROC/combinado foi calculado para o universo desta ativação, e nenhum Top 30 foi publicado. Os testes do motor de ranking da suíte continuam isolados em fixtures.

## Fingerprint, dry runs e ativação

Policy hash: `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`. Os dois dry runs tiveram hashes idênticos de política, status, seleção e artefatos. Ativação registrada em `activation_record.json`; a V1 fica imutável, e alteração metodológica requer nova versão.

- `GATE_01_CURRENT_TEST_SUITE` = **PASS**
- `GATE_02_CRITICAL_REGRESSION_COVERAGE` = **PASS**
- `GATE_03_RUFF` = **PASS**
- `GATE_04_POLICY_DETERMINISM` = **PASS**
- `GATE_05_S4_DETERMINISM` = **PASS**
- `GATE_06_L3_DETERMINISM` = **PASS**
- `GATE_07_STATUS_RECONCILIATION` = **PASS**
- `GATE_08_COVERAGE_RECONCILIATION` = **PASS**
- `GATE_09_SCREENING_SEPARATION` = **PASS**
- `GATE_10_SNAPSHOT_IMMUTABILITY` = **PASS**
- `GATE_11_NO_RANKING` = **PASS**
- `GATE_12_NO_TOP30` = **PASS**
- `GATE_13_IDEMPOTENCY` = **PASS**
- `GATE_14_NO_DATA_SNOOPING` = **PASS**
- `GATE_15_TEST_MANIFEST_DETERMINISM` = **PASS**

Todos os gates atuais passaram. Próxima fase autorizada: `MAGIC_FORMULA_DATA_COMPLETION_AND_RANKING_READINESS_V10`, limitada aos `ELIGIBLE_DATA_BLOCKED` e sem alterar S4, L3, exclusões, screening ou market cap.

Artefatos completos: `docs/appendices/magic_formula_v9_2/`.
