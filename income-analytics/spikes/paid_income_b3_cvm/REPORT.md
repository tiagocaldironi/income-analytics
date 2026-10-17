# SPIKE 2 — Proventos pagos por B3/CVM

Data da investigação: 28/08/2026. Escopo isolado: nenhuma rota, regra de
domínio, persistência ou interface do produto foi alterada.

## Resultado executivo

**Não foi identificada uma fonte pública, estruturada e abrangente de B3/CVM
que preencha o contrato de provento já pago para ações e FIIs.** A B3 e a CVM
oferecem evidências oficiais úteis, mas não uma API/dataset público único com
o valor por unidade e a data de pagamento já normalizados para todos os
tickers testados.

O veredito do spike é **BLOQUEADO para substituir o provedor pago**. A
alternativa gratuita viável é manter a informação como evidência/manual por
emissor, não como automação confiável de proventos recebidos.

## Fontes verificadas

| Fonte | Evidência encontrada | Serve como histórico de pagamento? |
| --- | --- | --- |
| B3 — Consultas de dividendos e outros eventos corporativos | Consulta pública no portal, sem API/bulk documentado e sem contrato estruturado versionado por ticker validado neste spike. | Não como integração gratuita escalável. |
| B3 — Cotações históricas (COTAHIST) | A própria página declara que a série de preços não inclui ajuste por proventos. | Não. |
| CVM — IPE de companhias abertas | ZIP anual CSV com metadados de documentos: categoria, tipo, assunto, entrega e link do documento. Não há valor por ação nem data de pagamento como campos. | Não; exigiria baixar/interpretar documentos, excluído pelo escopo. |
| CVM — INF_MENSAL FII | ZIP anual CSV estruturado. Em 2026, a tabela de complemento contém percentuais de dividend yield e amortização mensais. | Não: não traz data de pagamento nem valor por cota. |

URLs oficiais consultadas:

- https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/acoes/consultas/dividendos-e-outros-eventos-corporativos/
- https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/
- https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/
- https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/

## Cobertura observada

Foram baixados os ZIPs públicos CVM de 2024, 2025 e 2026. Para a janela
01/08/2024–31/08/2026, os dados permitem localizar os FIIs por CNPJ de classe:

| Ticker | CNPJ de classe CVM | Evidência disponível | Provento pago normalizável |
| --- | --- | --- | --- |
| GGRC11 | 26.614.291/0001-00 | Observações mensais de dividend yield | Não |
| HSML11 | 32.892.018/0001-31 | Observações mensais de dividend yield | Não |
| PETR4, TASA4, KLBN11, CMIG4 | — | IPE aponta documentos, não eventos normalizados | Não |

Isso cumpre a cobertura de relatórios dos FIIs, mas não a cobertura mínima
de **eventos pagos** solicitada para o produto. Não foi feita alegação de
completude de 12/24 meses de pagamentos.

## Contrato e classificação

O código experimental reutiliza PaidIncomeEvent, IncomeType, ProviderResponse
e QueryResult do Spike 1. O adapter CVM retorna explicitamente INVALID_PAYLOAD
e zero eventos, porque converter dividend yield mensal em pagamento por cota
inventaria campos obrigatórios:

- amount_per_unit;
- payment_date;
- classificação segura entre rendimento e amortização.

Essa decisão evita confundir competência mensal com data de pagamento e evita
duplicação de eventos.

## Cross-check e recomendação

O cross-check de três ações e um FII não pode ser aprovado: não há uma fonte
B3/CVM pública e estruturada que produza os mesmos eventos pagos para
comparar, sem scraping ou leitura de documento/PDF. Logo, a classificação
final é **BLOQUEADO**, não uma divergência de cálculo.

Próximo passo recomendado: adquirir/contratar uma fonte com direitos de uso e
campos de pagamento históricos, ou desenhar um fluxo manual auditável por
emissor. Não recomendar uso de COTAHIST para proventos.
