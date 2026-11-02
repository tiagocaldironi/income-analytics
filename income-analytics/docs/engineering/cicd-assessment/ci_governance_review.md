# PR5.2 — Revisão da governança de integração

Data: 28/10/2026. Estado: **GOVERNANCE_BLOCKED para integração com revisão independente**. Preparação técnica e testes locais concluídos; nenhuma proteção ativa. O impedimento é humano/organizacional, não uma falha nova dos cálculos ou do Engineering.

## Evidência remota reconsultada

- [PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48): open, draft, autor tiagocaldironi, head codex/ci-offline-pr51 em a2f6d64bb55210bb7514c2f172efa37116eeec6e; base develop em ca627ac72f110d0f4d62faaa9c51a08eaed54965. auto_merge=null; repositório allow_auto_merge=false. Nenhuma review submetida na consulta.
- [Run 40760146814](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814): completed/failure geral; CI / Engineering success. Checkout executado: merge sintético 2a6513494b3f228b4ce46c716920b6ee1de24af7. Fingerprint de execução: 1648121a859a166d0b03ece09654d323e7cf56efcc3608ff06665bf389d79d9e.
- GET repos/tiagocaldironi/income-analytics: public, owner tipo User, permissões do token admin/maintain/push=true. GET collaborators e permission: único colaborador retornado tiagocaldironi, admin. Nenhuma equipe ou segundo aprovador elegível comprovado.
- GET branches/develop/protection: HTTP 404, mensagem Branch not protected. GET rulesets e rules/branches/develop: listas vazias. Nenhum controle é tratado como aplicado.
- GET commits/a2f6d64.../check-runs: nove checks, nomes iguais aos do YAML; app github-actions, id 15368. O contexto selecionável é CI / Engineering, associado ao head do PR. GET check-runs no SHA sintético retornou vazio: a evidência do código executado está nos artefatos, não se confunde com o SHA ao qual o check foi publicado.
- GET codeowners/errors?ref=develop: 404. Não há CODEOWNERS em develop na árvore Git consultada; esse endpoint não valida a proposta local ainda não publicada.

## Documentos e código revisados

ci_gate_policy.md, ci_quality_baseline.json, ci_test_inventory.md, ci_consolidation_plan.md, pr51e_hosted_validation.md e ci_branch_protection_proposal.md confrontados com ci/gate_policy.py, gate_plugin.py, governance.py, test-groups.json e workflow na raiz Git. O ledger D é histórico (1066 casos); o aviso E e os artefatos hospedados registram 1071, sem apagar os resultados anteriores.

Revisão dos nove commits publicados e do diff final contra develop: 49 arquivos. Predominam CI, locks, testes e documentação; src/ muda somente na validação de schema CVM já revisada no PR5.1B. Não há diff em cálculos de aplicação, migrations ou fixtures/manifests financeiros congelados. A revisão PR5.2 não altera esses arquivos nem a baseline de dívida. O índice público mínimo CVM permanece a única fixture binária nova do PR anterior; nada novo da B3 foi arquivado.

## Matriz de gates e responsabilidade

| Gate | Critério verificável | Execução / resultado vigente | Responsável real e aprovação |
| --- | --- | --- | --- |
| Engineering | Runtime, Python hermético sem falha/erro/skip, frontend e não regressão; relatórios obrigatórios do mesmo SHA/fingerprint | CI / Engineering PASS; Python 1042P, frontend 31/31 | tiagocaldironi responde pela manutenção. Revisão independente do PR #48: sem elegível atual; precisa segundo colaborador write |
| Quality non-regression | Nenhuma nova identidade ou multiplicidade, sem compensação por erros removidos; ferramentas/config/lock coerentes | PASS; Ruff 130 + mypy 673, added=[]/removed=[] | Revisão de baseline/política pelo mantenedor e futuro owner independente; dívida inventariada, aceite formal ainda pendente |
| Diagnóstico completo | Exibir todos os resultados e códigos reais; não é gate global de sucesso enquanto pendências abertas | 1042P/15F/9E/5S; Ruff/mypy reprovados | Mantenedor acompanha dívida; não converter falhas em skips nem aprovar por contagem |
| Financial Certification | CERT_48, identidade, originais históricos e contratos financeiros aprovados por evidência independente | BLOCKED; 73P/15F/9E; 22 históricos + dois congelados executados | Mantenedor coordena recuperação; revisor financeiro independente não designado/comprovado. Não aceitar autocertificação |
| Release Readiness | Engineering + certificação íntegros, build/artefato reproduzível, homologação, segurança, backup/rollback | BLOCKED | Decisão futura explícita do mantenedor após evidências e revisão independente |
| Deployment Authorization | Artefato identificado, ambiente protegido, autorização e recuperação verificadas | NOT_IMPLEMENTED; deployment_authorized=false | Somente autorização futura explícita; esta entrega não implementa CD |

Os 22 IDs históricos e os dois IDs congelados permanecem no inventário e nos jobs full/financial. Ausência desses IDs gera erro de coleta. Teste novo desconhecido entra em Engineering; módulos externos são exceções explícitas, não seleção por resultado. Engenharia sem testes, com skip, com divergência inventário/JUnit ou código não zero falha. O resumo falha com check obrigatório ausente, saída não zero ou identidades inconsistentes. Testes locais confirmaram essas condições.

## Baseline e limites de confiança

