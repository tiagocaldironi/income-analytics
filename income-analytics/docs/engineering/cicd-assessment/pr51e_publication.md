# PR5.1E — Revisão e publicação controlada da CI

Data: 28/10/2026. Candidata local: codex/pr51e-controlled-ci. PR remoto #48 permanece draft, head 1bbd2d42686ab0c893790772a05a7845cfbc0295; develop/base ca627ac72f110d0f4d62faaa9c51a08eaed54965. Nenhum push/alteração remota foi realizado nesta preparação. A publicação depende da autorização explícita exigida no item 4 do PR5.1E.

## Revisão dos diffs e rastreabilidade

Os 27 arquivos consolidados A/B/C/D foram inventariados antes da cópia. A/B/C/D preservados; E é worktree/branch nova. Os três commits publicados do PR5.1 permanecem ancestrais, sem rebase/squash/reset. Os commits novos abaixo separam origem e finalidade:

| Commit | Finalidade | Arquivos |
| --- | --- | --- |
| 30de39420baa0f1b9963f2f3863243cc4609bf0b | docs(ci): record PR5.1A failure triage | 3 |
| cb625e1003cb7c3f760fa4ece793a38776ebc3b0 | fix(ci): align holdings tests and reject invalid CVM schemas | 4 |
| fec775a16d236706d0c39c741e671d2a9d2c2eea | test(ci): add verified CVM reference and provenance controls | 8 |
| bbccae43eeeb8439790628acf9a76ae5916ec004 | ci: separate engineering gates from blocked financial certification | 12 |
| 93bf0be672fc031592d6827f0796e6658c27cbb5 | fix(ci): reject incomplete mypy parsing and include stub errors | 2 |

Os hashes A/B/C/D documentam entregas antes sem commit. Os dois arquivos de implementação governança da revisão E foram mantidos fora do commit D e incluídos no commit seguinte; o histórico distingue exatamente a correção encontrada na revisão. Normalização LF ocorreu apenas em ci/test-groups.json e no plano de engenharia, sem alterar valores nem bytes congelados financeiros.

Lista completa por commit (caminhos relativos à raiz Git):

### 30de394 — docs(ci): record PR5.1A failure triage

- income-analytics/docs/engineering/cicd-assessment/ci_failure_triage.md
- income-analytics/docs/engineering/cicd-assessment/ci_quality_debt_baseline.md
- income-analytics/docs/engineering/cicd-assessment/ci_stabilization_plan.md

### cb625e1 — fix(ci): align holdings tests and reject invalid CVM schemas

- income-analytics/docs/engineering/cicd-assessment/pr51b_validation.md
- income-analytics/src/income_analytics/infrastructure/cvm_fundamentals_data.py
- income-analytics/tests/frontend/holdings_v2.mjs
- income-analytics/tests/infrastructure/test_cvm_statement_parser.py

### fec775a — test(ci): add verified CVM reference and provenance controls

- income-analytics/ci/magic_formula_references.py
- income-analytics/docs/engineering/cicd-assessment/magic_formula_ci_fixture_design.md
- income-analytics/docs/engineering/cicd-assessment/magic_formula_reference_inventory.md
- income-analytics/docs/engineering/cicd-assessment/magic_formula_reference_provenance.json
- income-analytics/docs/engineering/cicd-assessment/pr51c_validation.md
- income-analytics/tests/fixtures/cvm/receipt_index_2025_v1/README.md
- income-analytics/tests/fixtures/cvm/receipt_index_2025_v1/dfp_cia_aberta_2025.csv.gz
- income-analytics/tests/infrastructure/test_magic_formula_ci_reference_bundle.py

### bbccae4 — ci: separate engineering gates from blocked financial certification

