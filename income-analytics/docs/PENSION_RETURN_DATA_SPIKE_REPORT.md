# PENSION_RETURN_DATA_SPIKE_REPORT

## Executive Summary

**Decision: RECOMMEND_HYBRID.** Para previdência aberta, o Income deve usar
**CNPJ da classe/FIE** informado ou confirmado pelo usuário para consultar a
CVM. O processo SUSEP identifica o produto regulatório, mas não foi validado
como uma API pública e confiável de resolução automática Plano → FIE. Para
previdência fechada, manter saldo informado até que a granularidade do Painel
PREVIC seja validada por plano/perfil.

Não houve integração produtiva nesta spike.

## Question Being Answered

Qual identificador é necessário para recuperar a rentabilidade de uma
previdência? A resposta é o **CNPJ da classe/FIE que efetivamente recebe os
recursos**, e não o CNPJ da administradora, patrocinador ou o nome comercial do
plano.

## Sources Investigated

| Fonte | Resultado |
| --- | --- |
| CVM — cadastro de fundos, classes e subclasses | Aprovada: gratuita, ODbL, atualização diária; possui sinalização `Previdenciario` na subclasse. |
| CVM — Informe Diário | Aprovada: traz `DT_COMPTC`, `CNPJ_FUNDO_CLASSE`, `ID_SUBCLASSE` e `VL_QUOTA`. |
| SUSEP | Processo SUSEP identifica o plano; materiais do plano devem informar denominação e CNPJ dos FIEs, mas não foi encontrada API pública de resolução automática. |
| PREVIC | Parcial: Painel PREVIC-Cidadão oferece dados de entidades e planos, sem evidência de série diária de cotas por participante/perfil. |
| Open Insurance | Promissor para dados consentidos do cliente; não é fonte pública sem consentimento. |

## CVM Findings

O arquivo `registro_fundo_classe.zip` contém `registro_fundo.csv`,
`registro_classe.csv` e `registro_subclasse.csv`. A subclasse possui os campos
`Previdenciario` e `Exclusivo_Previdencia_Complementar`; portanto, após RCVM
175, o identificador correto deve aceitar CNPJ de **classe**, não somente CNPJ
do fundo raiz.

O Informe Diário mensal de agosto de 2026 foi consultado diretamente. Seus
campos essenciais foram confirmados: `CNPJ_FUNDO_CLASSE`, `DT_COMPTC` e
`VL_QUOTA`. O portal mantém os últimos 12 meses no conjunto principal e oferece
histórico desde 2000; mês corrente/anterior é reapresentado diariamente.

## Real Vehicles Tested

Os exemplos abaixo foram selecionados no cadastro oficial por subclasse ativa
marcada como previdenciária e cruzados com o Informe Diário de agosto de 2026.
São veículos reais; não são uma alegação de que um plano comercial específico
seja 1:1 com cada veículo.

| CNPJ da classe | Veículo | Primeira cota válida | Última cota válida | Retorno simples |
| --- | --- | ---: | ---: | ---: |
| 50.326.147/0001-44 | Kinea Institucional FIF RF Crédito Privado LP | 03/08: 1,492841900000 | 27/08: 1,506113200000 | 0,888995679984598503029691200% |
| 53.107.987/0001-04 | Safra Prev Melissa FIF Previdenciário | 03/08: 100,698512000000 | 26/08: 101,096687000000 | 0,395412992795762463699562900% |
| 53.161.098/0001-25 | Safra Prev Long Bias II FIF Previdenciário | 03/08: 91,375727000000 | 27/08: 91,234204000000 | -0,1548802998853295033154702000% |

O cálculo foi executado com `Decimal`: `(cota_final / cota_inicial) - 1`.
Datas sem informe devem retornar a cota anterior válida, junto de
`requested_date` e `effective_date`; nunca uma cota inventada.

## PGBL, VGBL and Plan-to-Fund Resolution

Normas e orientação da SUSEP confirmam que propostas de PGBL devem conter a
denominação e o CNPJ do(s) FIE(s) vinculado(s). Isso é a melhor rota inicial de
onboarding: solicitar ou extrair do extrato/proposta o CNPJ da classe/FIE.

