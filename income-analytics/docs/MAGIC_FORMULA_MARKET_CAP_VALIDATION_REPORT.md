# Magic Formula Stocks — validação temporal de Market Cap

## Estado

- `MARKET_DATA_STATUS`: `DATA_GAP`
- `TOOL_STATUS`: `VALIDATION_REQUIRED`
- Ranking: **não ativado**.

## O que foi implementado e passou em teste

| Caso | Resultado |
|---|---|
| Uma classe | `shares × price` usa `Decimal` |
| ON + PN | soma por classe sem usar uma classe como proxy |
| Preço ausente | `INSUFFICIENT_MARKET_DATA` |
| Data solicitada incompatível | `TEMPORAL_INCONSISTENCY` |
| Fim de semana | data solicitada e último pregão anterior preservados |
| Lineage | fonte/referência de ações e preço por classe persistíveis no componente |

## Fonte e evidência real

O arquivo oficial `dfp_cia_aberta_composicao_capital_2025.csv` foi localizado
no DFP CVM de 2025 e contém ON, PN e tesouraria para Votorantim, Vale, Localiza,
MRV e Ambev. Ele não contém `security_id`/ticker B3 e não oferece um metadado
universal de escala da quantidade. Há valores que exigem confirmação por classe
antes de qualquer multiplicação com preço (por exemplo, a fonte registra Vale
com `4.539.007` ON e Ambev com `15.761.639` ON, sem especificar a escala no
arquivo de composição).

Por essa razão, a implementação deliberadamente recusa gerar market cap real
até existir, para cada classe, uma referência oficial que prove o ticker e a
unidade da quantidade. Isso evita produzir valores de mercado mil vezes maiores
ou menores por uma inferência silenciosa.

## Próxima evidência necessária

1. cadastro oficial B3/CVM que relacione CNPJ, classe, `security_id` e ticker;
2. unidade/multiplicador de ações com referência temporal;
3. validação de eventos societários entre a data das ações e a data do preço.

Quando esses três elementos forem carregados, o motor já calcula market cap,
EV e EY de forma idempotente no snapshot existente. Até lá não há amostra real
aprovada, nem `MARKET_DATA_STATUS = PASS`.
