# PR5 — Fase 0: inventário de arquitetura

Data: 28/10/2026. Natureza: diagnóstico, sem implementação.

## Referência e limites

A referência publicada é `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`, confirmada pela API do GitHub e pelo HEAD do worktree de produção. A leitura de código foi feita principalmente no worktree `C:/Users/tiago/.codex/worktrees/portfolio-design-v2/Projetos/income-analytics`, em `23b3303a152a3511031c1dd4290fcc81018a8be3`, commit incorporado pelo merge `ca627ac`. A árvore de conteúdo desses dois commits deve ser usada como referência, não os relatórios antigos isoladamente.

O diretório solicitado, `C:/Projetos/income-analytics`, está na branch `codex/income-starter-guided-strategies`, HEAD `27fcd4d`, com alterações locais prévias. Essa branch tem diferenças relevantes em relação à referência: comparação de commits indica 175 arquivos alterados. Nada foi sincronizado, descartado ou mesclado. Estes seis documentos são as únicas novas alterações desta fase, gravadas no diretório solicitado.

Os caminhos de evidência abaixo são relativos à raiz da aplicação na referência publicada. **A raiz Git é o diretório pai**: no GitHub, o código fica em `income-analytics/`; o checkout do Actions precisará entrar nesse subdiretório. Comandos como `git ls-tree --full-tree origin/develop` e `git rev-parse --show-prefix` comprovam a distinção.

Classificações: **READY** = capacidade comprovada no escopo indicado; **PARTIAL** = existe, com lacunas; **MISSING** = ausência identificada; **BLOCKED** = impedimento concreto; **UNKNOWN** = sem comprovação suficiente. READY não equivale à aprovação de toda a release.

## Componentes existentes

| Dimensão | Estado | Inventário e evidência |
|---|---|---|
| Backend HTTP/ASGI | READY | Python, FastAPI, Uvicorn. Entrada `src/income_analytics/main.py`, app `income_analytics.main:app`; roteadores em `api/routers/`. |
| Frontend web | READY | HTML, CSS e JavaScript ES modules servidos pela mesma aplicação; `api/static/index.html`, `account.html`, `js/app-entry.js`, `js/features/`, `js/shared/`. Não é React/Vue nem há processo Node de produção identificado. |
| Gráficos | READY | ECharts 6.1.0 vendorizado em `api/static/vendor/echarts-6.1.0.min.js`; carregamento por `js/shared/charts.js`. Não depende de build npm para essa biblioteca. |
| Identidade | PARTIAL | Firebase Auth Admin no servidor e SDK web 13.1.0 carregado de `gstatic.com`; `infrastructure/firebase_identity.py`, `api/saas_security.py`, `js/auth-client.js`. Há testes de autorização; configuração real do console não foi auditada nesta fase. |
| Persistência principal | READY | SQLite + SQLAlchemy 2, modelo em `infrastructure/models.py`, repositórios em `sqlite_repositories.py`, configuração em `database.py`. Firebase não armazena o ledger financeiro. |
| Migrações | PARTIAL | Alembic, 27 revisões, um head estático `0027_contextual_onboarding_v2`. Em SaaS, startup exige schema atualizado; migração controlada ainda não tem pipeline. |
| Integrações de dados | PARTIAL | Adaptadores BRAPI, B3/COTAHIST/ETF/benchmarks, BCB/PTAX, CVM, CoinGecko, Twelve Data e Yahoo; arquivos em `infrastructure/`. Existência de adaptador não comprova disponibilidade, licença ou quota no ambiente alvo. |
| Importação | READY | Parsers B3/XLSX/IRPF e serviços de importação, com testes; `infrastructure/b3_xlsx_import.py`, `b3_report_parser.py`, `irpf_xlsx_import.py`, `application/b3_import.py`. |
| Processamento periódico | PARTIAL | Threads daemon iniciadas em `main.py` no modo local. Em SaaS são explicitamente desativadas. Worker de serviço separado não foi encontrado. |
| Artefato de aplicação | PARTIAL | `pyproject.toml` declara setuptools, mas a execução atual é por árvore de fontes. Wheel/instalador com todos os assets e migrations não foi inspecionado nem produzido nesta fase. |

## Organização do código

