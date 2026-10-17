# Magic Formula Stocks — independent golden validation

O golden é construído exclusivamente dos registros CVM DFP/FCA e B3 COTAHIST,
antes da abertura de uma nova sessão para leitura do snapshot. Cada métrica
guarda evidência, expected Decimal, actual, diferença e status. Ausência ou
divergência é `FAIL`; expected nunca é atualizado a partir do snapshot.

Os primeiros artefatos serão WEG, Suzano, Rumo e Telefônica Brasil, com a
mesma referência financeira/mercado de 31/12/2025 e preço efetivo de
30/12/2025. A promoção individual só ocorre após todos os componentes e
lineages passarem.
