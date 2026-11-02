# PR5 — Fase 0: assessment de prontidão CI/CD

Data: 28/10/2026. Referência publicada: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`.

## Resumo executivo

**Prontidão geral: PARTIAL.** Há arquitetura executável, testes extensos, mecanismos de isolamento, migrations e evidências financeiras. **CI de engenharia e CD não estão implementados como esteira versionada.** É possível iniciar a construção incremental da CI, mas **a promoção certificada para produção está BLOCKED** pelo gate de hashes financeiros e pela falta de um caminho reproduzível de runtime/empacotamento/promoção.

Isso não afirma que a aplicação atual esteja inoperante, nem determina rollback de produção. Avalia a capacidade de repetir e comprovar uma release futura. Não se atribui percentual artificial de prontidão: as dimensões têm riscos e dependências diferentes.

## Matriz consolidada

| Dimensão | Estado | Evidência verificável e conclusão |
|---|---|---|
| Arquitetura e stack identificáveis | READY | `main.py`, `pyproject.toml`, camadas `domain/application/api/infrastructure`; ver [architecture_inventory.md](architecture_inventory.md). |
| Baseline única de trabalho | PARTIAL | Produção/remoto em `ca627ac`; checkout original em `27fcd4d` com alterações locais; desenvolvimento em `23b3303`. `git worktree list`, `git status --short`, API da branch. É preciso definir a fonte de release sem apagar trabalho local. |
| Governança de merge | MISSING | `develop protected:false`, proteção retorna `Branch not protected`, rulesets vazios. API do GitHub, consulta 28/10/2026. |
| CI automatizada de testes/lint/tipos | MISSING | Sem `.github/workflows` versionado; único workflow remoto é Dependency Graph. README não basta como comprovação. |
| Testes automatizados disponíveis | READY, existência | 139 arquivos `test_*.py`, 834 definições AST e 30 `.mjs`. Existência não equivale a execução aprovada; ver [testing_and_quality_gates.md](testing_and_quality_gates.md). |
| Estado atual da suíte completa | UNKNOWN | Não executada nesta fase por restrição a migrations/escritas; relatórios anteriores e verificações dirigidas não substituem run no SHA candidato. |
| Certificação de bytes do motor | BLOCKED | `test_shares_unit_020_frozen_engine`, `shares_unit_v1/manifest.json`: comparação estática reproduz divergências LF/CRLF e expectativa mista. |
| Evidências, goldens e rastreabilidade | PARTIAL | Manifests/fixtures versionados e gate histórico `INCOMPLETE`; parte das evidências fica em `tmp/`, `data/` e diretórios privados. |
| Dependências reproduzíveis | PARTIAL | Faixas abertas no `pyproject.toml`, sem lock/constraints com hashes; versões locais não garantem instalação limpa. |
| Runtime mínimo declarado | BLOCKED | Alembic usado por `initialize_database` no startup, mas declarado apenas no extra dev. |
| Build/empacotamento | PARTIAL | Backend setuptools declarado, sem build/inspeção de artefato nesta fase. Inclusão de estáticos/migrations/referências: UNKNOWN. |
| Containers/IaC | MISSING | Sem Dockerfile/Compose/IaC identificados. Lacuna de automação; não é obrigação de adotar containers. |
| Artefato imutável e promoção | MISSING | Produção executa fontes de worktree; sem registro de artefato/digest/promoção identificado. |
| Homologação independente | MISSING | GitHub Environments vazio; sem ambiente segregado reproduzível comprovado. Prévia local é PARTIAL, não substitui homologação completa. |
| CD homologação | MISSING | Nenhum workflow/deploy versionado identificado. |
| CD produção | MISSING | Processo atual manual com launcher externo. Não há pipeline/approval/rollback automatizado identificado. |
| Persistência e evolução de schema | PARTIAL | SQLite atual em revisão 0027; Alembic existe, modo local pode migrar no import, SaaS exige schema pronto. Falta orchestration de release. |
| Backup/restore | PARTIAL | Backups específicos e ensaios históricos existem; rotina integral, retenção, off-host e restore periódico sem comprovação. RPO/RTO não definidos. |
| Auth/ownership/CSRF | READY, mecanismos | `firebase_identity.py`, `saas_security.py`, testes de segurança. Não é uma nova certificação de infraestrutura externa. |
| Segredos e configuração por ambiente | PARTIAL | Credencial externa e ignore existentes, `.env.example` incompleto e launcher fora do Git. Rotação/IAM/ACL: UNKNOWN. |
| Segurança de cadeia de dependências | PARTIAL | Secret scanning/push protection ativos; Dependabot security updates desativado; SAST/SBOM/assinatura versionados não encontrados. |
| Observabilidade | PARTIAL | Logs/perf opcionais, health de provedores e `/health` simples; alertas, readiness abrangente e retenção não comprovados. |
| E2E real desktop/mobile | MISSING, automação | `.mjs` não usa browser real; screenshots e validações manuais são históricas. |

Os estados MISSING se referem ao repositório e às configurações consultadas; serviços externos não auditados não são declarados inexistentes. UNKNOWN deve ser resolvido por evidência, não convertido automaticamente em aprovação.

## Riscos priorizados

| ID | Prioridade | Risco e consequência | Evidência | Tratamento proposto, ainda não executado |
|---|---|---|---|---|
| R1 | Crítica | Gate financeiro não reproduzível permite falsa certificação ou release permanentemente vermelha | Hashes brutos e objetos Git do manifesto congelado; gate histórico CERT_48 | Reconciliação independente e aprovada, preservando evidências originais; nunca atualizar hash só para passar. |
| R2 | Alta | Merge sem checks/revisão obrigatórios | `develop` sem proteção/rulesets e sem CI de engenharia | Implantar CI, estabilizar nomes dos checks e então torná-los obrigatórios. |
| R3 | Alta | Instalação mínima não garante o runtime que faz startup | Alembic dev-only; import em `database.py` | Revisar grupos de dependência e provar instalação/build em ambiente limpo no próximo escopo. |
| R4 | Alta | Deploy pode usar código/estado diferente do testado | Worktrees divergentes, produção por fontes, `data/` externo | Baseline explícita e artefato imutável; inventário de estado e promoção do mesmo digest. |
| R5 | Alta | Migration/rollback pode afetar ledger sem recuperação demonstrada | Auto-upgrade local no import; backups heterogêneos; sem RPO/RTO | Separar etapa de migration e ensaiar backup/restore em cópia, com aprovação e escritores controlados. |
| R6 | Alta | CI ou artefatos expõem credenciais/dados pessoais | Repositório público, dados locais, appendices parcialmente rastreados | Testes sintéticos, secrets mínimos, uploads por allowlist, revisão de evidências. |
| R7 | Média/alta | CI verde com autenticação/UI insuficientemente testadas | Cloud/emulador opt-in; `.mjs` usa doubles | Matriz offline, emulador e E2E real segregadas; cloud controlada fora de PRs não confiáveis. |
| R8 | Média | Gargalos/timeout/falha de fornecedor passam despercebidos | Logs opcionais, `/health` simples, dependências externas e SQLite | Metas, readiness, alertas e benchmark pareado com fixtures, sem alterar regra financeira. |
| R9 | Média | Mudanças de dependências entram sem previsibilidade | Faixas abertas, sem lock; duplicidade de distribuições httpx/httpx2 | Revisão de dependências e lock reproduzível; manutenção programada e scan. |

## Bloqueadores versus decisões

### Impedimentos comprovados

1. **Certificação financeira integral:** as expectativas de SHA-256 não são satisfeitas de forma uniforme pelo checkout/objetos Git atuais. Ver tabela de hashes no documento de testes. Impede declarar release certificada, não impede criar uma CI que evidencie a falha.
2. **Runtime mínimo reproduzível:** a declaração de dependências não garante Alembic necessário ao startup. Impede considerar o empacotamento de runtime READY sem revisão e prova em ambiente limpo.
3. **Promoção automatizada auditável:** sem artefato candidato, ambiente de homologação e gates de promoção, CD de produção não tem pré-requisitos comprovados. É uma dependência de implementação, não motivo para adicionar infraestrutura arbitrária agora.

### Decisões pendentes, sem implementação nesta fase

- Confirmar que `develop` será a integração e definir se release usará tag/branch e qual método de merge/versionamento. Evidência atual: default develop, tags heterogêneas, métodos múltiplos permitidos.
- Escolher runners e alvo de execução. Manter Windows/Tailscale/SQLite é opção válida inicial; containers/cloud pública não são pressupostos.
- Aprovar política de reconciliação da certificação, revisão independente, RPO/RTO, janela de manutenção e rollback de dados.
- Definir homologação e identidade de teste segregadas; não usar credencial Admin produtiva em PRs.
- Definir orçamento de quotas, limites operacionais, licença de fornecedores e responsável por segredos/backup/alertas.

## Resultado esperado do PR5 de implementação

Sequência proposta em [implementation_roadmap.md](implementation_roadmap.md): primeiro baseline/gates; depois CI offline; build reproduzível; homologação isolada; e somente após evidências e aprovação, CD de produção. Segurança e observabilidade acompanham cada etapa. Não agrupar toda a transformação em um único deploy de risco.

**Critério para avançar desta Fase 0:** revisar este inventário e aprovar o escopo da próxima etapa. Nenhuma mudança de código, teste, hash, dependência, pipeline, ambiente ou produção foi realizada aqui. Os documentos permanecem sem commit automático.
