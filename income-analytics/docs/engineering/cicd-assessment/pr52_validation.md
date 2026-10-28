# PR5.2 — Validação e entrega

**GOVERNANCE_BLOCKED para aprovação independente e integração.** Proposta e validação local concluídas; falta segundo colaborador elegível. Nenhum controle apresentado como ativo. Data: 28/10/2026.

## Estado consultado e preservação

PR #48 continua open/draft, head a2f6d64bb55210bb7514c2f172efa37116eeec6e, base develop ca627ac72f110d0f4d62faaa9c51a08eaed54965. Run 40760146814 completed: Engineering PASS, workflow failure pelos diagnósticos e certificação conhecidos. Nenhuma review independente existente. Único colaborador: tiagocaldironi, admin/write, também autor do PR.

Trabalho em branch isolada codex/pr52-ci-governance, partindo de a2f6d64. Nenhum commit/push criado. Três documentos locais pós-run de E foram copiados byte a byte, preservando a origem, para permitir revisão conjunta. Worktrees anteriores não editados.

## Arquivamento

Nove ZIPs originais baixados novamente antes da expiração em 11/11/2026, conferidos pelos nove digests SHA-256 fornecidos pela API do GitHub; 16 arquivos internos conferidos byte a byte contra a coleta E. JSON/JUnit/cobertura sanitizados, sem SQLite, credenciais, logs brutos, snapshots privados ou payloads B3. Manifest: ci_evidence_archive_manifest.json.

Destino local persistente autorizado pelo escopo de preservação: %USERPROFILE%/.codex/evidence/income-analytics/pr51e/40760146814, com archives/, reports/ e cópia do manifest. ACL herdada inspecionada: usuário, SYSTEM e Administradores com controle; CodexSandboxUsers com leitura/execução, sem Everyone/Users observado. Não é serviço externo, backup independente ou armazenamento imutável. Não houve upload/replicação externa. Os digests do ZIP e dos arquivos extraídos estão no manifest; a evidência preservada é do SHA E, não de PR5.2.

## Verificações

- Revisados os seis documentos exigidos, código dos gates, nove commits e diff publicado de 49 arquivos.
- Seleção padrão, IDs históricos/congelados, não regressão multiset, relatórios obrigatórios e estados independentes confirmados.
- CODEOWNERS proposto usa somente @tiagocaldironi, com write/admin comprovado; sintaxe/cobertura local validada. Enforcement depende da base e de regras futuras. Sem validação remota do parser de um arquivo ainda não publicado.
- Repositório público e admin=true: recursos básicos documentados como disponíveis mesmo no Free; plano específico UNKNOWN (API plan=null). Nenhuma chamada de mutação para comprovar disponibilidade foi feita.
- CI / Engineering está publicado por app 15368; contexto proposto corresponde exatamente. develop não protegida, rulesets/regras aplicáveis vazios.
- Testes: **40P/0F/0E/0S**, sendo 31 existentes e nove novos; Ruff no novo arquivo PASS. Teste Python induzido, erros reais Ruff/mypy temporários, mutação de baseline, cobertura de owners e ausência de auto-approve exercitados localmente.
- Não se comprovou bloqueio de merge remoto: inexistente/inativo, e ativação é expressamente excluída. Sem segundo owner, o bootstrap ainda não é operacionalmente viável.

Primeiro ciclo 39P/1F (baseline física CRLF), segundo 38P/2F (overlay inicial omitiu CODEOWNERS na raiz Git); terceiro 40P após correção somente do ambiente de teste. Detalhes em ci_governance_review.md. Nenhuma expectativa, baseline ou código existente foi ajustado para ocultar falhas.

Checkout de teste temporário: clone sem checkout, core.autocrlf=false antes de materializar a2f6d64; overlay explícito dos arquivos novos, incluindo .github/CODEOWNERS da raiz. Ambiente gerado por ci/run.py:isolated_environment, com PR52_ARCHIVE_ROOT apontando para o arquivo local sanitizado. Comando Python 3.14.7: `python -m pytest ci/test_ci.py ci/test_governance.py ci/test_pr52_governance.py -q --tb=short --junitxml=<TEMP>/raw.xml --basetemp=<TEMP>/pytest`. Requer dependências do lock já instaladas, PYTHONPATH=<checkout>/ci;<checkout>/src e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; nenhuma instalação nova realizada.

Fingerprint do checkout LF com os novos testes locais: 6ef5ec45c15c6fbbab081f45ad9a5a1f8b69def18a84331986e43e565a245f76. É árvore com overlay não commitado, NÃO o fingerprint E nem evidência hospedada de um commit PR5.2. O CODEOWNERS não entra no algoritmo atual do fingerprint de execução; seu diff/hash e revisão externa são necessários. Relatórios locais sanitizados em ci-reports/pr52 (ignorados), com tentativas anteriores preservadas.

Os testes PR5.2 são complementares e manuais: o workflow publicado ainda lista apenas test_ci.py e test_governance.py além de tests/. Qualquer incorporação permanente desses novos testes à esteira exige revisão posterior do escopo, commit autorizado e run novo.

## Arquivos preparados, sem commit

- .github/CODEOWNERS (na raiz Git).
- income-analytics/ci/test_pr52_governance.py.
- Neste diretório: ci_governance_review.md, ci_branch_protection_plan.md, ci_branch_protection_proposal.json, ci_evidence_archive_manifest.json e pr52_validation.md.
- Documentos E copiados sem modificar a origem: pr51e_validation.md, pr51e_hosted_validation.md e ci_branch_protection_proposal.md.

A descrição do PR #48 foi atualizada dentro da autorização; a branch remota mantém o SHA E. Não afirma que estes arquivos locais já fazem parte do diff remoto.

## Decisões pendentes e recomendação

Manter #48 em draft. O mantenedor tiagocaldironi pode aceitar a proposta administrativa e a dívida técnica, mas não aprovar independentemente seu próprio PR. Identificar e autorizar outro colaborador real com write; verificar elegibilidade e incluir também como owner antes de ativar owner reviews. Não conceder acesso ou inventar aprovador automaticamente.

Precisam de autorização futura distinta: commits/push dos arquivos locais, inclusão de colaborador/owners, aplicação de proteção, testes remotos de enforcement e eventual integração. CERT_48, identidade, 22 históricos, permissões B3, Emulator/cloud, build, homologação, backup/rollback permanecem pendentes. Engineering PASS hospedado; Financial BLOCKED; Release BLOCKED; Deployment NOT_IMPLEMENTED. Nenhum merge, deploy, migration produtiva, alteração financeira ou ativação de regras realizada.
