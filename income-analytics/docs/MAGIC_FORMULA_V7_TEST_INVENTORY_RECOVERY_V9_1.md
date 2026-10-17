# Magic Formula V7 test inventory recovery V9.1

## Resultado

`MAGIC_FORMULA_V7_TEST_INVENTORY_RECOVERY_V9_1 = FAIL` — não há evidência histórica suficiente para comparar os 274 IDs V7 com V8. A política continua `MF_BR_2027_V1_DRAFT` (`BLOCKED`).

## Evidências históricas

- Git disponível; HEAD `5a9f7ca7215c14463061e963502e95ae863ca536` em `C:\Projetos`. Os branches/tags preservados chegam a uma base de agosto de 2026, anterior aos artefatos V7; não há commit para os caminhos do relatório, manifesto ou teste V7.
- Há 2 refs `refs/codex/turn-diffs/checkpoints`, mas são objetos tree, não revisões commitáveis. A inspeção de seus caminhos não encontrou o teste/relatório V7.
- O `.pytest_cache` disponível foi atualizado em 13/10 e contém IDs da coleta atual; não é cache histórico V7. Nos caminhos acessíveis, não foi localizado JUnit/XML, pytest JSON ou manifest histórico com node IDs. A busca não pôde ser completa: vários diretórios basetemp antigos negam leitura por ACL.
- A configuração atual é `pyproject.toml`: `testpaths=tests`, `pythonpath=src`, `addopts=--import-mode=importlib`; não há `pytest.ini`, `setup.cfg` ou `tox.ini`. Sem revisão V7, não é possível provar que essa configuração já valia naquela execução.
- O arquivo atual `test_magic_formula_eligibility_policy_v7.py` coleta 48 casos no working tree de hoje. Seu nome/estado atual não prova que esses sejam os IDs da V7 completa.
- Os checkpoints foram somente lidos. Nenhum checkout, reset ou substituição do working tree ocorreu.

## Inventários e contagens

- V7 reportado: 274; V7 verificado: desconhecido. O manifesto V7 descreve dados/snapshot e não tem contagem nem node IDs de teste.
- V8 reportado: 243. Uma coleta atual dos arquivos `test_magic_formula_*.py`, excluindo os 30 testes de política V9.0 adicionados posteriormente, retorna 243 node IDs. A contagem bate, mas sem revision V8 só é evidência parcial, não inventário V8 histórico verificado.
- Suíte Magic Formula atual: 273 node IDs; 273 executados, 273 passaram, 0 falhas, 0 erros, 0 skipped. JUnit atual: `tmp/magic_formula_v9_1_junit.xml`.
- A diferença reportada permanece -31. Como os IDs V7 não existem em evidência recuperável, V7_ONLY, V8_ONLY e as categorias de classificação não podem ser calculadas sem inventar dados. `NOT_DISCOVERED=31` é o delta agregado, não 31 linhas com nomes presumidos.

## Regressões críticas atuais

Os 18 temas estão mapeados para testes atuais e a suíte atual passou. Para todos, o campo de teste V7 permanece `NOT_RECOVERED`; logo a cobertura atual não prova continuidade histórica e `CRITICAL_REGRESSION_LOST=UNKNOWN`.

## Gate e escopo

QUALIDADE ATUAL: 273/273 testes passaram; Ruff do gerador=PASS; suíte atual de regressão=PASS; hash do manifest determinístico=YES (`fd574a4bbe22a4459f41380b0e6dbdd841119df3aa7ff6a1cc17d0ba4c4cf8ca`).

`RECONCILIATION_PATH=NONE`; `ACCIDENTALLY_DROPPED=UNKNOWN`; `UNEXPLAINED=31`; `CRITICAL_REGRESSION_LOST=UNKNOWN`; `GATE_01_TEST_RECONCILIATION=FAIL`. O caminho B também não se aplica: não há evidência para provar que 274 era contagem errada nem reconstruir a transição V7→V8.

A auditoria não alterou metodologia, S4, L3, screening, market cap ou snapshot. Nenhum ranking/Top 30 foi calculado/publicado. A política permanece DRAFT. A limitação restante é obter uma revisão V7 ou artefato de execução que contenha os node IDs coletados; sem isso, não é possível diferenciar substituição deliberada de perda acidental.

## Artefatos

- `docs/appendices/magic_formula_v9_1/v7_test_inventory.csv` está somente com cabeçalho porque nenhuma linha histórica verificável foi encontrada.
- `v8_test_inventory.csv` contém 243 IDs da reconstrução atual, marcados `PARTIAL`.
- `test_inventory_diff.csv` e `test_semantic_reconciliation.csv` não contêm correspondências inferidas.
- `critical_regression_map.csv`, `test_manifest_current.json` e `reconciliation_gate.json` documentam a cobertura atual, execução, hashes e decisão do gate.
