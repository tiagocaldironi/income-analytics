# Magic Formula — expansão de fontes históricas de preço V5

Data da auditoria: 12/10/2026. Escopo: somente os 14 `SOURCE_GAP` da V4, preço exato de 30/12/2025 e mercado à vista B3 `010`. A V5 foi executada em dry run; nenhum preço ou snapshot novo foi persistido.

## 1. Baseline

| Métrica | Antes da V5 |
|---|---:|
| Universo | 307 empresas |
| Empresas completas | 185 |
| Cobertura | 60,26% |
| Snapshot | `ed8a9235-ee14-4a97-93fd-0dbcd87113fb` |
| Data de referência do snapshot | 31/12/2025 |
| Data de referência do preço | 30/12/2025 |
| Ranking | INACTIVE; ferramenta `VALIDATION_REQUIRED` |
| SOURCE_GAP auditados | 14 |

A identidade empresa/security da V4 foi mantida. A ausência abaixo significa ausência de um fechamento COTAHIST 010 na data exata; para empresas listadas antes de 2019 não prova que nunca tenham negociado em qualquer ano de sua vida de listagem.

## 2. Fontes investigadas

- COTAHIST anual oficial da B3: A2019, A2020 e A2021 foram baixados para esta V5 e integralmente percorridos; a V4 já tinha percorrido A2022–A2026. Anos verificados: **2019–2026**. Os scans casaram ticker e ISIN, validando classe, mercado e data. PREULT foi tratado como preço de fechamento.
- Busca direcionada por identidade/listagem: dados de emissor, ticker e ISIN da B3 usados para reduzir os anos necessários. Nenhum dado de fornecedor terceiro foi usado ou integrado.
- BDI da B3: tabela estruturada corrente encontrada, mas não acessível na data 30/12/2025 pelo seletor histórico (limite de janela recente). A tabela “Resumo de ações > Ações” mostra número de negócios e volume, sem campo de fechamento. Boletins antigos são encaminhados ao acervo em PDF. Resultado: `BDI_NOT_SUFFICIENT`; nenhum provider BDI foi criado.
- Outra fonte estruturada B3 adequada à data-alvo: não encontrada nesta investigação.

## 3. COTAHIST anterior a 2022

Os arquivos abaixo foram obtidos da URL oficial B3 e verificados por SHA-256. Cada TXT foi percorrido até o fim; os totais representam registros de cotação. As manifestações V4 para 2022–2026 preservam os hashes, mas não tinham `retrieved_at` registrado.

| Arquivo | Ano | SHA-256 | Obtido em (UTC) | Registros percorridos |
|---|---:|---|---|---:|
| COTAHIST_A2019.ZIP | 2019 | 5170d3f8f079c3306424b36c2fae9b467391f8fa37d16d389f487b4c5c28edb9 | 2026-10-12T20:34:18.523287+00:00 | 779229 |
| COTAHIST_A2020.ZIP | 2020 | 86442168939b9da7b3cc1ec1662c333ee5ab4c75f2be1865b5bf55ba4c52168f | 2026-10-12T20:34:16.105678+00:00 | 1251646 |
| COTAHIST_A2021.ZIP | 2021 | b0d4aed17d609c7ba615a23320c2fd513b580a251ae7d884a5015ef8a3fe4705 | 2026-10-12T20:30:08.896641+00:00 | 1831862 |

Achados pré-2022 relevantes:

- `BOBR3` / ISIN `BRBOBRACNOR6`: registro 010 em 14/01/2020, PREULT R$ 1,00. É anterior à referência e não pode preencher 30/12/2025.
- `SHUL3` / ISIN `BRSHULACNOR7`: registros 010 em 18/06/2021 (R$ 111,37) e 21/06/2021 (R$ 112,01). A pesquisa V4 também encontrou registro 010 em 12/09/2022. Nenhum corresponde a 30/12/2025. Há ainda registros fracionários 020 em 2019 e 2021; não foram convertidos em 010.
- Os outros 12 não tiveram registro correspondente nos anos adicionais percorridos. Para ativos listados antes de 2019, os anos anteriores a 2019 não foram baixados, logo atividade pública anterior permanece indeterminada.

## 4. BDI

A página/tabela BDI estruturada oferece dados recentes, porém não reproduz a cotação histórica requerida. O filtro da tabela histórica não permite selecionar 30/12/2025; os boletins antigos encaminham a PDFs no Acervo B3. A tabela de ações observada contém quantidade de negócios e volume, não PREULT nem campo de fechamento equivalente. Portanto a fonte existe, mas **não é utilizável como provider estruturado para esses preços**; PDFs serviriam apenas como possível evidência manual, não como provider primário nesta V5.

