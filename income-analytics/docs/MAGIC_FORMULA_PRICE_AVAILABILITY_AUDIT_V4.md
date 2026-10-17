# Magic Formula — auditoria de disponibilidade de preços V4

Data da auditoria: 12/10/2026. Esta é uma análise read-only e uma simulação: não houve gravação de preços, criação de snapshot, alteração de política, metodologia, filtros de elegibilidade ou liberação do ranking.

## Resultado executivo

O snapshot de produção mais recente continua sendo `ed8a9235-ee14-4a97-93fd-0dbcd87113fb`, criado em `2026-10-12T19:12:56.069873+00:00`, com data de referência `2025-12-31`. Ele contém 307 empresas, das quais 185 completas (60,26%). `ranking_status=INACTIVE` e `tool_status=VALIDATION_REQUIRED`. A análise V4 faz as simulações em `2025-12-30`, último pregão de 2025, sem substituir a data oficial do snapshot.

Dos 31 bloqueios residuais, 17 são empresas com identidade confirmada e preço indisponível, 9 têm negociação anterior mas nenhuma cotação em 30/12/2025 e 5 permanecem `UNRESOLVED` e foram deixadas sem investigação corretiva nesta etapa. A leitura do COTAHIST encontrou 3 casos com registros apenas no mercado fracionário para a classe afetada, 13 casos sem qualquer linha para ticker/ISIN nos arquivos locais de 2022–2026 e 1 caso com preço à vista antigo (2022). Nenhuma regra técnica de busca já aceita foi encontrada como causa comprovada (`LOOKUP_BUG=0`); não foi provado preço em dataset B3 alternativo (`ALTERNATIVE_B3_DATASET_REQUIRED=0 confirmado`).

## Baseline, universo e fonte

| Campo | Resultado |
|---|---:|
| Snapshot | `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` |
| Criado em (UTC) | `2026-10-12T19:12:56.069873+00:00` |
| Data oficial do snapshot | `2025-12-31` |
| Data usada nas simulações V4 | `2025-12-30` |
| Empresas / universo | 185 / 307 |
| Cobertura | 60,26% |
| Ranking | `INACTIVE` |
| Estado da ferramenta | `VALIDATION_REQUIRED` |
| Bloqueios residuais | 17 preço indisponível + 9 sem negócio na data + 5 unresolved = 31 |

Os arquivos COTAHIST anuais A2022–A2026 disponíveis localmente foram percorridos por ticker e ISIN, preservando a classe pelo ISIN/especificação. O campo PREULT foi lido nas posições `[108:121]` do registro fixo. O layout da B3 define o COTAHIST como série de negociações de todos os papéis-mercado e identifica 010 como mercado à vista e 020 como fracionário ([layout oficial COTAHIST](https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf)). A busca para a política atual exige mercado 010, ticker e ISIN exatos; uma linha 020 não foi tratada como cotação substituta. Isso é relevante porque a B3 registra a classe fracionária com sufixo `F` no ticker, embora o ISIN possa ser o mesmo.

Manifestos dos arquivos analisados (SHA-256):

| Arquivo | SHA-256 |
|---|---|
| COTAHIST_A2022.ZIP | `a4f9015b755f797d9c08b0d13f19dbfab18a6c75f379c0271a1cf1b5f6323cd8` |
| COTAHIST_A2023.ZIP | `ad1603788d78aaa1de806498572277f1d9443f88ae116452751b5800cb23523e` |
| COTAHIST_A2024.ZIP | `96a003d10fab0fa2ace0c64cdc2b892b4c111adf9da8e538aa0b28437bd2a172` |
| COTAHIST_A2025.ZIP | `6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d` |
| COTAHIST_A2026.ZIP | `67a343ae7ecb74bf70f7ccccb1ba29cf6aefd388a37e7a633681e7fb98a2b4f4` |

