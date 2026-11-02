# PR5.2B — Revisão de segurança e proteção técnica

Registro UTC 2026-10-28T21:22:38.291130+00:00. Escopo: candidato publicado 405b29d7c9bbd98bb373c4827b702ecaada3fc86, run 40770225788, checkout b3f313265ef52768acd49120a70d902c23981869. Sem correção adicional remota. Estado: revisão do escopo PASS; não é auditoria de segurança integral do produto.

## Evidências de execução

Workflow publicado conferido byte a byte contra blob Git local, assim como CODEOWNERS, pipeline_identity.py e bootstrap JSON. YAML: contents:read, Actions por SHA de 40 caracteres, checkout persist-credentials:false em todos os jobs, sem pull_request_target, secrets referenciados, continue-on-error, job de deploy ou ambiente produtivo. Logs efetivos mostram Contents:read/Metadata:read e instalação com hashes/locks e pip check. Não há auto-approve; PR draft e auto_merge=null, repositório allow_auto_merge=false.

ci/run.py:isolated_environment mantém somente allowlist de variáveis do sistema, redefine HOME/USERPROFILE/TEMP/cache/SQLite, jobs externos desativados, credencial Google inexistente e configurações cloud isoladas. Python/Node executam produto offline por guardas; dependências são provisionadas via PyPI controlado antes dos testes. Testes de isolamento e SQLite passaram no runner. Migration do check runtime é somente em SQLite descartável; nenhuma migration produtiva executada.

Os testes PR5.2 usam Git versionado e dados TEMP de unidade, sem arquivo pessoal/arquivo E. Arquivamento histórico é auditoria separada e manual; nenhuma fixture foi fabricada como resultado remoto. Não houve alteração de cálculos, fixtures/manifests/hashes financeiros, locks ou baseline de qualidade nesta publicação.

## Artefatos e dados

Allowlist efetiva: result.json, inventory.json, JUnit de engineering/financial/python, coverage.xml e gate-summary.json. Nove artefatos/16 arquivos inspecionados; ZIPs sem caminho fora da allowlist, bancos, snapshots, credenciais ou logs. JSON parseado e XML conferido sem conteúdo de failure/error/captured stdout/stderr. Cobertura contém metadados de código, não payloads de carteira. Digests ZIP verificam integridade frente à API; hashes dos arquivos extraídos estão em pr52b_gate_comparison.json.

Somente esses dados sanitizados e metadados foram preservados no arquivo local do usuário. Logs de provisionamento usados na revisão permanecem em TEMP fora do diretório arquivado e não entram em Git. Nenhum serviço/repositório externo foi criado. Destino herda os controles locais do perfil; não é armazenamento imutável/backup. Relatórios versionados existentes usam placeholder USERPROFILE, sem divulgar caminho privado absoluto.

## Governança administrativa — leitura e simulação

- develop ainda em ca627ac72f110d0f4d62faaa9c51a08eaed54965, protected=false; rulesets=[] após o run.
- Único colaborador retornado: tiagocaldironi, admin/write. Nenhum acesso concedido; INDEPENDENT_REVIEW_NOT_AVAILABLE.
- API codeowners/errors da branch publicada: errors=[]; arquivo está na head do PR, não integrado à base. Não gera proteção por si só nem review independente.
- Proposta atual exige zero reviews, require_code_owner_reviews=false e require_last_push_approval=false, com PR/check/conversas e proibições técnicas. Payload não aplicado; nível 2 exige futuro colaborador independente real.
- Simulação aprovada; requerer confirmação remota autorizada de PR-only com zero reviews e ausência de bypass, incluindo administrador. enforce_admins=true é proposta, não estado atual.
- Nenhuma alteração de proteção, ruleset, colaboradores, merge queue, auto-merge ou deploy. A autorização desta etapa foi somente para commits/push/descritivo do PR.

## Riscos e recomendação

O proprietário pode alterar regras/workflow/baseline; identidade detecta diferença, não aprova conteúdo. Sem revisão independente, esse risco persiste. Não interpretar check verde de workflow alterável como raiz de confiança independente. Nenhuma condição desconhecida foi apresentada como proteção ativa.

Recomenda-se a próxima etapa de aceite e eventual autorização administrativa do nível 1, com exportação da configuração anterior, teste não destrutivo do caminho legítimo/negativas e recuperação documentada em ci_single_maintainer_governance.md. Não ativar regras automaticamente nem exigir review do próprio autor. A proposta futura antiga do PR5.2 não deve ser aplicada por engano ao bootstrap. PR continua draft; merge/release/produção exigem decisões distintas.

Quatro gates: Engineering PASS hospedado, Financial BLOCKED, Release BLOCKED, Deployment NOT_IMPLEMENTED. Este relatório e os demais três são posteriores ao run e ficam locais, sem push adicional ou atribuição retroativa de teste.