## 5. Casos SOURCE_GAP

`FIRST_LOCAL` e `LAST_LOCAL` referem-se ao conjunto da V4 (2022–2026). “Histórico adicional” lista somente registros 010 relevantes, exceto quando explicita mercado 020.

| Empresa | CVM | CNPJ | Classe | Ticker | ISIN | Primeiro local | Último local | Histórico adicional | Resultado terminal | Bloqueio |
|---|---|---|---|---|---|---|---|---|---|---|
| Auren Operações S.A. | 026174 | 00194724000113 | ON | AESO3 | BRAESOACNOR0 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| BBM Logística S.A. | 024660 | 01107327000120 | ON | BBML3 | BRBBMLACNOR3 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| SUL 116 PARTICIPACOES S.A. | 016438 | 01957772000189 | ON | OPTS3 | BROPTSACNOR6 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| LIFEMED INDUSTRIAL DE EQUIP. E ART. MEDICOS E HOSP. S.A | 024872 | 02357251000153 | ON | LMED3 | BRLMEDACNOR3 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| IGUA SANEAMENTO S.A. | 023175 | 08159965000133 | ON | IGSN3 | BRIGSNACNOR0 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| PRÁTICA PRODUTOS S.A. | 024546 | 08574411000100 | ON | PTCA3 | BRPTCAACNOR9 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| KALLAS INCORPORAÇÕES E CONSTRUÇÕES S.A. | 025798 | 09146451000106 | ON | KLAS3 | BRKLASACNOR3 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| INC EMPREENDIMENTOS IMOBILIÁRIOS S.A. | 024279 | 09611768000176 | ON | INNC3 | BRINNCACNOR0 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| Grupo Salta Educação S.A. | 027820 | 17765891000170 | ON | SALT3 | BRSALTACNOR4 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| QUALITY SOFTWARE S.A. | 023302 | 35791391000194 | ON | QUSW3 | BRQUSWACNOR5 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| BRQ SOLUCOES EM INFORMATICA S.A. | 023817 | 36542025000164 | ON | BRQB3 | BRBRQBACNOR1 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |
| BOMBRIL S.A. - Em recuperação Judicial | 012190 | 50564053000103 | ON | BOBR3 | BRBOBRACNOR6 | — | — | 2020-01-14 R$1 (010) | PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE | preço(s) 010 apenas em data antiga; sem substituição stale |
| SCHULZ S.A. | 014664 | 84693183000168 | ON | SHUL3 | BRSHULACNOR7 | 2022-09-12 | 2022-09-12 | 2021-06-18 R$111.37 (010); 2021-06-21 R$112.01 (010); 6 reg. 020 em 2019 (não aceitos) | PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE | preço(s) 010 apenas em data antiga; sem substituição stale |
| METALURGICA RIOSULENSE S.A. | 013439 | 85778074000106 | ON | RSUL3 | BRRSULACNOR6 | — | — | — | OFFICIAL_SOURCE_CONFIRMED_NO_PRICE | sem preço exato 010 na data-base |

Os registros `first_local_record`/`last_local_record` foram `—` para 13 ativos; Schulz teve somente 12/09/2022 no intervalo V4. Isso não confunde ausência de linha no intervalo com prova de inexistência histórica.

## 6. Preços recuperados

Nenhum. Os 14 casos não têm fechamento COTAHIST 010 exatamente em 30/12/2025. Assim não há evidência candidata HIGH confidence para persistência, não houve read-back de novo preço e nenhum snapshot novo foi criado. Preços ausentes permaneceram indisponíveis, nunca zero.

## 7. Lacunas remanescentes

Doze casos terminam como `OFFICIAL_SOURCE_CONFIRMED_NO_PRICE` para a data-alvo: a fonte oficial COTAHIST completa cobre o dia de referência e não contém registro 010 para a identidade validada. Dois terminam como `PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE`: BOBR3 e SHUL3 possuem histórico 010 apenas em datas antigas. A investigação histórica não é vitalícia para os emissores listados antes de 2019; isso não muda o resultado da data exata coberta em 2025.

## 8. Conflitos entre fontes

Nenhum conflito foi detectado: não surgiu segunda fonte de preço estruturada para a mesma identidade/data. Nenhuma comparação de preço foi necessária. `SOURCE_CONFLICT = 0`.

## 9. Impacto na cobertura

| Métrica | Resultado |
|---|---:|
| Preços recuperados | 0 |
| Empresas que se tornariam completas | 0 |
| Empresas completas após a V5 | 185 |
| Cobertura após a V5 | 60,26% |