A ausência em A2022–A2026 não prova ausência histórica antes de 2022. Também não foi possível confirmar, por ticker individual, se a tabela interativa Stock do BDI disponibiliza outro fechamento que não conste do COTAHIST local. A B3 informa que as antigas páginas de cotações/dados públicos foram migradas ao BDI a partir de 15/12/2025 ([BDI da B3](https://arquivos.b3.com.br/bdi/)); isso justifica avaliar uma integração estruturada com BDI, mas não demonstra que ele resolva estes bloqueios.

## Os 17 casos com identidade confirmada e preço indisponível

| Empresa | Classe(s) / ISIN | Evidência local até 30/12/2025 | Diagnóstico |
|---|---|---|---|
| Auren Operações | AESO3 ON / `BRAESOACNOR0` | Nenhuma linha nos arquivos A2022–A2026 | `SOURCE_GAP`; requer fonte de preço histórica adicional ou evidência B3 anterior ao arquivo local |
| BBM Logística | BBML3 ON / `BRBBMLACNOR3` | Nenhuma linha | `SOURCE_GAP` |
| SUL 116 Participações | OPTS3 ON / `BROPTSACNOR6` | Nenhuma linha | `SOURCE_GAP` |
| LifeMed | LMED3 ON / `BRLMEDACNOR3` | Nenhuma linha | `SOURCE_GAP` |
| Iguá Saneamento | IGSN3 ON / `BRIGSNACNOR0` | Nenhuma linha | `SOURCE_GAP` |
| Prática Produtos | PTCA3 ON / `BRPTCAACNOR9` | Nenhuma linha | `SOURCE_GAP` |
| Kallas | KLAS3 ON / `BRKLASACNOR3` | Nenhuma linha | `SOURCE_GAP` |
| INC Empreendimentos | INNC3 ON / `BRINNCACNOR0` | Nenhuma linha | `SOURCE_GAP` |
| Grupo Salta Educação | SALT3 ON / `BRSALTACNOR4` | Nenhuma linha | `SOURCE_GAP`; ticker/classe declarada não teve registro B3 localizado |
| Quality Software | QUSW3 ON / `BRQUSWACNOR5` | Nenhuma linha | `SOURCE_GAP` |
| BRQ Soluções | BRQB3 ON / `BRBRQBACNOR1` | Nenhuma linha | `SOURCE_GAP` |
| Bombril | BOBR3 ON / `BRBOBRACNOR6` | Nenhuma linha | `SOURCE_GAP` |
| Mangels Industrial | MGEL3 ON / `BRMGELACNOR6` | Sem 010; há 020 como `MGEL3F`, último 21/09/2026; último anterior à referência em 17/09/2025 | `SECURITY_TYPE_NOT_COVERED`; preço fracionário distante não foi aceito |
| Aliperti | APTI3 ON / `BRAPTIACNOR6`; APTI4 PN / `BRAPTIACNPR3` | Apenas 020: APTI3F em 12/06/2023; APTI4F em 20/08/2025 (R$ 4.000,00) | `SECURITY_TYPE_NOT_COVERED`; duas classes são necessárias para completar a empresa e ambas falham 010 |
| Schulz | SHUL3 ON / `BRSHULACNOR7` | Último 010 em 12/09/2022 (R$ 27,94); 020 em 19/04/2023 | `SOURCE_GAP` por preço à vista excessivamente antigo |
| Conservas Oderich | ODER3 ON / `BRODERACNOR6`; ODER4 PN / `BRODERACNPR3` | ODER3 sem linha; ODER4 010 mais recente em 15/05/2023; ODER4F 020 em 29/12/2025 (R$ 119,99) | ODER3 `SOURCE_GAP`; ODER4 `SECURITY_TYPE_NOT_COVERED`. A linha 020 próxima à data foi excluída pela política vigente. No mercado fracionário, ODER4 passou de R$119,99 em 29/12 para R$60,01 em 12/01/2026 (−49,99%), sinal de instabilidade que torna inadequado presumir substituição sem regra e validação próprias |
| Metalúrgica Riosulense | RSUL3 ON / `BRRSULACNOR6` | Nenhuma linha | `SOURCE_GAP` |

Contagem por causa comprovada: `SOURCE_GAP=14` (inclui Schulz, cujo último 010 é de 2022), `SECURITY_TYPE_NOT_COVERED=3` empresas (Mangels, Aliperti e Oderich), `LOOKUP_BUG=0`, `HISTORICAL_TICKER_LOOKUP_GAP=0` confirmado, `ALTERNATIVE_B3_DATASET_REQUIRED=0` confirmado, `CORPORATE_ACTION_LOOKUP_GAP=0` comprovado, `LISTING_DATE_GAP=0`, `DELISTING_DATE_GAP=0`, `DATASET_GAP=0` (A2025 está presente e foi lido), `OTHER_CONFIRMED_CAUSE=0`. “0 confirmado” significa que a evidência disponível não demonstrou essa causa; não significa prova de inexistência em qualquer fonte B3.

## Os 9 casos sem negociação em 30/12/2025

Em todos os casos abaixo existe cotação à vista anterior, mas não na data de referência. O gap de pregões é contado no calendário de 250 pregões 010 de 2025 até 30/12. A contagem de negócios de liquidez considera quantos dos 30 pregões anteriores tiveram linha para a classe exata.

| Empresa / classe | Último 010 anterior (preço) | Gap calendário / pregões | Próximo 010 (preço; variação vs anterior) | Pregões com negócio em 30 |
|---|---|---:|---|---:|
| EMAE3 | 18/08/2025 (R$150,00) | 134 / 93 | Sem negócio posterior no arquivo local | 0 |
| PLAS3 | 23/12/2025 (R$4,99) | 7 / 3 | 06/01/2026 (R$5,00; +0,20%) | 12 |
| Melhoramentos MSPA4 PN | 11/12/2025 (R$39,50) | 19 / 11 | 16/01/2026 (R$41,00; +3,80%) | 5 |
| Melhoramentos MSPA3 ON | 28/11/2025 (R$46,50) | 32 / 20 | 16/01/2026 (R$47,00; +1,08%) | 2 |
| Baumer BALM3 | 18/12/2025 (R$28,00) | 12 / 6 | 02/01/2026 (R$28,00; 0,00%) | 4 |
| Karsten CTKA3 | 03/12/2025 (R$50,00) | 27 / 17 | 09/02/2026 (R$50,00; 0,00%) | 6 |
| RenauxView TXRX3 | 19/12/2025 (R$9,97) | 11 / 5 | 08/04/2026 (R$9,98; +0,10%) | 1 |
| Wetzel MWET3 | 05/12/2025 (R$16,00) | 25 / 15 | 22/01/2026 (R$16,00; 0,00%) | 4 |
| Metisa MTSA3 | 23/06/2025 (R$76,00) | 190 / 133 | Sem negócio posterior até 02/10/2026 | 0 |
| Josapar JOPA4 PN | 10/01/2025 (R$24,00) | 354 / 243 | 01/04/2026 (R$19,80; −17,50%) | 0 |
| Josapar JOPA3 ON | 17/12/2025 (R$20,11) | 13 / 7 | 02/02/2026 (R$20,12; +0,05%) | 3 |

A lista tem 9 empresas e 11 classes. Por pior classe requerida na empresa, os gaps distribuem-se: 0–3 dias=0, 4–7=1, 8–30=4 e >30=4. O próximo negócio é usado só para medir sensibilidade e jamais para selecionar cotação na data de referência. Em RenauxView, a identidade CVM declara TRXR3 e a B3 mapeia TXRX3 com o mesmo ISIN; os negócios foram contados pelo ISIN/classe, não por um ticker presumido.

## Simulações de política (sem persistência)

| Política | Classes recuperadas | Empresas completas adicionais | Universo completo | Cobertura | Bloqueios restantes |
|---|---:|---:|---:|---:|---:|
| Exata 30/12/2025 | 0 | 0 | 185 / 307 | 60,26% | 31 |
| Até 1 dia calendário | 0 | 0 | 185 / 307 | 60,26% | 31 |
| Até 3 dias | 0 | 0 | 185 / 307 | 60,26% | 31 |
| Até 5 dias | 0 | 0 | 185 / 307 | 60,26% | 31 |
| Até 7 dias | 1 | 1 (PLAS3) | 186 / 307 | 60,59% | 30 |
| Até 30 dias | 7 | 5 (PLAS3, BALM3, CTKA3, TXRX3, MWET3) | 190 / 307 | 61,89% | 26 |

Os números são preços individuais recuperáveis versus empresas completas: no cenário 30 dias, duas outras classes de empresas multi-classe podem ter preço individual, mas Melhoramentos, Josapar e Oderich continuam incompletas porque falta pelo menos uma classe. Nenhuma causa técnica confirmada completou uma empresa, então combinar um tratamento técnico com cada política produz o mesmo número de empresas. A potencial cotação ODER4F de 29/12 em mercado 020 está excluída, não persistida e não conta como recuperação.

## Sensibilidade de EY para as cinco empresas completas no cenário de 30 dias

O cálculo reaproveita os fundamentos atuais do snapshot e altera apenas o preço simulado da classe faltante; não reavalia EV, dívida, caixa ou os fundamentos em si. Valores apenas indicativos, não persistidos.

| Empresa | EY com preço anterior | EY com preço seguinte (informativo) | Diferença |
|---|---:|---:|---:|
| PLAS3 | −8,0481% | −8,0448% | +0,0033 p.p. |
| BALM3 | +15,0215% | +15,0215% | 0,0000 p.p. |
| CTKA3 | +13,8898% | +13,8898% | 0,0000 p.p. |
| TXRX3 | −2,5368% | −2,5367% | +0,0001 p.p. |
| MWET3 | −3,0608% | −3,0608% | 0,0000 p.p. |

O próximo negócio de várias classes só ocorre 23–99 dias depois da referência. A proximidade de EY nesse teste não prova atualidade nem liquidez; especialmente não deve justificar carregar preços obsoletos no ranking.

## Risco de seleção do snapshot e controle de estado

O repositório escolhe com `ORDER BY created_at DESC`, sem um segundo critério. Há dois snapshots com timestamp idêntico (`2026-10-12T18:40:11.188115+00:00`), portanto essa consulta não é determinística em caso de empate (`SNAPSHOT_SELECTION_DETERMINISTIC=NO`, `SNAPSHOT_ORDERING_RISK=YES`). A linha mais recente atual, com timestamp posterior, é única e é o snapshot identificado no baseline. A auditoria registra o risco, sem alterar o repositório nem o mecanismo de ordenação.

Os cinco unresolved preservados são JBS (CVM 020575), ZAMP (024317), Tegra (025844), Tekno (011231) e Eurofarma (026700). Nenhum ranking foi ativado; nenhum preço simulado foi gravado. Os 6 preços já publicados e verificados nesta linha de trabalho — CSNA3 R$8,94 e as cinco recuperações V3 (MBRF3 R$19,98, CTAX3 R$0,97, WDCN3 R$2,63, FIEI3 R$14,49, AMAR3 R$1,01) — continuam no snapshot com data efetiva 30/12/2025.

## Conclusão e próximos passos de diagnóstico

O bloqueio principal dos 17 é cobertura histórica, com uma divisão importante: para 3 emissores há atividade observável apenas em 020; para 13 não há linha no arquivo disponível; e para Schulz só há preço 010 muito antigo. Dos 9 sem cotação na data, somente PLAS3 se encaixa em uma janela de até 7 dias. A política de 30 dias completa cinco empresas, mas tolera gaps de até 27 dias e deixa quatro casos de baixa negociação/antigos sem solução. Portanto nenhuma tolerância foi ativada nesta auditoria.

A ação técnica mais concreta para reduzir `SOURCE_GAP` é validar a disponibilidade e o esquema de dados históricos de ações no BDI, e confrontar o período anterior a 2022 para os 13 sem linha. Em paralelo, qualquer política para 010 stale closes deve ser avaliada como decisão metodológica separada, usando liquidez, gap de pregões e risco de ordenação. Não há evidência suficiente nesta execução para persistir cotações 020 como substitutas de 010.

## Artefatos e verificação

- Scanner read-only: `scripts/audit_magic_formula_price_availability_v4.py`.
- Lógica pura de seleção e projeção: `src/income_analytics/application/magic_formula_price_availability_audit.py`.
- Evidência tabular e manifestos: `tmp/magic-formula-price-blockers-batch-v3/availability-audit-data.json`.
- Resumo da simulação: `tmp/magic-formula-price-blockers-batch-v3/availability-audit-summary.json`.
- Testes V4: `tests/application/test_magic_formula_price_availability_audit.py`.
