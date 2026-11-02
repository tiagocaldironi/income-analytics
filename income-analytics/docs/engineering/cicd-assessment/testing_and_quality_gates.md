# PR5 — Fase 0: testes e gates de qualidade

Data: 28/10/2026. Referência publicada: `ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Consulte o [inventário](architecture_inventory.md) para os checkouts e limites.

## Método e resultado desta fase

**Nenhuma suíte pytest, teste cloud, emulador, benchmark de escrita ou migration foi executada nesta fase.** Coletar testes também pode importar `main.py`, cujo carregamento chama `initialize_database`; por isso a contagem usou análise AST dos arquivos, sem importar o produto. Não se declara uma nova suíte verde nem um resultado de cobertura atual.

Foram lidos testes/configurações/relatórios versionados e calculados SHA-256 sobre bytes existentes, em memória. Os hashes registrados, testes e manifests não foram alterados. Resultados de PRs anteriores são evidência histórica, não execução nova no SHA avaliado.

## Inventário automatizado

Contagem estática de `test_*.py`: **139 arquivos, 834 definições `test_*`**, incluindo um arquivo/definição na raiz de `tests/`. Não equivale ao número coletado por pytest: parametrizações, skips e plugins podem mudar a quantidade de casos. Frontend: **30 arquivos `.mjs`**.

| Categoria | Arquivos `test_*.py` | Definições | Estado da existência e evidência |
|---|---:|---:|---|
| `tests/unit/` | 28 | 119 | READY — entidades, value objects, serviços e sessão; por exemplo `unit/application/test_portfolio_session.py`. |
| `tests/domain/` | 6 | 22 | READY — fundações financeiras, SaaS e contratos de domínio. |
| `tests/application/` | 48 | 432 | READY — cálculos, simulação, Magic Formula, evidências CVM, preços e integridade; `test_performance_financial_integrity.py`, `test_historical_shares_units.py`. |
| `tests/infrastructure/` | 20 | 72 | READY — SQLite, adapters, ownership, importações e desempenho de queries; `test_history_query_performance.py`, `test_sqlite_b3_import_repository.py`. |
| `tests/api/` | 14 | 65 | READY — endpoints, lançamentos, agrupamento, datas e multiportfólio; `test_asset_transactions.py`, `test_operation_history_loading.py`, `test_local_multiportfolio_v2.py`. |
| `tests/acceptance/` | 14 | 86 | READY — MVP financeiro, projeções, performance e contratos de frontend. |
| `tests/security/` | 5 | 28 | PARTIAL — matriz determinística, headers e testes opt-in reais/emulador; execução atual não comprovada. |
| `tests/audit/` | 1 | 4 | READY — caracterização de prontidão SaaS, não aprovação de release. |
| `tests/spikes/` | 2 | 5 | PARTIAL — testes de estudos/adaptadores; não devem se tornar requisito cloud implícito de PR. |
| Raiz `tests/test_database_safety.py` | 1 | 1 | READY — verifica que a suíte aponta para banco temporário e não pessoal. |
| `tests/frontend/*.mjs` | 30 | Não contado como pytest | PARTIAL — asserts nativos Node, leituras de fontes e VM/DOM doubles; não constituem E2E de browser real. |

A suíte Node cobre, entre outros: `portfolio_v2.mjs`, `multiportfolio_context_v2.mjs`, `firebase_auth_session.mjs`, `saas_xss_characterization.mjs`, `simulation_executable_v2.mjs`, `api_request_deadlines.mjs`, `asset_history_categories.mjs` e `portfolio_loading_regression.mjs`.

## Comandos para uma futura execução autorizada

Os comandos abaixo **não foram executados**. Pressupõem ambiente já provisionado, dependências revisadas e diretório de trabalho `income-analytics/` dentro do checkout Git. Não instalar dependências nem executar migrations como parte desta fase diagnóstica.

```powershell
# Suíte Python; tests/conftest.py seleciona um DB temporário exclusivo.
py -3.14 -m pytest -q

# Regressões financeiras dirigidas: não substituem a certificação completa.
py -3.14 -m pytest -q tests/unit/application/test_portfolio_session.py tests/application/test_performance_financial_integrity.py tests/acceptance/test_portfolio_performance_mvp.py

# Histórico, isolamento e autorização com provedor determinístico.
py -3.14 -m pytest -q tests/api/test_asset_transactions.py tests/api/test_operation_history_loading.py tests/api/test_operation_history_grouping.py tests/api/test_local_multiportfolio_v2.py tests/security/test_firebase_authorization.py

# Gate congelado e evidências oficiais.
py -3.14 -m pytest -q tests/application/test_historical_shares_units.py tests/application/test_magic_formula_phase2_integration.py tests/application/test_petrobras_canonical_e2e.py

# Frontend: cada falha deve reprovar a execução agregada.
Get-ChildItem tests/frontend/*.mjs | ForEach-Object {
    node $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Falha no teste frontend: $($_.Name)" }
}

# Qualidade estática; não usar --fix/format no diagnóstico.
py -3.14 -m ruff check .
py -3.14 -m mypy src

# Cobertura informativa; não existe fail-under configurado.
py -3.14 -m pytest --cov=income_analytics --cov-report=term-missing
```

Em outro sistema operacional, trocar `py -3.14` pelo Python 3.14 provisionado. `test_database_safety.py` exige `TEMP` e compara com o diretório temporário; a matriz Linux precisará comprovar essa configuração. Não se afirma portabilidade integral dos scripts PowerShell ou da suíte antes dessa validação.

**PARTIAL — isolamento de testes:** `tests/conftest.py` define `INCOME_ANALYTICS_TESTING=1` e um SQLite UUID em `tempfile.gettempdir()` antes das importações. Isso protege o banco pessoal na execução prevista, mas os testes criam/migram o banco temporário. Não são testes sem escrita, motivo de não execução nesta fase.

**PARTIAL — autenticação real:**

- `test_firebase_authorization.py` usa provedor determinístico e TestClient.
- `test_firebase_emulator.py` exige `INCOME_RUN_FIREBASE_EMULATOR_TESTS=1`, Auth Emulator em `127.0.0.1:9099` e configuração `demo-*`. Comando futuro: `py -3.14 -m pytest tests/security/test_firebase_emulator.py -q` após provisionamento controlado. O emulador não foi iniciado.
- `test_firebase_live.py` exige `INCOME_RUN_FIREBASE_LIVE_TESTS=1`, credencial Admin e configuração real; o teste cria/remove identidades cloud e contém asserção para um projeto específico. Não é adequado ao CI de PR sem desenho de ambiente próprio. Comando futuro: `py -3.14 -m pytest tests/security/test_firebase_live.py -q`, somente com autorização e segregação.

## Certificação financeira: bloqueador comprovado

**BLOCKED — `test_shares_unit_020_frozen_engine`.** O teste em `tests/application/test_historical_shares_units.py` compara SHA-256 bruto com `tests/fixtures/cvm/shares_unit_v1/manifest.json`, chave `frozen_code_sha256`. A comparação estática reproduziu o impedimento, sem executar pytest:

| Arquivo em `src/income_analytics/application/` | SHA esperado | SHA bruto do worktree avaliado | SHA dos bytes LF / objeto Git |
|---|---|---|---|
| `magic_formula_stocks.py` | `27b58d132b461afe867ca2af05757b1309739c40156549ac0bf1785ae5ad27a4` | `27b58d132b461afe867ca2af05757b1309739c40156549ac0bf1785ae5ad27a4` | `44fe1057b14dc45d13e0d302d7b24e361921ee2dab87b1dfde674c30dc344a9d` |
| `magic_formula_ranking_validation.py` | `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37` | `039656c877d516ce2e2cdcf5d6bba7efadf948a92958875ecd140a16349ce83d` | `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37` |
| `magic_formula_contract.py` | `9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f` | `40b1def756c8cde12f556835ac7e989adab18907b1a0d7364aff3bfd6aa032f9` | `9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f` |

Conclusão restrita: neste worktree, dois arquivos divergem; para os objetos Git em LF, o primeiro diverge. **Não basta definir `core.autocrlf=false` para obter todos os hashes esperados.** A substituição CRLF→LF foi somente em memória para diagnóstico. Não se certifica equivalência semântica por essa observação, não se aprova trocar hashes e não se sugere ignorar o teste.

Os **30 documentos** da chave `documents` desse manifesto tiveram seus hashes comparados por leitura: **30 correspondências, zero divergências**. Essa verificação não valida todos os manifests do repositório.

Evidência histórica adicional: `docs/appendices/multiportfolio_v2_certification_closure/release_gate.json` registra `INCOMPLETE`, pendência `CERT_48`, suíte histórica “882 passed, 1 failed”. `test_manifest.txt`, `docs/PORTFOLIO_V2_PR2_COMPLETION.md` e `docs/FIREBASE_AUTH_VALIDATION.md` documentam o problema. Os números são de revisões anteriores; não são a contagem nem a aprovação atual.

## Outros gates e evidências

| Gate/capacidade | Estado | Evidência e interpretação |
|---|---|---|
| Regressão de TWR, fluxos e projeções | PARTIAL | Suítes em `tests/application`, `tests/acceptance` e `tests/unit`; nenhum gate obrigatório GitHub. Nenhum cálculo alterado nesta fase. |
| Validação de ranking/fundamentos | PARTIAL | `magic_formula_activation_gate.py`, `magic_formula_ranking_validation.py`, testes de contrato/lineage/universo. São gates de dados e metodologia específicos; não autorizam sozinhos release do app. |
| Evidências independentes/goldens | PARTIAL | `tests/golden/magic_formula/README.md` exige fonte CVM/B3 independente. Há manifests em `tests/fixtures/cvm/{shares_unit_v1,phase2_v1,petrobras_canonical_v2,price_identity_v1,universe_discovery_v1}`. Nem toda referência em `tmp/`/`data/` está disponível no Git. |
| Performance | PARTIAL | Scripts `analytics_engine_benchmark.py`, `analytics_scaling_benchmark.py`, `analytics_concurrency_benchmark.py`, `profile_analytics_cpu.py`; teste de queries do histórico. Relatório `INCOME_ANALYTICS_ANALYTICS_ENGINE_PERFORMANCE_V1_1.md` tem gate histórico de sistema FAIL. Não foi reexecutado nem extrapolado para hoje. |
| Lint e tipos | PARTIAL | Ruff E/F/I, linha 100, Python 3.14; mypy strict em `pyproject.toml`. Relatos antigos de dívidas não comprovam o total atual. Nenhum full lint/type check executado agora. |
| Cobertura mínima obrigatória | MISSING | pytest-cov declarado, mas sem `fail-under` ou política de cobertura identificada em `pyproject.toml`; percentual atual UNKNOWN. |
| E2E automatizado de navegador | MISSING | Evidências PNG e validação manual existem em `docs/evidence/`; `.mjs` usa VM/doubles. Nenhum runner Playwright/Cypress/Selenium versionado identificado. A exceção manual histórica era restrita ao Multiportfolio V2 local. |
| Gate obrigatório no merge | MISSING | `develop` desprotegida, sem rulesets, sem pipeline de engenharia versionada. Ver [repository_and_dependencies.md](repository_and_dependencies.md). |

**Regra proposta para o PR5:** primeiro tornar as falhas visíveis e reprodutíveis. A futura CI pode começar antes do fechamento da pendência, mas certificação/release não pode ser declarada READY enquanto o gate financeiro permanecer sem reconciliação aprovada.