PGBL/VGBL não garante cardinalidade 1:1. Um plano pode oferecer perfis e
veículos distintos, trocar de fundo ao longo do tempo ou investir via FIQ/FIE.
Consequentemente, não é seguro associar automaticamente por nome, CNPJ da
administradora ou processo SUSEP. O teste PGBL/VGBL de resolução automática
ficou **não aprovado por ausência de vínculo público estruturado**, não por
ausência de cota pública após o CNPJ ser conhecido.

## Fees and Return Semantics

`FUND_RETURN` mede a variação de cota e normalmente já reflete taxa de
administração e despesas do fundo. Não prova o retorno líquido individual:
carregamento, custos contratuais, aportes, resgates e portabilidades podem
alterar o resultado do participante.

`INVESTOR_RETURN` futuro exige quantidade de cotas e fluxos datados (para TWR
ou XIRR). `current_balance` isolado não permite inferir quantidade de cotas.

## Closed Pension Limitations

Classificação: **PARTIALLY_SUPPORTED**. O Painel PREVIC-Cidadão é útil para
dados públicos de EFPC e planos, porém esta spike não encontrou prova de uma
série diária de cotas por plano/perfil comparável ao Informe Diário da CVM.
Não usar médias anuais/setoriais como retorno individual.

## Open Insurance

Com consentimento, é a rota futura mais promissora para saldo, plano,
movimentações e identificação precisa do veículo. Exige participante elegível,
OAuth/consentimento e contratos de integração; permanece fora de escopo.

## Proposed Architecture

`Pension → PensionInvestmentVehicle → PensionMarketDataProvider → CVM → FundQuota`

Futuro `PensionInvestmentVehicle` deve ter `vehicle_cnpj`, tipo, nome, datas
de início/fim e possível `cvm_identifier`. Mudança de perfil/fundo cria um novo
vínculo datado; não sobrescreve o anterior.

Contrato proposto (não implementado):

```text
resolve_vehicle(identifier)
get_quota(vehicle_id, date) -> requested_date, effective_date, quota, source
get_quota_history(vehicle_id, start_date, end_date)
```

Recomendação de ingestão: job diário baixa o ZIP mensal CVM, filtra apenas os
CNPJs cadastrados no Income e persiste `fund_quota_history` indexado por
veículo/data. A carteira nunca deve baixar o arquivo CVM ao abrir.

## Score Matrix

| Critério | Nota (0–5) | Evidência |
| --- | ---: | --- |
| PLAN_TO_FUND_RESOLUTION | 2 | processo/material pode conter FIE; não há resolução pública automática validada |
| FUND_IDENTIFICATION | 5 | CNPJ de classe/FIE é identificador preciso |
| QUOTA_AVAILABILITY | 5 | Informe Diário CVM confirmou `VL_QUOTA` |
| HISTORY | 4 | principal com 12 meses e arquivo histórico desde 2000 |
| FRESHNESS | 4 | atualização diária, com possível atraso/reapresentação |
| DATA_QUALITY | 4 | fonte oficial; mudanças de classe exigem controle de efetividade |
| COST | 5 | gratuita |
| LICENSING | 5 | ODbL identificada no portal CVM |
| IMPLEMENTATION_COMPLEXITY | 3 | ZIPs grandes e relação plano-veículo precisa ser explícita |
| CLOSED_PENSION_COVERAGE | 2 | dados públicos úteis, mas sem cota diária validada |

## Risks and Unknowns

- Uma classe pode sofrer evento societário, cota zerada ou troca de estrutura;
  validar continuidade antes de calcular retorno.
- Não foi provado vínculo automático SUSEP → FIE para três planos comerciais.
- Busca fuzzy por nome pode associar o veículo errado e não deve ser automática.

## Recommended Next Task

Implementar uma feature separada de **vínculo manual assistido de veículo de
previdência aberta**: CNPJ da classe/FIE obrigatório para ativar cotação, busca
somente para confirmação, ingestão CVM diária e retorno de fundo claramente
rotulado como `FUND_RETURN`.

## Final Status

SPIKE_COMPLETE
