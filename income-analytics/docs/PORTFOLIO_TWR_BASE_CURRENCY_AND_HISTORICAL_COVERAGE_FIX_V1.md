# Portfolio TWR em BRL e cobertura histórica — V1

Implementação aplicada ao pipeline de performance em 17/10/2026. O TWR continua sendo o encadeamento geométrico existente, `Π(1 + retorno_subperíodo) - 1`; os eventos DEPOSIT/WITHDRAWAL continuam como fluxos externos, BUY/SELL como operações e proventos como retorno econômico.

## Implementação

O projector agora avalia posição e caixa em BRL por data histórica. Preço e PTAX só são elegíveis quando a data da observação é menor ou igual à data avaliada. Preços mantêm a tolerância original de 7 dias; FX usa no máximo 5 dias corridos. Posições internacionais exigem simultaneamente preço e câmbio válidos. Capital implícito de compra é segregado por moeda e convertido ao câmbio da data de valuation. A cotação oficial do B3SA3 em 11/06/2021 é R$16,13 (COTAHIST); o preço de negociação R$16,19 não foi tratado como cotação de mercado.

## Recuperação de dados

O backfill B3 foi limitado a 2022 apesar do histórico COTAHIST local começar em 2021. O limite foi corrigido para 2021 e o pipeline persistiu 579 closes oficiais para 42 ativos considerados; AUPO11 possui apenas quatro cotações persistidas, de 01/09/2026 a 16/10/2026; a série anterior ao início disponível não foi recuperada pelo COTAHIST. A rotina PTAX importou 1.345 observações USD/BRL de 11/06/2021 a 16/10/2026. A Twelve Data importou 542 preços para IVV, NOBL e IAU, incluindo pré-histórico curto para posições iniciadas em fim de semana. A CoinGecko importou 298 observações diárias de BTC (22/12/2025–17/10/2026), pois a carteira também tinha exposição cripto em USD sem série histórica persistida.

## Resultado reprocessado

| Período | TWR | Estado | Cobertura mínima |
|---|---:|---|---:|
| 16/10/2025–16/10/2026 | -4,4439% | AVAILABLE | 98,1809% |
| 11/06/2021–16/10/2026 | +7,3143% | AVAILABLE | 98,1809% |

O limite de 90% foi atingido sem fabricar preços. Na data crítica 27/07/2026, a cobertura ainda identifica AUPO11 e dois títulos Tesouro IPCA+ (`FI-2032-779BC14B`, `FI-2032-D5F3130F`) com valuation ausente porque não há observações de IPCA utilizáveis nessa data; a cobertura BRL continua acima do corte. O read model final foi reconstruído da versão 113 para 124 em 17/10/2026. A tela usa a data mais recente disponível (17/10, sábado, devido à cotação diária de BTC): TWR 12M = -4,8399% e total = +7,1824%. A validação do contrato com data final fixa 16/10 resulta em -4,4439% e +7,3143%, respectivamente. A tabela final e os JSONs anexos registram os resultados e limites.

## Limitações

A série B3 de AUPO11 não foi encontrada no acervo COTAHIST usado; não foi substituída por valor de transação nem cotação futura. Os dois títulos CDI ainda têm uma lacuna localizada de valuation contratual. O TWR está disponível conforme a cobertura mínima, mas é parcial porque há posições/datas não cobertas. A linha de FX é PTAX diária; fim de semana/feriado usa a última data anterior dentro do limite de 5 dias.
