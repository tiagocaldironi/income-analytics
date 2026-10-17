# Magic Formula Stocks — Security Master & Shares Outstanding Spike

## Decisão

`RECOMMEND_HYBRID` para a identidade de emissor e security; ainda não há fonte
gratuita, pública e versionada que permita aprovar ações em circulação por
classe para uma data histórica. Portanto, market cap real permanece bloqueado.

## Fontes avaliadas

| Fonte | Resultado | Uso aprovado |
|---|---|---|
| B3 Empresas Listadas / `GetInitialCompanies` | expõe `codeCVM`, CNPJ e `issuingCompany` | vínculo CVM ↔ B3 por dois identificadores |
| B3 `GetListedSupplementCompany` | expõe totais ON/PN e ISINs em dados suplementares, mas sem data de referência das quantidades | apenas conferência atual; não market cap histórico |
| CVM FCA `valor_mobiliario` 2025 | expõe CNPJ, ticker, classe, início/fim de negociação e referência do formulário | Security Master histórico de ticker/classe |
| CVM DFP `composicao_capital` 2025 | ON/PN e tesouraria, sem unidade universal segura | reconciliação, não quantidade normalizada isolada |
| B3 OutstandingShares / PositionOfShareholders / SummaryData (UP2DATA) | catálogo indica dados acionários estruturados, mas o acesso histórico não foi demonstrado pelo canal público | pendente de licença/contrato ou evidência pública equivalente |

## Modelo criado

`SecurityMaster` preserva: emissor, código CVM, emissor B3, security ID,
ticker, ISIN, classe, início/fim de validade, fonte, referência e status.
O resolver aceita identidade de emissor apenas quando **código CVM e CNPJ**
coincidem. Não há join por nome nem prefixo de ticker.

## Resultado da amostra

| Companhia | Código CVM | B3 issuer | Ticker FCA 2025 | Classe | Status |
|---|---:|---|---|---|---|
| Vale | 4170 | VALE | VALE3 | ON | RESOLVED |
| Ambev | 23264 | ABEV | ABEV3 | ON | RESOLVED |
| MRV | 20915 | MRVE | MRVE3 | ON | RESOLVED |
| Localiza Fleet | 24813 | TFLE | — | — | MISSING (não há ação pública no FCA) |
| Votorantim Cimentos | 27189 | VEBM | — | — | MISSING (somente dívida no FCA) |
| Petrobras | 9512 | PETR | PETR3 / PETR4 | ON / PN | RESOLVED para identidade; shares históricos pendentes |

Petrobras prova o vínculo multi-classe real `security → ticker → classe` sem
inferência. A etapa de market cap permanece bloqueada porque a quantidade ON e
PN precisa ter unidade e referência temporal comprovadas para a mesma base do
preço.

## Tesouraria e temporalidade

Quando a fonte de ações em circulação for aprovada, a semântica será:
`outstanding = issued - treasury`, uma única vez e por classe. Cada registro
precisará ter quantidade bruta, unidade, multiplicador, quantidade normalizada,
data de referência, fonte e vigência. Mudança de ticker/classe e eventos de
capital delimitam `valid_from`/`valid_to`; conflito bloqueia o emissor inteiro.

## Gaps e recomendação operacional

Para ativar market cap histórico, é necessário obter uma entrega B3
OutstandingShares/PositionOfShareholders com data e unidade, ou uma fonte
oficial pública equivalente. Não será usado o valor atual do endpoint
suplementar como aproximação de 2025. Até essa evidência, cada security sem
quantidade temporalmente resolvida recebe `UNIT_UNRESOLVED` e o issuer recebe
`INSUFFICIENT_MARKET_DATA`.
