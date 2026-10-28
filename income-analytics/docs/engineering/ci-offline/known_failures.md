# Pendências expostas pela primeira CI offline

Referência de código do produto: `ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Nenhum arquivo de `src/`, teste existente, fixture ou manifesto financeiro foi modificado pelo PR5.1. As observações iniciais abaixo foram obtidas com os locks deste PR, em venv nova sem dados pessoais; a validação por SHA está em [validation.md](validation.md).

| Área | Resultado inicial | Diagnóstico e encaminhamento |
|---|---|---|
| Instalação | PASS | 71 wheels com hashes, instalação editável e `pip check` aprovados. |
| Runtime mínimo | PASS | 57 wheels, pytest ausente; app e Alembic carregam com DB descartável. |
| Ruff global | FAIL, 130 diagnósticos | Arquivos do produto/testes/scripts/migrations já presentes na baseline. Nenhum diagnóstico nos arquivos novos de CI após correção de estilo. Não foram usados ignores, baseline de supressão ou autofix em código anterior. |
| mypy strict em `src` | FAIL, 674 erros | Inclui funções sem anotação e incompatibilidades de tipos já presentes no código da baseline. Não foram inseridos `type: ignore` ou mudanças financeiras para obter verde. |
| Python completo | FAIL | 995 passed, 14 failed, 9 errors, 5 skipped, 42 warnings; cobertura informativa de linhas 80,69% na execução exploratória. Não há novo limite de cobertura nem certificação implícita. |
| CERT_48 dedicado | FAIL | Uma função executada, uma falha; esperado, sem waiver. O arquivo exato que primeiro diverge depende dos bytes LF/CRLF do checkout. O CI define checkout de objetos Git em LF; não reescreve o motor. |
| Frontend | FAIL | 29/30 suítes existentes aprovadas; `holdings_v2.mjs` ainda exige texto `Ganho`, removido em alterações anteriores da interface. O autoteste novo da guarda de rede é separado dessas 30 suítes. Não foi reintroduzido o texto nem alterada a asserção. |

## Dependências de evidência fora do clone

Os 13 failures Python além de CERT_48 e os 9 errors estão relacionados a arquivos de evidência/snapshots não incluídos no checkout limpo, não a credenciais a serem fornecidas pela CI:

- `tests/api/test_magic_formula_product_api.py`: sete errors por ausência de `docs/appendices/magic_formula_v12_2/ranking_snapshot.json`.
- `test_magic_formula_canonical_ranking.py`: três failures por ausência de `docs/appendices/magic_formula_v9_2/methodological_universe.csv`.
- `test_magic_formula_methodology_policy_v1.py`: três failures por ausência de `docs/appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv`.
- `test_magic_formula_historical_price_sources_v5.py`, `test_magic_formula_preview.py` e `test_magic_formula_price_availability_audit.py`: referências a snapshots/SQLite externos indisponíveis, retornando erro de abertura de banco; incluem sete failures e dois errors.

Isso comprova uma dependência de parte da suíte existente em estado não versionado. O workflow **não precisa nem aceita o banco pessoal para funcionar**: executa e reporta a falha. Para tornar esses testes herméticos, é necessária revisão futura de evidências públicas/sintéticas e critérios financeiros. Não copiar `data/`, credenciais ou snapshots reais do host e não inventar expected financeiros neste PR.

## Separação das pendências

1. **Infraestrutura CI:** instalação, execução de todos os checks, isolamento e geração de relatórios podem ser avaliados mesmo com dívida do produto visível.
2. **Qualidade de código:** Ruff/mypy exigem tratamento específico, com revisão e sem flexibilização silenciosa das regras.
3. **Fixtures herméticas:** os arquivos ausentes exigem proveniência/revisão próprias; não são motivo para baixar dados live durante CI.
4. **Asserção de UI desatualizada:** revisar em PR de teste/UI separado, preservando a decisão de produto.
5. **Certificação:** reconciliar CERT_48 de forma independente. Não alterar manifesto/hash ou excluir/xfail o teste para liberar merge ou produção.

Falhas continuam retornando exit code diferente de zero. Nenhuma delas foi convertida em sucesso ou skip. Os cinco skips são exclusivamente quatro testes do emulador e um teste cloud já separados por opt-in.
