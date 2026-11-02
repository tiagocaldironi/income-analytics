# PR5.2B — Validação hospedada

**HOSTED_VALIDATED**. [PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48); [run 40770225788](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788), pull_request, windows-2025. Workflow geral **failure**, preservando diagnósticos e certificação conhecidos; CI / Engineering **success**.

## Identidades verificadas

- Head publicado e checkout local commitado: 405b29d7c9bbd98bb373c4827b702ecaada3fc86.
- Checkout/event_sha GitHub: b3f313265ef52768acd49120a70d902c23981869, merge sintético; pr_head_sha=405b29d7c9bbd98bb373c4827b702ecaada3fc86 em todos os relatórios.
- Fingerprint v2: c049a052e93d37b54b80841e538dd694029975e5d27a325e59a3d1603ad1df7f.
- governance_policy_sha256: 73db10df451889f01ab20a25a17090f0e88e0fed7aeb26551630ca83fda95e48.
- Schema 3, Python 3.14.7, todos os oito relatórios worktree_dirty=false.
- Node 24.19.0; Ruff 0.16.6, mypy 2.3.1, pytest 9.1.1, Alembic 1.19.2 e pip check confirmados nos logs/provisionamento travado. Fingerprint inclui o próprio módulo de identidade, CODEOWNERS, workflow, classificação, testes e política efetiva.

## Checks

| Check | GitHub |
| --- | --- |
| [CI / Frontend](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105104996) | success |
| [CI / Quality non-regression](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105241) | success |
| [CI / Python engineering](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105270) | success |
| [CI / Financial certification](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105287) | failure |
| [CI / Full Python diagnostic](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105291) | failure |
| [CI / mypy diagnostics](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105326) | failure |
| [CI / Ruff diagnostics](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105351) | failure |
| [CI / Runtime installation](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123105105660) | success |
| [CI / Engineering](https://github.com/tiagocaldironi/income-analytics/actions/runs/40770225788/job/123108017459) | success |

## Equivalência demonstrada

| Verificação | Local commitado e hospedado |
| --- | --- |
| Runtime | PASS |
| Python Engineering | 1069P / 0F / 0E / 0S |
| Infraestrutura/governança | 58P / 0F / 0E / 0S, incluídos em Engineering |
| Frontend | 31/31 |
| Quality non-regression | PASS; 803 existentes, zero adicionados/removidos |
| Ruff / mypy | 130 / 673 diagnósticos existentes, exits 1/1 |
| Python completo | 1069P / 15F / 9E / 5S |
| Financial | 73P / 15F / 9E / 0S; BLOCKED |
| Agregado | Engineering PASS; Financial/Release BLOCKED; Deployment NOT_IMPLEMENTED |

Comparação por Counter dos objetos completos de caso (classe/nome parametrizado/status) e diagnóstico (ferramenta/arquivo/linha/coluna/regra/mensagem), preservando multiplicidade. Inventários engineering/financial/full idênticos, incluindo seleção, classificação e resultado. Baseline de qualidade e seus digests/configuração/versões iguais. Comparação local commitado versus overlay PR5.2A também integralmente aprovada; o estado dirty mudou conforme esperado, não o conteúdo executado.

Os 58 casos de governança existem e passaram no runner; dez são do arquivo PR5.2 (nove controles incorporados e simulação adicional). Incluem falha Python temporária, Ruff/mypy reais em TEMP, mutação de baseline copiada, relatórios ausentes/falhos, políticas/versões inconsistentes, arquivo de teste ausente e tentativa de rotular financeiro com blockers como PASS. Nenhum exige PR52_ARCHIVE_ROOT ou credencial pessoal. SQLite temporário e guardas de credenciais/rede passaram. CERT_48 executado e failed; 22 históricos/identidade continuam no escopo financeiro/full. Sem novo skip ou supressão.

Resumo agregado hospedado idêntico ao local: consistent_identity=true, nenhum relatório obrigatório ausente. Nenhuma divergência observada. Artefatos sanitizados em nove ZIPs/16 arquivos, todos os digests de ZIP confrontados com API e arquivos internos identificados no JSON de comparação. Arquivo persistente local em %USERPROFILE%/.codex/evidence/income-analytics/pr52b/40770225788, sem logs brutos; não é backup imutável ou serviço externo.

## Digests dos artefatos

| Artefato | Digest ZIP fornecido pelo GitHub e verificado | Expiração GitHub |
| --- | --- | --- |
| gate-summary-b3f313265ef52768acd49120a70d902c23981869 | sha256:56723e7cc514b00c62da29c63f940008adb2e1db9e8eed17cec7eb55a2aa95a2 | 2026-11-11T21:21:00Z |
| governance-ruff-b3f313265ef52768acd49120a70d902c23981869 | sha256:4162317eb3a7b97b227411c3fae30a2c22b190429c9d6ff3f520cd3cff8e2b0e | 2026-11-11T21:15:23Z |
| governance-financial-b3f313265ef52768acd49120a70d902c23981869 | sha256:706fde7e5c7aeb21732e9a8d4d8a58c8e283778c9ddab7e8876ade0f23f0c154 | 2026-11-11T21:17:22Z |
| governance-node-b3f313265ef52768acd49120a70d902c23981869 | sha256:7ce4ccdc31867b0e1821083f8c29d1104ae4a74974e38804fde69609df5b6425 | 2026-11-11T21:15:10Z |
| governance-quality-b3f313265ef52768acd49120a70d902c23981869 | sha256:9847027274434e66a9aeead515fb85f8e0388d968707446e241457e2b7739999 | 2026-11-11T21:15:23Z |
| governance-runtime-b3f313265ef52768acd49120a70d902c23981869 | sha256:8afb99d89301d7dd2eaf0a6bf59cd5dbdcaf5252b633d2805191d4f2a1c04144 | 2026-11-11T21:15:32Z |
| governance-engineering-b3f313265ef52768acd49120a70d902c23981869 | sha256:bc0db5d0508cedc95541e6699a837e55d4c82bb1d18bd6e315571919063ebd5d | 2026-11-11T21:19:51Z |
| governance-mypy-b3f313265ef52768acd49120a70d902c23981869 | sha256:04d6facb834196d4df9cea652d953203050f078049361bd6c34bca6276d67fd0 | 2026-11-11T21:15:19Z |
| governance-python-b3f313265ef52768acd49120a70d902c23981869 | sha256:a2beae26e3332d7286d99575c24bdc00e4e24fd49a67f9b27aa4e2bc771a51bf | 2026-11-11T21:19:49Z |

Digests dos 16 arquivos extraídos, flags de equivalência e URLs dos checks em pr52b_gate_comparison.json. Não confundir digests dos ZIPs/arquivos com fingerprint de execução ou SHA Git.

## Recomendação

Publicação/validação hospedada concluídas; manter draft conforme instrução. É tecnicamente possível avançar para revisão e autorização separada da proteção nível 1; ainda falta aplicar/testar seus efeitos, especialmente PR obrigatório com zero reviews e caminho legítimo do mantenedor. CODEOWNERS não fornece revisão independente. Risco INDEPENDENT_REVIEW_NOT_AVAILABLE permanece.

Eventual integração exclusivamente de infraestrutura exige decisão explícita do mantenedor e aceite do risco/dívida, não um aprovador fictício. Certificação financeira, release e produção não estão autorizados: CERT_48, identidade, referências históricas/B3, Emulator/cloud, build reproduzível, homologação, backup/rollback continuam pendentes. Relatórios pós-run locais não foram commitados/pushados e não fazem parte do SHA testado.
