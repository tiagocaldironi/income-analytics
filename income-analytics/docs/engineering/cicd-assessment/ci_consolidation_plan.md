# PR5.1D — Plano de consolidação

Plano registrado antes de aplicar as cópias locais. Data: 28/10/2026.

Base: develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965. PR #48 aberto/draft, head 1bbd2d42686ab0c893790772a05a7845cfbc0295, três commits publicados (e023ade, 2e3491f, 1bbd2d4). A/B/C compartilham esse HEAD e merge-base ca627ac. B/C não possuem commits próprios e não foram integrados ao PR remoto.

Nova branch/worktree: codex/pr51d-ci-gates. Operação permitida: cópia dos arquivos identificados; nenhuma branch/worktree de origem é modificada. Não é merge/cherry-pick/rebase. Nenhum commit/push/PR será criado automaticamente.

Ordem: (1) infraestrutura já versionada do PR #48; (2) alterações B preservadas em C; (3) acréscimos C aprovados e relatórios; (4) três documentos A locais; (5) governança D em arquivos CI/workflow/documentação. B é dependência explícita de C e está byte a byte idêntico em C; nenhuma sobreposição divergente foi encontrada. Casos financeiros pendentes não serão removidos nem reclassificados por estarem reprovados.

## Origens e arquivos locais

| Origem | Arquivo | SHA-256 antes da consolidação |
| --- | --- | --- |
| A | docs/engineering/cicd-assessment/ci_failure_triage.md | 7d440c063b68e84d4b4c6459482f5670d63d51d347bad111fe38001a74fed54d |
| A | docs/engineering/cicd-assessment/ci_quality_debt_baseline.md | f8833cf7c2cb8f4b739fc92c284f69d954c8157d50150354f90868bdb4e5902f |
| A | docs/engineering/cicd-assessment/ci_stabilization_plan.md | 99f4aaba0b8663ce40a57bc6b6e56abe38d9b1ced730a7ab2b791c02f3c09851 |
| B | docs/engineering/cicd-assessment/pr51b_validation.md | 8bad73296a2a6ba61ffebe6b81f5166d9053d06036bf3dd858564a7ce2d01f7d |
| B | src/income_analytics/infrastructure/cvm_fundamentals_data.py | f11731d3d2979557e1725109517baa4006a83d6f3eb7f87c6215a42b91aff1ba |
| B | tests/frontend/holdings_v2.mjs | dbf33cbb87ebf114f43845303ab8376465edc75df14d2e4bd896a8ae4c893cac |
| B | tests/infrastructure/test_cvm_statement_parser.py | 98661de24afd2bf63577371073ffff8a1e5c6abd5df38fbb26aae9784c8a4843 |
| C | ci/magic_formula_references.py | af0631fdfe331e7d8fd95f1b87c1f91a61a0e96e8d05b055340b1475eec5586b |
| C | docs/engineering/cicd-assessment/magic_formula_ci_fixture_design.md | 6da660bf875a349fb52becb137952354232f1d722f9ad98386acc0292d371a5f |
| C | docs/engineering/cicd-assessment/magic_formula_reference_inventory.md | 84b91e0354af2829870835e45053cb506aa3df764e16b2ef90412cff7edd8ac4 |
| C | docs/engineering/cicd-assessment/magic_formula_reference_provenance.json | c8ace928d1571592e149f2a8d274bbb745c74f3f52dc0c0c0ca21d8f9c5ec8b6 |
| C | docs/engineering/cicd-assessment/pr51b_validation.md | 8bad73296a2a6ba61ffebe6b81f5166d9053d06036bf3dd858564a7ce2d01f7d |
| C | docs/engineering/cicd-assessment/pr51c_validation.md | b4a8259852898df9e1f16ecbd11e72153720950690de43b34817fdd106e6b3f2 |
| C | src/income_analytics/infrastructure/cvm_fundamentals_data.py | f11731d3d2979557e1725109517baa4006a83d6f3eb7f87c6215a42b91aff1ba |
| C | tests/fixtures/cvm/receipt_index_2025_v1/README.md | 696ef00d430e681674558cee93e954c49e9e125a33228c5d6972c6e227e7ce50 |
| C | tests/fixtures/cvm/receipt_index_2025_v1/dfp_cia_aberta_2025.csv.gz | 420c5dffb1a9504a74dd2f98632acb5f47df764415cce17d10d9e2384bf1592f |
| C | tests/frontend/holdings_v2.mjs | dbf33cbb87ebf114f43845303ab8376465edc75df14d2e4bd896a8ae4c893cac |
| C | tests/infrastructure/test_cvm_statement_parser.py | 98661de24afd2bf63577371073ffff8a1e5c6abd5df38fbb26aae9784c8a4843 |
| C | tests/infrastructure/test_magic_formula_ci_reference_bundle.py | 229c5c0c4a965341d0daa1747d3a1394e7ca4878f62c1bdedd2cabf43dab732b |

## Escopo D previsto

Separar engenharia hermética, diagnósticos completos, certificação não aprovada e integrações externas inventariadas; criar baseline estática Ruff/mypy por identidade e multiplicidade, nunca só totais. Classificar toda coleta por dependência comprovada. Manter guardas de rede/SQLite e relatórios sanitizados. Não alterar produto além das duas correções B já autorizadas nem fixtures/manifests congelados.

O resultado local usará HEAD ancestral + conteúdo dos arquivos porque não há autorização para criar commit. Uma árvore limpa será montada a partir do Git e overlay explicitamente inventariado, sem arquivos ignorados/pessoais. Gates só serão considerados aprovados se efetivamente executados; certificação permanece BLOCKED e deploy NOT_IMPLEMENTED. Branch protection não será modificada.

## Execução e preservação confirmadas

Consolidação realizada só no novo worktree. A/B/C mantiveram HEAD, status e SHA-256 de todos os arquivos locais inventariados. O workflow na raiz Git .github/workflows/ci-offline.yml foi copiado explicitamente para o clone de validação, pois diff relativo ao subdiretório da aplicação não inclui automaticamente esse arquivo irmão. Nenhum conflito divergente B→C foi detectado.

Validação: clone novo do head publicado + overlay identificado; venvs novos runtime/dev com locks e pip check. Fingerprint executado bdb3cd620e91bc4b04a5dc9c7cbfade08aa4af8c65d2d89d366164d0c22dbaec, igual ao worktree integrado. Nenhum commit candidato foi criado; SHA ancestral e fingerprint não devem ser apresentados como commit novo publicado. Consulte pr51d_validation.md para resultados e limites hospedados.
