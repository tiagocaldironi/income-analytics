# Magic Formula — fechamento de regressões e gate de release V12.1

**Resultado:** `V12_11_REGRESSION = FAIL` · `MAGIC_FORMULA_FEATURE_READY_FOR_USE = NO`

As 43 falhas originais foram classificadas e os defeitos de schema, carteira, importação B3 e fixture de ações históricas foram corrigidos. As validações finais passaram: 831/831 na suíte completa, 273/273 no baseline V9.2 e 34/34 nos testes focados. O release continua bloqueado por um look-ahead confirmado no snapshot V11.

## Inventário e causas originais

O XML original tinha 831 testes: 788 PASS, 18 FAIL e 25 ERROR de setup. Os 43 problemas pertencem a cinco causas, sem UNKNOWN:

| ID | Problemas | Categoria | Causa e resolução |
|---|---:|---|---|
| RC01 | 26 | SCHEMA/MIGRATION_DEFECT | Petrobras exigia o revision 0016 como head exato, embora a base de teste estivesse no descendente válido 0018. O contrato agora valida head único e ancestralidade. |
| RC02 | 14 | SHARED_COMPONENT_REGRESSION | UUID aleatório desempata eventos/cotações no mesmo instante e vendas econômicas completas eram descartadas. Ordenação estável e tratamento de venda foram corrigidos. |
| RC03 | 1 | TEST_EXPECTATION_OBSOLETE | Um teste B3 esperava revisão para toda liquidação, em conflito com o contrato do parser para liquidação completa. A expectativa foi alinhada e duplicidade entre relatórios passou a ser detectada. |
| RC04 | 1 | EXISTING_REPOSITORY_DEFECT | Liquidação sem dados financeiros era exibida como NEW; agora fica REVIEW_REQUIRED e não é aplicada. |
| RC05 | 1 | TEST_FIXTURE_DEFECT | Manifesto de ações históricas continha hashes congelados obsoletos; os hashes foram conferidos e atualizados. |

Todas as causas foram classificadas como não introduzidas pela Fórmula Mágica V10–V12. `MAGIC_FORMULA_REGRESSION=0`, `ENVIRONMENT_SETUP_DEFECT=0`, `UNKNOWN=0`.

### Petrobras e schema

O golden evidence esperava `0016_magic_formula_canonical_contract` como versão exata. O schema de teste está em `0018_portfolio_price_refresh_runs`, cadeia válida `0016 → 0017 → 0018`, com um único head. A checagem foi corrigida para validar a revisão contratual na ancestralidade; não houve migration destrutiva nem alteração de banco real. Os 25 erros de setup e o teste Petrobras adicional passaram.

## Auditoria temporal — bloqueio de release

O código usa `ACCOUNTING_CUTOFF=2026-10-13` como limite efetivamente aplicado à data de protocolo CVM, não apenas como data da auditoria. Porém, o snapshot é apresentado com referência histórica de preço e ranking `2025-12-30` e usa fundamentos FY2025 (`2025-12-31`). Os 174 protocolos FY2025 ocorreram em 2026, depois da referência de preço.

Portanto, embora os documentos estejam dentro do corte contábil configurado, os **174/174** não estavam disponíveis em 30/12/2025. Isso é look-ahead para um ranking histórico daquela data. Não alterei metodologia, universo ou ranking para esconder essa divergência. O gate temporal fica FAIL até reconstruirmos os fundamentos disponíveis em 30/12/2025 e recalcularmos o snapshot. A auditoria por ticker, período e data de protocolo está em `temporal_semantics_audit.json`.

## Resultado das validações

| Verificação | Resultado |
|---|---|
| Suíte completa | 831 PASS · 0 FAIL · 0 ERROR · 0 SKIP |
| Baseline V9.2 | 273/273 PASS |
| Testes focados da feature | 34/34 PASS |
| Ruff nos nove arquivos Python relevantes à correção | PASS |
| Ruff global (`src tests scripts`) | 121 ocorrências fora do escopo da correção; não apliquei reformatação ampla não relacionada |
| Snapshot dry-run | mesmo ID, 174 empresas e mesmo hash V11; não persistido |
| Policy `MF_BR_2027_V1` | hash preservado; política, S4, L3, exclusões financeiras e screening inalterados |
| Interface | testes automatizados cobriram snapshot persistido, busca, filtros varejo/aviação, paginação, metodologia e cards mobile; smoke manual no navegador não executado |
| Performance | 100 leituras: p50 21,791 ms; p95 30,678 ms; limite 250 ms — PASS |
| Manifesto | 831 node IDs; hash SHA-256 registrado |

## Gates V12.1

PASS: `01` inventário, `02` zero UNKNOWN, `03` schema, `04` Petrobras, `05` carteira, `06` B3, `07` ações históricas, `08` baseline V9.2, `09` testes focados, `10` suíte completa, `11` Ruff no escopo da correção, `12` política inalterada, `15` integridade do snapshot, `16` smoke automatizado da UI, `17` performance e `18` manifesto.

FAIL: `13` semântica temporal válida e `14` no-look-ahead confirmado. Esses dois gates representam a mesma causa técnica, RC06: fundamentos posteriores à referência histórica de 30/12/2025 foram selecionados.

**Conclusão:** os 43 problemas de regressão foram encerrados; a feature ainda não está liberada. A única causa funcional restante é RC06, look-ahead temporal comprovado em 174 empresas. Corrigir exige selecionar/reconstruir fundamentos publicamente disponíveis até 30/12/2025, preservar `MF_BR_2027_V1` e então recalcular e validar integralmente o ranking.

## Artefatos

- `docs/appendices/magic_formula_v12_1/full_suite_failures.csv`
- `docs/appendices/magic_formula_v12_1/root_causes.csv`
- `docs/appendices/magic_formula_v12_1/schema_head_diagnostic.json`
- `docs/appendices/magic_formula_v12_1/temporal_semantics_audit.json`
- `docs/appendices/magic_formula_v12_1/regression_validation.json`
- `docs/appendices/magic_formula_v12_1/test_manifest.json`
- `docs/appendices/magic_formula_v12_1/release_gate.json`