Digest versionado/runner da baseline: 4bff522ba5cf8f203dbb7851a88f3745df4a6f75f4478c88fdd933740bed152a. Counter usa ferramenta, arquivo, linha/coluna, regra, mensagem e multiplicidade. Ruff/mypy continuam reprovados individualmente; Quality aprova apenas não regressão. Não há refresh automático ou ignore global novo.

O digest no relatório torna uma alteração identificável, mas não torna o JSON imutável: um PR que muda baseline e workflow pode mudar seu próprio critério de sucesso. CODEOWNERS e revisão independente obrigatória são o controle externo proposto; atualmente não estão ativos. Engineering aprovado não equivale a aprovação humana de um workflow modificado. O token read-only e a ausência de auto-approve não impedem administradores de mudar configurações; por isso exigir trilha de autorização para qualquer recuperação.

## CODEOWNERS e viabilidade

Proposto em .github/CODEOWNERS na raiz Git, com quatro padrões ancorados: workflows, o próprio CODEOWNERS, todo income-analytics/ci/ e todo assessment. Cobre baseline, classificação, runner, comparador, políticas e os novos testes. Sintaxe restrita a caminhos exatos/diretórios, case-sensitive, sem padrões especiais; testes positivos e negativos verificam cobertura e precedência. Único owner incluído: @tiagocaldironi, elegível por admin/write comprovado.

Essa proposta local não solicita reviews nem aplica bloqueio. CODEOWNERS é lido da base do PR; adicioná-lo apenas à head não protege a primeira integração. Drafts não recebem solicitação automática de owners. Não publicar/ativar exigência de owners sem incluir segundo owner real nas mesmas linhas e uma estratégia de bootstrap aprovada. Um segundo colaborador apenas com write, sem figurar nos padrões, não resolve a exigência de owner review para um PR do owner único.

Quem pode aprovar agora: tiagocaldironi pode aceitar política e autorizar ações administrativas; não pode contar como aprovador independente do próprio PR #48. Nenhum outro usuário retornado pela API pode cumprir esse papel no estado observado. Não tratar revisão do agente, bot, leitor público ou aceite no chat como aprovação independente válida do GitHub.

## Testes e limites de comprovação

40 testes locais aprovados: 31 existentes de infraestrutura/governança + nove novos em ci/test_pr52_governance.py. Testes novos executados manualmente; não inseridos silenciosamente na lista do workflow publicado. Ruff no novo arquivo: PASS. Não houve novo run remoto nem declaração de execução hospedada do PR5.2.

| Condição negativa | Evidência | Limite |
| --- | --- | --- |
| Teste Python novo falha Engineering | Teste existente executa pytest temporário com --ci-gate=engineering; exit=1 e resumo FAIL | Teste induzido só em TEMP |
| Novo Ruff/mypy falha Quality | Dois testes novos executam ferramentas reais sobre arquivo temporário inválido; compare_diagnostics retorna FAIL | Sem adicionar dívida à baseline |
| Troca/duplicação de erro não é compensável | Casos existentes exercitam seis mudanças de identidade e multiplicidade | Sem refresh |
| Alterar baseline é identificável | Cópia temporária alterada muda digest; original bate com evidência hospedada preservada | Aprovação da alteração exige review externa, ainda bloqueada |
| Falha financeira não vira sucesso | Resumo reavaliado sobre oito relatórios reais; CERT_48 failed, exit=1, financeiro/release BLOCKED | Não reconcilia a pendência |
| Nome obrigatório estável | YAML local e checks GitHub concordam em CI / Engineering, app 15368 | Não foi ativado required check |
| CODEOWNERS cobre críticos | Nove paths positivos e path alheio negativo; retirar regra workflows remove cobertura | Validação local do subconjunto usado; parser GitHub não consultável para arquivo não publicado |
| Workflow não se autoaprova | YAML read-only sem auto-review; proposta exige review independente e último push por outra pessoa | Bloqueio remoto de workflow não revisado NÃO comprovado/ativo; depende de aprovação/ativação futura |

Primeira execução local: 39P/1F por CRLF no worktree criado pelo app, contra LF exigido no workflow. Segunda: 38P/2F porque o primeiro overlay temporário omitiu .github/CODEOWNERS (irmão do diretório da aplicação). Corrigido o provisionamento do checkout LF e cópia explícita do arquivo da raiz, sem alterar expectativas, baseline ou código existente; execução final 40P/0F/0E/0S. Relatórios sanitizados das tentativas ficam em ci-reports/pr52-initial, pr52-second e pr52 (ignorados pelo Git).

## Fontes primárias e conclusão

- [GitHub: CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners): exige write, usa base, revisão depende de proteção; público tem suporte mesmo no plano Free.
- [GitHub: protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): público tem suporte; reviews, checks e restrições administrativas são configuráveis.
- [GitHub: aprovação de PRs](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews): o autor não pode aprovar o próprio PR; aprovação do agente não satisfaz essa exigência.

Documentação consultada em 28/10/2026; payload é proposta, não validação de uma escrita na API. O campo plan do usuário veio null; não inferir plano pago. O caráter público torna os recursos básicos propostos disponíveis sem comprovar assinatura. A falta de segundo aprovador impede afirmar governança pronta ou recomendar integração imediata do PR #48. Manter draft até decisão de mantenedor e revisor elegível. Nenhuma regra foi ativada.
