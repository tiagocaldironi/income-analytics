# PR 5 — diagnóstico anterior à implementação

## Existente
`PortfolioSession.hypothetical_contribution` obtém a projeção oficial e `base_currency_valuation`, sem persistir cenário. `HypotheticalPortfolioProjector` preserva LEGACY_BEFORE_DEFICIT e STRATEGY_GUIDED. O segundo chama `ContributionTargetAllocator`: déficits positivos após aporte, rateio proporcional, centavos ROUND_DOWN e desempate lexical. A distribuição por ativos exige política intraclasse completa; não inventa pesos iguais. O algoritmo distribui dinheiro, não unidades.

`MarketPrice` contém preço Money, moeda do Asset, effective_date, provider e price_timestamp opcional. O índice de sessão fornece a última observação até a data solicitada. Valores de curva da renda fixa são derivados para avaliação e não são ofertas de aplicação. A conversão oficial usa FxRateObservation e limite de cinco dias corridos; não há segunda fonte de câmbio.

Classes: ações/ETFs brasileiros, FIIs, renda fixa, exterior, ETF internacional, REIT, cripto, caixa, previdência, imóveis e outros. Cadastro não registra suporte a frações, lote mínimo, mínimo de aplicação, incrementos ou corretagem. Quantidades existentes podem ser decimais; isso não confirma negociabilidade.

O cenário atual bloqueia a comparação se a avaliação das posições estiver incompleta. Não verifica validade de preço de execução, idade da observação ou quantidades. Testes existentes cobrem projeção monetária, alocador, estratégia e interface, mas não compras negociáveis.

## Proposta
Camada nova e somente de leitura na aplicação. Reutiliza avaliação/cotações/câmbio e alocador monetário existente, sem editar motores, históricos ou hashes. Unidades brasileiras inteiras, exterior inteiro por padrão e frações somente mediante confirmação explícita. Precisão cripto configurável. Renda fixa exige mínimo/incremento e cotação observada; valor de curva não vira preço de compra.

Política inicial explícita: preço até sete dias corridos (cripto: um), câmbio até cinco, sem observação futura. Toda referência será exibida como preço datado, nunca tempo real. Custos informados são estimativas, não consulta à corretora.

A semente monetária é arredondada para unidades e orçamento. Em seguida, saldo é reavaliado contra déficits de classe e ativo; compras adicionais exigem melhoria, desempate por benefício/custo e ticker. Compras decimais são agrupadas em lotes para não iterar bilhões de incrementos. Orçamento de ativos sem dados é separado do residual por indivisibilidade. Classes sem política por ativo exigem configuração da estratégia, sem escolha automática de ativos.
