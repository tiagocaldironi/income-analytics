# PR5.1C — Validação e pendências

Data: 28/10/2026. **Entrega parcial comprovada; recuperação dos 22 casos ainda bloqueada.** Não houve produção de snapshots novos, alteração de algoritmo/expectativa, skip/xfail ou waiver de certificação.

## Git e identidade do candidato

PR #48 permanece aberto em draft, head `1bbd2d42686ab0c893790772a05a7845cfbc0295`, base `ca627ac72f110d0f4d62faaa9c51a08eaed54965`, consultados pelo conector GitHub. Branch C: `codex/pr51c-magic-formula-references`, worktree isolado criado do head exato. Branch B não tem commits próprios: seus quatro arquivos sem commit foram copiados explicitamente; fonte B permanece byte a byte igual. Nenhum reset, cherry-pick, merge, rebase, alteração de develop ou trabalho no checkout produtivo.

Testes locais executados com HEAD **1bbd2d42686ab0c893790772a05a7845cfbc0295** e alterações sem commit (worktree_dirty=true nos reports). Não há SHA de commit novo: a proibição de commit/push automático foi respeitada. Não apresentar estes resultados como Actions publicado para um SHA candidato novo. A impressão de conteúdo abaixo vincula a execução aos arquivos efetivos além do HEAD ancestral.

## O que foi recuperado e o que foi implementado

- Snapshot V12.2 e universo ed8a autenticados contra digests históricos já versionados, sem recalcular ranking. As seis cópias CVM foram autenticadas pela cadeia source_manifest_hash do V12.2. A autenticidade desses conteúdos não autoriza redistribuição de seus componentes B3.
- Manifesto novo [magic_formula_reference_provenance.json](magic_formula_reference_provenance.json): 19 entradas, 9 VERIFIED, 2 RECOVERABLE, 7 BLOCKED, 1 REJECTED. Uma entrada ci_approved=true. Hash observado hoje e hash ancorado anteriormente são diferenciados.
- Fixture aprovada `tests/fixtures/cvm/receipt_index_2025_v1/dfp_cia_aberta_2025.csv.gz` + README: índice original CVM com atribuição/ODbL, sem informações de carteiras ou anexos de contatos. Não é ZIP contábil completo nem golden financeiro.
- `ci/magic_formula_references.py`: verifica estado, aprovação, caminho e dois digests, recusa ausência/divergência, provisiona ZIP index-only determinístico em TEMP sem sobrescrever. Sem downloads/DB/fallback financeiro.
- `tests/infrastructure/test_magic_formula_ci_reference_bundle.py`: 9 testes de integridade, schema, uso pelo consumidor de datas, determinismo e rejeições de segurança/pendências. Nenhuma expectativa histórica foi modificada.
- [Inventário](magic_formula_reference_inventory.md) e [desenho da fixture](magic_formula_ci_fixture_design.md): origem, cadeia V6→V12.2, licenças, schema/rowids/timestamps, aprovação e estratégia para o pack completo.

O workflow existente coleta o novo teste via tests/; nenhum workflow ou runner existente foi alterado para ignorar falhas. A integração final de GitHub depende de revisão/commit/push autorizados. O DB de origem foi apenas inventariado em leitura imutável e permaneceu intacto; nenhum teste o abriu. Não houve cópia de DB ou JSON B3 para fixtures distribuíveis.

## Resultados efetivos

Python 3.14.7, Node 24.19.0, dependências travadas já disponíveis no venv PR5.1; instalação adicional não executada. Todos os subprocessos de validação usaram ci/run.py::isolated_environment, guardas offline, jobs externos desligados, env allowlist e SQLite TEMP, sem credenciais herdadas de produção.

| Verificação | Baseline B | Resultado C | Leitura correta |
| --- | --- | --- | --- |
| Python completo offline | 1007P / 15F / 9E / 5S | **1016P / 15F / 9E / 5S** | +9 testes aprovados; todos os casos antigos conservam status |
| 22 casos afetados, seleção explícita | 13F / 9E | **13F / 9E** | Referências não aprovadas continuam ausentes; não exercem suas asserções históricas |
| Testes novos do pack | — | **9/9** | Somente índice CVM/provisionador e negativas de segurança |
| Arquivo limpo + overlay explícito | — | **9/9** | Sem diretório data/ ou arquivos ignorados locais |
| Frontend existente | 30/30 | **30/30** | Mais autoteste runner: 31/31 agregado |
| Ruff global | 130 | **130** | Mesmo multiconjunto (arquivo/linha/regra) de B |
| Mypy src | 673 | **673** | Mesmo multiconjunto de B |
| CERT_48 na suíte completa | Reprovado | **Reprovado** | Nenhuma mudança/dispensa |
| Fixture de identidade na suíte | Reprovada | **Reprovada** | Fora do escopo |
| Cobertura informativa | 80,69% | **80,79%** | Não é certificação financeira |

A execução completa levou 222,102s. Os nove testes foram coletados na execução final. A primeira passagem em C antes desses testes manteve 1007P/15F/9E/5S; a final foi repetida com os nove presentes. Não há redução dos 22 bloqueios históricos para reivindicar como sucesso.

Regressões de contratos existentes executadas na suíte completa: canonical_contract 32P; point_in_time 6P; universe 25P; historical_price 20P; Petrobras e2e 27P. Canonical_ranking tem 1P/3F (os builders ainda sem pack); historical_price_sources_v5 tem 11P/1F; methodology_policy_v1 tem 27P/3F. Testes de idempotência/append-only/determinismo que dependem dos inputs ausentes continuam sem validação do contrato histórico real. Aprovações unitárias não substituem esse bloqueio.

