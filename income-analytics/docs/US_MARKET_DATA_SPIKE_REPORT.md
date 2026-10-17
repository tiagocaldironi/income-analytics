# US_MARKET_DATA_SPIKE_REPORT

Data: 30/08/2026  
Escopo: spike técnica; nenhuma integração de produto, dado de carteira ou credencial foi alterado.

## Decisão

\`\`\`
RECOMMEND_TWELVE_DATA
\`\`\`

A Twelve Data é a melhor escolha para a futura primeira versão do
\`USMarketDataProvider\`: os metadados do instrumento expõem \`Common Stock\`,
\`ETF\` e \`REIT\`, o que preserva a segregação semântica exigida pelo Income.
Alpaca é um excelente candidato complementar para corporate actions, mas o
asset master de equities não fornece a distinção REIT necessária de forma
suficientemente explícita para ser a fonte única da classificação.

Esta é uma decisão de provider técnico, não uma aprovação automática do plano
gratuito para exibir dados a usuários finais.

## Ambiente e evidências

- Nenhuma chave Alpaca ou Twelve Data estava configurada no ambiente.
- Alpaca sem credenciais respondeu HTTP 401 para barras históricas; sua API
  exige headers \`APCA-API-KEY-ID\` e \`APCA-API-SECRET-KEY\`.
- A chave demo pública da Twelve Data retornou dados reais para:
  - \`AAPL /price\`: \`319.64001\`;
  - \`IVV /price\`: \`773.044983\`;
  - \`AAPL /time_series?interval=1day\`: USD, NASDAQ, \`Common Stock\` e
    barras diárias até 28/08/2026;
  - \`AAPL /dividends\`: ex-date 10/08/2026, valor USD 0.27.
- A mesma chave demo bloqueou a massa restante e chamadas batch com HTTP
  401/403. Isso é uma limitação da chave demo, não uma classificação dos
  ativos. A validação completa precisa de uma chave server-side própria.
- Consultas de fim de semana na Twelve Data retornaram \`No data\`/HTTP 400.
  O adapter deve buscar barras diárias até a data solicitada e selecionar a
  última barra \`<= requested_date\`; nunca deve substituir uma cotação
  histórica pelo último preço atual.

## Ativos e classificação pretendida

| Símbolo | Classe Income | Evidência de classificação |
| --- | --- | --- |
| AAPL, MCD | INTL_STOCK | \`type = Common Stock\` |
| IVV, VNQ | INTL_ETF | \`type = ETF\` |
| O, PLD | US_REIT | \`type = REIT\` |

O modelo atual do Income ainda não contém \`US_REIT\`; isso é uma decisão de
domínio da futura implementação. Não deve ser escondido como \`INTL_STOCK\`
apenas por utilizar o mesmo endpoint.

## Endpoints futuros (não implementados)

### Twelve Data

- \`/quote\` ou \`/price\`: cotação recente;
- \`/time_series?interval=1day\`: histórico e fallback para último pregão;
- \`/eod?date=...\`: fechamento por data quando disponível;
- \`/dividends\`: histórico de dividendos;
- \`/splits\`: eventos de split.

### Alpaca

- \`/v2/stocks/{symbol}/bars/latest\`: barra mais recente;
- \`/v2/stocks/bars?symbols=...&timeframe=1Day\`: histórico em lote;
- \`/v1/corporate-actions\`: dividendos, splits, mergers, spin-offs e
  mudanças de nome/símbolo.

## Normalização proposta

\`\`\`text
AssetReference
  symbol, name, asset_class, exchange, currency, country,
  provider, provider_symbol

MarketPrice
  symbol, price, currency, requested_date, effective_date,
  timestamp, price_type, provider

CorporateAction
  external_id, symbol, type, declaration_date, ex_date,
  record_date, payment_date, amount, currency, provider
\`\`\`

\`requested_date\` e \`effective_date\` são distintos. Para fim de semana e
feriado, o segundo é a data da última barra válida. O adapter deve sinalizar
\`HISTORICAL\`/EOD/DELAYED conforme o feed, em vez de afirmar tempo real.

## Dividendos e corporate actions

A Twelve Data documenta \`ex_date\` e \`amount\` no endpoint de dividendos,
mas essa resposta não é suficiente, sozinha, para registrar um provento
efetivamente pago: \`payment_date\` pode estar ausente. Além disso, dividendos
custam 20 créditos por símbolo e exigem plano Grow/Venture ou superior.

Alpaca possui cobertura mais ampla de corporate actions (cash/stock dividend,
splits, reverse splits, spin-offs, mergers e alterações de símbolo), por isso
deve permanecer como opção estratégica futura, não como justificativa para
misturar responsabilidades no primeiro adapter.

## Limites, lote e capacidade

| Provider | Preço/histórico | Lote | Limites observados/documentados |
| --- | --- | --- | --- |
| Twelve Data | Sim | Sim | Basic: 8 créditos/minuto, 800/dia; \`time_series\` custa 1 crédito/símbolo |
| Alpaca | Sim | Sim (\`symbols\` CSV) | Free: 200 chamadas/minuto, histórico 7+ anos, feed IEX; REST free tem atraso de 15 min |

Para 10/50/100 ativos, priorizar chamada em lote, cache diário e atualização
assíncrona. A arquitetura \`1 ativo = 1 chamada\` não é aceitável.

## Licença e camada gratuita

O plano Basic gratuito da Twelve Data é descrito como uso interno e
non-display; logo não é uma aprovação para mostrar cotações em um produto
voltado ao usuário final. Alpaca também possui restrições contratuais de
redistribuição de market data. Antes de produção/comercialização é obrigatória
revisão contratual do plano escolhido.

Para desenvolvimento local e protótipo interno, a Twelve Data é suficiente
para preço/histórico com chave server-side. Para dividendos, corporate actions
ou exibição/distribuição, a camada gratuita não é suficiente.

## Matriz de avaliação

| Critério | Alpaca | Twelve Data |
| --- | ---: | ---: |
| Stocks | 5/5 | 5/5 |
| ETFs | 5/5 | 5/5 |
| Classificação REIT | 2/5 | 5/5 |
| Preço histórico | 5/5 | 5/5 |
| Cotação recente | 4/5 | 4/5 |
| Dividendos | 5/5 | 2/5 |
| Corporate actions | 5/5 | 3/5 |
| Rate limits para MVP | 5/5 | 3/5 |
| Latência | 3/5 | 3/5 |
| Free tier | 3/5 | 3/5 |
| Evolução comercial | 4/5 | 4/5 |
| **Total** | **46/55** | **42/55** |

A nota total não vence a decisão de domínio: o requisito de classificar REIT
sem heurística de ticker é obrigatório. Por isso a recomendação é Twelve Data,
com Alpaca documentada como fonte complementar futura de corporate actions.

## Contrato futuro

\`\`\`python
class USMarketDataProvider(Protocol):
    def resolve_asset(self, symbol: str) -> AssetReference: ...
    def get_latest_price(self, symbol: str) -> MarketPrice: ...
    def get_historical_price(self, symbol: str, requested_date: date) -> MarketPrice: ...
    def get_corporate_actions(self, symbol: str, start: date, end: date) -> list[CorporateAction]: ...
\`\`\`

## Próxima implementação recomendada

Complexidade: **MEDIUM**

1. Criar \`US_REIT\` no domínio, se essa separação de alocação for aprovada.
2. Configurar \`TWELVE_DATA_API_KEY\` apenas no backend.
3. Implementar adapter isolado, cache de barras e fallback de último pregão.
4. Adicionar testes de contrato para a massa AAPL/MCD/IVV/VNQ/O/PLD, 401,
   429, ticker inválido, fim de semana e indisponibilidade.
5. Validar licença/plano para o modo de exibição pretendido.

## Fontes

- https://twelvedata.com/docs/introduction/overview
- https://twelvedata.com/pricing
- https://docs.alpaca.markets/us/reference/stockbars
- https://alpaca.markets/data
- https://docs.alpaca.markets/us/reference/corporateactions-1
