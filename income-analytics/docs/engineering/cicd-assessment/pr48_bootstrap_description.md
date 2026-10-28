# Descrição preparada para PR #48 — sem atualização remota nesta fase

O PR consolida CI hermética, instalação travada, frontend, isolamento SQLite e governança de checks, incluindo as correções técnicas frontend/parser CVM previamente aprovadas. Não altera cálculos financeiros certificados.

## Engenharia e identidade

PR5.1E teve Engineering aprovado no run 40760146814, head a2f6d64bb55210bb7514c2f172efa37116eeec6e, checkout sintético 2a6513494b3f228b4ce46c716920b6ee1de24af7. Esse resultado não valida a árvore nova PR5.2A. Consultar ci_pr52a_validation.md para a execução local, novos fingerprint versão 2/identidade de política e inventário. Após autorização para publicar, substituir este parágrafo com link e SHA do novo run hospedado, sem atribuir resultado antigo ao candidato novo.

PR5.2A inclui explicitamente ci/test_pr52_governance.py nos comandos de engenharia, preservando tests/, test_ci.py e test_governance.py. Os testes não usam arquivo pessoal de evidências nem credenciais; arquivo ausente/coleta inválida falham. A agregação rejeita versões e políticas inconsistentes e relatórios financeiros com bloqueadores rotulados como PASS.

## Governança provisória

**INDEPENDENT_REVIEW_NOT_AVAILABLE.** Único mantenedor elegível verificado: @tiagocaldironi. Proposta nível 1: PR obrigatório, zero aprovações exigidas, CI / Engineering obrigatório, conversas resolvidas, branch atualizada e proibição de force-push/exclusão/bypass permanente. CODEOWNERS declara responsabilidade; require_code_owner_reviews e require_last_push_approval permanecem false. Nenhuma proteção está ativa por esta proposta.

Nível 2 preserva revisão independente/owners/invalidação de aprovações após confirmar outro colaborador elegível e obter autorização separada. Integração eventual sem revisão independente exige decisão explícita e registro de risco do mantenedor. Não é autocertificação financeira.

## Pendências e próximos passos

Financial Certification BLOCKED, Release Readiness BLOCKED e Deployment Authorization NOT_IMPLEMENTED. CERT_48, identidade, 22 casos históricos, permissões B3, Emulator/cloud, build reproduzível, homologação, backup e rollback continuam pendentes. Diagnósticos Ruff/mypy integrais continuam reprovados pela dívida conhecida; não confundir Engineering com workflow global aprovado.

Publicação de commits locais e execução hospedada nova exigem autorização específica; ativação de proteção só depois de revisar os efeitos e autorizar administração. Manter draft. Sem merge, deploy ou migrations produtivas.