Quatro testes Emulator e um cloud continuam explicitamente skipped offline, sem skip novo. Nenhum teste foi removido ou mudou de status frente a B, comprovado por comparação de (classe,nome,status) dos result.json.

## Comandos e evidência reproduzível

Com ambiente travado provisionado e diretório income-analytics/:

```powershell
python ci/run.py python
python ci/run.py node
python ci/run.py ruff
python ci/run.py mypy
```

Foram usados o Python absoluto do venv PR5.1 e os scripts deste worktree; PYTHONPATH isolado aponta para o src/ci correto. Execuções adicionais dirigidas usaram execute/isolated_environment do mesmo runner, pytest -p offline_plugin e JUnit em TEMP: os nove testes do pack e os 22 IDs da triagem, excluindo os dois casos de certificação. Reports sanitizados estão em ci-reports/{python,node,ruff,mypy}/result.json e JUnit/coverage; são ignorados pelo Git, sem payloads financeiros.

Reprodução sem arquivos ignorados: `git archive HEAD income-analytics` a partir da raiz Git foi extraído para TEMP; somente os oito arquivos listados abaixo foram sobrepostos, sem data/, DB ou apêndices locais. A coleta/execução do pack nesse diretório novo passou 9/9 usando o ambiente offline. É reprodução da árvore ancestral com overlay explícito, não alegação de clone de commit ainda inexistente. Metadados temporários: income-pr51c-clean-run-izuf74gz/validation.json; execução limpa em income-pr51c-clean-ec2gamqf/income-analytics. Nenhum dataset foi baixado.

Falha de desenvolvimento resolvida: inicialmente dois testes tentaram provisionar no basetemp pytest, irmão de TEMP no runner, e foram recusados pelo limite de escrita. Os testes passaram a criar TemporaryDirectory sob o TEMP verdadeiro; a proteção do provisionador não foi relaxada. Nova execução dirigida e suíte final aprovaram os nove casos. Isso não foi convertido em skip ou omitido da validação.

## Identidade dos arquivos executados

Impressão SHA-256 do mapa ordenado a seguir: `f28d5e7a3ce010129f75879b295496fa029b47afdd3d14198e6ababa8627752b`.

| Arquivo | SHA-256 |
| --- | --- |
| ci/magic_formula_references.py | af0631fdfe331e7d8fd95f1b87c1f91a61a0e96e8d05b055340b1475eec5586b |
| tests/infrastructure/test_magic_formula_ci_reference_bundle.py | 229c5c0c4a965341d0daa1747d3a1394e7ca4878f62c1bdedd2cabf43dab732b |
| tests/fixtures/cvm/receipt_index_2025_v1/dfp_cia_aberta_2025.csv.gz | 420c5dffb1a9504a74dd2f98632acb5f47df764415cce17d10d9e2384bf1592f |
| tests/fixtures/cvm/receipt_index_2025_v1/README.md | 696ef00d430e681674558cee93e954c49e9e125a33228c5d6972c6e227e7ce50 |
| docs/engineering/cicd-assessment/magic_formula_reference_provenance.json | c8ace928d1571592e149f2a8d274bbb745c74f3f52dc0c0c0ca21d8f9c5ec8b6 |
| src/income_analytics/infrastructure/cvm_fundamentals_data.py | f11731d3d2979557e1725109517baa4006a83d6f3eb7f87c6215a42b91aff1ba |
| tests/frontend/holdings_v2.mjs | dbf33cbb87ebf114f43845303ab8376465edc75df14d2e4bd896a8ae4c893cac |
| tests/infrastructure/test_cvm_statement_parser.py | 98661de24afd2bf63577371073ffff8a1e5c6abd5df38fbb26aae9784c8a4843 |

## Critérios de aceite e bloqueadores

| Critério | Estado |
| --- | --- |
| Referências usadas são verificadas/reproduzíveis | Atendido para índice aprovado; pack histórico completo BLOCKED |
| Os 22 casos executam asserções históricas reais | **Não atendido** — referências não aprovadas permanecem ausentes |
| Sem regressões adicionais | Atendido na validação local final |
| Contratos financeiros/metodológicos intactos | Atendido; sem diff financeiro/expectativas congeladas |
| Sem dados pessoais/credenciais em fixture/artefatos | Atendido no material incluído; DB/JSON B3 não distribuídos |
| Validação por SHA candidato | HEAD exato + fingerprint registrados; commit candidato/Actions dependem de autorização |
| Indisponibilidades documentadas | Atendido no inventário/manifesto |

Bloqueadores independentes: (1) CSVs V8/V9.2 sem digest histórico completo/por linha independente; (2) predecessores do DB, inclusive 6d418… e registros empatados, com autoconsistência mas sem autenticação histórica completa; (3) permissão B3 aplicável não localizada; (4) inventário documental completo de ações/identidades necessário para replay amplo. Não basta usar um artefato privado para contornar licença. Não executar geradores para substituir o golden e não fabricar registros com IDs antigos.

**Recomendação:** revisar a parte comprovada e a fixture/provisionador mínimos; manter PR5.1C completo bloqueado até recuperar/aprovar o pack histórico. Não recomendar declaração de CI estabilizada nem promoção de produção. CERT_48 e o manifest de identidade continuam fora do escopo e bloqueiam certificação. Sem commit, push, merge, deploy ou migration produtiva automáticos.
