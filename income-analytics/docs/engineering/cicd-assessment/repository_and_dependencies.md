# PR5 — Fase 0: repositório, dependências e versionamento

Data: 28/10/2026. Referência publicada: `ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Escopo, classificação e distinção dos checkouts em [architecture_inventory.md](architecture_inventory.md). Nenhuma branch, configuração, dependência ou commit foi alterado.

## Repositório e governança

| Dimensão | Estado | Evidência verificada |
|---|---|---|
| Repositório remoto | READY | `tiagocaldironi/income-analytics`, visibilidade pública, default branch `develop`. Metadados consultados pelo conector GitHub e `gh api repos/tiagocaldironi/income-analytics`. |
| Layout Git | READY | Raiz Git local `C:/Projetos`, aplicação no subdiretório `income-analytics/`; `git ls-tree --full-tree origin/develop`. Workflows devem ficar em `.github/workflows/` da raiz Git, não dentro da aplicação. |
| Branches de trabalho | PARTIAL | `develop` e muitas branches `codex/*`, incluindo `codex/history-query-performance`, `codex/request-timeout-refresh-fix` e `codex/b3-lending-reconciliation`. Lista remota consultada com `gh api .../branches --paginate`; nomes não comprovam aprovação ou merge. |
| Proteção de `develop` | MISSING | API retorna `protected:false`; endpoint `branches/develop/protection` retorna 404 com mensagem explícita `Branch not protected`. |
| Rulesets | MISSING | `gh api repos/tiagocaldironi/income-analytics/rulesets`: lista vazia. Nenhuma regra de revisão/check obrigatório comprovada. |
| Política obrigatória de revisão | MISSING | Não há proteção ou ruleset impondo revisão/checks; nenhum CODEOWNERS versionado encontrado. O uso recente de PRs é uma prática, não um gate obrigatório. |
| Estratégias de merge | PARTIAL | GitHub permite merge commit, squash e rebase; auto-merge desativado e exclusão de branch após merge desativada. Não há método único imposto. |
| Versão de produto e tags | PARTIAL | `pyproject.toml` e `FastAPI(...)` declaram `0.1.0`; existem tags `v0.1.0` a `v0.4.0` e tags `income-v2-*`/`income-simulation-v2-*`. Não há automação de release/versionamento identificada. |
| Licença | PARTIAL | Arquivo `LICENSE` na raiz Git tem zero bytes; não constitui uma licença definida para redistribuição. Não bloqueia escrever CI, mas demanda decisão antes de distribuir artefatos. |

### Workflows realmente existentes

**MISSING — CI de engenharia versionada.** `git ls-files` e árvore remota examinada não contêm `.github/workflows/*.yml` ou `.yaml`. A referência a “CI” no README não comprova pipeline.

**PARTIAL — automação do GitHub:** `GET .../actions/workflows` lista somente **Dependency Graph**, caminho dinâmico `dynamic/dependabot/update-graph`, ativo. `GET .../actions/runs?per_page=5` retorna um run histórico bem-sucedido de Graph Update, de 14/07/2026. Esse workflow não executa os testes/lint/certificação do projeto e não equivale a CI/CD.

**MISSING — ambientes de release no GitHub:** `GET .../environments` retorna `total_count:0`. Não há evidência de aprovações por Environment, proteção de deploy ou secrets segregados por esses ambientes. Secrets de repositório e seus valores não foram consultados.

### Inventário de branches e tags

A consulta remota paginada identificou `develop` e as seguintes branches `codex/*`. Todas retornaram `protected:false`. Lista pontual de 28/10/2026, sem criar, remover ou atualizar refs:

```text
codex/asset-history-ux
codex/b3-lending-reconciliation
codex/compact-holding-identities
codex/compact-negative-result
codex/compact-positive-result
codex/compact-understand-date-filter
codex/contextual-onboarding-v2
codex/delete-imported-operations
codex/design-system-v2
codex/fast-operation-history
codex/financial-projection-foundation
codex/firebase-account-onboarding
codex/firebase-auth-authorization
codex/fix-per-class-asset-allocation
codex/fix-performance-history-and-benchmarks
codex/fix-price-timestamp-read
codex/global-contribution-allocation
codex/history-query-performance
codex/holdings-v2
codex/identity-tools-polish
codex/income-starter-draft-catalog-v1
codex/income-starter-v2-research-governance
codex/income-starter-v3-guided-journey
codex/interactive-composition
codex/local-multiportfolio-v2
codex/monthly-income-date-labels
codex/multiportfolio-v2-certification-closure
codex/multitenancy-readiness-audit-v0
codex/performance-category-benchmark-filters
codex/performance-financial-integrity
codex/portfolio-composition-pie
codex/portfolio-domain-foundation-v1
codex/portfolio-understand-redesign-v1
codex/portfolio-v2-alignment
codex/portfolio-v2-guidance
codex/portfolio-v2-holdings
codex/portfolio-v2-overview
codex/portfolio-v2-overview-completion
codex/request-timeout-refresh-fix
codex/return-direction-indicator
codex/return-value-typography
codex/saas-multiuser-foundations
codex/sidebar-scrollbar-polish
codex/simulation-executable-v2
codex/sticky-holdings-identity
codex/theme-settings-polish
codex/understand-period-compact-v1
```

Refs locais adicionais incluem `codex/income-starter-guided-strategies`, `codex/income-starter-v4-allocation-proposals`, `codex/resolve-v1-merge` e a ref `origin/pr/11`; não foram tratadas como branches remotas atualmente confirmadas. `git worktree list` identificou os checkouts original, de desenvolvimento, de produção, de auth e dois baselines detached; sua existência não significa que todos executem serviços.

Tags disponíveis localmente, obtidas por `git tag -l`: `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.4.0`, `income-v2-2026-10-24`, `income-v2-2026-10-24-consolidated`, `income-simulation-v2-2026-10-25`. Não foi realizada publicação de tag nem inferida assinatura ou política SemVer obrigatória a partir dos nomes.

Comandos somente de leitura utilizados para reproduzir essas constatações:

```powershell
git status --short
git branch -a
git tag -l
git worktree list
git ls-tree --full-tree origin/develop
gh api repos/tiagocaldironi/income-analytics/actions/workflows
gh api repos/tiagocaldironi/income-analytics/branches --paginate
gh api repos/tiagocaldironi/income-analytics/branches/develop/protection
gh api repos/tiagocaldironi/income-analytics/rulesets
gh api repos/tiagocaldironi/income-analytics/environments
```

## Stack declarada e versões observadas

As versões instaladas abaixo foram consultadas por `importlib.metadata.version`, sem importação do app. São o estado do interpretador Python 3.14 local usado na avaliação, não um lockfile, garantia de ambiente limpo ou inventário transitivo completo. O launcher produtivo também seleciona Python 3.14, mas não isola uma venv própria comprovada.

| Componente | Declaração em `pyproject.toml` | Versão local observada |
|---|---|---|
| Python | `>=3.14` | 3.14.7 |
| FastAPI | `>=0.116` | 0.141.1 |
| Uvicorn | `[standard]>=0.35` | 0.52.4 |
| SQLAlchemy | `>=2.0` | 2.0.52 |
| Pydantic | `>=2.11` | 2.13.5 |
| Firebase Admin | `>=7.7,<8` | 7.7.0 |
| pytest, extra `dev` | `>=8.4` | 9.1.1 |
| pytest-cov, extra `dev` | `>=6.2` | 7.1.0 |
| Ruff, extra `dev` | `>=0.12` | 0.16.6 |
| mypy, extra `dev` | `>=1.17` | 2.3.1 |
| Alembic, extra `dev` | `>=1.19` | 1.19.2 |
| httpx2, extra `dev` | `>=2.14` | 2.14.0 |
| httpx | Não declarado diretamente | 0.28.1 |
| setuptools / wheel | Build backend: `setuptools>=80`, `wheel` | Não encontrados como distribuições nesse interpretador |
| `build` | Não declarado | Não encontrado |
| SQLite | Biblioteca do Python | 3.50.4 |
| Node.js | Sem faixa/arquivo de versão identificado | v24.19.0, para testes `.mjs` |
| ECharts | Arquivo vendorizado e loader | 6.1.0 |
| Firebase SDK web | URLs em `js/auth-client.js` | 13.1.0 |

**PARTIAL — dependências reproduzíveis:** há declaração PEP 621/517, mas não foram encontrados lockfile Python, constraints congeladas ou hashes de dependências. A maioria das faixas permite upgrades sem revisão de versão exata. Node não tem `package.json`, lockfile ou task runner no projeto examinado; os testes são scripts nativos.

**BLOCKED — instalação mínima de runtime conforme declaração atual:** `infrastructure/database.py::initialize_database` importa Alembic e é chamado em `main.py` ao carregar o app. Porém Alembic está apenas no extra `dev`. Uma instalação que use apenas as dependências runtime declaradas não tem Alembic garantido. Não foi instalado nada para reproduzir essa falha; o impedimento é comprovado pela relação estática entre import e declaração.

**PARTIAL — ferramentas e imports adicionais:** testes de Firebase usam `requests`; TestClient usa a integração `httpx`; scripts de evidência PDF usam `pypdf`. Nem todos estão declarados diretamente para seus grupos de uso. Não se presumiu que `httpx2` substitua `httpx`: os dois nomes de distribuição aparecem instalados. A procedência, necessidade e compatibilidade dessa escolha devem ser revisadas antes do lock. Dependências transitivas disponíveis na máquina não substituem uma instalação limpa comprovada.

## Build e distribuição

| Dimensão | Estado | Evidência / limite |
|---|---|---|
| Backend de build Python | PARTIAL | `[build-system]` usa `setuptools.build_meta`, packages sob `src/`. Não foi executado build nem instalado backend. |
| Dados de pacote | UNKNOWN | Sem seção explícita de package-data ou MANIFEST.in identificada. Inclusão efetiva de HTML/CSS/JS/SVG, migrations e dados necessários no wheel não foi comprovada. |
| Build frontend | MISSING | Não há bundler ou comando npm identificado. O frontend atual funciona como arquivos estáticos, portanto bundler não é pré-requisito automático. |
| Docker/Compose | MISSING | Sem Dockerfile, `.dockerignore` ou Compose versionados na árvore examinada. Capacidade do host de executar Docker não foi testada. |
| Artefato imutável e registro | MISSING | Nenhum fluxo de publicação de wheel/imagem ou promoção por digest encontrado. Execução atual usa checkout. |
| SBOM, assinatura e atestação | MISSING | Não há geração/validação versionada identificada. Dependency Graph não comprova SBOM de release. |

Os scripts `build_magic_formula_*` e `build_analytics_engine_artifacts.py` geram snapshots/evidências de negócio ou profiling. Eles não são um empacotador do aplicativo nem devem ser executados como um build genérico.

## Git, arquivos e reprodutibilidade

**BLOCKED — hashes financeiros dependentes de checkout:** `.editorconfig` pede LF; `core.autocrlf=true` foi observado localmente; não há `.gitattributes` global versionado. Existe uma regra localizada em `tests/fixtures/cvm/phase2_v1/.gitattributes`, insuficiente para os arquivos congelados Python. O manifesto inclui expectativas de bytes diferentes entre arquivos, detalhadas em [testing_and_quality_gates.md](testing_and_quality_gates.md). Não se recomenda alterar hashes ou “corrigir” automaticamente o manifesto nesta fase.

**PARTIAL — dados e credenciais fora do Git:** `.gitignore` exclui `.env`, `*.db`, `data/`, `tmp/`, backups e padrões de service accounts. Arquivos já rastreados, como parte de `docs/appendices/`, continuam rastreados apesar da regra de ignore; portanto um futuro upload de artefatos deve usar allowlist e revisão de dados. Nenhum nome de service account rastreado foi encontrado; isso não é uma varredura do histórico por secrets.

**PARTIAL — documentação operacional:** README contém execução LAN e roadmap antigo. Guias de ambiente, Git e testes estão vazios na referência. Existem documentos de segurança e releases, mas há divergências entre versões históricas e ambiente atual. O roadmap propõe consolidar instruções executáveis e verificáveis sem tratar planos antigos como implementação.
