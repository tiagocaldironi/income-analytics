# Relatório de implementação — rentabilidade da carteira

## Resumo

Foi preservado o TWR global existente e adicionada a base de classificação persistida de fluxos para suportar TWR por classe e ativo sem inferências retroativas.

## Auditoria

| Métrica | Local | Ação |
| --- | --- | --- |
| TWR global | `PerformanceProjector` | Preservado; aportes e retiradas são neutralizados. |
| Resultado total | `PortfolioProjection` | Mantido separado de rentabilidade. |
| Variação de classe | `portfolio.js` | Exibe somente variação de preço, sem proventos. |
| TWR por classe/ativo | Novo contrato de fluxo | Exige cobertura classificada; retorna dados insuficientes quando não houver. |

## Alterações

- `CapitalFlowType` com capital externo, transferência interna, contribuição patronal e desconhecido.
- Metadados persistidos no evento financeiro, incluindo classe de origem e destino.
- Migração `0013_capital_flow_classification`.
- Dashboard inclui TWR global de 12 meses e total, calculados no backend e persistidos no snapshot.
- Interface solicita origem de recurso apenas em compras e exige origem para transferências internas.
- Resumos de classe mostram valor, variação, peso atual, peso ideal e estado de cobertura da rentabilidade.

## Self-QA

- Aportes e retiradas continuam neutralizados pelo TWR global.
- Compras históricas sem caixa disponível recebem somente o aporte implícito necessário na data da compra, sem exigir lançamento retroativo de caixa.
- Compra e venda internas não são retiradas globais.
- Proventos entram como caixa e resultado econômico, sem reinvestimento artificial.
- Histórico ambíguo não é inferido nem convertido em zero por cento.
- Cálculos de domínio usam `Decimal`; o frontend somente formata resultados devolvidos pela API.

## Status

`HUMAN_REVIEW_REQUIRED`: a base de dados atual possui operações históricas sem classificação de origem de capital. O sistema as preserva como `UNKNOWN` e sinaliza cobertura insuficiente por classe/ativo, conforme a política aprovada. Novos lançamentos já registram a classificação necessária.
