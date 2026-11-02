# PR5.1A — Triagem das falhas de CI

Data: 28/10/2026. Escopo exclusivamente diagnóstico; nenhuma correção de produto, teste, fixture, manifest, hash ou configuração produtiva integra esta entrega.

Referência financeira: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`. CI analisada: [run 40692226171](https://github.com/tiagocaldironi/income-analytics/actions/runs/40692226171), PR #48, head `1bbd2d42686ab0c893790772a05a7845cfbc0295`, checkout de merge sintético `3f81a9eb5a7d3ae0accc2ad98d0f3a1bcefb70cd`. Não confundir o SHA do head com o checkout efetivamente testado.

Caminhos citados são relativos à aplicação `income-analytics/` dentro da raiz Git. Linhas referem-se à baseline avaliada. Estimativas são de trabalho técnico, sem prazo de aprovação externa, e não devem ser somadas por diagnóstico em cascata.

## Síntese e método

Prontidão **PARTIAL** para CI; certificação/promoção **BLOCKED**. Instalação runtime aprovada. Python: **995 aprovados, 15 falhas, 9 erros, 5 skips**, cobertura **80,69%**. Frontend: **29/30 suítes existentes aprovadas**, mais autoteste da infraestrutura aprovado (**30/31** agregado). Ruff **130**; mypy **674**. O job CERT_48 repete um teste Python, não é uma 16ª falha independente.

Confrontamos seis result.json/JUnit sanitizados da execução final, logs locais completos com mesmas ferramentas/dependências e código versionado. Ruff/mypy têm multiconjuntos `(arquivo, linha, regra)` exatamente iguais aos remotos, incluindo duplicações. Mensagens no ledger vêm dos logs locais equivalentes: os artefatos CI removem payloads deliberadamente. Logs pytest do checkout LF reproduzem as 15F+9E. Nenhuma suíte completa foi reexecutada nesta triagem.

Prova adicional limitada: ZIP sintético com CSV de cabeçalho inválido, entregue ao parser em memória, sem DB/rede/escrita. Confirmou AttributeError no caminho de erro. Hashes foram apenas lidos/calculados. Nenhum gerador de snapshot, migration, launcher, commit, merge ou deploy foi executado.

Evidências temporárias locais sob TEMP: `income-pr51a-actions-40692226171/` (artefatos finais), `income-offline-ci-ko6t3hgn/junit.xml` e `python.raw.log` (checkout LF), `income-offline-ci-sk83a1gh/ruff.raw.log`, `income-offline-ci-5yfb78vz/mypy.raw.log`. São fontes da análise, não dependências da futura CI. Link do run e ledgers preservam identificação por ocorrência sem exigir arquivos pessoais.

## Classificação das 24 ocorrências Python

Cada linha herda todos os campos de seu perfil. F = reprovação no corpo/asserção; E = preparação. Mesmo perfil não significa defeitos independentes. Bloqueadora em certificação se refere à promoção/release; a política de merge está no plano.

| Perfil | Causa / certeza | Categoria | Criticidade | Tratamento | Esforço | Evidência |
| --- | --- | --- | --- | --- | --- | --- |
| PY-API | ranking_snapshot.json ausente; erro antes das asserções HTTP. Comprovada. | fixture | alta | Recuperar proveniência e referência pública hermética auditável; preservar ranking/digest. | 2–4 dias compartilhados | tests/api/test_magic_formula_product_api.py:30–48 |
| PY-V9 | CSV V9.2 ausente; build abre antes de universo/DFP. Comprovada. | fixture | alta | Pacote reprodutível de referências e auditoria transitiva, sem banco pessoal. | 2–4 dias compartilhados | application/magic_formula_canonical_ranking.py:24–43 |
| PY-V8 | CSV V8 ausente; contagem não executa. Comprovada. | fixture | alta | Referência rastreada ou fixture independente auditada em PR próprio; manter expectativas. | 1–2 dias compartilhados | tests/application/test_magic_formula_methodology_policy_v1.py:27–30,58–60 |
| PY-DB | Universo SQLite readonly ausente; permissões não são causa demonstrada. | fixture | alta | Fixture hermética com snapshots/linhagem e timestamps empatados; explicitar dependências latest em futuro PR. | 3–5 dias compartilhados | infrastructure/magic_formula_universe_repository.py; testes listados |
| PY-CERT | CERT_48: bytes do motor divergem; expectativas misturam CRLF/LF. Equivalência financeira não certificada. | certificação | bloqueadora | Reconciliação independente de proveniência e recertificação; não atualizar manifest para aprovar. | 1–3 dias investigação; aprovação UNKNOWN | tests/application/test_historical_shares_units.py; shares_unit_v1/manifest.json |
| PY-ID | Fixture de identidade tem hashes CRLF, quatro textos Git LF. Comprovada. | certificação | bloqueadora | Cadeia de custódia e política de bytes independente; não converter PDF/atualizar hash automaticamente. | 1–2 dias investigação; decisão UNKNOWN | tests/infrastructure/test_historical_identity_fixture.py:15–16; price_identity_v1/manifest.json |

| ID | Resultado | Arquivo:linha | Caso | Perfil completo |
| --- | --- | --- | --- | --- |
| P01 | E | tests/api/test_magic_formula_product_api.py:48 | test_magic_formula_api_reads_persisted_snapshot_and_searches_ticker | PY-API |
| P02 | E | tests/api/test_magic_formula_product_api.py:64 | test_sector_metadata_covers_the_165_ranked_companies_without_changing_hash | PY-API |
| P03 | E | tests/api/test_magic_formula_product_api.py:87 | test_tools_catalog_marks_available_magic_formula_as_partial | PY-API |
| P04 | E | tests/api/test_magic_formula_product_api.py:96 | test_magic_formula_company_detail_returns_source_provenance | PY-API |
| P05 | E | tests/api/test_magic_formula_product_api.py:127 | test_detail_does_not_build_a_company_outside_the_requested_snapshot | PY-API |
| P06 | E | tests/api/test_magic_formula_product_api.py:135 | test_csna3_has_no_detail_when_it_is_blocked_from_the_published_ranking | PY-API |
| P07 | E | tests/api/test_magic_formula_product_api.py:159 | test_runtime_http_endpoint_returns_the_published_point_in_time_contract | PY-API |
| P08 | F | tests/application/test_historical_shares_units.py:230 | test_shares_unit_020_frozen_engine | PY-CERT |
| P09 | F | tests/application/test_magic_formula_canonical_ranking.py:16 | test_builds_a_deterministic_ranking_with_temporal_provenance | PY-V9 |
| P10 | F | tests/application/test_magic_formula_canonical_ranking.py:39 | test_screening_search_and_pagination_preserve_global_rank | PY-V9 |
| P11 | F | tests/application/test_magic_formula_canonical_ranking.py:57 | test_snapshot_repository_is_append_only_and_idempotent | PY-V9 |
| P12 | F | tests/application/test_magic_formula_historical_price_sources_v5.py:231 | test_production_snapshot_readback_is_independent_and_idempotent | PY-DB |
| P13 | F | tests/application/test_magic_formula_methodology_policy_v1.py:226 | test_v1_27_v8_baseline_statuses_sum_to_307 | PY-V8 |
| P14 | F | tests/application/test_magic_formula_methodology_policy_v1.py:231 | test_v1_28_methodological_coverage_denominator_is_complete_plus_blocked | PY-V8 |
| P15 | F | tests/application/test_magic_formula_methodology_policy_v1.py:238 | test_v1_29_conservative_coverage_includes_reviews | PY-V8 |
| P16 | E | tests/application/test_magic_formula_preview.py:25 | test_preview_001_only_complete_data_universe_is_counted | PY-DB |
| P17 | F | tests/application/test_magic_formula_preview.py:39 | test_preview_002_uses_the_validated_ranking_engine | PY-DB |
| P18 | E | tests/application/test_magic_formula_preview.py:56 | test_preview_003_production_gate_stays_blocked | PY-DB |
| P19 | F | tests/application/test_magic_formula_preview.py:65 | test_preview_current_snapshot_counts_are_derived_from_eligible_issuers | PY-DB |
| P20 | F | tests/application/test_magic_formula_price_availability_audit.py:129 | test_dry_run_does_not_persist_universe_snapshot | PY-DB |
| P21 | F | tests/application/test_magic_formula_price_availability_audit.py:143 | test_ranking_stays_blocked_in_saved_snapshot | PY-DB |
| P22 | F | tests/application/test_magic_formula_price_availability_audit.py:151 | test_snapshot_ordering_audit_resolves_duplicate_timestamp_with_rowid | PY-DB |
| P23 | F | tests/application/test_magic_formula_price_availability_audit.py:164 | test_csna3_and_v3_recoveries_survive_current_snapshot | PY-DB |
| P24 | F | tests/infrastructure/test_historical_identity_fixture.py:12 | test_versioned_official_identity_and_price_recovery | PY-ID |

Conciliação: PY-API 7E; PY-V9 3F; PY-V8 3F; PY-DB 7F+2E; PY-CERT 1F; PY-ID 1F = **15F+9E**. PY-DB inclui readback 1F, auditoria 4F, preview 2F+2E. Erros preview compartilham setup; sete erros API compartilham leitura inicial do JSON.

Cinco skips: quatro casos Firebase Emulator e um Firebase live, opt-in explícito. Não equivalem a aprovações nem devem exigir credencial produtiva em PR offline/fork. A falta dessa validação permanece visível para release SaaS.

## Referências ausentes e sua origem

Os cinco inputs abaixo não são listados por git ls-files e estão ausentes no checkout limpo. `.gitignore` ignora data/, tmp/ e docs/appendices/. Isso explica dependência de evidências acumuladas localmente, sem provar que não existam cópias em outro ambiente; nenhuma foi usada/publicada nesta fase.

| Input | Origem identificável | Consumidores / restrições |
| --- | --- | --- |
| docs/appendices/magic_formula_v12_2/ranking_snapshot.json | scripts/build_magic_formula_v12_2.py::main, grava ranking_snapshot.json; docs/MAGIC_FORMULA_POINT_IN_TIME_RANKING_AND_RELEASE_V12_2.md | 7E API. canonical_rankings.db é criado em tmp_path e não é input perdido. JSON contém data_snapshot_id/digest; valores exatos UNKNOWN sem arquivo. |
| docs/appendices/magic_formula_v9_2/methodological_universe.csv | scripts/audit_magic_formula_baseline_activation_v9_2.py (~322); lê V9 methodological_universe.csv/security_selection.csv; V9 deriva de V8 via audit_magic_formula_methodology_activation_v9.py | 3F ranking; depois exige universo ed8a… e DFP 2025. Gerador não executado. |
| docs/appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv | scripts/audit_magic_formula_policy_review_resolution_v8.py::main (~297, escrita ~696); lê V7 summary/security/taxonomy/blockers, V6 eligibility/liquidity e evidências B3; docs/MAGIC_FORMULA_POLICY_REVIEW_RESOLUTION_V8.md | 3F contagens; baseline307 e denominadores de cobertura distintos fazem parte do contrato, não ajustar para CI. |
| data/magic_formula/universe_snapshots.db | scripts/discover_magic_formula_universe.py e publicações/recoveries; docs/MAGIC_FORMULA_PUBLISHABLE_UNIVERSE_GATE.md, MAGIC_FORMULA_PRICE_IDENTITY_RECOVERY_V1.md, MAGIC_FORMULA_PRICE_BLOCKERS_BATCH_RECOVERY_V3.md | Readback: ed8a9235-ee14-4a97-93fd-0dbcd87113fb. Preview: 6d418683-6c09-4cfd-a67b-a4cc54718ddd. Auditoria: latest/linhagem, empate created_at ordenado por rowid. DB vazio/único snapshot não basta. |
| data/cvm/dfp_cia_aberta_2025.zip | infrastructure/cvm_fundamentals_data.py; application/magic_formula_canonical_ranking.py:27,649+; fonte pública CVM, índice dfp_cia_aberta_2025.csv | Dependência transitiva ainda não alcançada após CSV ausente; não houve download/validação deste ZIP. |

Replay da publicação V12.2 declara ainda DFP 2023/2024/2025, ITR2025, FCA2024/2025 e evidências em tmp/magic_formula_v12_2/shares_evidence_dfp2024 e data/magic_formula/shares_point_in_time_v1. Linhagem do universo inclui CVM/B3 COTAHIST, com referência a COTAHIST_A2025.ZIP. São dependências transitivas de replay, não novas primeiras causas de traceback. Disponibilidade/proveniência completa é UNKNOWN. Não inferir ID exato do JSON pelo nome V12.2.

Recuperação precisa registrar fonte, licença, aquisição, schema, seleção, digest e revisão independente. Geradores também escrevem snapshots/outros artefatos: não foram executados para “fabricar fixture”. Não gerar golden pelo próprio código sob teste e apresentá-lo como verdade independente; não copiar DB pessoal ou snapshot produtivo para o Git.

## Frontend: contrato atual

`tests/frontend/holdings_v2.mjs:12` exige Ganho e é a primeira asserção reprovada. Linha16 exige Perda: segunda asserção obsoleta, ainda não alcançada no run. `api/static/js/features/portfolio.js::renderHoldingRow` (~553) renderiza sinal, valor e classe visual sem prefixos; zero/indisponível têm mensagens próprias.

Histórico: PR35, merge c3d5c51344b7566d62920e7357176ce368feb641, remove texto positivo; PR36, merge 2514ee1fb7c322d40b721961efc82bc5df087bab, remove negativo. Correspondem ao pedido aprovado pelo usuário. Não há evidência de mudança de cálculo no erro Node.

**FE-01: contrato; média; causa comprovada; 1–3h.** Futuro PR deve alinhar as duas asserções, mantendo escape/XSS, sinais, valores, classes visuais, filtros, ordenação, nulos, zero, estados vazios, metas e ausência de mutação. Não reintroduzir textos nem remover suíte para obter verde.

## Defeito real revelado pelo mypy

**CODE-01: código; alta; 1–3h incluindo teste negativo futuro.** Em infrastructure/cvm_fundamentals_data.py:59, CvmStatementParser.parse usa self.code ao detectar colunas ausentes. O atributo pertence a CvmSourceSchemaError, não ao parser. ZIP sintético em memória com membro dfp_cia_aberta_DRE_con_2025.csv e cabeçalho COLUNA_INCOMPATIVEL confirmou AttributeError em vez de CvmSourceSchemaError. Nenhuma correção foi realizada.

Impacto comprovado: rejeição de esquema inválido viola contrato de exceção. Efeito nas camadas chamadoras/importação/retentativa ainda exige teste dirigido; não foi demonstrado cálculo incorreto, aceitação indevida de valores, segredo exposto ou bypass de acesso. Os demais erros estáticos não podem ser classificados automaticamente como defeitos runtime; evidências e hipóteses estão no ledger.

## CERT_48 separada da fixture de identidade

O teste frozen compara bytes com tests/fixtures/cvm/shares_unit_v1/manifest.json. Stocks esperado corresponde ao CRLF local; ranking_validation e contract esperados correspondem ao blob LF Git. Em CI LF falha primeiro stocks; em CRLF local falha ranking_validation. Uma escolha única de autocrlf não satisfaz o conjunto.

| Arquivo sob application/ | Manifest SHA-256 | Blob Git / LF SHA-256 |
| --- | --- | --- |
| magic_formula_stocks.py | 27b58d132b461afe867ca2af05757b1309739c40156549ac0bf1785ae5ad27a4 | 44fe1057b14dc45d13e0d302d7b24e361921ee2dab87b1dfde674c30dc344a9d |
| magic_formula_ranking_validation.py | 47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37 | 47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37 |
| magic_formula_contract.py | 9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f | 9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f |

O histórico docs/appendices/multiportfolio_v2_certification_closure/release_gate.json registra INCOMPLETE/CERT_48: pendência, não atestado atual de produção. EOL explica bytes observados, mas **não prova equivalência financeira nem encerra certificação**. Reconciliação independente continua necessária. Nenhum hash/manifest foi atualizado.

PY-ID usa outro manifest, tests/fixtures/cvm/price_identity_v1/manifest.json. Cinco arquivos locais batem; no Git os quatro textos divergem: cotahist-record.txt, current-directory.json, issuer-before.json, offer-identity.json. offer-notice.pdf preserva hash no blob Git. Primeiro erro CI: cotahist-record esperado 67fdbb7e6f3e56f235635240b3c4057876afb20b055b11562bdf532c457a45d9 versus blob 3890cfc22c50bb9ff0cdb35af7f754fa3bf5f47ee4022a3769ff1f88913b9293. Não converter PDF nem generalizar causa de todos os bytes sem inventário.

## Infraestrutura resolvida e riscos

Primeira execução exploratória tinha falha extra em test_database_safety.py: TEMP Windows 8.3 versus expandido. Runner PR5.1 canonicalizou TEMP com .resolve(); teste passou no run final. **Infraestrutura, média, resolvida**, fora das 15F+9E. Preservar proteção SQLite, não afrouxá-la.

- **Integridade financeira, alta/bloqueadora para release:** inputs ausentes impedem comprovar ranking, temporalidade, readback e imutabilidade; hashes impedem certificação. Isso, isoladamente, não prova retorno produtivo errado.
- **Entrada externa, alta:** CODE-01 confirmado; XML/Optional precisam de validação negativa dirigida. Não transformar cotação ausente em zero nem aceitar schema incompleto.
- **Segurança, alta como área a preservar:** contratos de auth/Firebase/ownership/serialização precisam revisão; Ruff em testes de autorização é estilo. Não há exploração ou bypass comprovado. Provedor determinístico não substitui skips externos.
- **Cadeia de evidência, alta:** copiar DB pessoal ou regenerar golden/hash para verde destrói independência e pode expor dados; usar referências públicas/sintéticas aprovadas.
- **Relatórios, média:** manter sanitização; não anexar bancos, tokens, payload financeiro ou logs completos a artefatos públicos. Ledger contém diagnósticos de código, não carteiras.

Veja [baseline completa](ci_quality_debt_baseline.md) e [plano de estabilização](ci_stabilization_plan.md). Os três documentos constituem a entrega; sem alterações funcionais.
