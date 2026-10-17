# Magic Formula Stocks — Historical Shares Resolution Spike

## Decisão

`RECOMMEND_HYBRID_HISTORICAL_SHARES`, com aprovação **por emissor e por
referência**, não por regra global. A combinação aceita é:

1. CVM DFP composição de capital: ON, PN, tesouraria e data histórica;
2. CVM FCA: classe, ticker e vigência da security;
3. B3 COTAHIST: preço até a data solicitada;
4. B3 Empresas Listadas: reconciliação de semântica/unidade quando a estrutura
   de capital não mudou.

Não há evidência de acesso público versionado ao histórico de
`OutstandingShares`/`PositionOfShareholders` do UP2DATA. Esses produtos são a
fonte B3 preferível para escala universal, mas requerem licença para serem
considerados como fonte operacional ampla.

## Golden case — Petrobras

Referência financeira: `2025-12-31`. O DFP CVM contém quantidades por classe,
sem tesouraria; o FCA 2025 registra PETR3 como ON e PETR4 como PN, ambas válidas
desde 2018. A resposta pública B3 atual coincidiu exatamente com os totais DFP
e lista os últimos desdobramentos/grupamentos em 2008; ela foi usada somente
como reconciliação de unidade, não como proxy temporal.

| Classe | Ticker | Ações emitidas | Tesouraria | Outstanding | Preço solicitado | Pregão efetivo | Preço | Market cap parcial |
|---|---|---:|---:|---:|---|---|---:|---:|
| ON | PETR3 | 7.442.231.382 | 0 | 7.442.231.382 | 31/12/2025 | 30/12/2025 | R$ 32,57 | R$ 242.393.476.111,74 |
| PN | PETR4 | 5.446.501.379 | 0 | 5.446.501.379 | 31/12/2025 | 30/12/2025 | R$ 30,82 | R$ 167.861.172.500,78 |

**Market cap total: R$ 410.254.648.612,52.** Todos os componentes são
`Decimal`, possuem fonte e referência e passam a política temporal.

## Reconciliação da amostra

| Emissor | DFP 2025 | B3 atual | Resultado |
|---|---|---|---|
| Petrobras | ON/PN coincidem exatamente | ON/PN coincidem | RESOLVED para 31/12/2025 |
| Vale | `4.539.007` ON | `4.439.159.752` ON | UNIT_UNRESOLVED / possível evento ou escala |
| Ambev | `15.761.639` ON | `15.484.664.889` ON | UNIT_UNRESOLVED / diferença temporal e escala |
| MRV | `562.827` ON | `562.835.771` ON | UNIT_UNRESOLVED / escala precisa de prova documental |

Não se infere multiplicador `1.000` para Vale, Ambev ou MRV. Cada uma fica
fora de market cap até a prova por fonte oficial temporalmente adequada.

## Corporate actions e limites

O endpoint B3 suplementar lista eventos históricos, mas não fornece uma série
versionada de ações outstanding. Split, grupamento, bonificação, conversão ou
aumento/redução de capital após a referência tornam a reconciliação insuficiente
e devolvem `TEMPORAL_CONFLICT`/`UNIT_UNRESOLVED`.

## Status

- Petrobras: shares históricos `RESOLVED` para a referência validada.
- Demais emissores: `DATA_GAP` até evidência específica.
- Universo/ranking: `HISTORICAL_SHARES_STATUS = DATA_GAP`,
  `MARKET_DATA_STATUS = DATA_GAP`, `TOOL_STATUS = VALIDATION_REQUIRED`.
