# PR5.2A — Governança provisória de mantenedor único

Data: 28/10/2026. Risco declarado: **INDEPENDENT_REVIEW_NOT_AVAILABLE**. Este modelo substitui, para o bootstrap, a exigência operacional inviável de uma review independente já no primeiro PR. Não substitui os registros históricos PR5.2, não inventa aprovação e não ativa proteção.

## Estado verificado

PR #48 aberto/draft, head codex/ci-offline-pr51 em a2f6d64bb55210bb7514c2f172efa37116eeec6e; develop permanece ca627ac72f110d0f4d62faaa9c51a08eaed54965. Único colaborador retornado: tiagocaldironi, admin/write, autor do PR. Repositório público, token com admin=true; develop protected=false, rulesets vazios e auto-merge desabilitado. Nenhum acesso novo concedido.

Run remoto E 40760146814: Engineering success; workflow geral failure por diagnósticos e certificação conhecidos. Esse run não valida PR5.2A. SHAs, identidade nova e resultados locais estão em ci_pr52a_validation.md.

## Nível 1 — Controles técnicos candidatos

- PR obrigatório como registro de cada integração, com histórico de escopo, SHA, testes e decisão do mantenedor.
- CI / Engineering, da app GitHub Actions 15368, obrigatório; branch atualizada e conversas resolvidas.
- Sem force-push, exclusão de develop, auto-merge não autorizado ou bypass permanente; aplicar a administradores quando suportado.
- Zero aprovações requeridas, require_code_owner_reviews=false e require_last_push_approval=false. Não basta zerar a contagem mantendo essas duas exigências: elas poderiam continuar bloqueando o único mantenedor.
- CODEOWNERS declara responsabilidade por workflows, CI, políticas, classificação e baseline. Não é review independente e, sem regra de proteção, não impede nenhuma alteração. Seu conteúdo precisa estar na base para orientar reviews futuras.

O mantenedor poderá decidir uma integração de infraestrutura sem revisão humana independente depois de satisfeitos os controles técnicos e obtidas as autorizações necessárias. Essa decisão deve registrar explicitamente o risco acima. PASS de CI não é aceite financeiro, aprovação independente ou autorização de release. O proprietário mantém capacidade administrativa de editar regras; isso é risco residual, não garantia de inviolabilidade.

## Nível 2 — Revisão independente futura

Somente após verificar outro colaborador real com write, disponibilidade e ownership nos caminhos críticos: exigir uma review independente, owners, invalidação de aprovações e aprovação do último push por outra pessoa. Alterações em workflows, runner, baseline, classificação, segurança e contratos financeiros exigem revisão específica. Nenhum convite, owner fictício ou nível 2 é ativado automaticamente.

Os documentos ci_branch_protection_plan.md e ci_branch_protection_proposal.json copiados de PR5.2 descrevem o nível futuro e seu bloqueio anterior. Para o bootstrap atual, usar exclusivamente ci_branch_protection_bootstrap.json; não aplicar o payload antigo que exige um aprovador.

## Semântica, viabilidade e limitações

ci_branch_protection_bootstrap.json é envelope de proposta; apenas proposed_branch_protection_payload descreve uma eventual escrita em branches/develop/protection. O objeto required_pull_request_reviews permanece presente, com contagem zero e exigências de owners/último push desativadas. strict=true exige CI de árvore atualizada, enforce_admins=true evita a exceção administrativa padrão. restrictions=null não é uma lista de bypass concedida; o repositório pessoal não oferece o mesmo modelo de equipes/restrições de organização.

O campo plan da API não é comprovável; suporte básico deriva do repositório ser público. API de leitura confirma administração disponível, ausência atual de regras e check CI / Engineering recente da app correta. Não foi feita chamada de escrita para testar o payload.

