# PR5.1D — Validação da consolidação e governança

Data: 28/10/2026. Branch/worktree isolado `codex/pr51d-ci-gates`. **Resultado técnico local: Engineering PASS; Financial Certification BLOCKED; Release Readiness BLOCKED; Deployment Authorization NOT_IMPLEMENTED.** Não há aprovação de merge/produção implícita.

## Identidade e origem

Baseline financeira: develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965. HEAD efetivamente usado: **1bbd2d42686ab0c893790772a05a7845cfbc0295**, ancestral publicado do PR #48. B/C continuam sem commits próprios; não foram presumidos integrados. D preserva a correção de parser/testes B e o pack mínimo/proveniência C, além dos documentos A. Plano/origens/digests estão em [ci_consolidation_plan.md](ci_consolidation_plan.md).

Validação em clone local novo `income-pr51d-clean-8r1t9dt6/checkout/income-analytics`, criado com core.autocrlf=false e sem hardlinks do Git publicado; overlay explícito dos arquivos D identificados, inclusive .github/workflows na raiz Git. Nenhum arquivo ignorado/data/DB pessoal foi copiado. Dois venvs novos fora do checkout, runtime e dev, receberam wheels pelos locks e hashes, sem resolver/atualizar dependências. Instalação editable --no-deps --no-build-isolation e pip check passaram em ambos. Runtime comprovou ausência de pytest e startup em SQLite descartável.

Árvore executada (source_fingerprint): **bdb3cd620e91bc4b04a5dc9c7cbfade08aa4af8c65d2d89d366164d0c22dbaec**. Os oito relatórios concordam em SHA/fingerprint; o mesmo fingerprint foi calculado no worktree D. Ele cobre src/tests/ci/alembic, configuração relevante, manifests novos de referência/qualidade e workflow. Documentos de redação não alteram a identidade de execução.

Alterações ainda sem commit; reports registram worktree_dirty=true. Não há novo SHA de commit D nem execução GitHub Actions hospedada: commit/push/PR não foram autorizados. SHA ancestral+fingerprint identificam a árvore local, sem alegar candidato imutável já publicado. Isso limita a recomendação de integração e a validação hospedada.

## Checks efetivamente executados

Python 3.14.7 / Node 24.19.0. Todos os checks de produto usam allowlist de ambiente, credenciais cloud inexistentes, guarda de rede e SQLite TEMP exclusivo. Aquisição de wheels no provisionamento usa PyPI/hash; execução do produto é offline. Migrations dos testes/startup só em SQLite descartável, nunca em produção.

| Check | Resultado | Exit | Evidência |
| --- | --- | --- | --- |
| Runtime installation | PASS | 0 | Lock runtime + pip check + app.title e ausência de pytest |
| Python engineering | PASS: **1037P / 0F / 0E / 0S** | 0 | 1066 coletados, 1037 selecionados, 29 roteados a outros escopos |
| Full Python diagnostic | FAIL: **1037P / 15F / 9E / 5S** | 1 | Todos os 1066 casos executados; resultados históricos preservados |
| Financial certification | **BLOCKED: 73P / 15F / 9E / 0S** | 1 | 97 selecionados; 22 históricos + CERT_48/identidade identificáveis |
| Frontend | PASS: **30/30 + autoteste = 31/31** | 0 | Fontes versionadas; guarda Node offline |
| Ruff diagnostics | FAIL_WITH_DEBT: **130** | 1 | Configuração integral preservada |
| mypy diagnostics | FAIL_WITH_DEBT: **673** | 1 | Strict integral preservado |
| Quality non-regression | PASS: **803 existentes, 0 novos, 0 removidos** | 0 | Identidades e multiplicidade, lock/configuração/versões conferidos |
| Engineering aggregate | **PASS**, identidade consistente | 0 | Runtime + Python engineering + Node + quality |

Infraestrutura/controle: **26 testes aprovados** (5 PR5.1 preservados e 21 novos D). O teste SQLite global também permaneceu ativo. Cobertura de linha informativa da suíte completa: 80.79%; não certifica retorno financeiro.

## Comparação com PR5.1C

- C: 1016 aprovados / 15 falhas / 9 erros / 5 skips. D: 1037 / 15 / 9 / 5.
- Todos os **1045 casos anteriores** conservaram identidade e status; nenhum removido, nenhum falhando novo ocultado. Os 21 acréscimos são testes de governança aprovados.
- Ruff/mypy mantiveram 130/673, com multiconjunto exato igual à baseline C. Qualidade global permanece reprovada; o PASS é exclusivamente da política de não regressão.
- Os 22 casos históricos continuam 13F+9E. A CERT_48 e a identidade são as outras duas falhas; não foram convertidas em skip/xfail ou classificadas falsamente como não herméticas.
- Cinco integrações Firebase permanecem nos skips offline preexistentes; inventário marca integração externa/NOT_RUN, não aprovação. Nenhuma execução externa real foi alegada.

## Provas dos gates e testes negativos

ci/test_governance.py comprova:

