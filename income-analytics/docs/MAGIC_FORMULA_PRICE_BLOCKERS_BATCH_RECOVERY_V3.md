# MAGIC_FORMULA_PRICE_BLOCKERS_BATCH_RECOVERY_V3

## Resultado

Lote concluído para os 36 bloqueios marginais de preço da referência 2025-12-31. Cinco emissores tiveram recuperação de alta confiança; 31 permaneceram sem alteração porque a cadeia de identidade/preço não foi comprovada para todas as classes exigidas. O ranking segue bloqueado e inativo.

- Snapshot publicado e lido de volta: `ed8a9235-ee14-4a97-93fd-0dbcd87113fb`.
- Snapshot anterior: `9dd05e5a-d4a0-402c-809e-fd7f4cbc4f64`.
- Antes: FULL_DATA_READY 180/307 (58.63%); dimensão independente MARKET_PRICE_READY 232/307 (75.57%).
- Depois: FULL_DATA_READY 185/307 (60.26%); dimensão independente MARKET_PRICE_READY 237/307 (77.20%).
- Ganho de FULL_DATA_READY: +5 emissores, 58,63% → 60,26%. A cobertura independente de preço foi de 75,57% → 77,20%.
- Status: `ranking_status=INACTIVE`, `tool_status=VALIDATION_REQUIRED`; API `preview_status=ACTIVE`, `ranking_gate=BLOCKED`, `reference_date=2025-12-31`.
- B3 COTAHIST: `COTAHIST_A2025.ZIP`, SHA-256 `6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d`. As cinco cotações foram conferidas nas linhas brutas, campo PREULT, mercado 010, ISIN e data; preço foi o fechamento efetivo dentro da política existente de até sete dias corridos anteriores.
- Dry run determinístico: os lotes 3 e 4 produziram o mesmo digest lógico `e80a581a8694ccc1dbb9575bc3075d27bdef808b0500c71e5fca481b06e7230f`.
- Readback independente: 36 casos, cinco preços/arquivos B3 verificados, 31 emissores não recuperados idênticos ao BEFORE. Banco: backup em `tmp/magic-formula-price-blockers-batch-v3/dry-run-5/universe-before-publication.db`; leitura de volta `PASS`.

## Contagem terminal

| Status | Casos |
|---|---:|
| RECOVERED | 5 |
| IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | 17 |
| NO_TRADE_ON_REFERENCE_DATE | 9 |
| NOT_LISTED_ON_REFERENCE_DATE | 0 |
| DELISTED_BEFORE_REFERENCE_DATE | 0 |
| SOURCE_GAP | 0 |
| AMBIGUOUS_IDENTITY | 0 |
| UNRESOLVED | 5 |

## Inventário dos 36 casos

