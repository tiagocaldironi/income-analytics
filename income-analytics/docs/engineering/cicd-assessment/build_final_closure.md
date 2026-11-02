# PR6 — Build reproduzível

Build reproduzível implementado e validado no GitHub Actions. O registro
autoritativo da integração protegida e do push pós-merge é o recibo final do
[PR #51](https://github.com/tiagocaldironi/income-analytics/pull/51), com SHA de
`develop`, run e digest final. Este documento fixa a medição hospedada de referência,
sem autorreferência ao SHA do commit que contém o próprio relatório.

## Baseline e limites

Baseline consultada: `develop@7a7ffd9cb4a27a40fe4e6c1c7b2a4ca6fc09f4b1`.
Ruleset `26078982`: ativo, somente `develop`, sem bypass, PR obrigatório,
`CI / Engineering` do GitHub Actions (`15368`), branch atualizada, resolução de
conversas e bloqueio de force push/exclusão. A proteção não é modificada pelo PR6.
Worktree e branch `codex/pr6-reproducible-build` isolados; originais preservados.

Não há deploy, restart produtivo, release público, promoção financeira, alteração
de autenticação, banco produtivo ou cálculos. `CERT_48` continua BLOCKED. O ZIP é
uma unidade interna de entrega de engenharia, não uma autorização de produção.

## Inventário e classificação

| Item/evidência | Classificação | Decisão |
|---|---|---|
| `src/income_analytics/main.py`, `api/routers/`, application/domain/infrastructure | Runtime | Incluir todos os arquivos versionados de `src/`, bytes exatos do Git. |
| `api/static/` HTML/CSS/ES modules, ECharts vendorizado | Runtime | Incluir integralmente; nenhum bundler ou compilação Node necessário. |
| Python 3.14.7 Windows x64 | Runtime/build | Alvo único certificado por este build; Python deve ser fornecido pelo ambiente. |
| `ci/runtime-windows-py314.lock` | Runtime/build | Copiar como `requirements.lock`; 57 wheels diretas/transitivas, versões e SHA-256. Inclui Alembic, pip, setuptools e wheel. |
| `ci/requirements-windows-py314.lock`, Ruff/mypy/pytest | Desenvolvimento/CI | Preservar CI existente; não incluir ferramentas de teste no pacote runtime. |
| Node 24.19.0, `tests/frontend/*.mjs` | Desenvolvimento/CI | Executar suítes no job existente; Node não compõe runtime nem identidade do ZIP. |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/` | Runtime | Incluir 27 migrations originais, com teste do head em SQLite descartável. Não há template de geração versionado; desnecessário para upgrade. |
| `pyproject.toml` | Metadados/configuração | Incluir sem alterar; não executar resolver nem build setuptools da aplicação. Execução por `PYTHONPATH=src`, conforme arquitetura atual. |
| `INCOME_AUTH_MODE`, `INCOME_ENV`, origem e flags | Configuração externa | Documentar, sem copiar ambiente pessoal. Smoke usa somente modo local/desenvolvimento. |
| Firebase Admin/ADC, BRAPI e demais tokens | Segredos externos | Excluir; não herdar no smoke; nenhum secret produtivo usado pelo workflow. |
| SQLite, backups, cache COTAHIST, logs, venvs | Estado persistente/temporário | Excluir. Smoke contém todo estado sob uma raiz temporária removida ao terminar. |
| Magic Formula: DBs/arquivos históricos e CVM | Dados externos | Excluir. Não inventar referências; indisponibilidade financeira existente permanece explícita. |
| Firebase Web SDK/CDNs, cotações, PTAX, CVM e demais APIs | Serviços externos | Não embutir credenciais nem certificar disponibilidade. Frontend online pode usar CDNs. |
| `scripts/start_income_lan.ps1` e launcher HTTPS pessoal | Operação específica Windows | Não incluir nem modificar. Instruções do bundle são somente para validação descartável. |
| `ci/artifact.py`, `smoke_artifact.py`, policy e instruções | Build/verificação | Empacotar suporte stdlib para validar o pacote sem Git ou dependências instaladas. |
| GitHub Actions `.github/workflows/ci-offline.yml` | Build/CI | Novo job `CI / Reproducible build`; mesmas permissões mínimas e Actions fixadas por SHA. |

## Formato e instalação

ZIP `income-analytics-<checkout_sha>-windows-x64.zip`, com `src/`, `alembic/`,
`alembic.ini`, `pyproject.toml`, `wheelhouse/`, `requirements.lock`, `artifact.py`,
`smoke_artifact.py`, `build-policy.json`, `INSTALL.md`, `manifest.json`.
O manifest lista os 385 arquivos de payload, tamanhos e SHA-256. O próprio
manifest é a entrada adicional: 386 entradas no ZIP. Seu conteúdo é coberto pelo
digest externo do pacote e pelo digest do artifact de transporte, evitando ciclo.

ZIP foi escolhido porque preserva a árvore de execução atual e permite instalação
offline com wheels; não exige Docker, compilador, npm, caminhos pessoais ou um
wheel incompleto sem migrations/static. A aplicação não é instalada como editable.
As dependências são instaladas em venv externo com `--no-index --require-hashes
--only-binary=:all:`. Python 3.14.7 Windows x64 é pré-requisito; não é um EXE nem
um runtime Python redistribuído. Outros SOs/arquiteturas não foram certificados.

Instruções completas: [`ci/build_installation.md`](../../../ci/build_installation.md)
(copiado como `INSTALL.md`). Inicialização em loopback; explicitamente selecionar
SQLite novo fora da árvore. Os caminhos de dados externos da aplicação continuam
dependendo da configuração/working directory existente; este PR não reconfigura
persistência nem autenticação produtiva.

## Determinismo e identidades

- Ler exclusivamente blobs do commit HEAD, após exigir checkout limpo. Ignorados
  e arquivos pessoais não entram no pacote; `src/` e migrations não são normalizados.
- Ordenar caminhos POSIX; ZIP_STORED evita diferenças de versão do compressor.
- Fixar data ZIP em 1980-01-01, regular-file POSIX 0644, sem extras/comentários.
- Gerar JSON UTF-8/ASCII escapado, chaves ordenadas, newline LF.
- Usar dois checkouts independentes e dois downloads sem cache, todos sujeitos
  aos mesmos hashes. Comparar os SHA-256 dos ZIPs e validar ambos no build.
- Não incluir relógio, caminho absoluto, venv ou aleatoriedade no conteúdo.
- Preservar versões/hashes dos locks existentes, sem resolver novamente dependências.

`commit_sha` identifica o checkout construído (merge sintético em PR; commit real
em push). `pr_head_sha` e `event_sha` ficam no relatório Actions, separadamente.
`source_ref` do pacote usa o SHA imutável, evitando que renomear uma branch altere
um build do mesmo commit.

`source_fingerprint` do manifest é o digest dos caminhos e bytes distribuídos
(exceto wheels, cobertas pelo lock e manifest). Não é o fingerprint de execução
v2 de `pipeline_identity.py`, publicado separadamente no relatório de CI.
`build_policy_sha256` cobre builder, smoke, policy, lock e pyproject distribuídos.
`governance_policy_sha256` cobre também workflow, orquestrador, testes e controles
de CI. São identidades distintas do commit e do digest do pacote final.

O digest final fica em `.sha256` externo e `result.json`; nunca dentro do ZIP.
SHA-256 interno detecta inconsistência, mas não autentica sozinho a origem. Antes
de executar o verificador distribuído, comparar com digest/commit obtidos no run
autenticado, usando uma cópia confiável do verificador do repositório.

## Execução local e hospedada

Com checkout LF limpo e Python 3.14.7 Windows x64, na raiz da aplicação:

```powershell
python ci/build_pipeline.py
```

O pip do ambiente de build deve ser fornecido conforme o lock runtime; o workflow
cria `.venv`, instala o lock com hashes e executa esse comando por seu Python.
O script clona os blobs em duas árvores temporárias, adquire wheels de PyPI com
hashes, monta e verifica os ZIPs, compara bytes, instala somente a partir do pacote
em um terceiro ambiente descartável e publica apenas os outputs permitidos em
`ci-reports/build/`. Falhas retornam código não-zero e relatório sanitizado.

```powershell
python ci/artifact.py verify <ZIP> --commit <SHA> --sha256 <digest-do-run>
python ci/smoke_artifact.py <ZIP> --commit <SHA> --sha256 <digest-do-run>
```

O smoke elimina variáveis herdadas, usa HOME/SQLite/cache temporários, desliga jobs
externos, não usa credenciais, nega conexão/DNS/UDP externos nos subprocessos e
permite apenas loopback. Essa guarda cobre sockets Python, não equivale a firewall
do SO para bibliotecas nativas. Configuração local, ausência de credenciais e jobs
desligados são controles adicionais; cloud/native networking não é certificado.
Cria venv novo, instala sem rede, executa `pip check`,
aplica migrations no SQLite temporário, importa backend, sobe Uvicorn, testa
`/health`, `/` e CSS, verifica schema=head, termina servidor e remove o ambiente.
Importação isolada e startup real são verificações distintas.

Actions roda em PR para `develop`, push e dispatch. `CI / Engineering` conserva
nome e app; exige relatório build com identidade consistente, exit=0, manifest,
duas construções idênticas, instalação/startup/cleanup PASS e sem acesso produtivo.
O agregador também rejeita job build falho ou pulado, mesmo se existir um relatório.
Testes negativos fazem parte da seleção Python Engineering, sem desabilitar casos.

## Integridade, exclusões e retenção

Verificador rejeita caminhos absolutos/traversal/Windows drive, duplicatas inclusive
case-insensitive, estrutura/metadata ZIP inválidas, arquivos extras/ausentes,
conteúdo/manifest divergente, commit/digest diferentes, migrations obrigatórias
ausentes, wheels incompatíveis com o lock e dependências sem pin/hash.
Allowlist fechada exclui `data/`, bancos, temporários, caches, `.env`, logs, chaves,
venvs, docs pessoais e scripts produtivos. Scanner de conteúdo procura chaves
privadas, credenciais service-account e tokens de formatos conhecidos. Isso não
substitui um inventário completo de segurança ou análise de supply chain.

Artifacts Actions `application-<checkout_sha>-windows-x64` e
`governance-build-<checkout_sha>`: retenção de 14 dias, como os relatórios CI.
Repo público implica artefato acessível conforme permissões do Actions; não há
GitHub Release nem divulgação a usuários finais. ZIP contém apenas código público
e dependências públicas travadas. Run/commit/manifest/digest permitem rastreio;
após expiração, reconstruir o mesmo commit com o mesmo alvo/locks. Indisponibilidade
futura do PyPI é um risco externo; espelhamento de longo prazo não integra este PR.

## Resultados e evidências

Validação inicial limpa `ac0d6866ce150ae77394f0161be147ec0ffada51`:
86 testes de build/governança PASS; build duplo idêntico, 385 arquivos,
instalação/migrations/startup/health/static/cleanup PASS; ZIP SHA-256
`5f26fa1f8d89adf800e68054b77f83087b28d3aafef1fa54f3ea59b0ba6442c6`.
Qualidade: 803 diagnósticos existentes,
zero adicionados/removidos, baseline intacta. Ajustes subsequentes reforçam
estrutura ZIP, egress e teste de hashes de wheels; medições finais abaixo.

### Medição hospedada de referência

- [Run 40853584364](https://github.com/tiagocaldironi/income-analytics/actions/runs/40853584364), evento PR para `develop`.
- Head da branch: `0cba422eb694148e6462f98f6004d385c77273ea`.
- Checkout construído: `0cf4bdc5bd60fa1a1afa9d4809453da18966c654` (merge sintético, não o head do PR).
- ZIP SHA-256: `39864da5356e843bba18158b2d4cfdfb37cb56b5b7d1a4ec5cfde4b71b93a762`.
- Fingerprint distribuído: `f39434e641b35571233b37f5fe0ac3aaf7f88169191404cc0ce20a97b999aad3`.
- Política de build: `1594f72e60abd1b2cd93653897e1babcbf73f062538f933b5decf2a834840898`.
- Fingerprint de execução v2: `6eca8283da6dd622d2c5b7f605834a3a451100b80072696536ef0c2a482fdff1`.
- Política de governança: `98cc8047e6edc173ded67e7ab68496bf0dd3d2317c480879f43b0590ec503fce`.

| Validação | Resultado hospedado |
|---|---|
| CI / Engineering | PASS, nome/app preservados |
| Build independente duplo | PASS, mesmo SHA-256 |
| ZIP baixado/manifest/proveniência | PASS, SHA conferido com relatório e digest do transporte GitHub |
| Instalação offline, pip check | PASS, venv novo e wheels travadas |
| SQLite temporário/head Alembic/import/startup/health/static/cleanup | PASS |
| Python Engineering | 1104 PASS, 0 falhas/erros/skips |
| Governança/build, incluídos acima | 93 PASS |
| Frontend | 31/31 PASS |
| Qualidade | 803 diagnósticos existentes; zero adições/remoções; baseline intacta |
| Ruff / mypy | 130 / 673, FAIL_WITH_DEBT explicitamente mantidos |
| Python completo | 1104 PASS / 15 falhas / 9 erros / 5 skips |
| Financeiro | 73 PASS / 15 falhas / 9 erros / 0 skips; BLOCKED |
| Produção/CD | Preservada / NOT_IMPLEMENTED |

A conclusão global do workflow é `failure` pelos diagnósticos e certificação
bloqueados; o gate independente Engineering e o build são `success`. Nenhuma
falha foi dispensada. Todos os casos anteriores foram comparados por identidade e
status com a baseline de CI: preservados; novos casos são somente CI aprovados.
Inventário de testes da aplicação e diagnósticos Ruff/mypy: equivalência exata.
`test_shares_unit_020_frozen_engine` continua executado e reportado.

O pacote foi baixado do Actions e validado por `ci/artifact.py` contra o commit e
SHA do relatório. O digest do ZIP externo do artifact também confere com o digest
fornecido pela API do GitHub. Manifest externo e interno coincidem. Local e
hospedado têm os mesmos fingerprints de código/política e resultados de instalação;
o SHA dos pacotes local e PR difere corretamente pelo commit de proveniência.

Detalhes sanitizados e IDs/digests dos artifacts: [`build_hosted_validation.json`](build_hosted_validation.json).
O recibo final no PR registra a repetição destas validações após o merge na
`develop` e o digest do artefato desse commit. Cada commit tem identidade própria;
não reutilizar o ZIP de referência como se fosse de outro SHA.


## Riscos residuais e fora do escopo

Certificação financeira, 22 testes de referências históricas, frozen identity e
`CERT_48` continuam executados no CI e bloqueadores de promoção financeira.
Ruff/mypy mantêm dívida explícita; apenas ausência de regressão é gate.
Smoke não certifica Firebase/cloud, fornecedores de dados, navegador completo,
cálculos, backup, restauração, rollback, homologação ou capacidade de produção.
CD e autorização de deploy permanecem NOT_IMPLEMENTED/false.

Windows/Python alvo, código vendorizado e wheels são confiados pelos locks/commit;
scanner de padrões não prova ausência de todo segredo imaginável. Validação de
proveniência depende do digest externo autenticado e do verificador confiável.
Nenhuma configuração de produção é inferida do sucesso do build.