1. Mesmo diagnóstico existente é dívida visível permitida pela não regressão; remoção pode melhorar sem atualizar baseline.
2. Seis mudanças de identidade (arquivo, localização, regra, mensagem, ferramenta) falham mesmo compensadas pela remoção de um erro antigo com total igual.
3. Nova duplicata na mesma identidade falha por multiplicidade.
4. Os 22 históricos e dois frozen permanecem distintos e selecionados em certificação; frozen é tecnicamente hermético.
5. Teste novo não reconhecido fica em Engineering; dependência externa precisa justificativa dos módulos explícitos.
6. Engenharia positiva não libera finanças, release ou deploy.
7. Relatório obrigatório ausente/falho ou fingerprint diferente impede aprovação.
8. Normalização remove path pessoal sem apagar significado do erro.
9. Falha induzida real: arquivo test_induced.py criado somente em tmp_path contém assert False. Subprocesso pytest com --ci-gate=engineering seleciona o teste e retorna 1/“1 failed”; a agregação recebe esse resultado e reprova Engineering. Nenhum arquivo produtivo/versionado é adulterado; o teste de controle passa ao verificar a rejeição esperada.
10. YAML tem contents:read, sem pull_request_target/secrets/continue-on-error, checkout sem credenciais persistidas, Actions por SHA e resumo always.

Os testes antigos de infraestrutura também confirmam redaction de JUnit/stdout/stderr, descarte de credenciais herdadas, TEMP canonicalizado, bloqueio de rede em subprocesso e socketpair interno funcional. Asserções financeiras/goldens não foram modificadas.

## Inventário e relatórios

[ci_test_inventory.md](ci_test_inventory.md) lista individualmente **1066 casos Python e 31 suítes Node**. Classes: 197 unitários, 840 integrações herméticas, 24 de certificação histórica, 5 externas. Category/engineering/financial/hermetic_capable são dimensões separadas. Financial tem 73 contratos aprovados também incluídos em Engineering; não somar grupos como casos únicos.

Reports sanitizados locais em ci-reports/{runtime,engineering,financial,python,node,ruff,mypy,quality}/result.json; inventários/JUnit por grupo e gate-summary.json. Os artifacts do workflow só incluem esses JSON/JUnit/cobertura/inventário allowlist. Nenhum DB, raw log, snapshot privado ou payload financeiro é publicado. Baseline versionada de qualidade contém apenas diagnósticos estáticos relativos; não há path pessoal/credencial.

## Comandos de reprodução

No checkout candidato com runtime-only venv:

```powershell
python ci/governance.py runtime
```

Com venv dev instalado pelos locks:

```powershell
python ci/governance.py engineering
python ci/governance.py financial
python ci/governance.py python
python ci/governance.py node
python ci/governance.py ruff
python ci/governance.py mypy
python ci/governance.py quality
python ci/governance.py summary
```

Os três checks de diagnóstico e a certificação retornam falha real esperada, não sucesso. O comando summary avalia estados independentes; coleta de reports duplicados/misturados falha. Nenhum comando atualiza a baseline.

## Arquivos D e consolidação

Novos D: ci/gate_policy.py, ci/gate_plugin.py, ci/governance.py, ci/test_governance.py, ci/test-groups.json, ci_gate_policy.md, ci_test_inventory.md, ci_quality_baseline.json, ci_consolidation_plan.md, pr51d_validation.md. Atualizados: .github/workflows/ci-offline.yml na raiz Git e aviso no README CI legado. Os arquivos B/C/A listados no plano são cópias identificadas, sem alterações incidentais em suas origens. ci/run.py e as guardas originais permanecem disponíveis e inalterados.

Preservação final: HEAD/status e SHA-256 de todos os arquivos locais A/B/C bateram com o inventário inicial. Nenhum reset/clean/rebase/merge/cherry-pick, operação em produção, alteração de branch protection, commit, push ou PR criado.

## Riscos, limites e recomendação

- A baseline e a política D são candidatas à revisão; não existe comprovação de aprovação humana/branch protection aplicada. Mudanças futuras exigem revisão explícita, sem refresh automático; não há raiz de confiança externa ao repo para um PR que altera o próprio workflow.
- Validação é local no Windows e clone novo com overlay. Execução hospedada e status checks efetivos só poderão ser confirmados após commit/push autorizados. Os nomes estão definidos, mas não foram ativados como obrigatórios no GitHub.
- As guardas de rede são controles de processo para evitar acessos acidentais, não firewall/isolamento hostil de OS. Runner efêmero, leitura mínima e ausência de secrets produtivos continuam necessários para código não confiável.
- CERT_48, manifest de identidade e 22 referências históricas permanecem bloqueadores financeiros independentes. Há também lacunas de proveniência/permissão B3 descritas em C.
- Instalação limpa não comprova artefato de release imutável; builds editable podem incluir metadados variáveis. Não há homologação, rollback/backup verificado nem autorização de implantação nesta entrega.
- Firebase Emulator/cloud e E2E real de browser não foram validados por testes Node/offline.

**Recomendação:** manter em revisão para aprovação explícita da política/baseline e do plano Git antes de commit/push/atualização do PR #48. A consolidação e os gates estão tecnicamente validados localmente; isso não aprova certificação, release ou produção. Nenhum merge ou deploy automático.
