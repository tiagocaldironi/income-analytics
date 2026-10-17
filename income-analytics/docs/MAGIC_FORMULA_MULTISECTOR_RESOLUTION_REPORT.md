# Magic Formula Stocks — Multisector Resolution

| Emissor | Accounting | Security/Capital | Price | Component QA | Status |
| --- | --- | --- | --- | --- | --- |
| Petrobras | anchor existente | anchor existente | anchor existente | regressão pendente | RESOLVED histórico |
| WEG | PASS técnico V2 | PASS técnico V2 | PASS técnico V2 | REVIEW_REQUIRED: fixture incompleta | NOT_RESOLVED |
| Suzano | PASS técnico V2 | PASS técnico V2 | PASS técnico V2 | REVIEW_REQUIRED: fixture incompleta | NOT_RESOLVED |
| Rumo | PASS técnico V2 | PASS técnico V2 | PASS técnico V2 | REVIEW_REQUIRED: fixture incompleta | NOT_RESOLVED |
| Telefônica Brasil | PASS técnico V2 | PASS técnico V2 | PASS técnico V2 | REVIEW_REQUIRED: fixture incompleta | NOT_RESOLVED |

O gate multissetorial não pode ser marcado como PASS enquanto os snapshots
componentizados V2 não tiverem sido materializados e comparados. Não há ranking
publicado nem status `AVAILABLE`. O pré-check formal foi persistido e relido
em nova sessão para os quatro emissores. A promoção está bloqueada por
`GOLDEN_EVIDENCE_DEFECT`: as fixtures em `tests/golden/magic_formula` ainda
não possuem todos os locators FCA/COTAHIST exigidos pelo gate final.
