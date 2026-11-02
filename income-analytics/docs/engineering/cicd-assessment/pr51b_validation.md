# PR5.1B — Correções FE-01 e CODE-01: validação

Data: 28/10/2026. Branch isolada `codex/pr51b-frontend-cvm`, criada de `1bbd2d42686ab0c893790772a05a7845cfbc0295` (estado do PR #48). Baseline financeira: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`.

Validação **local**, Python 3.14.7 / Node 24.19.0, alterações ainda sem commit. Os result.json registram o HEAD ancestral e worktree_dirty=true; não representam nova execução GitHub nem resultado de um SHA já publicado. Dependências travadas do PR5.1 reutilizadas do venv existente, sem instalação adicional; PYTHONPATH dos runners seleciona src/ci deste worktree, não o produto do checkout anterior. O worktree do PR #48 e seus três documentos PR5.1A foram preservados.

## Alterações por arquivo

| Arquivo | Alteração |
| --- | --- |
| tests/frontend/holdings_v2.mjs | Substitui as duas expectativas obsoletas Ganho/Perda por sinal, valor e classe visual. Acrescenta casos positivos, negativos, zero e nulos e verifica ausência dos prefixos. Mantém demais asserções. |
| src/income_analytics/infrastructure/cvm_fundamentals_data.py | Usa CvmSourceSchemaError.code em vez de self.code na rejeição de colunas ausentes. Nenhuma mudança no caminho válido ou nos cálculos. |
| tests/infrastructure/test_cvm_statement_parser.py | 12 casos novos em memória: sete colunas obrigatórias individualmente ausentes, CSV vazio, DFP/ITR válidos e propagação em dois consumidores. |
| docs/engineering/cicd-assessment/pr51b_validation.md | Este relatório: método, evidência, resultados e limites. |

## FE-01

Causa: teste continuava exigindo textos removidos intencionalmente do renderer. A correção altera somente o teste; portfolio.js produtivo não tem diff. São verificados resultado positivo com +, negativo com valor negativo, classes positive/negative, zero com Sem variação e nulo com Resultado indisponível. Os casos adicionais isolam a célula Resultado para não aceitar valores de outra coluna. Formatação pelo helper existente, escape/XSS, busca por acentos, ordenação, nulos ao final, filtros, estados vazios, metas e imutabilidade continuam testados. O helper money é um double deste teste; os testes de frontend existentes continuam cobrindo os demais contratos.

## CODE-01

Causa: o atributo code pertence a CvmSourceSchemaError; self no método é CvmStatementParser. Antes, schema inválido gerava AttributeError. Agora é mantida a exceção de domínio ValueError especializada, code SOURCE_SCHEMA_ERROR e mensagem SOURCE_SCHEMA_ERROR: colunas ausentes em <membro>. Não há novo código arbitrário.

Os ZIPs/CSVs novos são bytes sintéticos em BytesIO, sem arquivos oficiais novos, fixtures, snapshots ou goldens. Os dois casos válidos comparam o CvmRawAccount completo para DFP e ITR; conversão Decimal, escala, escopo, datas e metadados permanecem iguais.

Consumidores inspecionados: scripts/rematerialize_magic_formula_v2.py::run, scripts/recover_petrobras_canonical.py::build_evidence e scripts/build_magic_formula_v12_2.py (chamada parse). Não há captura que transforme o erro em sucesso. Testes negativos dos dois primeiros substituem somente a aquisição dataset por bytes em memória e confirmam propagação de CvmSourceSchemaError antes da construção do repositório; não executam rematerialização/persistência. O gerador V12.2 foi inspecionado estaticamente, sem executar publicação ou adquirir referências ausentes. Integrações válidas phase2 e Petrobras foram executadas em SQLite temporário.

## Resultados e comparação PR5.1A

| Verificação | Baseline | PR5.1B local | Conclusão |
| --- | --- | --- | --- |
| holdings_v2.mjs | Reprovado | Aprovado | FE-01 resolvido |
| Frontend existente | 29/30 | 30/30 | Sem regressão |
| Autoteste Node runner | Aprovado | Aprovado | Agregado 31/31 |
| Parser novo | Ausente | 12/12 | CODE-01 protegido |
| Parser + consumidores direcionados | — | 52/52 | 12 novos + 13 phase2 + 27 Petrobras |
| Python offline completo | 995P / 15F / 9E / 5S | 1007P / 15F / 9E / 5S | +12 aprovados, mesmos status anteriores |
| CERT_48 dedicado | 1 falha | 1 falha | Preservada; sem dispensa |
| Ruff completo | 130 | 130 | Multiconjunto idêntico, nenhum novo |
| Mypy src | 674 | 673 | Somente attr-defined em cvm_fundamentals_data.py:59 removido |
| Cobertura de linha informativa | 80,69% | 80.69% | Não representa certificação |

A execução completa final foi feita após a inclusão de todos os testes. A primeira passagem tinha coletado dez casos novos antes da adição dos dois de consumidores (1005P/15F/9E/5S); foi repetida para validar o conjunto final de 12. Nenhum caso antigo foi removido e nenhum mudou de status: comparação por (classe, nome) contra o artefato do run 40692226171. Não houve skip/xfail novo.

## Execução e isolamento

Com ambiente PR5.1 provisionado e diretório de trabalho income-analytics/:

```powershell
node tests/frontend/holdings_v2.mjs
python ci/run.py node
python ci/run.py python
python ci/run.py ruff
python ci/run.py mypy
python ci/run.py cert48
```

Os comandos foram executados com o Python absoluto do venv PR5.1; o runner reutiliza sys.executable. A execução direcionada usou ci/run.py::isolated_environment + execute, pytest -p offline_plugin e os arquivos tests/infrastructure/test_cvm_statement_parser.py, tests/application/test_magic_formula_phase2_integration.py e tests/application/test_petrobras_canonical_e2e.py. Seu JUnit temporário registrou 52 aprovados.

O runner allowlista variáveis, usa HOME/USERPROFILE e SQLite temporários, desativa jobs externos/Firebase opt-in e aplica bloqueio de rede. Migrações feitas pelos testes se limitaram aos SQLite descartáveis. Nenhum banco pessoal/produtivo ou credencial Admin de produção foi utilizado. As quatro integrações Emulator e uma live continuam explicitamente skipped offline; não contam como aprovadas.

Relatórios sanitizados locais: ci-reports/{python,node,ruff,mypy,cert48}/result.json, JUnit/coverage do Python. São ignorados pelo Git. Logs brutos ficaram em diretórios temporários privados; não foram publicados. Os resultados Ruff/mypy foram comparados por multiconjunto (arquivo, linha, regra), incluindo duplicações; o único removido é o attr-defined do parser. Ruff dos dois arquivos Python alterado/novo também passou isoladamente.

## Riscos remanescentes e recomendação

- 22 ocorrências Python por referências ausentes continuam independentes desta correção: V8/V9.2/V12.2 e universo SQLite/replay CVM ainda precisam de recuperação auditável.
- CERT_48 e a integridade da fixture de identidade permanecem bloqueadoras de certificação/promoção, sem alteração de bytes congelados, manifests, hashes ou expectativas.
- Restam 130 Ruff e 673 mypy; esta entrega não saneia dívida transversal nem estabelece CI integralmente verde.
- O caminho negativo do publicador V12.2 foi revisado por código; não houve replay completo com os inputs ausentes. Nenhuma conclusão sobre certificação dessa publicação decorre destes testes.

**Recomendação:** aprovar tecnicamente as correções pontuais FE-01/CODE-01 para revisão e eventual merge consciente das pendências preexistentes. O resultado não aprova integralmente PR5.1, não certifica regras financeiras e não autoriza produção. Nenhum commit, push, merge ou deploy foi realizado automaticamente.
