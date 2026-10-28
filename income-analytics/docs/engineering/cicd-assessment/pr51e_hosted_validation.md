# PR5.1E — Validação hospedada

Data: 28/10/2026. **PR5.1E HOSTED_VALIDATED**. [PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48) mantido em draft. [Run 40760146814](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814) concluído; evento pull_request, runner windows-2025. Engineering aprovado; conclusão geral do workflow: failure, pois os jobs de dívida e certificação continuam falhando explicitamente.

## Identidade e publicação

- Remoto antes do push: 1bbd2d42686ab0c893790772a05a7845cfbc0295.
- Local de código validado: 93bf0be672fc031592d6827f0796e6658c27cbb5.
- Head documental preparado e publicado: a2f6d64bb55210bb7514c2f172efa37116eeec6e.
- Checkout hospedado, merge sintético: 2a6513494b3f228b4ce46c716920b6ee1de24af7.
- Base develop preservada: ca627ac72f110d0f4d62faaa9c51a08eaed54965.
- Fingerprint em todos os oito relatórios locais e hospedados: 1648121a859a166d0b03ece09654d323e7cf56efcc3608ff06665bf389d79d9e.
- Todos os relatórios executados indicam worktree_dirty=false. pr_head_sha identifica a2f6d64; checkout_sha/event_sha identificam o merge sintético. A diferença de SHA não alterou o fingerprint efetivo.
- Push fast-forward confirmado: 1bbd2d4..a2f6d64. Cinco commits de consolidação/revisão e sexto commit documental já preparado. Nenhum commit corretivo novo foi publicado.

## Checks GitHub

| Check | Conclusão GitHub |
| --- | --- |
| [CI / Frontend](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069543856) | success |
| [CI / Ruff diagnostics](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544117) | failure |
| [CI / Full Python diagnostic](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544264) | failure |
| [CI / Financial certification](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544445) | failure |
| [CI / mypy diagnostics](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544556) | failure |
| [CI / Quality non-regression](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544568) | success |
| [CI / Python engineering](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544636) | success |
| [CI / Runtime installation](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123069544862) | success |
| [CI / Engineering](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814/job/123072637520) | success |

## Comparação por identidade e resultado

| Relatório | Estado hospedado | Identidades/multiplicidades versus local | Fingerprint |
| --- | --- | --- | --- |
| engineering | PASS / exit 0 | iguais | igual |
| financial | BLOCKED / exit 1 | iguais | igual |
| mypy | FAIL_WITH_DEBT / exit 1 | iguais | igual |
| node | PASS / exit 0 | iguais | igual |
| python | FAIL / exit 1 | iguais | igual |
| quality | PASS / exit 0 | iguais | igual |
| ruff | FAIL_WITH_DEBT / exit 1 | iguais | igual |
| runtime | PASS / exit 0 | iguais | igual |

- Engineering: 1042P/0F/0E/0S.
- Python completo: 1042P/15F/9E/5S; 1071 casos.
- Financial: 73P/15F/9E/0S; 97 casos.
- Node: 31/31, incluindo autoteste. Comparação dos nomes de todas as suítes e respectivos exit codes.
- Ruff: 130 diagnósticos; mypy: 673. Comparação de Counter das representações JSON completas de cada diagnóstico, incluindo arquivo, regra, localização, mensagem e multiplicidade. Nenhuma nova identidade nem compensação por remoção.
- Quality: baseline/current 803/803; added=[]; removed=[]; digest baseline 4bff522ba5cf8f203dbb7851a88f3745df4a6f75f4478c88fdd933740bed152a idêntico; códigos reais Ruff/mypy 1/1.
- Casos Python comparados por classe, nome parametrizado e status, preservando multiplicidade. Inventários completos de engineering/financial/python idênticos aos locais, incluindo classificação, seleção e resultado; não apenas contagens.
- 31 casos ci.test_ci/ci.test_governance aprovados. test_pytest_uses_an_isolated_temporary_database aprovado. Guardas de credenciais, rede, canonicalização TEMP e sanitização aprovadas.
- test_shares_unit_020_frozen_engine efetivamente executado e failed. Não houve skip/waiver financeiro. Os cinco skips externos preexistentes permanecem visíveis no diagnóstico completo.
- Resumo agregado JSON hospedado idêntico ao local. Nenhum relatório ausente; consistent_identity=true.

## Segurança e isolamento comprovados

Workflow publicado em .github/workflows/ci-offline.yml, blob GitHub 67811a66100207c8a16b77a4424fd042761a66e0. Inspeção do YAML remoto e logs confirma contents:read/metadata:read, Actions fixadas por SHA, persist-credentials:false, ausência de pull_request_target, secrets referenciados, environments produtivos, deploy e migrations produtivas. API do PR informa auto_merge=null e draft=true.

Python 3.14.7 em todos os relatórios; Node v24.19.0 no log Frontend. Instalações hash-checked dos locks passaram e pip check informa No broken requirements found; versões Ruff 0.16.6, mypy 2.3.1, pytest 9.1.1 e Alembic 1.19.2 comprovadas nos logs. Instalação de dependências usa PyPI controlado; testes de produto executam com guardas offline Python/Node. Emulador/cloud não executados.

