# PR5.2A — Validação do bootstrap

**BOOTSTRAP_READY para revisão/publicação autorizada; proteção NÃO ATIVADA.** Sem alegação de validação hospedada do candidato novo. Risco: INDEPENDENT_REVIEW_NOT_AVAILABLE. Data: 28/10/2026.

## Origem e estado remoto

[PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48) continua open/draft, branch codex/ci-offline-pr51 em a2f6d64bb55210bb7514c2f172efa37116eeec6e. develop permanece ca627ac72f110d0f4d62faaa9c51a08eaed54965. Remoto reconsultado sem divergência. Único colaborador admin/write: tiagocaldironi. Repositório público, administração disponível; develop sem proteção e rulesets vazios. Auto-merge desabilitado.

[Run E 40760146814](https://github.com/tiagocaldironi/income-analytics/actions/runs/40760146814) permanece evidência histórica: head a2f6d64, merge sintético 2a6513494b3f228b4ce46c716920b6ee1de24af7, fingerprint v1 1648121a859a166d0b03ece09654d323e7cf56efcc3608ff06665bf389d79d9e. Não atribuir esse run ao código PR5.2A.

Nova branch local codex/pr52a-single-maintainer partiu de a2f6d64. E e PR5.2 inventariados antes das cópias, incluindo HEAD, status e SHA-256 de todos os arquivos locais; origens preservadas. Os arquivos PR5.2 continuavam fora do diff remoto. Nenhum reset, clean, rebase, cherry-pick ou merge foi aplicado aos worktrees anteriores. Nenhum commit/push novo.

## Implementação

- governance.py inclui explicitamente ci/test_pr52_governance.py, preservando tests/, test_ci.py e test_governance.py; workflow raiz documenta a seleção. Os nove casos PR5.2 foram tornados herméticos e incorporados ao check Python engineering, componente obrigatório de CI / Engineering.
- Ausência do arquivo é fatal na construção de identidade e no comando explícito de pytest; coleta inválida/relatório ausente não aprova agregação. Os guardas existentes continuam executados.
- ci/pipeline_identity.py define fingerprint versão 2, arquivos de política obrigatórios e governance_policy_sha256. Inclui CODEOWNERS, workflow, runner/política/plugin, classificação, três arquivos de testes, módulo de identidade, baseline e bootstrap JSON. O fingerprint de execução também cobre fontes/testes/migrations/configs já considerados. Nenhum manifest financeiro alterado.
- Relatórios schema 3 registram SHA de checkout, source_fingerprint, fingerprint_version e governance_policy_sha256. O resumo rejeita políticas/versões inconsistentes ou legadas. Um relatório financeiro com blockers não pode ser aprovado por trocar status/exit code para PASS/0.
- CODEOWNERS continua declaração de responsabilidade com owner real; o nível 1 desativa owner review e último push por outra pessoa. O nível 2 preserva aprovação independente futura após verificar segundo colaborador.
- ci_branch_protection_bootstrap.json é a proposta atual; planos PR5.2 copiados são registros históricos de revisão independente, não payloads a aplicar ao mantenedor único.

## Execução local e identidade testada

Checkout temporário novo de Git a partir de a2f6d64bb55210bb7514c2f172efa37116eeec6e, core.autocrlf=false antes de materializar arquivos, sem dados pessoais/arquivos ignorados da origem. Overlay explícito dos arquivos preparados, sem criar commit. Portanto **worktree_dirty=true** nos oito relatórios: é checkout novo com overlay auditado, não commit novo limpo nem execução remota. Checkout commitado limpo/hospedado depende de autorização de publicação futura.

- SHA ancestral do checkout: **a2f6d64bb55210bb7514c2f172efa37116eeec6e**.
- Fingerprint de execução **v2: c049a052e93d37b54b80841e538dd694029975e5d27a325e59a3d1603ad1df7f**.
- Identidade da política: **73db10df451889f01ab20a25a17090f0e88e0fed7aeb26551630ca83fda95e48**.
- Mesmas identidades nos oito checks; nenhuma reutilização do fingerprint E.
- Python 3.14.7, Node 24.19.0; venvs runtime/dev previamente instalados pelos locks foram reutilizados, sem instalar dependências. PYTHONPATH aponta para este checkout e ambiente é gerado por ci/run.py:isolated_environment.

Primeiro ciclo de regressão passou funcionalmente, mas o overlay preservava CRLF nos quatro arquivos CI modificados, com fingerprint cde96170379ff122012b200048b1b964416af5bbb9a0048870ce0d8e1d8c847c. Para evitar diferença após gravação Git, somente .github/workflows/ci-offline.yml, ci/gate_policy.py, ci/governance.py e ci/test_governance.py foram normalizados para LF; todos os checks foram repetidos sobre a árvore final. Não houve alteração de baseline ou bytes financeiros para obter aprovação. Arquivos críticos inalterados do checkout LF foram conferidos contra blobs HEAD. Worktree de preparação criado pelo app pode materializar arquivos inalterados em CRLF; a identidade acima é do checkout LF de validação, não dessas cópias físicas Windows.

## Resultados finais

| Check | Resultado |
| --- | --- |
| Runtime installation | PASS, sem pytest no ambiente runtime |
| Python Engineering | **1069P / 0F / 0E / 0S** |
| Infraestrutura/governança | **58P / 0F / 0E / 0S**, incluídos nos 1069 |
| Frontend | **31/31** |
| Quality non-regression | PASS; 803 existentes, zero novos/removidos |
| Ruff | 130 diagnósticos existentes, exit=1 |
| mypy | 673 erros existentes, exit=1 |
| Python completo | **1069P / 15F / 9E / 5S**, exit=1 |
| Financial Certification | **73P / 15F / 9E / 0S**, BLOCKED, exit=1 |
| Agregação Engineering | PASS, consistent_identity=true, sem relatório obrigatório ausente |

Comparação por Counter de classe/nome/status e por identidade/multiplicidade dos diagnósticos: todos os casos E preservados com o mesmo status. Engineering/full acrescentam 27 casos aprovados (nove PR5.2, 17 de identidade/integração e um de simulação), sem remover/ocultar teste de engenharia. Os nove casos originais preservam a finalidade; dois mudaram de auditoria pessoal para unidades herméticas, claramente sintéticas, sem se apresentar como evidência remota. Novos nomes/modelo refletem explicitamente o nível 1.

Financial, frontend, Ruff e mypy permanecem idênticos por caso/suíte/diagnóstico, não apenas contagem. Os 22 históricos e os dois testes congelados continuam executados; CERT_48 continua failed. Cinco skips externos continuam explícitos. Cálculos, fixtures, manifests/hashes congelados, baseline Ruff/mypy, locks, configurações strict, migrations e processos produtivos não possuem diff novo.

## Testes negativos

- Pytest temporário novo e falho retorna exit=1 e bloqueia Engineering.
- Ruff e mypy reais sobre fonte inválida temporária geram diagnósticos que reprovam não regressão.
- Remoção de erro não compensa identidade nova; duplicação também falha.
- Mutação de cópia TEMP da baseline muda digest; original é comparado ao blob versionado. Baseline não é regenerada.
- Remover cada relatório obrigatório ou marcar falha bloqueia Engineering.
- Fingerprint, versão legada ou identidade de política inconsistente bloqueiam a agregação.
- Mutações individuais nos 12 arquivos de política alteram ambas as identidades; remover test_pr52_governance.py é fatal. Comando Python inspecionado por teste inclui explicitamente os três arquivos CI.
- Tentar apresentar relatório financeiro com blockers como PASS/0 permanece BLOCKED; dados são unidade sintética declarada. Certificação real é exercitada separadamente pelos jobs financial/full.
- Simulação da política permite PR legítimo sem reviewer e rejeita check falho, conversa pendente, base desatualizada, push direto, force-push e exclusão. Não prova enforcement remoto.

Comando do conjunto de infraestrutura: `python -m pytest ci/test_ci.py ci/test_governance.py ci/test_pr52_governance.py -q` no ambiente isolado. Regressões: `python ci/governance.py runtime|engineering|financial|python|node|ruff|mypy|quality`, cada alternativa em processo separado; runtime usa venv mínimo. Agregação: `python ci/governance.py summary --reports gate-inputs`, com apenas os oito result.json do mesmo candidato. O CI publicado criará esses ambientes via locks; os testes não requerem PR52_ARCHIVE_ROOT nem acesso ao arquivo local E.

Relatórios sanitizados finais copiados para ci-reports/pr52a-final (ignorados por Git), incluindo resultado, inventários, JUnit, cobertura e comparação. Logs brutos permanecem apenas no TEMP privado do runner local. Não há run novo no GitHub.

## Inventário preparado

Caminhos relativos à raiz Git. Documentos E/PR5.2 copiados mantêm a história; apenas cópias CODEOWNERS e test_pr52_governance.py foram adaptadas ao bootstrap.

| Arquivo | Estado local |
| --- | --- |
| .github/CODEOWNERS | novo / copiado localmente |
| .github/workflows/ci-offline.yml | modificado |
| income-analytics/ci/gate_policy.py | modificado |
| income-analytics/ci/governance.py | modificado |
| income-analytics/ci/pipeline_identity.py | novo / copiado localmente |
| income-analytics/ci/test_governance.py | modificado |
| income-analytics/ci/test_pr52_governance.py | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_bootstrap.json | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_plan.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_proposal.json | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_proposal.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_evidence_archive_manifest.json | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_governance_review.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_pr52a_validation.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/ci_single_maintainer_governance.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/pr48_bootstrap_description.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/pr51e_hosted_validation.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/pr51e_validation.md | novo / copiado localmente |
| income-analytics/docs/engineering/cicd-assessment/pr52_validation.md | novo / copiado localmente |

## Política, publicação e próximos passos

**INDEPENDENT_REVIEW_NOT_AVAILABLE** aceito como limitação provisória do modelo solicitado, não como aprovação independente. Nível 1: PR, zero reviews, Engineering obrigatório, conversas resolvidas, branch atualizada e proibições técnicas; owner/last-push reviews false. Nível 2 exige outro colaborador elegível e autorização separada. CODEOWNERS não cria proteção por si só.

Leitura das APIs e documentação oficial indica viabilidade em repositório público com administração; plano pago específico não comprovado. Zero reviews sozinho não garante PR-only: manter objeto de proteção PR, impedir bypass e verificar efeitos em teste remoto autorizado antes de declarar eficácia. Regras ainda inativas. Detalhes/recuperação em ci_single_maintainer_governance.md; payload em ci_branch_protection_bootstrap.json.

Descrição futura preparada em pr48_bootstrap_description.md; **não atualizada remotamente** nesta etapa. Próximo passo: revisão do diff e autorização específica para commits/push fast-forward, depois novo run hospedado e comparação com este candidato. Apenas após revisão dos efeitos e autorização administrativa, ativar e comprovar regras. Eventual merge é decisão distinta; manter #48 draft agora. Nenhum controle é apresentado como ativo.

Quatro gates: Engineering **PASS local**; Financial **BLOCKED**; Release **BLOCKED**; Deployment **NOT_IMPLEMENTED**, deployment_authorized=false. CERT_48, identidade, 22 referências, permissões B3, Emulator/cloud, build, homologação, backup/rollback continuam pendentes. Nada nesta entrega autoriza certificação financeira ou produção.
