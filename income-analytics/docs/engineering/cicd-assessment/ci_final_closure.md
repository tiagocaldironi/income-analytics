# Encerramento definitivo do CI — Income Analytics

**CI_IMPLEMENTED_AND_PROTECTED**. Evidência operacional registrada em 2026-10-28T22:06:55.559984+00:00. CI integrado, proteção ativa e validação pós-merge concluída. CD não implementado; certificação/release financeiros continuam bloqueados. INDEPENDENT_REVIEW_NOT_AVAILABLE permanece como risco provisório, sem aprovação fictícia.

## GitHub e identidade

- [PR #48](https://github.com/tiagocaldironi/income-analytics/pull/48): integrado pelo mantenedor em 28/10/2026, método merge, preservando commits. Nenhuma review artificial submetida; zero aprovações obrigatórias.
- SHA de develop na conclusão operacional da integração CI: **e6a30902f9186af27e7b288305c0bd6918ee526a**.
- [Run pós-merge 40775898058](https://github.com/tiagocaldironi/income-analytics/actions/runs/40775898058): evento **push**, ref develop, checkout/event_sha iguais ao SHA acima; pr_head_sha vazio, corretamente, pois não é evento de PR.
- Fingerprint v2: **c049a052e93d37b54b80841e538dd694029975e5d27a325e59a3d1603ad1df7f**.
- Identidade da política: **73db10df451889f01ab20a25a17090f0e88e0fed7aeb26551630ca83fda95e48**. Relatórios schema 3; oito checks com worktree_dirty=false, identidades consistentes e árvore correta.
- A publicação deste relatório é posterior e exclusivamente documental. O SHA que contém o próprio documento não é autorreferenciado como se já tivesse sido testado; consultar histórico/HEAD e o novo run da publicação. O relatório operacional acima é do merge de CI, não uma atribuição retroativa à documentação.

## Controles realmente ativos

Ruleset **26078982 — Income CI - protected develop**, enforcement=active, alvo final somente refs/heads/develop, bypass_actors=[]; [regras do repositório](https://github.com/tiagocaldironi/income-analytics/rules). Confirmados por GET rulesets/26078982 e rules/branches/develop; protected=true.

| Controle | Estado efetivo |
| --- | --- |
| Pull Request | Obrigatório; regra pull_request ativa |
| Check obrigatório | **CI / Engineering**, fonte GitHub Actions **integration_id=15368** |
| Atualização com base | strict_required_status_checks_policy=true |
| Conversas | required_review_thread_resolution=true |
| Aprovações humanas | Zero, provisoriamente |
| CODEOWNERS review | false; arquivo é declaração de responsabilidade |
| Último push por outra pessoa | false |
| Bypass | Nenhum ator configurado, incluindo administrador |
| Force-push | Bloqueado por non_fast_forward |
| Exclusão | Bloqueada por deletion |
| Auto-merge / merge queue | Não ativados; auto-merge do repositório permanece desabilitado |

Esta é uma **regra efetiva**, distinta dos JSONs históricos de proposta. Não aplicar os payloads antigos de PR5.2 ao mantenedor único. A regra atual foi escolhida e ativada dentro da autorização de encerramento, sem desabilitar controles para integrar.

## Enforcement remoto comprovado

1. **Push direto rejeitado:** um commit já aprovado em Engineering (405b29d) foi enviado por fast-forward normal a uma branch de controle isolada, inicialmente em ca627ac. O mesmo ruleset ativo de develop também cobria essa branch. GitHub rejeitou com **GH013 — Changes must be made through a pull request**; alvo permaneceu intacto. A rejeição ocorreu apesar de o check obrigatório estar aprovado, comprovando a exigência de PR. Não se fez push direto a develop.
2. **Merge com Engineering falho rejeitado:** [PR temporário #49](https://github.com/tiagocaldironi/income-analytics/pull/49) adicionou somente um teste deliberadamente falho, nunca destinado a develop. [Run 40774775041](https://github.com/tiagocaldironi/income-analytics/actions/runs/40774775041) executou 1069 testes aprovados e uma falha: test_controlled_ci_enforcement_failure; o agregado CI / Engineering foi failure. PR foi retargetado para branch isolada sob a mesma regra, com zero reviews exigidas e sem draft. A tentativa real de merge recebeu **HTTP 405 — Required status check "CI / Engineering" is failing**. Nenhum merge do teste ocorreu.
3. **Fluxo legítimo comprovado:** #48 saiu de draft, seu head 405b29d foi conferido com Engineering success da app 15368 e foi integrado por API normal, sob o ruleset ativo, sem bypass nem review independente fictícia. Os diagnósticos não obrigatórios continuaram reprovados e não impediram a integração de infraestrutura, conforme política autorizada.
4. **Force-push/exclusão:** comprovados pela leitura autoritativa das regras efetivas non_fast_forward/deletion, com ausência de bypass e protected=true. **Não foram feitas tentativas destrutivas em develop.** Essa é a limitação deliberada do teste, conforme especificação.
5. PR #49 foi fechado sem merge; três refs remotas temporárias foram removidas depois de retirar apenas seus alvos temporários do ruleset. A proteção de develop manteve exatamente as mesmas regras durante a limpeza. O commit do teste negativo não é ancestral de develop.

A prova negativa foi feita em branches isoladas sob o **mesmo ID e parâmetros de ruleset**, não em simulação local nem fabricando status. O positivo foi o próprio #48. Evidências estruturadas, metadados e digests dos artefatos estão em ci_final_evidence.json. Não se afirma que uma tentativa destrutiva foi realizada quando só houve inspeção de regra.

## Resultado pós-merge

| Verificação | Resultado |
| --- | --- |
| **CI / Engineering** | **PASS hospedado** |
| Python Engineering | **1069P / 0F / 0E / 0S** |
| Infraestrutura/governança | **58 testes aprovados**, ativos e incluídos em Engineering |
| Frontend | **31/31** |
| Runtime | PASS, instalação runtime mínima |
| Quality non-regression | PASS; 803 existentes, zero novos/removidos |
| Ruff | 130 diagnósticos conhecidos, exit=1 |
| mypy | 673 erros conhecidos, exit=1 |
| Python completo | 1069P / 15F / 9E / 5S |
| Financial Certification | **BLOCKED**, 73P / 15F / 9E / 0S |
| Release Readiness | **BLOCKED** |
| Deployment Authorization | **NOT_IMPLEMENTED**, deployment_authorized=false |

Workflow geral permanece **failure**, porque os quatro jobs de dívida/certificação reportam seus resultados reais. Não foi usado continue-on-error, skip novo, compensação por contagem, refresh automático de baseline ou waiver financeiro. O único check obrigatório é Engineering; runtime/Python/frontend/qualidade compõem esse gate e devem passar.

Comparação com o candidato hospedado anterior e com a baseline local commitada: mesmos casos/status, inventários e diagnósticos por identidade/multiplicidade; mesma baseline de qualidade, versões e política. CERT_48, identidade e 22 históricos continuam executados e não aprovados. Os cinco skips externos já existentes permanecem visíveis. Nenhuma regressão de cálculo ou engenharia foi introduzida.

## Segurança e produção

Workflow apenas em PR para develop e push em develop, token contents:read, Actions por SHA, checkout sem credenciais persistidas. Testes executam offline, com SQLite TEMP, jobs externos desativados e ambiente sem credenciais produtivas herdadas. Runtime utiliza migrations somente em SQLite descartável. Artefatos limitados a JSON/JUnit/cobertura/inventário sanitizados; sem bancos, logs brutos, snapshots privados ou payloads de carteira.

Nenhum deploy ou migration produtiva foi executado. Repositório sem Pages, hooks de push ou deployments cadastrados na inspeção; pipeline não contém CD. Checkout produtivo permaneceu no HEAD ca627ac72f110d0f4d62faaa9c51a08eaed54965: status e **897 hashes de arquivos versionados** idênticos antes/depois. Não foi alterado launcher/processo produtivo nem acessado banco produtivo. Operações Git ocorreram em worktree isolado; anteriores foram preservados.

A única correção de src/ no PR #48 era o erro de classe usado na rejeição de schema CVM, previamente aprovado; não houve alteração de fórmulas, contratos, fixtures ou hashes financeiros congelados. A instalação de CI não publicou uma nova versão produtiva do sistema.

## Manutenção e recuperação

- Abrir PR para toda alteração; conferir CI / Engineering do head atual, app 15368 e fingerprint/política, resolver conversas e manter branch atualizada. Integrar apenas por método permitido; nenhuma exceção silenciosa.
- Mudanças em CI/workflow/classificação/baseline exigem revisão técnica explícita do mantenedor e registro de risco enquanto INDEPENDENT_REVIEW_NOT_AVAILABLE. O proprietário pode tecnicamente editar regras; isso não é uma raiz de confiança independente. Não tratar CODEOWNERS como review humana.
- Quando houver segundo colaborador real e elegível, validar acesso/disponibilidade/ownership e evoluir separadamente para revisão independente, owners e invalidação de aprovações. Não conceder acesso ou criar aprovador automaticamente.
- Se regra bloquear fluxo legítimo, capturar configuração por GET, identificar o campo exato e corrigir só a divergência autorizada. Revalidar negativos e caminho legítimo. Nunca contornar Engineering falho nem desativar toda a proteção como solução permanente. Preservar snapshot anterior, justificativa e evidência de restauração.
- Usar ruleset 26078982 como fonte de configuração ativa; os JSONs de proposta anteriores são históricos. Manter as evidências sanitizadas antes da expiração dos artefatos do GitHub; cópias locais não são backup imutável.

## Fora do escopo e encerramento

CI está operacional, integrado e protegido. Permanecem deliberadamente fora desta execução: build/artefato reproduzível, CD, homologação, backup/rollback de entrega e inventário adicional de segurança. Certificação financeira depende da reconciliação independente de CERT_48, identidade, referências históricas e permissões B3; Emulator/cloud têm validação separada. Nada disso foi iniciado para encerrar o CI, nem autoriza promoção produtiva.

Relatórios PR5.1E, PR5.2 e PR5.2A/B foram preservados como histórico. Este é o documento principal de encerramento, sem nova sequência de fases.
