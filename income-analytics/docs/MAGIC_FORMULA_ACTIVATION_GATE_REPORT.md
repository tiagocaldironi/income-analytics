# Magic Formula Stocks — Activation Gate

## Decisão

**Não liberar.** `TOOL_STATUS = VALIDATION_REQUIRED`; nenhum ranking foi
publicado.

## Universo elegível inicial

Bancos, seguradoras, financeiras e emissores sem ação pública foram excluídos.
O conjunto inicial de ações com fundamentos comparáveis era Petrobras, Vale,
Ambev e MRV.

| Métrica | Resultado |
|---|---:|
| total_eligible_issuers | 4 |
| resolved_issuers | 1 |
| ranked_issuers | 0 |
| unresolved_issuers | 3 |
| coverage_percentage | 25% |

## Breakdown de exclusões

| Motivo | Emissores |
|---|---:|
| `UNIT_UNRESOLVED` | 3 (Vale, Ambev, MRV) |

## Correção de escala monetária

Na conferência independente Petrobras 31/12/2025, o DFP retornou EBIT,
caixa, dívida, NWC e imobilizado em **milhares de reais**. O market cap golden
é corretamente expresso em reais. A normalização agora preserva
`ESCALA_MOEDA = MIL`, multiplica por 1.000 com regra explícita e mantém raw
value, escala, multiplicador e valor normalizado no lineage. EV, Earnings
Yield e ROC foram recalculados em BRL unit.

O golden case de **market cap** permanece válido: PETR3/PETR4 somam
R$ 410.254.648.612,52. Petrobras agora é um caso completo de EV/EY/ROC.

## Critérios não atendidos

- Não há 5–10 emissores `RESOLVED` multissetoriais.
- Não há três recomputações completas independentes de fundamentos → ranking.
- Há somente um emissor completo; o universo não alcança cinco emissores.
- Cobertura e exclusões são visíveis, mas não há universo resolvido para ordenar.

O mínimo de cinco emissores vem deste Activation Gate, não é um threshold
inventado para liberar a ferramenta. Uma futura política de cobertura deverá
definir explicitamente universo e limiar, antes de qualquer mudança para
`AVAILABLE`.
