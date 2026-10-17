# Magic Formula — refinamento da política de elegibilidade V7

**Resultado: PASS (auditoria e simulação; nenhuma política ativada).** A V7 separa a política setorial da escolha operacional do ticker, mede L3 somente na security selecionada e conserva REVIEW como estado próprio. Não calculou ranking nem Top 30.

## Baseline e proveniência

Fonte candidata: **360** registros; exclusões financeiras estruturais já existentes: **35**; registros fora da baseline mantidos para revisão: **18**; baseline V6 preservada: **307** empresas. A baseline tem **185 completas / 307 = 60,26%** antes da nova política. Snapshot lido em modo somente leitura: `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` (referência 2025-12-31; preço V6 2025-12-30). `SNAPSHOT_CHANGED=NO`.

O FCA estruturado traz setor, descrição de atividade e valores mobiliários por companhia. A taxonomia abaixo usa a descrição oficial do FCA; casos sem descrição suficiente ou atividade materialmente mista continuam em revisão. O conteúdo original da fonte CVM tem alguns caracteres acentuados corrompidos no CSV e foi preservado na coluna de descrição. Fontes oficiais: [CVM FCA](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca) e [CVM FRE](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre). O FCA permite classificar atividade e listagem; o FRE ainda é necessário para resolver os casos de holding/atividade insuficientemente descrita.

## Taxonomia de comércio

O arquivo V6 contém **37 registros** do setor amplo: são **36 exclusões da regra V6 mais ASAI3**, que sobreviveu como exceção. Portanto, o número 36 descreve a regra/exclusão anterior; não o total de linhas setoriais quando a exceção é incluída.

| Categoria refinada | Empresas |
|---|---:|
| TRADITIONAL_RETAIL | 11 |
| WHOLESALE | 1 |
| CASH_AND_CARRY | 1 |
| DISTRIBUTION | 4 |
| COMMERCE_ADJACENT | 10 |
| MIXED_COMMERCE | 4 |
| UNCERTAIN | 6 |


`TRADITIONAL_RETAIL` exclui na simulação: **11**. `POLICY_REVIEW`: **10**. Casos `UNCERTAIN`/LOW nunca viram exclusão. ASAI3 = **CASH_AND_CARRY / PASS**; `ASAI3_EXCEPTION_STILL_NEEDED=NO` na taxonomia refinada; a exceção legada permanece declarada por compatibilidade durante a migração. Aviação preservada: CVM 024112 e 019569 (2); utilities e exclusões financeiras não foram alteradas.

Tabela auditável linha a linha: [commerce_taxonomy_37.csv](appendices/magic_formula_eligibility_policy_v7/commerce_taxonomy_37.csv).

## Aviação e exclusões estruturais

Aviação continua excluída pelos dois códigos já definidos (CVM 024112 e 019569). Utilities continuam sem nova exclusão. As 35 exclusões financeiras estruturais seguem fora do universo de 307, sem alteração. Nenhuma exclusão foi ampliada para logística, aeroportos, fabricantes ou serviços auxiliares.

## Security selecionada e liquidez

A política recomendada para avaliação é **S4**: somente listing B3 válido na data-base, maior proporção de pregões negociados nos últimos 30, depois maior mediana diária de volume financeiro e, em empate econômico completo, identidade estável. A seleção não lê preço, retorno, ranking ou cobertura. A cobertura/liquidez é calculada depois da escolha; preço ausente deixa a empresa bloqueada por dados, não troca a classe.

V6 contava 86 emissores multiclasses no cadastro amplo; o FCA deixa **75** emissores com mais de uma classe de ação/UNIT listada e válida em 2025-12-31. S4 resolveu **257** emissores e deixou **50** em BUYABLE_SECURITY_REVIEW. Das 307 seleções/resoluções, 245 têm preço disponível, verificado somente depois da seleção. S0 atual/indefinido deixa 307 em REVIEW. Resultados simulados S1–S4 (RESOLVED / LIQUIDITY_FAIL / REVIEW): {"S0": {"BUYABLE_SECURITY_REVIEW": 307}, "S1": {"RESOLVED": 257, "BUYABLE_SECURITY_REVIEW": 50}, "S2": {"RESOLVED": 257, "BUYABLE_SECURITY_REVIEW": 50}, "S3": {"LIQUIDITY_FAIL": 23, "RESOLVED": 234, "BUYABLE_SECURITY_REVIEW": 50}, "S4": {"RESOLVED": 257, "BUYABLE_SECURITY_REVIEW": 50}}. Diferença de ticker selecionado contra S4: {"S1": {"different_selection_vs_S4": 22}, "S2": {"different_selection_vs_S4": 0}, "S3": {"different_selection_vs_S4": 0}, "S4": {"different_selection_vs_S4": 0}}. S3 escolhe entre classes que passam L3; S4 seleciona primeiro por execução e então aplica L3.

L3 proposto, não ativado: `traded_days_ratio_30d >= 0.50`, equivalente a pelo menos 15 das 30 sessões. No S4, PASS=234, FAIL=23, REVIEW=50. A regra evita depender de um negócio isolado recente e não exige liquidez institucional; volume é apenas desempate. Recência L1/L2 sozinha é insuficiente, e não há mínimo de volume.

## Market cap

Market cap permanece DIAGNOSTIC ONLY: no V6, estava disponível para 163/269 emissores na simulação da política anterior. Nesta V7 não há piso nem percentil; valores ausentes não excluem empresas.

