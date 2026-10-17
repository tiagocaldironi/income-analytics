# Magic Formula — resolução da revisão de política V8

Auditoria reprodutível e somente de leitura, com referência de liquidez em **2025-12-30**. A política permanece `MF_BR_2027_V1_DRAFT`; S4 e L3 não foram ativados, ranking/Top 30 não foram calculados e o snapshot não foi alterado.

## Correção da política

Varejo e aviação deixam de ser critérios de elegibilidade metodológica. A metodologia conserva exclusões estruturais financeiras, seleção S4 e limiar L3 candidato de 15/30 pregões. A preferência padrão não filtra setores; o perfil pessoal pode excluir varejo tradicional e aviação. Esses filtros são aplicados depois do rank e não mudam EY, ROC ou rank global. ASAI3 continua `CASH_AND_CARRY`; a exceção antiga é apenas compatibilidade e deve ser removida após migração dos consumidores de snapshots antigos.

`RETAIL_METHODOLOGY_EXCLUSION=NO`; `AVIATION_METHODOLOGY_EXCLUSION=NO`; `DEFAULT_EXCLUDE_RETAIL=NO`; `DEFAULT_EXCLUDE_AVIATION=NO`. Os 18 registros fora da baseline continuam separados e não foram incorporados. Market cap permanece diagnóstico apenas, sem mínimo e sem efeito sobre a elegibilidade.

## Baseline e taxonomia

