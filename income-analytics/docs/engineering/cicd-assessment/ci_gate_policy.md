# PR5.1D — Política independente de gates

Data: 28/10/2026. Candidato local em codex/pr51d-ci-gates, ancestral 1bbd2d42686ab0c893790772a05a7845cfbc0295; baseline financeira ca627ac72f110d0f4d62faaa9c51a08eaed54965. Política e baseline iniciais sujeitas à revisão deste PR; nenhum commit, push, PR, proteção de branch ou deploy autorizado por esta execução.

## Matriz de estados

| Gate | Critério de aprovação | Estado independente | Implementação |
| --- | --- | --- | --- |
| Engineering CI | Runtime reproduzível; Python selecionado sem falha/erro/skip; frontend completo; guardas SQLite/rede/segurança; nenhuma identidade/multiplicidade nova Ruff/mypy; relatórios do mesmo SHA/conteúdo | PASS ou FAIL segundo execução | ci/governance.py + gate_policy.py; check CI / Engineering |
| Financial Certification | Evidência histórica original aprovada, CERT_48/identidade e contratos congelados íntegros; rankings, temporalidade, imutabilidade/idempotência | BLOCKED enquanto pendências independentes não encerradas | Executa testes possíveis, publica casos/motivos e retorna exit=1; check CI / Financial certification |
| Release Readiness | Engineering e certificação aprovados + artefato reproduzível, migrations verificadas, homologação, segurança, backup/rollback | BLOCKED — evidências/requisitos de release incompletos | Apenas estado no resumo; sem promoção |
| Deployment Authorization | Aprovação explícita, ambiente protegido, identidade do artefato, versão/evidências e recuperação | NOT_IMPLEMENTED; deployment_authorized=false | Sem job de deploy |

Engineering PASS nunca implica lint global limpo, certificação, release ou implantação. Financial BLOCKED não é exibido como PASS: GitHub Actions recebe exit não zero e resumo estruturado explícito. Full Python diagnostic, Ruff e mypy continuam com seus exit codes reais reprovados; não há continue-on-error para mascará-los.

## Seleção auditável de testes

ci/test-groups.json contém 22 node IDs históricos exatos, 2 IDs de integridade congelada, os dois módulos externos e módulos financeiros adicionais. gate_plugin inventaria toda coleta ANTES de selecionar; registra arquivo/linha/categoria/dependências, capacidade hermética, destino e resultado. Grupo de certificação e suíte completa validam que os 24 IDs ainda existem: ausência gera erro de coleta. Não se seleciona por status, nome contendo fail ou contagem desejada.

- Engineering executa todos os demais casos; teste novo desconhecido entra por padrão e pode reprovar o gate. Nenhum caso é dispensado por falhar.
- Os 22 históricos exigem originais V8/V9.2/V12.2 e DB de universos não aprovados; permanecem executados na certificação e no diagnóstico completo, com os erros reais. Não são substituídos por registros sintéticos ou IDs antigos reutilizados.
- CERT_48 e identidade são autocontidos e tecnicamente herméticos. Sua exclusão SOMENTE do escopo Engineering é por finalidade formal de certificação, não por alegação falsa de dependência externa. Ambos executam nos outros dois grupos e continuam bloqueadores financeiros.
- Contratos financeiros herméticos adicionais continuam no Engineering e também no grupo financeiro quando listados; a classificação não remove proteção de cálculo apenas porque o arquivo é financeiro.
- Quatro casos Emulator e um live exigem serviços/identidades externos. Não entram no Engineering; permanecem identificados na coleta e nos cinco skips preexistentes do diagnóstico offline. Sem skip/xfail novo do plugin de gates. A validação externa é opcional e separada, NOT_RUN_OFFLINE; não houve instalação/execução cloud neste PR.

Deselect significa roteamento para outro grupo explícito, não aprovação ou remoção. Os inventários de todos os grupos preservam esses IDs. Caso um teste selecionado não tenha resultado JUnit correspondente, o runner falha por INventory/JUnit mismatch. Engineering vazio ou com skip é reprovado.

## Checks estáveis