Arquivos: [buyable_security_selection.csv](appendices/magic_formula_eligibility_policy_v7/buyable_security_selection.csv) contém cada security candidata e seus critérios; o resumo por emissor está em [buyable_security_issuer_summary_307.csv](appendices/magic_formula_eligibility_policy_v7/buyable_security_issuer_summary_307.csv). A lista completa de candidatos está em [security_candidates_010.csv](appendices/magic_formula_eligibility_policy_v7/security_candidates_010.csv).

## Rechecagem dos 9 emissores sem negociação

Após S4, 1 mantiveram o ticker alvo V4, 7 mudaram para outra security selecionada e 1 ficaram em revisão sem candidato comparável. A tabela lista o candidato operacional, L3 e preço desse ticker; uma classe não é resgatada pela liquidez de outra. Consulte [no_trade_security_recheck_9.csv](appendices/magic_formula_eligibility_policy_v7/no_trade_security_recheck_9.csv).

## Funil e estados finais V7

`360 = 35` exclusões financeiras estruturais já existentes `+ 18` registros fora da baseline `+ 307` na baseline. Dentro dela: 13 excluídas por política de usuário, 10 em revisão setorial, 47 em BUYABLE_SECURITY_REVIEW, 23 LIQUIDITY_FAIL e **214 L3_PASS**. Desses 214, 157 estão completos e 57 seguem bloqueados por dados. Os 157 são candidatos completos após elegibilidade, sem ranking calculado.

| Estado | Empresas |
|---|---:|
| INELIGIBLE_STRUCTURAL | 0 |
| INELIGIBLE_USER_POLICY | 13 |
| POLICY_REVIEW | 10 |
| BUYABLE_SECURITY_REVIEW | 47 |
| LIQUIDITY_FAIL | 23 |
| LIQUIDITY_REVIEW | 0 |
| ELIGIBLE_DATA_BLOCKED | 57 |
| ELIGIBLE_COMPLETE | 157 |


`STATUS_SUM=307`. Structural exclusions dentro da baseline=0; financeiras 35 continuam fora da baseline. Confirmadas elegíveis=214; confirmadas inelegíveis=36; revisão necessária=57. Completas=157; bloqueadas por dados=57. Coverage entre elegíveis confirmadas=73.36%; denominador conservador que inclui REVIEW=57.93%.

## Blockers e registros externos

Blockers V6 cruzados com estado e ticker V7: 31. `USER_POLICY_EXCLUDED=0`, `LIQUIDITY_FAIL=14`, `REVIEW=9`, `ELIGIBLE_PRICE_BLOCKED=8`. Buckets de origem: `{'PRICE_BLOCKED': 26, 'BLOCKER_REVIEW': 5}`. Quem falhou L3 não deve receber novas tentativas de preço até eventual mudança aprovada da regra. [blockers_v7_31.csv](appendices/magic_formula_eligibility_policy_v7/blockers_v7_31.csv).

Dos 57 elegíveis bloqueados por dados: `{'PRICE_BLOCKED': 23, 'FUNDAMENTALS_BLOCKED': 8, 'MULTIPLE_BLOCKERS': 17, 'SHARES_BLOCKED': 9}`. A classificação usa os reason codes V6, sem recalcular métricas nem ranking: [eligible_data_blockers_57.csv](appendices/magic_formula_eligibility_policy_v7/eligible_data_blockers_57.csv).

Os 18 registros fora da baseline foram inventariados separadamente: **17 SECTOR_REVIEW**, **1 SOURCE_MAPPING**, identity=0, duplicate=0, other=0; adicionados à baseline=0. [outside_baseline_review_18.csv](appendices/magic_formula_eligibility_policy_v7/outside_baseline_review_18.csv).

## Recomendação e controles

Recomenda-se submeter à decisão do usuário a exclusão somente de `TRADITIONAL_RETAIL`, manter casos mixed/uncertain em REVIEW, avaliar S4 com L3 de 50% como filtro operacional e preservar volume/market cap como diagnóstico. Ainda há **50** comparações de security em revisão e **10** classificações de comércio em revisão; isso não deve ser promovido a exclusão automática.

`POLICY_ID=MF_BR_2027_V1_DRAFT`; varejo, seleção S4, L3 e market cap **não ativados**. `RANKING_CALCULATED=NO`, `RANKING_ACTIVE=NO`, `RANKING_BLOCKED=YES`, `TOP_30_PUBLISHED=NO`. Artefatos de decisão: [final_eligibility_307.csv](appendices/magic_formula_eligibility_policy_v7/final_eligibility_307.csv), [audit_manifest.json](appendices/magic_formula_eligibility_policy_v7/audit_manifest.json).

`POLICY_READY_FOR_APPROVAL=YES`: o draft tem regras determinísticas, resultados reproduzíveis e estados REVIEW preservados. Decisões propostas para aprovação explícita: (1) excluir somente `TRADITIONAL_RETAIL`; (2) adotar S4 para representar operacionalmente o emissor; (3) adotar L3 de 50% como filtro; (4) manter as 50 comparações incompletas de security e as 10 classificações mixed/uncertain em REVIEW até nova evidência.

## Validação

O gerador verifica snapshot V6, baseline 307, taxonomia 37, 18 fora da baseline, 9 emissores no-trade e soma final 307. O relatório é uma simulação reproduzível; a política segue DRAFT até decisão explícita.