| CVM | Empresa | Classe(s) | Identificador original | Resultado | Ticker comprovado | Preço | Data efetiva | Motivo |
|---|---|---|---|---|---|---:|---|---|
| 026174 | Auren Operações S.A. | ON | AESO3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | AESO3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 024660 | BBM Logística S.A. | ON | BBML3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | BBML3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 016438 | SUL 116 PARTICIPACOES S.A. | ON | OPTS3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | OPTS3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 016993 | EMAE - EMPRESA METROP.AGUAS ENERGIA S.A. | ON | EMAE3 | NO_TRADE_ON_REFERENCE_DATE | EMAE3 | — | — | EFFECTIVE_DATE_GAP |
| 024872 | LIFEMED INDUSTRIAL DE EQUIP. E ART. MEDICOS E HOSP. S.A | ON | LMED | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | LMED3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 020575 | JBS S.A. | ON | JBSS3 | UNRESOLVED | — | — | — | B3_CVM_CNPJ_IDENTITY_NOT_CONFIRMED |
| 020788 | MARFRIG GLOBAL FOODS S.A. | ON | ADR | RECOVERED | MBRF3 | R$ 19.98 | 2025-12-30 | Cadeia CVM/CNPJ + classe/ISIN + COTAHIST confirmada |
| 019100 | CONTAX PARTICIPAÇÕES S.A. - EM RECUPERAÇÃO JUDICIAL | ON | ATMP3 | RECOVERED | CTAX3 | R$ 0.97 | 2025-12-30 | Cadeia CVM/CNPJ + classe/ISIN + COTAHIST confirmada |
| 025895 | LIVETECH DA BAHIA INDÚSTRIA E COMÉRCIO S.A. | ON | N/A | RECOVERED | WDCN3 | R$ 2.63 | 2025-12-30 | Cadeia CVM/CNPJ + classe/ISIN + COTAHIST confirmada |
| 020630 | FICA EMPREENDIMENTOS IMOBILIÁRIOS S.A. | ON | CRDE3 | RECOVERED | FIEI3 | R$ 14.49 | 2025-12-30 | Cadeia CVM/CNPJ + classe/ISIN + COTAHIST confirmada |
| 023175 | IGUA SANEAMENTO S.A. | ON | 023175 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | IGSN3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 024546 | PRÁTICA PRODUTOS S.A. | ON | PTCA3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | PTCA3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 025798 | KALLAS INCORPORAÇÕES E CONSTRUÇÕES S.A. | ON | KLAS3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | KLAS3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 024279 | INC EMPREENDIMENTOS IMOBILIÁRIOS S.A. | ON | INNC3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | INNC3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 024317 | ZAMP SA | ON | ZAMP3 | UNRESOLVED | — | — | — | NO_B3_SECURITY_FOR_DECLARED_CLASS |
| 027820 | Grupo Salta Educação S.A. | ON, PN | SALT4, SALT3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | SALT3 | — | — | NO_B3_SECURITY_FOR_DECLARED_CLASS;NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 025844 | TEGRA INCORPORADORA S.A. | ON | TEGA | UNRESOLVED | — | — | — | B3_CVM_CNPJ_IDENTITY_NOT_CONFIRMED |
| 011231 | TEKNO S.A. - INDUSTRIA E COMERCIO | ON, PN | TKNO3, TKNO4 | UNRESOLVED | — | — | — | B3_CVM_CNPJ_IDENTITY_NOT_CONFIRMED |
| 023302 | QUALITY SOFTWARE S.A. | ON | QUSW3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | QUSW3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 023817 | BRQ SOLUCOES EM INFORMATICA S.A. | ON | BRQB | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | BRQB3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 012190 | BOMBRIL S.A. - Em recuperação Judicial | ON | BOBR3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | BOBR3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 013471 | PLASCAR PARTICIPACOES INDUSTRIAIS S.A. | ON | B3 | NO_TRADE_ON_REFERENCE_DATE | PLAS3 | — | — | EFFECTIVE_DATE_GAP |
| 003654 | CIA MELHORAMENTOS DE SAO PAULO | ON, PN | MSPA4, MSPA3 | NO_TRADE_ON_REFERENCE_DATE | MSPA3 | — | — | EFFECTIVE_DATE_GAP |
| 008397 | MANGELS INDUSTRIAL S.A. | ON | MGEL3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | MGEL3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 012823 | ALIPERTI S.A. | ON, PN | APTI4, APTI3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | APTI3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 022055 | MARISA LOJAS S.A. | ON | 022055 | RECOVERED | AMAR3 | R$ 1.01 | 2025-12-30 | Cadeia CVM/CNPJ + classe/ISIN + COTAHIST confirmada |
| 026700 | EUROFARMA LABORATÓRIOS S.A. | ON | EUFA | UNRESOLVED | — | — | — | B3_CVM_CNPJ_IDENTITY_NOT_CONFIRMED |
| 001562 | BAUMER S.A. | ON | BALM3 | NO_TRADE_ON_REFERENCE_DATE | BALM3 | — | — | EFFECTIVE_DATE_GAP |
| 004146 | KARSTEN S.A. | ON | CTKA3 | NO_TRADE_ON_REFERENCE_DATE | CTKA3 | — | — | EFFECTIVE_DATE_GAP |
| 007544 | TEXTIL RENAUXVIEW S.A. | ON | TRXR3 | NO_TRADE_ON_REFERENCE_DATE | TXRX3 | — | — | EFFECTIVE_DATE_GAP |
| 011991 | WETZEL S.A. | ON | MWET3 | NO_TRADE_ON_REFERENCE_DATE | MWET3 | — | — | EFFECTIVE_DATE_GAP |
| 014664 | SCHULZ S.A. | ON | SHUL3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | SHUL3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 013439 | METALURGICA RIOSULENSE S.A. | ON | RSUL3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | RSUL3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |
| 008753 | METISA METALURGICA TIMBOENSE S.A. | ON | MTSA3 | NO_TRADE_ON_REFERENCE_DATE | MTSA3 | — | — | EFFECTIVE_DATE_GAP |
| 013285 | JOSAPAR-JOAQUIM OLIVEIRA S.A. - PARTICIP | ON, PN | JOPA4, JOPA3 | NO_TRADE_ON_REFERENCE_DATE | JOPA3 | — | — | EFFECTIVE_DATE_GAP |
| 004693 | CONSERVAS ODERICH S.A. | ON, PN | ODER4, ODER3 | IDENTITY_CONFIRMED_PRICE_UNAVAILABLE | ODER3 | — | — | NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY |

## Salvaguardas e validação

O resolvedor exige CVM e CNPJ iguais, emissor ativo com cotação na B3, ticker/ISIN compatíveis com a classe, COTAHIST oficial e preço único dentro da janela existente. Quando qualquer classe obrigatória falha, nada é aceito para aquele emissor. A fonte usa PREULT; nenhuma cotação alternativa ou extensão da janela foi usada.

O universo de cálculo, regras financeiras e metodologia `MAGIC_FORMULA_STOCKS_V1` não foram alterados. Não houve promoção ao Top 30 nem liberação do ranking. Foram executados 155 testes de regressão relevantes (PASS) e Ruff (PASS).

Nota de auditoria: uma primeira gravação (`c458573e-bf4f-4d58-a1be-bcef9df4f430`) herdou o timestamp do snapshot pai e não foi escolhida como `latest` por empate. Ela permanece no histórico imutável. O snapshot final acima tem timestamp posterior e é o `latest` confirmado pelo repositório e pela API.
