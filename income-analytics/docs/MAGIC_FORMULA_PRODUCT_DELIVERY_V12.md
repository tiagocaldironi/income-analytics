# Fórmula Mágica — V12: entrega de produto

A tela de Fórmula Mágica está disponível em Ferramentas. Ela consome snapshot persistido, oferece busca, filtros pós-ranking, paginação, cards de cobertura e explicação metodológica, detalhes e provenance. Desktop usa tabela; mobile usa cartões. Sem snapshot, apresenta estado vazio; durante busca, carrega estado de loading; falhas não mostram exceções internas. A abertura da tela não recalcula o ranking.

- `V12_01_READ_MODEL`: PASS
- `V12_02_APPLICATION_CONTRACT`: PASS
- `V12_03_UI`: PASS
- `V12_04_SEARCH`: PASS
- `V12_05_FILTERS`: PASS
- `V12_06_PAGINATION`: PASS
- `V12_07_GLOBAL_RANK_IMMUTABLE`: PASS
- `V12_08_METHODOLOGY_HELP`: PASS
- `V12_09_MOBILE`: PASS
- `V12_10_PERFORMANCE`: PASS
- `V12_11_REGRESSION`: FAIL
- `V12_12_RUFF`: PASS
- `V12_13_TEST_MANIFEST`: PASS

Artefatos: `docs/appendices/magic_formula_v12/`.


Validação executada: baseline V9.2 273/273 passou; testes focados da feature 34/34 passaram. Suíte completa: 788 passaram, 18 falharam e 25 tiveram erro de setup. `MAGIC_FORMULA_FEATURE_READY_FOR_USE` = NO.
