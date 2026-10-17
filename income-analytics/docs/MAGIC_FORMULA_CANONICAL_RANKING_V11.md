# Fórmula Mágica — V11: ranking canônico

Snapshot `mf-783598cd7f717527425123eb` guarda 174 empresas, com política `MF_BR_2027_V1` e hash `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`. Referência de mercado 2025-12-30; corte contábil 2026-10-13. Ranks EY/ROC são densos; score é a soma; global rank usa competition rank sobre score e empate ordenado por UUID estável. EBIT negativo não é filtrado. EV ou capital empregado não positivo seguem a regra já existente do motor e não recebem rank. Retail e aviação são atributos de screening; os filtros não recompõem ranks.

- `V11_01_POLICY_HASH_MATCH`: PASS
- `V11_02_RANKABLE_UNIVERSE_VALID`: PASS
- `V11_03_EY_VALID`: PASS
- `V11_04_ROC_VALID`: PASS
- `V11_05_EY_RANK_VALID`: PASS
- `V11_06_ROC_RANK_VALID`: PASS
- `V11_07_COMBINED_SCORE_VALID`: PASS
- `V11_08_GLOBAL_RANK_VALID`: PASS
- `V11_09_TIES_DETERMINISTIC`: PASS
- `V11_10_RANKING_HASH_DETERMINISTIC`: PASS
- `V11_11_SCREENING_NOT_IN_CANONICAL_RANK`: PASS
- `V11_12_NO_LOOKAHEAD`: PASS
- `V11_13_PROVENANCE_COMPLETE`: PASS

Artefatos: `docs/appendices/magic_formula_v11/`.
