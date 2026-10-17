# Magic Formula Stocks — Data Spike

## Decisão

`RECOMMEND_CVM_B3`, condicionado a um adaptador versionado e a testes por companhia.

## Evidência

A CVM publica DFP estruturado, atualizado semanalmente, com DRE, BPA e BPP; ITR tem o mesmo modelo trimestral. A B3 COTAHIST fornece preço diário e código de negociação. Fontes: [DFP CVM](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp), [índice DFP](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/), [layout COTAHIST](https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf).

## Mapeamento proposto

| Métrica | Origem consolidada | Regra |
|---|---|---|
| EBIT | DRE | lucro operacional antes do resultado financeiro e IR; excluir companhia se a conta não for comparável |
| Dívida líquida | BPP | empréstimos/financiamentos de curto e longo prazo menos caixa e equivalentes |
| Market cap | B3 + composição de capital CVM | preço no `reference_date` × ações emitidas na mesma referência |
| EV | Derivada | market cap + dívida líquida |
| NWC | BPA/BPP | ativos circulantes operacionais menos passivos circulantes operacionais; caixa e dívida excluídos |
| Net fixed assets | BPA | imobilizado líquido; excluir quando não comparável |

Não usar dados individuais quando a demonstração consolidada estiver disponível. Bancos, seguradoras, holdings financeiras e empresas sem contas comparáveis ficam fora do universo. A implementação deve validar de 5 a 10 emissores de setores distintos com DFP/ITR reais antes de mudar o status de `DATA_GAP`.
