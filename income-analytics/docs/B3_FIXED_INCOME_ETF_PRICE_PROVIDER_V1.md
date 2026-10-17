# Provider coverage for Brazilian fixed-income ETFs

The standard quote chain for ordinary Brazilian securities remains BRAPI → B3 COTAHIST. Assets classified as `BRAZILIAN_ETF` use BRAPI → B3 BDI's **Negócios de VM de renda fixa realizados no Puma** structured table → B3 COTAHIST. The BDI table includes fixed-income ETFs; the category provider is generic and does not contain ticker-specific branches.

- **Source:** B3 Boletim Diário do Mercado (BDI), table `DebenturesBusiness`.
- **Access method:** structured JSON `POST` to `https://arquivos.b3.com.br/bdi/table/{table}/{start}/{end}/{page}/{pageSize}`, with an empty JSON body. The table is selected under BDI's Renda Fixa section.
- **Update frequency and delay:** daily bulletin, not an intraday or real-time feed. The observation date is the bulletin's reference/trading date; retrieval time is recorded separately by `MarketPriceObservation`. B3 may publish the bulletin after the trading session, and its schedule can vary.
- **Price field:** last traded price (`Último`/`Last`), not the next-day reference price. Empty/no-trade values are ignored.
- **Current price:** supported when the BDI table has a valid recent trade. The provider checks the latest eight calendar dates so weekends and short holidays are covered.
- **Historical price:** supported only within that recent eight-calendar-day lookup window. The provider never substitutes today's price for an earlier requested date. Historical backfill older than that remains a separate gap; BDI reports older than 20 days are available through B3's PDF archive and are not parsed here.
- **Provenance:** persisted source is `b3_etf`; run history records per-ticker provider attempts, results, fallback reasons, final price, and observation date.

The official BDI bulletin explicitly describes the Puma fixed-income table as covering debentures, CRI, CRA, FIDC, and fixed-income ETFs. Official examples include AUPO11, AREA11, and BDAP11 in B3's fixed-income ETF/forward market listings.
