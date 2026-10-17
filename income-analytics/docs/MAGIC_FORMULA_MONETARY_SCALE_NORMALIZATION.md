# Magic Formula Stocks — normalização de escala monetária

## Unidade canônica

A Fórmula Mágica usa `BRL_UNIT`. O parser CVM preserva `raw_value`, moeda e
`ESCALA_MOEDA`; o normalizador produz valor em reais com `Decimal` e registra a
regra no lineage.

| Escala CVM | Multiplicador | Regra |
|---|---:|---|
| `UNIDADE` | 1 | `MONETARY_SCALE_BRL_UNIT_V1` |
| `MIL` | 1.000 | `MONETARY_SCALE_BRL_THOUSAND_V1` |
| `MILHAO` | 1.000.000 | `MONETARY_SCALE_BRL_MILLION_V1` |
| desconhecida | — | bloqueia como dados insuficientes |

Não existe inferência baseada no tamanho do número. Cada item de lineage agora
retém valor bruto, moeda, escala, multiplicador, valor normalizado e rule ID.

## Petrobras — QA independente, 31/12/2025

O DFP consolidado informa `ESCALA_MOEDA = MIL`. A validação independente aplica
`raw × 1.000` antes de combinar os valores com o market cap B3 em reais.

| Métrica | DFP bruto (R$ mil) | Normalizado (R$) |
|---|---:|---:|
| EBIT | 145.628.000 | 145.628.000.000 |
| Caixa | 35.608.000 | 35.608.000.000 |
| Dívida CP | 67.253.000 | 67.253.000.000 |
| Dívida LP | 316.772.000 | 316.772.000.000 |
| NWC | 29.686.000 | 29.686.000.000 |
| Imobilizado | 924.624.000 | 924.624.000.000 |

Com market cap de R$ 410.254.648.612,52:

- Net debt: R$ 348.417.000.000
- Invested capital: R$ 954.310.000.000
- EV: R$ 758.671.648.612,52
- Earnings Yield: 19,1951287841%
- ROC: 15,2600308076%

O valor de market cap, securities, ações e política temporal não foram
alterados. Snapshots existentes sem escala normalizada não são tratados como
validados; qualquer snapshot novo deve preservar o lineage monetário.