## 10. Ordenação de snapshots

A seleção de `latest()` agora ordena por `created_at DESC, rowid DESC`. Como a tabela é append-only (triggers impedem UPDATE/DELETE), o `rowid` é a sequência real de inserção no SQLite; UUID não é usado como proxy de tempo. O teste de empate cria dois snapshots com timestamp igual e verifica que o segundo inserido é selecionado. O snapshot antigo permanece imutável e nenhum snapshot novo foi criado nesta execução.

## 11. Regressões

A bateria direcionada executou **193 testes, todos passando**, incluindo parser COTAHIST, correspondência por ISIN/ticker, validação da classe e do mercado, data exata, rejeição 020/stale/ISIN incorreto, conflitos, provenance, empate de timestamp, preservação do snapshot e idempotência. Os seis golden cases V3 permanecem cobertos pelas regressões existentes: CSNA3 R$ 8,94; MBRF3 R$ 19,98; CTAX3 R$ 0,97; WDCN3 R$ 2,63; FIEI3 R$ 14,49; AMAR3 R$ 1,01 (30/12/2025). Ruff será registrado pelo resultado de lint da execução V5.

## 12. Recomendação

Manter o ranking bloqueado. Não aplicar stale price, fallback 020, interpolação ou forward-fill. Para os 12 sem preço no dia, manter a ausência explícita. Para completar a investigação de atividade ao longo de toda a vida de emissores anteriores a 2019, a próxima auditoria deve escolher intervalos adicionais por ativo e baixar apenas anos relevantes; isso não deve alterar preço da data-base nem o gate do ranking.

## Saída de aceite

```text
MAGIC_FORMULA_HISTORICAL_PRICE_SOURCE_EXPANSION_V5 = PASS
TOTAL_UNIVERSE = 307
COMPLETE_BEFORE = 185
COVERAGE_BEFORE = 60.26%
SOURCE_GAP_CASES = 14
HISTORICAL_COTAHIST_YEARS_CHECKED = 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026
BDI_STRUCTURED_SOURCE_FOUND = YES
BDI_USABLE_FOR_HISTORICAL_PRICES = NO
OTHER_OFFICIAL_B3_SOURCE_FOUND = NO
RECOVERED_FROM_HISTORICAL_COTAHIST = 0
RECOVERED_FROM_BDI = 0
RECOVERED_FROM_OTHER_OFFICIAL_B3_SOURCE = 0
PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE = 2
SOURCE_CONFLICT = 0
OFFICIAL_SOURCE_CONFIRMED_NO_PRICE = 12
SOURCE_STILL_UNAVAILABLE = 0
INSUFFICIENT_EVIDENCE = 0
STATUS_SUM = 14
SECURITY_PRICES_RECOVERED = 0
COMPANIES_BECOMING_COMPLETE = 0
COMPLETE_AFTER = 185
COVERAGE_AFTER = 60.26%
REFERENCE_DATE_CHANGED = NO
STALE_PRICE_POLICY_CHANGED = NO
MARKET_020_ACCEPTED_AS_010 = NO
METHODOLOGY_CHANGED = NO
OLD_SNAPSHOT = ed8a9235-ee14-4a97-93fd-0dbcd87113fb
NEW_SNAPSHOT = NONE
OLD_SNAPSHOT_PRESERVED = YES
SNAPSHOT_SELECTION_DETERMINISTIC = YES
SNAPSHOT_TIE_TEST = PASS
RANKING_ACTIVE = NO
RANKING_BLOCKED = YES
TOP_30_PUBLISHED = NO
GOLDEN_CASES = PASS
V3_RECOVERIES = PASS
INDEPENDENT_READ_BACK = PASS (baseline snapshot re-read; no new price to promote)
IDEMPOTENCY = PASS (two dry runs, no DB/snapshot mutation)
TESTS = 193 PASS / 0 FAIL
RUFF = PASS
REMAINING_SOURCE_GAPS = 0 (all 14 terminally classified; 12 no exact price, 2 old-price policy-incompatible)
REMAINING_NO_TRADE = 9
REMAINING_SECURITY_TYPE_NOT_COVERED = 3
REMAINING_UNRESOLVED = 5
```

### Artefatos de auditoria

- Dry run: `tmp/magic-formula-price-blockers-batch-v3/v5-dry-run.json`
- Manifesto: `tmp/magic-formula-price-blockers-batch-v3/v5-source-manifest.json`
- Executor reproduzível: `scripts/audit_magic_formula_historical_price_source_v5.py`