| Check | Papel | Pode estar reprovado enquanto Engineering passa? |
| --- | --- | --- |
| CI / Runtime installation | Lock runtime sem pytest; import app apenas em SQLite descartável | Não |
| CI / Python engineering | Todos os testes do escopo hermético obrigatório | Não |
| CI / Frontend | 30 suítes + autoteste da guarda | Não |
| CI / Quality non-regression | Identidades/multiplicidade comparadas com baseline revisável | Não |
| CI / Engineering | Agregação de runtime, Python, frontend e não regressão, com identidade consistente | Não |
| CI / Full Python diagnostic | Suíte integral; falhas/erros/skips preservados | Sim, com falhas históricas visíveis |
| CI / Ruff diagnostics | Ruff integral, sem supressões globais | Sim: dívida existente continua FAIL_WITH_DEBT |
| CI / mypy diagnostics | mypy strict integral, sem redução de configuração | Sim: dívida existente continua FAIL_WITH_DEBT |
| CI / Financial certification | Testes históricos + integridade + contratos adicionais; motivos de BLOCKED | Sim; isso proíbe certificar/release |

O workflow usa pull_request para develop, push em develop e execução manual. Mantém Python3.14.7/Node24.19.0, Actions fixadas por SHA, contents:read, checkout sem credenciais persistidas e artifacts allowlist por SHA. A agregação roda com always para conseguir relatar bloqueios quando os diagnósticos/certificação falham. Não eleva permissões nem usa pull_request_target. Todos os relatórios presentes precisam concordar em checkout_sha/source_fingerprint; relatório obrigatório ausente, duplicado ou de outra árvore não aprova Engineering.

## Política incremental de qualidade

Baseline versionada: ci_quality_baseline.json, 130 Ruff + 673 mypy, originada da PR5.1C e confrontada com seus relatórios. Cada ocorrência contém tool, file relativo, rule/code, line, column quando disponível, normalized message e multiplicidade. O comparador usa Counter de identidades completas. Remover erro antigo não compensa erro novo, mesmo mantendo ou reduzindo o total. Duplicata nova também falha.

Mudança de localização/mensagem é conservadoramente nova e requer correção/revisão da baseline. Normalização remove caminhos absolutos pessoais e espaços redundantes, não nomes de regras ou significado do erro. Versões das ferramentas e digest do lock precisam corresponder à baseline. Falha da ferramenta/parser não é lista vazia aprovada.

Não existe comando de refresh automático no runner. Mudanças deliberadas do JSON devem trazer justificativa, diff de identidades e revisão do mantenedor; a primeira baseline faz parte desta revisão. Branch protection/owners que tornem essa revisão mandatória são proposta futura, não controle GitHub já ativado. Um PR capaz de alterar workflow/baseline exige revisão humana; o pipeline não é uma raiz de confiança fora do repositório.

## Segurança e isolamento

Reutilizados, sem relaxamento: allowlist de ambiente; TEMP canonicalizado; SQLite UUID descartável antes de importar app; jobs externos desligados; credenciais Admin/cloud não herdadas; guardas socket/DNS/subprocesso; JUnit sem mensagens de falha, stdout/stderr ou payload financeiro; artifacts somente JSON sanitizado, JUnit, cobertura e inventário. Baseline contém diagnósticos estáticos de código, sem paths pessoais ou dados de carteira. Nenhum DB/JSON privado é publicado.

Forks não recebem secrets produtivos; token tem leitura, sem permissionamento de escrita. Código de PR permanece não confiável e deve executar só no runner efêmero. Instalação de wheels/hash via PyPI é provisionamento controlado, separado de execução offline do produto. Não há migration/launcher/Tailscale/Firebase produtivo neste workflow.

## Relação com proteção futura de branch

Após revisão do candidato e estabilidade hospedada, CI / Engineering é candidato a check obrigatório de PR. Para alterações de código certificado, exigir adicionalmente certificação financeira íntegra e revisão independente; enquanto BLOCKED não promover mudanças financeiras como certificadas. Release exige Gate2 e evidências próprias; deploy exige aprovação explícita em ambiente protegido futuro. Não ativar proteções, rulesets, bypass, auto-merge ou CD neste PR. Manter o PR #48 em revisão até decisão explícita sobre integração e baseline.
