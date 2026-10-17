# Magic Formula Stocks — cobertura parcial de ações históricas

## Estado

A resolução de market cap ocorre por emissor. Ela não libera ranking global e
não muda `TOOL_STATUS = VALIDATION_REQUIRED`.

## Status por emissor

| Status | Significado |
|---|---|
| `RESOLVED` | todas as classes relevantes, unidades, datas e preços passaram |
| `UNIT_UNRESOLVED` | a escala da quantidade do DFP não foi comprovada |
| `SECURITY_UNRESOLVED` | não há security/ticker/classe histórico confiável |
| `TEMPORAL_CONFLICT` | referência de shares, preço ou evento societário conflita |
| `INSUFFICIENT_MARKET_DATA` | falta classe, preço ou outro componente obrigatório |

Apenas `RESOLVED` produz market cap. Qualquer outro status deixa o valor nulo e
registra o motivo auditável; não há multiplicador padrão.

## Cobertura

O serviço calcula `total_eligible_issuers`, `resolved_market_cap_issuers`,
`unresolved_market_cap_issuers` e `coverage_percentage`. A futura ativação
definirá explicitamente o universo elegível e o limiar de cobertura; 100% do
mercado não é um requisito implícito.

## Petrobras — golden case permanente

Para 31/12/2025, PETR3 e PETR4 mantêm as quantidades, preços e market cap de
R$ 410.254.648.612,52 já validados. O lineage por classe é:

| Campo | PETR3 e PETR4 |
|---|---|
| shares source | `CVM_DFP` |
| security source | `CVM_FCA` |
| price source | `B3_COTAHIST` |
| supplemental B3 atual | somente `validation_evidence_only` |

Nenhuma mudança nesse caso é aceita sem nova evidência, alteração metodológica
versionada e atualização explícita do teste de regressão.

## Gaps separados

- **Source gap:** não há acesso público demonstrado a uma série B3 versionada
  de outstanding shares por classe.
- **Issuer-specific data gap:** Vale, Ambev e MRV têm unidade do DFP ainda não
  comprovada para sua referência.
- **Non-eligible security:** Votorantim Cimentos e Localiza Fleet não têm ação
  pública identificada no FCA da amostra; não são falhas de preço.
