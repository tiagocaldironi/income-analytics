# PR5.1 — CI offline reproduzível

Baseline: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Implementação em branch/worktree separado, sem modificar os checkouts existentes. A avaliação original está em [cicd-assessment](../cicd-assessment/cicd_readiness_assessment.md); esses seis documentos foram copiados sem alterações para preservar a referência diagnóstica.

## Escopo

O workflow está em `.github/workflows/ci-offline.yml` **na raiz Git**, acima do diretório `income-analytics/`. Executa em Pull Requests para `develop`, pushes em `develop` e disparo manual. Não há CD, migration de produção, acesso a credenciais produtivas ou ativação de proteção de branch.

Jobs independentes, sem `continue-on-error` e com `fail-fast:false`:

| Check proposto | Responsabilidade |
|---|---|
| `CI / runtime (windows-py314)` | Instalar somente runtime/build tools, comprovar ausência de pytest e importar o app com SQLite descartável; prova de Alembic em runtime. |
| `CI / ruff (windows-py314)` | Ruff no repositório da aplicação inteiro, sem autofix e sem ocultar dívida anterior. |
| `CI / mypy (windows-py314)` | mypy strict em `src`, sem ignorar os erros existentes. |
| `CI / python (windows-py314)` | Suíte completa Python + testes da infraestrutura CI, JUnit e cobertura; emulador/cloud explicitamente skipped. |
| `CI / cert48 (windows-py314)` | Executar separadamente `test_shares_unit_020_frozen_engine`; também permanece na suíte completa. |
| `CI / node (windows-node24)` | Executar as 30 suítes frontend e o autoteste do bloqueio de rede. |

Runners GitHub-hosted `windows-2025`, CPython **3.14.7 x64**, Node **24.19.0**. Ações fixadas por SHA; token somente `contents:read`; checkout sem persistir credenciais; sem `pull_request_target`, environments ou secrets. Em PRs o checkout padrão é o merge sintético: relatórios registram `checkout_sha`, SHA do evento e SHA do head do PR separadamente.

`core.autocrlf=false` é fornecido somente no ambiente do workflow, para reproduzir os bytes dos objetos Git. Não altera regras/manifestos financeiros nem torna CERT_48 aprovado: há expectativas mistas de LF/CRLF. Nenhum `.gitattributes` financeiro foi adicionado.

## Dependências e instalação limpa

`pyproject.toml` passou a declarar Alembic como runtime; o extra dev usa `httpx` em vez de `httpx2` e declara `requests`, usado pelos testes de integração. Não houve upgrade do ambiente produtivo.

- `ci/requirements-windows-py314.lock`: 71 wheels, ferramentas e transitivas incluídas.
- `ci/runtime-windows-py314.lock`: 57 wheels, sem pytest/Ruff/mypy.
- Todos os itens têm versão exata e SHA-256 do wheel escolhido em PyPI. A instalação usa `--require-hashes --only-binary=:all:`; não resolve versões novas em CI.
- Os locks são específicos de **Windows x64 / CPython 3.14**, não locks universais. Outros sistemas exigem lock e validação próprios.
- `ci/requirements-seed.txt` fixa as versões diretas inicialmente alinhadas à máquina avaliada; `ci/lock.py` gera a closure transitiva a partir do pyproject e dessas constraints. Regenerar é manutenção explícita com revisão de diff, não uma etapa de CI.
- `setuptools`, `wheel` e pip também são fixados. O projeto é instalado editável, sem nova resolução nem build isolation; `pip check` é executado antes e depois. Isto não certifica wheel/artefato de distribuição ou CD.

Preparação local em um **clone limpo**, dentro de `income-analytics/`:

```powershell
py -3.14 -m venv .venv
./.venv/Scripts/python.exe -m pip --isolated install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r ci/requirements-windows-py314.lock
./.venv/Scripts/python.exe -m pip --isolated install --no-deps --no-build-isolation -e .
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe ci/run.py ruff
./.venv/Scripts/python.exe ci/run.py mypy
./.venv/Scripts/python.exe ci/run.py python
./.venv/Scripts/python.exe ci/run.py cert48
./.venv/Scripts/python.exe ci/run.py node
```

Cada comando retorna o exit code do check; não encadear de modo que apenas o último resultado seja considerado. Para o teste mínimo de runtime, usar venv separado, instalar o lock `runtime-windows-py314.lock`, instalar o projeto sem deps/build isolation e executar `ci/run.py runtime`. O runner rejeita esse check se pytest estiver instalado.

A instalação de wheels e o provisionamento de Python/Node precisam de rede. **Offline refere-se à execução dos testes e checks**, não ao download inicial de dependências. Para instalação sem rede seria necessário disponibilizar previamente um wheelhouse; isso não foi implementado nem alegado.

Manutenção dos locks, somente em Windows/Python 3.14 e em ambiente isolado:

```powershell
./.venv/Scripts/python.exe ci/lock.py
./.venv/Scripts/python.exe ci/lock.py --runtime
```