Simulação local verifica caminho legítimo de PR sem review, reprovação de check, branch desatualizada, conversa pendente, push direto, force-push e exclusão segundo a política proposta. Isso não prova enforcement remoto. Antes da ativação, confirmar em teste autorizado que a combinação concreta realmente exige PR com zero reviews e que não impede o único mantenedor de integrar PR legítimo. Se o comportamento da proteção clássica diferir, interromper; avaliar ruleset com regra explícita pull_request em mudança autorizada, sem conceder bypass como atalho.

Fontes consultadas em 28/10/2026: [REST branch protection](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection) admite contagem zero para não exigir reviewers; [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) documenta suporte público e controles administrativos; [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) distingue exigir PR de exigir sua aprovação. Nenhuma fonte substitui o teste de efetividade futuro na configuração real.

## Fronteira de confiança e identidade

Fingerprint de execução versão 2 e governance_policy_sha256 cobrem CODEOWNERS, workflow, política/runner/plugin, classificação, testes de governança, baseline e bootstrap JSON. Fonte em ci/pipeline_identity.py. Mudanças nesses arquivos alteram as duas identidades; ausência de arquivo obrigatório é fatal. Relatórios schema 3 registram versão, SHA de checkout, fingerprint e identidade da política; agregação rejeita versões/políticas misturadas.

Identidade detecta diferença, não aprova conteúdo. Um mantenedor capaz de modificar workflow, testes e política pode alterar seus próprios critérios. Sem revisão independente, esse risco persiste e deve ser aceito explicitamente em cada integração crítica. Nenhum manifest/hash financeiro congelado foi atualizado. O fingerprint E não é reutilizado para esta árvore.

## Publicação e ativação em etapas separadas

1. Revisar o diff local e aceitar provisoriamente o risco de mantenedor único, os quatro gates e a dívida conhecida. Autorizar especificamente commits rastreáveis e push fast-forward para a branch do PR, preservando origens. Nenhuma autorização de publicação foi inferida nesta execução.
2. Reconsultar remoto antes de publicar; interromper se head/base divergirem. Publicar somente escopo aprovado, manter draft e exigir execução hospedada do novo SHA. Comparar identidade, testes e diagnósticos com evidências locais; não apresentar run E como validação nova.
3. Após Engineering hospedado e revisão dos efeitos, solicitar autorização administrativa específica. Exportar configuração vigente e aprovar payload/recuperação antes de qualquer aplicação.
4. Aplicar somente regras autorizadas; confirmar campos por GET. Testar bloqueios em PR/branch controlados e o caminho legítimo, sem ataques ou operações destrutivas em develop. Não testar force-push ou exclusão reais na branch alvo. Não ativar merge queue sem suporte a merge_group.
5. Integração de #48 exige decisão própria do mantenedor e registro de risco; esta fase não faz merge. Certificação, release e produção continuam independentes e bloqueados.

## Recuperação administrativa

Sem bypass permanente. Se uma futura regra impedir operação legítima, registrar PR/SHA, erro, controle e impacto; conferir identidade/checks antes de considerar exceção. O mantenedor autoriza explicitamente qualquer ajuste temporário, escopo e prazo. Preservar configuração anterior, restaurar controles e verificar por GET e testes de efetividade. Não mascarar teste falho nem modificar baseline/finanças para recuperar CI. Não automatizar alteração emergencial das regras nesta entrega.

## Evidências históricas e testes herméticos

Arquivo E permanece local e manual, com nove ZIPs e 16 arquivos sanitizados/digests descritos em ci_evidence_archive_manifest.json. Não é dependência dos testes automáticos. Conferir esses hashes e o resumo real no arquivo quando auditar o run E; nunca fabricar fixture com aparência de resultado hospedado.

Dois controles PR5.2 foram tornados herméticos: mutação compara baseline com blob versionado HEAD e altera somente cópia TEMP; bloqueio financeiro usa entradas sintéticas explicitamente unitárias para tentar rotular um relatório com blockers como PASS. Essa unidade testa o comparador, não afirma certificação. Financial/full continuam executando CERT_48, identidade e 22 casos históricos reais, com seus resultados não aprovados.
