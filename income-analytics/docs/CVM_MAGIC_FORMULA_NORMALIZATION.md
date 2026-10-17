# CVM Magic Formula — normalização contábil

## Registry V1 corrigido

O adapter `CVM_MAGIC_FORMULA_ADAPTER_V1` ainda não havia sido liberado nem
possuía snapshots de produção persistidos quando a revisão do DFP 2025 revelou
o defeito abaixo. Por isso a correção foi feita no V1, com registro explícito,
sem reescrever resultados históricos.

| Métrica normalizada | Demonstração | Conta CVM | Rule ID | Regra |
|---|---|---:|---|---|
| EBIT | DRE | 3.05 | EBIT_RULE_002 | Resultado antes do resultado financeiro e dos tributos |
| Caixa e equivalentes | BPA | 1.01.01 | CASH_RULE_001 | Não inclui aplicações financeiras |
| Dívida financeira CP | BPP | 2.01.04 | DEBT_ST_RULE_001 | Empréstimos e financiamentos circulantes |
| Dívida financeira LP | BPP | 2.02.01 | DEBT_LT_RULE_001 | Empréstimos, financiamentos e debêntures não circulantes |
| Ativos correntes operacionais | BPA | 1.01.03, 1.01.04 | NWC_ASSET_RULE_002 | Clientes e estoques; escopo estreito e auditável |
| Passivos correntes operacionais | BPP | 2.01.02 | NWC_LIABILITY_RULE_001 | Fornecedores |
| Imobilizado líquido | BPA | 1.02.03 | FIXED_ASSET_RULE_001 | Não usa todo o ativo não circulante |

## Exclusões deliberadas

`1.01.02 — Aplicações Financeiras` não pertence ao ativo circulante
operacional e também não é convertido automaticamente em caixa. Contas sem
regra estrutural explícita permanecem fora da normalização; o resultado é
`INSUFFICIENT_DATA`, nunca uma aproximação por descrição ou subtotal.

Todo item aceito mantém no lineage a conta CVM, descrição, valor bruto,
rule ID, escopo, período, dataset e versão do adapter.
