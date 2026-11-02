# PR5.2B — Publicação controlada

**HOSTED_VALIDATED**. Registro UTC: 2026-10-28T21:22:38.291130+00:00. [PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48) permanece open/draft; sem auto-merge, merge, proteção ativa ou produção.

## Preflight e preservação

Remoto e develop reconsultados antes dos commits e novamente antes do push: a2f6d64bb55210bb7514c2f172efa37116eeec6e / ca627ac72f110d0f4d62faaa9c51a08eaed54965. Ancestralidade confirmada; inventário exato de 19 arquivos PR5.2A, hashes confrontados com overlay LF validado. 24 arquivos ignorados/cache/relatórios foram inventariados sem inclusão. Nenhum arquivo desconhecido, banco, ZIP, TEMP, credencial ou snapshot entrou nos commits.

Preparação em novo worktree/branch codex/pr52b-controlled-governance. E, PR5.2 e PR5.2A originais preservados por comparação de HEAD/status/hashes; nenhum reset, rebase, clean, cherry-pick ou merge aplicado às origens. Manifest de evidência contém somente metadados e destino com placeholder USERPROFILE, sem caminhos privados absolutos. O arquivo local de evidências não integra a execução dos testes.

## Commits publicados

| Commit | Finalidade | Arquivos |
| --- | --- | --- |
| 56aa85624446064c8edd9870ac25d9a935b427a9 | ci: record PR5.2 ownership and governance proposals | 10 |
| 405b29d7c9bbd98bb373c4827b702ecaada3fc86 | ci: bootstrap single-maintainer gates with versioned policy identity | 11 |

Commit 1 preserva a entrega PR5.2 antes de sua adaptação; commit 2 integra o bootstrap e deixa o conjunto final autoconsistente. O commit intermediário não é apresentado como validado. União final: 19 arquivos, 1140 inserções/24 remoções. Listas completas por commit em pr52b_gate_comparison.json.

Push confirmado estritamente fast-forward: a2f6d64..405b29d, HEAD final **405b29d7c9bbd98bb373c4827b702ecaada3fc86**, para codex/ci-offline-pr51. develop permaneceu intacta. Nenhum force-push ou novo PR. Descrição revisada a partir de pr48_bootstrap_description.md para refletir a publicação e, depois, o run realmente verificado.

## Validação antes da publicação

Clone novo do candidato commitado, core.autocrlf=false antes do checkout, sem overlay nem arquivos pessoais. Os oito checks registraram worktree_dirty=false e checkout_sha=405b29d7c9bbd98bb373c4827b702ecaada3fc86. LF dos arquivos executáveis/políticas preservado, sem normalizar bytes financeiros para obter aprovação. Fingerprint v2 **c049a052e93d37b54b80841e538dd694029975e5d27a325e59a3d1603ad1df7f** e identidade de política **73db10df451889f01ab20a25a17090f0e88e0fed7aeb26551630ca83fda95e48** reproduzem PR5.2A exatamente.

A matriz completa reproduziu todos os casos/status, inventários e diagnósticos da baseline PR5.2A, não apenas contagens. Relatórios locais mantêm códigos reais: engenharia e qualidade passam; diagnósticos/certificação continuam reprovados. Venvs travados previamente instalados reutilizados para a validação local; nenhuma instalação nova necessária. GitHub realizou instalação pelo lock em runners novos.

## Publicação e limites

[Run novo 40770225788](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788) valida o candidato, incluindo merge sintético b3f313265ef52768acd49120a70d902c23981869. PR5.1E não foi usado como substituto de execução nova. Resultados hospedados e segurança estão em pr52b_hosted_validation.md / pr52b_security_review.md.

Engineering PASS; Financial BLOCKED; Release BLOCKED; Deployment NOT_IMPLEMENTED. Risco INDEPENDENT_REVIEW_NOT_AVAILABLE. CODEOWNERS publicado na head do PR como responsabilidade; sem owner review obrigatório. develop ainda sem proteção. Nível 1 propõe zero reviews, owners/last-push false, PR/check/conversas e restrições técnicas; eficácia só poderá ser demonstrada depois de autorização administrativa separada.

Os quatro relatórios PR5.2B foram criados após o run e ficam locais, sem commit/push adicional. Não atribuir sua execução retroativamente ao SHA 405b29d7c9bbd98bb373c4827b702ecaada3fc86. Nenhum merge, deploy, migration produtiva, mudança financeira ou de proteção foi realizado.