- .github/workflows/ci-offline.yml
- income-analytics/ci/gate_plugin.py
- income-analytics/ci/gate_policy.py
- income-analytics/ci/governance.py
- income-analytics/ci/test-groups.json
- income-analytics/ci/test_governance.py
- income-analytics/docs/engineering/ci-offline/README.md
- income-analytics/docs/engineering/cicd-assessment/ci_consolidation_plan.md
- income-analytics/docs/engineering/cicd-assessment/ci_gate_policy.md
- income-analytics/docs/engineering/cicd-assessment/ci_quality_baseline.json
- income-analytics/docs/engineering/cicd-assessment/ci_test_inventory.md
- income-analytics/docs/engineering/cicd-assessment/pr51d_validation.md

### 93bf0be — fix(ci): reject incomplete mypy parsing and include stub errors

- income-analytics/ci/governance.py
- income-analytics/ci/test_governance.py

## Política e baseline validadas

- Engineering seleciona os demais testes por padrão, sem usar status de falha como critério. Os 22 IDs históricos exigem referências originais comprovadas no inventário; os dois testes de hashes são tecnicamente herméticos e continuam sob Financial Certification por finalidade. Os cinco externos exigem Emulator/cloud e permanecem visíveis nos skips offline preexistentes.
- Nenhum dos 1066 casos D foi removido ou mudou de status. Os cinco acréscimos E protegem o parser do relatório mypy.
- Baseline JSON permaneceu byte a byte idêntica à D: 130 Ruff + 673 mypy. Identidades incluem ferramenta, arquivo, regra, localização, mensagem normalizada e multiplicidade. Ferramentas/lock/configuração conferidos. Não há refresh, ignore global ou compensação de erros novos por removidos.
- Quatro estados independentes mantidos: Engineering PASS local não significa Financial/Release/Deploy aprovados. O job financeiro continua não aprovado.
- Apenas o índice CVM aprovado está incluído como fixture nova; não há SQLite, snapshot privado ou pacote B3 incluído. Manifestos/hashes congelados, cálculos, migrations, locks e configuração strict permanecem sem diff frente ao PR #48.

## Achado da revisão E e correção

O parser mypy aceitava apenas arquivos .py. Um diagnóstico novo em .pyi poderia ficar omitido caso outros erros já reconhecidos levassem a ferramenta a retornar 1. Correção isolada de CI: reconhecer .py e .pyi, recusar linha de erro não interpretada e conferir total informado pelo mypy. Cinco testes verificam fonte/stub, duas formas de erro não interpretado e divergência do resumo. A saída real da versão fixada foi validada: permanecem 673 diagnósticos reconhecidos, sem nova dívida.

Nenhuma alteração financeira foi necessária para obter aprovação do Engineering.

## Validação local do candidato commitado

Commit de código efetivamente executado: **93bf0be672fc031592d6827f0796e6658c27cbb5**, worktree_dirty=false nos oito relatórios. Fingerprint da árvore de execução: **1648121a859a166d0b03ece09654d323e7cf56efcc3608ff06665bf389d79d9e**. Venvs dev/runtime travados e isolados já instalados na validação D foram reutilizados; PYTHONPATH aponta para este checkout candidato. Produto sem rede, DBs apenas TEMP e nenhuma credencial produtiva herdada.

| Check | Resultado local esperado para comparação hospedada |
| --- | --- |
| Runtime installation | PASS, sem pytest no runtime |
| Python engineering | **1042P / 0F / 0E / 0S** |
| Full Python diagnostic | **1042P / 15F / 9E / 5S**, exit=1 |
| Financial certification | **73P / 15F / 9E / 0S**, BLOCKED, exit=1 |
| Frontend | **30 suítes + autoteste = 31/31** |
| Ruff diagnostic | **130**, FAIL_WITH_DEBT |
| mypy diagnostic | **673**, FAIL_WITH_DEBT |
| Quality non-regression | PASS, **803 existentes, 0 adicionados, 0 removidos** |
| Infraestrutura + governança | **31 testes aprovados**: 5 originais + 21 D + 5 E |
| Resumo | Engineering PASS; Financial BLOCKED; Release BLOCKED; Deployment NOT_IMPLEMENTED |