O resolvedor usa PyPI explícito e aceita somente wheels de `files.pythonhosted.org`. O relatório de resolução temporário não é versionado nem aceito como input de instalação; quem define a instalação é o requirements lock com hashes. Bases: [pip — repeatable installs](https://pip.pypa.io/en/latest/topics/repeatable-installs/) e [hash-checking](https://pip.pypa.io/en/stable/topics/secure-installs/).

## Isolamento e limites

`ci/run.py` cria um sandbox temporário exclusivo por check e não herda configurações do produto, tokens ou credenciais do processo chamador. Retém apenas variáveis essenciais do sistema; configura HOME/USERPROFILE/TEMP próprios, modo local/development, jobs desativados, opt-ins cloud/emulador desligados, signup fechado e um caminho inexistente de credencial Admin.

`tests/conftest.py` continua intacto e seleciona outro SQLite UUID nesse TEMP. Importar o app pode executar migrations **somente nesse banco descartável**, como os testes existentes já fazem. Testes de migration em subprocessos também usam bancos de fixture, nunca o banco pessoal. Nenhum launcher produtivo é chamado.

`ci/sitecustomize.py`, carregado apenas com `INCOME_CI_OFFLINE=1`, bloqueia conexões TCP/DNS/UDP do Python. Socketpair interno usado por asyncio no Windows é permitido. A guarda acompanha subprocessos Python que preservem o PYTHONPATH. Alguns testes de migration definem seu próprio PYTHONPATH: executam apenas Alembic em banco temporário, mas essa guarda não é um firewall do sistema e não deve ser anunciada como sandbox contra código malicioso.

Node usa preload `ci/node-offline.mjs`, bloqueando fetch, conexões net, datagramas e resoluções DNS comuns. Testes de VM continuam usando seus próprios doubles. O runner rejeita `data/` como symlink ou junction para evitar referências ao diretório pessoal; o workflow executa checkout novo e não copia dados de nenhum host/worktree. Dados sintéticos gerados por testes ficam no sandbox ou em diretórios ignorados do checkout descartável.

O workflow não é uma fronteira de segurança para PRs hostis: usa runners hospedados descartáveis, não recebe secrets e mantém permissões mínimas. Não usar runners pessoais/produtivos para esse fluxo sem desenho de segurança separado.

## Emulador e cloud

As quatro funções de `tests/security/test_firebase_emulator.py` e a função de `test_firebase_live.py` são coletadas e reportadas como skipped por política offline. O plugin acrescenta a marca mesmo se alguém habilitar opt-in externamente. Nenhum skip é aplicado ao CERT_48 ou aos testes que falham por falta de evidências.

Não existe workflow cloud/emulador neste PR. Execução futura é uma trilha distinta: emulador oficial em projeto `demo-*` e job próprio; cloud em projeto de teste segregado e com autorização. O teste live atual contém projeto específico e pode criar/remover identidades; não deve receber credencial produtiva em PRs. Rodar esses testes fora do runner offline exige seguir a documentação de segurança e provisionar ambiente próprio.

## Relatórios e associação ao commit

Saídas públicas por allowlist em `ci-reports/<check>/`, ignoradas no Git:

- `result.json`: SHA real, SHA do evento/PR, baseline, Python, hash do lock, indicador de árvore suja, exit code, contagens e identificadores de testes/diagnósticos.
- JUnit sanitizado: somente nomes e resultados, sem assertion payload, mensagens ou stdout/stderr capturados.
- `coverage.xml`: métricas de linhas e nomes de arquivos; source root normalizado, sem código-fonte ou payload financeiro.

O workflow sobe esses arquivos mesmo com check reprovado, em artifact com SHA e retenção de 14 dias, e escreve resumo no job. Não sobe `.db`, `.coverage`, logs brutos, diretórios `data/`, `tmp/`, `docs/appendices/` ou relatórios inteiros de pip. Logs brutos ficam em diretório temporário privado local/runner e não são enviados pelo upload. Artefatos de PRs continuam sendo conteúdo não confiável e não são consumidos por automações privilegiadas.

A mesma execução reporta todos os checks sem suprimir falhas. Arquivo ausente no artefato é erro, não sucesso silencioso. Resultados de árvore suja são exploração local, não evidência final do commit. O estado e as pendências estão em [known_failures.md](known_failures.md) e [validation.md](validation.md).

## Checks obrigatórios propostos, não ativados

Após revisão das primeiras execuções e tratamento explícito das dívidas, propor os seis nomes da tabela acima como checks obrigatórios de `develop`, com revisão de PR. Não foi alterada proteção de branch, ruleset ou configuração de merge. Não habilitar bloqueios antes de haver baseline reproduzível e decisão sobre os checks vermelhos.

**CERT_48 continua bloqueador de certificação e promoção de produção**, mesmo se o PR de infraestrutura for aprovado para instalar uma CI que evidencie essa dívida. Esta CI não certifica release, não implementa CD e não autoriza deploy.
