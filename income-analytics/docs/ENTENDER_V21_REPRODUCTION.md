# ENTENDER V2.1 — Reprodução e causa raiz

## Modelo anterior

O `WealthExplanationService` calculava `economic_result` a partir da variação
total, mas calculava valorização de ativos e renda fixa por subconjuntos de
contribuidores. Em seguida calculava `unexplained_change` sem usar uma lista
canônica de componentes assinados. O frontend convertia todos os valores com
`Math.abs`, fazendo componentes negativos parecerem adições.

Como resultado, as linhas mostradas podiam somar mais ou menos que a diferença
entre patrimônio inicial e final. A cobertura ainda era baseada no valor
absoluto de um subconjunto, permitindo `100%` junto de resíduo não nulo.

## Root cause

Não havia uma única identidade de reconciliação. Os pais também não possuíam
filhos auditáveis. Proventos eram adicionados como componente econômico, mas a
variação de valuation não era sempre calculada no mesmo universo de caixa,
ativos, FX e preços persistidos.

## Correção canônica

O serviço passa a retornar `components[]` com `signed_amount`, `direction` e
`children`. A soma dos componentes explicados é calculada primeiro; o único
resíduo é `UNEXPLAINED = closing - opening - explained_sum`. Assim,
`opening + sum(components) = closing` em `Decimal`. A UI apenas apresenta o
sinal entregue pelo backend e permite abrir cada componente.