| Pasta | Responsabilidade comprovada | Evidência |
|---|---|---|
| `src/income_analytics/domain/` | Entidades, value objects, enums, eventos, projeções e cálculos financeiros | `entities/financial_event.py`, `entities/asset.py`, arquivos de performance/projeção; 128 arquivos Python na árvore examinada. |
| `src/income_analytics/application/` | Casos de uso, sessões de carteira, análises, simulação, contratos e gates do Magic Formula | `portfolio_session.py`, `portfolio_context.py`, `auth_context.py`, `magic_formula_activation_gate.py`; 60 arquivos Python. |
| `src/income_analytics/api/` | Rotas, middleware de segurança e interface estática | `routers/dashboard.py`, `routers/auth.py`, `saas_security.py`; 12 arquivos Python. |
| `src/income_analytics/infrastructure/` | Persistência e acesso a fornecedores | `database.py`, `sqlite_repositories.py`, `firebase_identity.py`; 35 arquivos Python. |
| `alembic/` | Evolução do schema | `env.py`, `versions/0001_...` a `0027_...`. |
| `tests/` | Testes e evidências congeladas | Categorias detalhadas em [testing_and_quality_gates.md](testing_and_quality_gates.md). |
| `scripts/`, `spikes/`, `demo/` | Operação, auditoria, estudos e demonstração | Scripts de benchmark/importação/validação; não constituem uma esteira de release. |
| `docs/`, `.ai/` | Documentação, decisões e processo de desenvolvimento assistido | `.ai/workflows/dev-qa.md` é um processo textual; não é um workflow do Actions. |

Os princípios em `docs/architecture/SOFTWARE_ARCHITECTURE.md` são documentação de intenção e estão datados de julho/2026. Não foram tratados como prova de que todos os consumidores previstos, como aplicativo mobile ou Streamlit, existam. Os guias `01-ambiente.md`, `02-git.md` e `05-testes.md` estavam vazios na referência examinada.

## Fluxo operacional e financeiro

```text
Navegador: HTML/CSS/ES modules + ECharts + Firebase Web SDK
  -> HTTPS privado/Tailscale -> Uvicorn/FastAPI
     -> Firebase: verificação de identidade e revogação
     -> SQLite: sessão local, ownership, CSRF e limites
     -> contexto de carteira -> PortfolioSession -> casos de uso/domínio
     -> repositórios SQLAlchemy -> SQLite financeiro e read models
     -> adaptadores externos: cotações, câmbio, fundamentos e proventos
```

Evidências: `main.py::serve_portfolio`, `saas_security.py::authorize_request`, `application/portfolio_context.py`, `application/portfolio_session.py`, `infrastructure/auth_repository.py`.

**PARTIAL — isolamento arquitetural:** há fronteiras de domínio/aplicação/infra e escopo explícito por carteira, mas `api/routers/dashboard.py` concentra grande parte da orquestração. A sessão completa carrega dados para projeções; as rotas de histórico usam `history_only` para limitar leituras. Não se infere que toda rota seja uma consulta SQL paginada: o histórico ainda reconstrói eventos e filtra/ordena em memória. Evidências: `portfolio_session.py::__post_init__`, `dashboard.py::get_asset_transactions` e `get_operations_history`.

**READY, escopo de representação — eventos e projeções:** o ledger usa eventos financeiros; posições e análises são derivadas, com snapshots persistidos para consulta. Isso não significa certificação financeira integral nem event sourcing distribuído. Evidências: `FinancialEvent`, `PortfolioSession`, `SqlitePortfolioDashboardSnapshotRepository` e os testes de performance.

## Execução local observada

| Ambiente | Estado | Forma identificada |
|---|---|---|
| Desenvolvimento LAN documentado | PARTIAL | `scripts/start_income_lan.ps1` seleciona `.venv/Scripts/python.exe` ou Python disponível, configura `PYTHONPATH=src` e inicia Uvicorn em `0.0.0.0:8000`. IP LAN no README é específico da máquina. |
| Prévia de validação | PARTIAL | Processo Python/Uvicorn identificado na porta configurada 8003; árvore de desenvolvimento. Não há definição reproduzível de homologação no repositório. |
| Produção privada atual | PARTIAL | Launcher externo `%LOCALAPPDATA%/IncomeAnalytics/Start-Income-HTTPS.ps1`, worktree `firebase-official-merge`, Python 3.14, Uvicorn em `127.0.0.1:8002`; Tailscale Serve 443, sem Funnel. |
| Homologação independente | MISSING | Nenhum GitHub Environment; nenhum launcher/deploy versionado com banco e identidade segregados de homologação encontrado. A prévia local não comprova essa separação completa. |

Foram lidos nomes de configurações do launcher e metadados de processos; não foram iniciados/parados serviços nem executadas rotas que alterem dados. A presença de processo/configuração não é um novo teste funcional de produção.

## Consequências para CI/CD

1. CI pode testar Python e Node sem reconstruir o produto como SPA com bundler; será preciso separar testes offline, emulador e cloud. Evidências: `pyproject.toml`, `tests/frontend/*.mjs`, `firebase.json`.
2. Build deve comprovar inclusão de estáticos, migrations e dados de referência necessários, além das dependências reais de runtime. Evidências: montagem de `/static` em `main.py`, uso de Alembic em `database.py` e `data/` fora do Git.
3. CD precisa respeitar ownership, persistência SQLite, schema, identidade, quotas e gates financeiros. Copiar fontes ou reiniciar o processo não atende sozinho a esses requisitos. Ver [assessment](cicd_readiness_assessment.md) e [roadmap](implementation_roadmap.md).