ci/run.py:isolated_environment transmite apenas allowlist de variáveis do sistema; não herda credenciais do runner. HOME/USERPROFILE, SQLite, cache e configurações são temporários; credencial Google aponta para arquivo inexistente e jobs externos estão desativados. Testes verificam remoção de tokens sintéticos e paths produtivos, bloqueio de rede e proteção do banco. Runtime usa migration apenas em SQLite descartável, nenhuma conexão produtiva.

Nove artefatos foram baixados: oito relatórios e resumo. Inspeção dos 16 arquivos confirmou allowlist de JSON/JUnit/cobertura, sem DB, snapshot ou log bruto. JUnit não contém mensagens de falhas/captured stdout/stderr; coverage contém metadados de código. Logs usados na auditoria ficaram em TEMP local, fora dos uploads. Retenção GitHub: 14 dias; preservar esses relatórios antes da expiração em eventual etapa de arquivamento autorizada.

Limite: esta é verificação do workflow, dos artefatos e dos controles efetivamente executados; não certifica segurança integral do repositório ou do GitHub. Não houve necessidade de acessar valores de secrets. Não foi identificada condição de segurança não verificável no escopo de execução que impedisse a validação da CI.

## Estados e recomendação

- Engineering CI: PASS hospedado.
- Financial Certification: BLOCKED.
- Release Readiness: BLOCKED.
- Deployment Authorization: NOT_IMPLEMENTED; deployment_authorized=false.

Sem divergência hospedada identificada, sem falha de governança. Engenharia atende à publicação controlada. Manter draft conforme instrução; candidato apto à revisão humana para futura integração exclusivamente de CI, condicionada ao aceite da política e dívida técnica. Não há autorização nem recomendação de promoção produtiva. CERT_48 exige reconciliação independente; identidade de bytes congelados e 22 referências históricas continuam pendentes. Empacotamento, homologação, backup/rollback e CD permanecem etapas futuras.

Proposta de proteção está em ci_branch_protection_proposal.md; nenhuma proteção foi ativada. Estes três relatórios documentais foram escritos após o run, permanecem locais sem commit/push novo. O run valida a2f6d64 e seu merge sintético, não uma revisão documental posterior.

## Integridade dos artefatos baixados

Obter os artefatos no run acima; o digest abaixo refere-se ao arquivo extraído, sem conteúdo financeiro reproduzido.

| Arquivo no artefato | SHA-256 |
| --- | --- |
| gate-summary-2a6513494b3f228b4ce46c716920b6ee1de24af7/gate-summary.json | `5604dc7b039fceb5f01d1c2f4328bb0c8b4db2c8707770a30a261686ae0b4a44` |
| governance-engineering-2a6513494b3f228b4ce46c716920b6ee1de24af7/engineering-junit.xml | `d606fa23f440768a7cfe3d5401a1ea464e5594acce3428039e2b69b86e30edff` |
| governance-engineering-2a6513494b3f228b4ce46c716920b6ee1de24af7/inventory.json | `6c94f1dcf414c78c721f9ffb89892db004bd1fcab26de2894a99918dad710ce7` |
| governance-engineering-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `e0f4cad23cf9784e674e7493a256f523b4d80d683aa3f6d1ac1951966b5cf663` |
| governance-financial-2a6513494b3f228b4ce46c716920b6ee1de24af7/financial-junit.xml | `b770b19e40ca10fee2dc507a2eb3838e3e16d5ef697e95d900577a1a2e692ede` |
| governance-financial-2a6513494b3f228b4ce46c716920b6ee1de24af7/inventory.json | `2541ff181d7d5bf1fc3a7406bdb5da3fd70bd0a662ce9761d790caf4528dc982` |
| governance-financial-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `33ba61decfee33b80c9a7753417d1acefaa4a8ce6ecee17b1544d2c3934a24c8` |
| governance-mypy-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `b326a2e5dc012c9c5d85fa01278c7616a211dcafeb0bb736308dca4fd9413fff` |
| governance-node-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `59ca8daa843353f69dab4cd725efba1936fbdef20e5b8d6723c4cc3dfb693f50` |
| governance-python-2a6513494b3f228b4ce46c716920b6ee1de24af7/coverage.xml | `0e44c60caf323afd27423c65ee55c0af43a2c055b05fb5c364e133b265e0602c` |
| governance-python-2a6513494b3f228b4ce46c716920b6ee1de24af7/inventory.json | `92a426c0ed0d0d329ca1c5a148411b47c97d0955b289a7068e2a4ae052e700c1` |
| governance-python-2a6513494b3f228b4ce46c716920b6ee1de24af7/python-junit.xml | `e295f65f2789ca449996e86699608be19887e38a1165c8e1ffaa91ad658291d5` |
| governance-python-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `62e6d4fd9268bfc6a2d1018befa7447b2dd180b3bdb93f5525c0ba5514072c46` |
| governance-quality-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `26b9687b28c4f6a200c57c61e3b493cb22089f2ef9b40512ab294305e390da9f` |
| governance-ruff-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `b84492078691b3f7dc11b931e845340fba9a411766cfd92645d976f0556e1391` |
| governance-runtime-2a6513494b3f228b4ce46c716920b6ee1de24af7/result.json | `1833316c1d158db6baa7493832c41c72bcb630d134c9492c92aa2142cc7706af` |