`360 = 35 exclusões financeiras estruturais + 18 fora da baseline + 307 empresas da baseline`. A taxonomia V7 foi preservada e refinada com os dez FRE oficiais. Contagens finais por categoria: `{"CASH_AND_CARRY": 1, "COMMERCE_ADJACENT": 12, "DISTRIBUTION": 4, "MIXED_COMMERCE": 6, "TRADITIONAL_RETAIL": 13, "WHOLESALE": 1}`. Resolução dos 10: `{"RESOLVED_HIGH_CONFIDENCE": 8, "RESOLVED_MEDIUM_CONFIDENCE": 2}`. Os dez foram resolvidos com confiança alta ou média; a incerteza de setor já não bloqueia a metodologia. O índice CVM FRE 2025 aponta para os formulários oficiais, cujos XMLs contêm PDFs embutidos; foram lidas as seções 1.1, 1.3 e, quando necessário, 1.4. IDs e checksums estão na taxonomia e no manifest. Fontes: [CVM FRE](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre), [layout oficial B3 COTAHIST](https://www.b3.com.br/data/files/33/67/B9/50/D84057102C784E47AC094EA8/SeriesHistoricas_Layout.pdf).

## Segurança comprável e L3

V7 tinha 257 seleções e 50 reviews, sendo 47 reviews no funil principal. Nesta revisão foram percorridas as candidatas contra os arquivos B3 COTAHIST já existentes de 2022–2025, exclusivamente mercado 010. Classes com identidade confirmada em COTAHIST receberam cálculo sobre as 30 sessões terminadas em 2025-12-30; classes sem ISIN/ticker ou comparação suficiente continuam em review. Causa principal e evidência por emissor estão em `buyable_security_review_resolution.csv`.

Outcomes dos 50 reviews: `{"BUYABLE_SECURITY_RESOLVED_L3_FAIL": 22, "BUYABLE_SECURITY_RESOLVED_L3_PASS": 9, "BUYABLE_SECURITY_UNRESOLVED_REVIEW": 19}`; S4 resolveu 31 e restam 19 em revisão. Assim, seleções totais passam de 257 para 288. O L3 permanece candidato: `ratio >= 0.50` (15/30). Dos 50 reviews L3, outcomes: `{"LIQUIDITY_FAIL": 22, "LIQUIDITY_PASS": 9, "LIQUIDITY_REVIEW": 19}`. Os 23 L3 FAIL de V7 foram confirmados com identidade e cálculo das 30 sessões pelos registros COTAHIST auditados; resultados linha a linha estão no CSV. `market 020` não é usado nem como substituto nem para completar a comparação.

## Universo metodológico proposto

`{"BUYABLE_SECURITY_REVIEW": 19, "ELIGIBLE_COMPLETE": 180, "ELIGIBLE_DATA_BLOCKED": 63, "INELIGIBLE_STRUCTURAL": 0, "LIQUIDITY_FAIL": 45, "LIQUIDITY_REVIEW": 0}` (soma 307). Elegíveis confirmados = 243; completos = 180; bloqueados por dados = 63; cobertura metodológica = 74.07%. Reviews são mantidos conservadoramente no denominador; cobertura conservadora = 68.70%.

Empresas visíveis com filtros padrão: 243. Com o perfil pessoal `exclude_traditional_retail=true`, `exclude_aviation=true`: 230. Os filtros não ativam ranking nem recalculam posições. ASAI3 passa sem consultar a exceção de elegibilidade.

## Blockers históricos

Os 31 blockers V6 preservam tipo, motivo e proveniência. A classificação após V8 é `{"DATA_RECOVERY_DEFERRED_BY_LIQUIDITY": 14, "HIGH_VALUE_DATA_RECOVERY_TARGET": 8, "REVIEW_TO_L3_FAIL": 7, "REVIEW_UNRESOLVED": 2}`. Os casos de L3 fail ficam marcados `DATA_RECOVERY_DEFERRED_BY_LIQUIDITY`; somente linhas ainda `ELIGIBLE_DATA_BLOCKED` entram na lista de alvos de recuperação. Nenhuma recuperação de preço/fundamentos/ações foi iniciada.

## Decisão e critérios de parada

`POLICY_READY_FOR_APPROVAL = YES` porque as regras são determinísticas, filtros são separados, reviews são explícitos e o estado conservador está definido. `UNRESOLVED_SECURITY_REVIEW = 19`; sem busca aberta após falha das fontes oficiais já auditadas. S4/L3 estão prontos para decisão de aprovação, não ativados. O ranking e o Top 30 permanecem bloqueados até aprovação e uma etapa separada.

Snapshot preservado: `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` (`0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9`).

## Aceite de V8

`METHODOLOGY_SCREENING_SEPARATION=PASS`; `ASAI3_GOLDEN_CASE=PASS`; `S4_REVIEW_RESOLUTION=PASS`; `L3_REVIEW_RESOLUTION=PASS`; `MISSING_DATA_SELECTION_BIAS=PASS`. `POLICY_READY_FOR_APPROVAL=YES`; `S4_ACTIVATED=NO`; `L3_ACTIVATED=NO`; `RANKING_CALCULATED=NO`; `RANKING_ACTIVE=NO`; `TOP_30_PUBLISHED=NO`; `SNAPSHOT_CHANGED=NO`. Revisão de segurança não resolvida permanece explícita e sujeita à regra de parada.

Validação executada: 243 testes Magic Formula passaram; Ruff e Ruff format passaram; a geração foi comparada por checksum para confirmar idempotência.

## Apêndices

- [Taxonomia final](appendices/magic_formula_policy_review_resolution_v8/commerce_taxonomy_final.csv)
- [Reviews de security](appendices/magic_formula_policy_review_resolution_v8/buyable_security_review_resolution.csv)
- [Resolução L3](appendices/magic_formula_policy_review_resolution_v8/liquidity_review_resolution.csv)
- [Blockers históricos](appendices/magic_formula_policy_review_resolution_v8/historical_blockers_after_v8.csv)
- [Universo metodológico](appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv)
- [Atributos de screening](appendices/magic_formula_policy_review_resolution_v8/screening_attributes_v8.csv)
- [Manifest e checksums dos arquivos fonte](appendices/magic_formula_policy_review_resolution_v8/audit_manifest.json)
