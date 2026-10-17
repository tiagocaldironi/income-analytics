# Fórmula Mágica — V10: conclusão de dados e prontidão

## Auditoria da arquitetura

A política `MF_BR_2027_V1` permanece ativa e inalterada. S4/L3 e o fingerprint são lidos dos artefatos V9.2. A extração usa CVM DFP/FCA, shares do DFP e preços B3 COTAHIST; o ranking usa a normalização contábil existente e ranks densos do serviço de ações. O repositório antigo de ranking aceita somente amostra de validação e não guardava ranking completo; foi criada persistência append-only para snapshots, linhas e provenance. O endpoint anterior servia um preview sem persistência; a nova tela lê o snapshot salvo.

## Backlog e recuperação

A lista V9.2 preserva 63 blockers, 32 P0, 14 P1 e 17 P2. A antiga baseline guardava somente os totais, sem associar prioridade a cada CVM. Para processar deterministicamente, foi reconstruída uma ordem operacional que usa quantidade/tipo de gaps e CVM estável, sem valores financeiros ou potencial de ranking. Os arquivos oficiais já integrados ao projeto foram reprocessados; não foi encontrado dado suficiente para recuperar esses 63 casos. As lacunas continuam elegíveis e bloqueadas.

A cobertura permanece metodológica 180/243 = 74.07% e conservadora 180/262 = 68.70%. Dos 180 completos, 174 têm denominadores positivos para o motor existente; 6 são transparentemente não ranqueáveis por EV/capital empregado não positivo.

## Tempo e provenance

Referência de mercado: 2025-12-30. Cada cotação usada é nessa data ou anterior; nunca é puxada cotação atual para trás. Período contábil: DFP FY2025 consolidada. Corte contábil: 2026-10-13; datas oficiais de recebimento `DT_RECEB` foram lidas do índice CVM DFP 2025. A provenance por empresa grava linhas contábeis, ticker/ISIN, preço e fonte B3, capital social e data do protocolo.

## Gate V10

- `V10_01_POLICY_UNCHANGED`: PASS
- `V10_02_PRIORITY_INDEPENDENT_OF_RANKING`: PASS
- `V10_03_NO_DATA_SNOOPING`: PASS
- `V10_04_TEMPORAL_CONSISTENCY`: PASS
- `V10_05_NO_LOOKAHEAD`: PASS
- `V10_06_PROVENANCE_COMPLETE`: PASS
- `V10_07_RECOVERY_DETERMINISTIC`: PASS
- `V10_08_COVERAGE_RECONCILED`: PASS
- `V10_09_STOP_RULE_APPLIED`: PASS
- `V10_10_RANKABLE_UNIVERSE_VALID`: PASS

Artefatos: `docs/appendices/magic_formula_v10/`.
