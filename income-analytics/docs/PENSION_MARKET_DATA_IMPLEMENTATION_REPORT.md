# PENSION_MARKET_DATA_IMPLEMENTATION_REPORT

## Executive Summary

Implementada a primeira versão de dados de mercado para previdência aberta:
CNPJ explícito de classe/FIE → CVM → cotas persistidas → FUND_RETURN local.
O saldo informado continua independente e não houve alteração da performance
global da carteira.

## Spike Decision Reference

Implementação segue `RECOMMEND_HYBRID` do relatório da spike: CVM para veículo
explicitamente associado; planos fechados permanecem com saldo informado.

## Domain and Database Changes

- `PensionInvestmentVehicle`: vínculo datado, separado de administradora e
  patrocinador, preparado para múltiplos veículos.
- `PensionFundQuota`: Decimal, data de referência, fonte e instante de coleta.
- Migration `0012_pension_market_data`: novas tabelas aditivas, com unicidade
  lógica de `vehicle_id + reference_date`; nenhum lançamento é modificado.

## CVM Provider and Ingestion

`CvmPensionMarketDataProvider` encapsula CSV/ZIP oficiais de cadastro e
Informe Diário. A associação valida o CNPJ contra cadastro CVM e a atualização
busca a janela inicial de 31 dias ou somente datas posteriores à última cota.
O repository usa merge/UPSERT, preservando idempotência.

## API and UI

- `PUT /api/pensions/{ticker}/vehicle`: associa CNPJ explícito e retorna nome
  oficial da CVM.
- `POST /api/pensions/{ticker}/vehicle/refresh`: ingere cotas incrementais.
- `GET /api/pensions/{ticker}/fund-return`: retorna estados AVAILABLE,
  NO_VEHICLE, INSUFFICIENT_DATA, SOURCE_ERROR ou NOT_SUPPORTED.
- O formulário OPEN permite nome/CNPJ opcional do fundo/FIE e esclarece que o
  dado é **Rentabilidade do fundo**, não rentabilidade individual.

## Date Handling and Semantics

O retorno é `(end_quota / start_quota) - 1` com Decimal. Datas efetivas são
retornadas; ausência de cota não cria valor sintético. CLOSED não consulta CVM.

## SELF_QA and Regression

- CNPJ da administradora não é usado como FIE.
- Não existe resolução por nome/fuzzy matching.
- Não há float, cota zero artificial ou consulta CVM ao abrir a carteira.
- Testes de domínio, persistência e módulos: 28 aprovados.
- Lint dos módulos alterados: aprovado.
- Migration aplicada no banco local; health endpoint respondeu 200.

## Known Limitations and Future Work

Ainda não há job diário automático específico, UI de cartão de retorno na
carteira, portabilidade, troca de veículo, quantidade de cotas, TWR/XIRR nem
rentabilidade individual. Esses itens permanecem fora de escopo.

## Final Status

DONE
