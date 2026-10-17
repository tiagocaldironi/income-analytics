# Magic Formula Stocks — validação de dados reais

## Escopo

Esta é uma amostra de validação do registry, não uma ativação do ranking. Foram
lidos os DFPs CVM consolidados de 2025, referência `2025-12-31`, com valores
em milhares de reais conforme o arquivo da CVM. O adapter usa somente contas
consolidadas da mesma companhia e da mesma data.

## QA do registry

| Companhia (CD_CVM) | Métrica | Conta | Valor bruto / normalizado | Rule ID | Resultado |
|---|---|---:|---:|---|---|
| Votorantim Cimentos (027189) | EBIT | 3.05 | 4.062.000 | EBIT_RULE_002 | PASS |
| Vale (004170) | EBIT | 3.05 | 31.969.000 | EBIT_RULE_002 | PASS |
| Localiza Fleet (024813) | EBIT | 3.05 | 2.908.592 | EBIT_RULE_002 | PASS |
| MRV (020915) | EBIT | 3.05 | 201.196 | EBIT_RULE_002 | PASS |
| Ambev (023264) | EBIT | 3.05 | 23.423.386 | EBIT_RULE_002 | PASS |

Todas as cinco possuíam as contas obrigatórias do registry corrigido:
`1.01.01`, `2.01.04`, `2.02.01`, `1.01.03`, `1.01.04`, `2.01.02` e `1.02.03`.
O adapter devolveu `VALID` para cada conjunto consolidado, sem misturar
períodos ou demonstrações individuais.

## Evidência da exclusão de aplicações financeiras

| Companhia | 1.01.02 excluída | OCA normalizado (1.01.03 + 1.01.04) |
|---|---:|---:|
| Votorantim | 938.000 | 5.944.000 |
| Vale | 1.066.000 | 45.305.000 |
| Localiza Fleet | 2.338.762 | 921.134 |
| MRV | 0 | 9.639.841 |
| Ambev | 1.681.692 | 16.871.698 |

Os valores da primeira coluna não entram em caixa nem em OCA. O lineage
persistido para cada métrica leva o código, descrição, valor bruto, valor
normalizado, rule ID, escopo, dataset, versão e início/fim de período.

## Limites e próximo gate

O confronto contábil confirmou o mapeamento estrutural, mas não substitui a
validação independente de capital social por classe, preço B3 na mesma data,
market cap, EV, cobertura de universo e exclusões setoriais. Assim, o status
permanece `VALIDATION_REQUIRED`; nenhum ranking foi calculado ou publicado.
