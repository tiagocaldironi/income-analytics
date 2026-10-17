# Metodologia de rentabilidade da carteira

## Métricas

- **Variação de preço**: `(valor de mercado - custo em aberto) / custo em aberto`. Não inclui proventos, aportes ou retiradas.
- **Retorno total**: resultado realizado, não realizado e proventos. É uma medida econômica acumulada, não substitui TWR.
- **TWR**: retorno ponderado pelo tempo. É a métrica principal de rentabilidade da carteira.
- **XIRR/MWR**: permanece disponível pela API existente, mas não é o indicador principal desta tela.

## Convenção de fluxos

O motor de TWR da carteira usa fluxo externo no início de cada subperíodo. Aportes e retiradas fecham o subperíodo anterior e abrem o próximo; compras, vendas internas e proventos não são fluxos externos globais. Proventos entram no caixa, portanto são contabilizados uma vez no retorno econômico.

Para carteiras legadas, lançar caixa antes da compra não é pré-requisito. Cada compra que exceder o caixa disponível recebe somente o capital implícito necessário na sua própria data; essa data vira uma fronteira do TWR e o valor é neutralizado como aporte. Déficits causados por retiradas nunca são convertidos em capital implícito.

## Escopos

O TWR global usa o patrimônio inteiro e somente aportes/retiradas. Para classes e ativos, eventos novos persistem `EXTERNAL_CAPITAL`, `INTERNAL_TRANSFER`, `EMPLOYER_CONTRIBUTION` ou `UNKNOWN`, com classe de origem e destino quando aplicável. Transferências internas são neutras globalmente, saída na origem e entrada no destino. Contribuição patronal é entrada externa, não retorno do fundo.

## Cobertura e limitações

Eventos históricos sem classificação permanecem `UNKNOWN`; o sistema não deduz origem pela sequência de operações. Quando a ausência impede a série confiável por classe/ativo, a API e a interface retornam `INSUFFICIENT_DATA`, nunca `0%`. A cobertura começa após a última movimentação ambígua relevante.

Previdência mantém retorno do fundo separado do retorno da posição. Para ativos estrangeiros, valores agregados seguem a moeda-base quando houver taxa de câmbio; a decomposição de retorno local e cambial permanece fora de escopo.