Total coletado: 1071 testes Python, sendo 1066 anteriores e cinco novos. Os 22 casos históricos permanecem 13F+9E; CERT_48 e identidade são as outras duas falhas. Estes números não são resultado hospedado novo.

Este relatório e seu aviso no inventário são documentação posterior à execução. O commit que os inclui não modifica o fingerprint de execução; não se atribui retroativamente a execução local a esse novo SHA documental. A execução hospedada deverá validar o head final publicado e seu merge sintético.

## Plano remoto condicionado à autorização

1. Reconsultar PR #48 e develop, confirmar head esperado e ancestralidade. Sem sobrescrever trabalho remoto novo.
2. Fazer push fast-forward da branch E para a head branch do PR #48, codex/ci-offline-pr51. Não usar force. A branch/worktree A local permanece no HEAD original, sem checkout/reset; só a head remota autorizada avança.
3. Atualizar descrição do PR para incluir A/B/C/D/E e estados reais; manter draft. Não criar outro PR nem habilitar auto-merge.
4. Aguardar workflow disparado pelo push; consultar os checks com backoff e baixar apenas artefatos sanitizados.
5. Comparar pr_head_sha, checkout_sha de merge, source_fingerprint, versões/contagens, identidades Ruff/mypy, IDs coletados e estados. O SHA sintético do PR difere do head por definição; o campo pr_head_sha identifica o candidato. Se houver divergência nova, investigar sem alterar finanças/expectativas ou ocultar falha.
6. Registrar links dos runs, resultados hospedados e recomendação atualizada. Não afirmar workflow global verde: os diagnósticos e certificação continuam reprovados por desenho transparente.

## Checks candidatos a obrigatórios em develop

Inspeção remota: develop está em ca627ac, protected=false e lista de rulesets vazia. Nenhuma proteção foi alterada.

| Check | Proposta | Condição |
| --- | --- | --- |
| **CI / Engineering** | Check obrigatório principal de PR | Após confirmar nome e estabilidade em execuções hospedadas; depende dos quatro componentes abaixo |
| CI / Runtime installation | Obrigatório redundante opcional | Já incluído na agregação; útil para diagnóstico direto |
| CI / Python engineering | Obrigatório redundante opcional | Já incluído na agregação, sem skips/falhas aceitos |
| CI / Frontend | Obrigatório redundante opcional | Já incluído na agregação |
| CI / Quality non-regression | Obrigatório redundante opcional | Já incluído; baseline inicial e alterações posteriores exigem revisão |
| CI / Full Python diagnostic | Manter visível, sem torná-lo globalmente obrigatório agora | 24 falhas/erros históricos conhecidos ainda não resolvidos |
| CI / Ruff diagnostics / CI / mypy diagnostics | Manter diagnósticos integrais visíveis | Não confundir baseline de dívida com lint limpo; promover a obrigatórios globais quando saneados |
| CI / Financial certification | Obrigatório para certificação/release e alterações em contratos financeiros certificados | Permanece BLOCKED; não usar Engineering como bypass financeiro |

Recomendação: primeiro confirmar o candidato hospedado e a estabilidade dos nomes; então propor ativação apenas de CI / Engineering para PRs gerais. Alterações financeiras certificadas exigem revisão e certificação independente. Gate de release/deploy continua sem implementação de promoção. Esta entrega define a proposta, não ativa branch protection.

## Limites e estado da publicação

- Commits locais preparados e revisão/testes concluídos; autorização para publicar ainda pendente.
- GitHub Actions do candidato ainda não executado: sem push autorizado, não há comparação hospedada concluída.
- CERT_48, identidade, referências originais e permissões de redistribuição B3 continuam bloqueadoras financeiras.
- Mantida a recomendação de PR em revisão/rascunho; sem merge/deploy ou mudança de proteções automática.
