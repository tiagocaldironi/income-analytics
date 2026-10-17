# Auditoria da taxonomia setorial da Fórmula Mágica

**Resultado:** o pipeline tem uma classificação setorial primária da CVM para todos os emissores do universo congelado. Ele não tem níveis econômicos estruturados de subsetor ou segmento. O campo `Segmento` encontrado na FCA de valores mobiliários é segmento de listagem (por exemplo, Novo Mercado), não setor/segmento econômico. A data de disponibilidade pública de cada classificação não está registrada; por isso, a segurança point-in-time é `UNKNOWN`.

## Escopo e referência

- Universo metodológico congelado: 307 emissores distintos de `docs/appendices/magic_formula_v9_2/methodological_universe.csv`.
- Ranking canônico: snapshot `mf-f1ee50809c83979ba221d84e`, as-of **2025-12-30**, com 165 empresas.
- A fonte de setor usada no snapshot é o arquivo geral FCA da CVM de 2025, registrado no manifesto do snapshot. O snapshot geral tem referência **2025-12-31**, posterior em um dia à data do ranking. Isso, por si só, não prova que a classificação já estava publicamente disponível em 2025-12-30.
- O FCA contém `Data_Referencia`, `Versao` e `ID_Documento`, mas não foi encontrada no registro utilizado uma data de protocolo/disponibilização que permita estabelecer quando cada classificação se tornou conhecida.
- Não inferi setor, subsetor ou segmento pelo nome da empresa. Ausência de dado estruturado aparece como `UNKNOWN`.

## Campos e cobertura

| FIELD | AVAILABLE | SOURCE | SOURCE_FIELD | EXAMPLE_FOR_WEGE3 | COVERAGE (307) | COVERAGE (165) | POINT_IN_TIME_SAFE | NOTES |
|---|---|---|---|---|---:|---:|---|---|
| Setor econômico reportado | Sim | CVM FCA de companhias abertas, arquivo geral 2025 | `Setor_Atividade` | `Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças` | 307/307 (100%) | 165/165 (100%) | `UNKNOWN` | Classificação primária presente no objeto canônico como `economic_sector`. Fonte por emissor fica rastreável em `sector_source_reference`. |
| Subsetor econômico | Não identificado | Nenhum campo estruturado encontrado na FCA geral integrada ou no objeto canônico | `UNKNOWN` | `UNKNOWN` | 0/307 (0%) | 0/165 (0%) | `UNKNOWN` | Não confundir com descrições livres da atividade. |
| Segmento econômico | Não identificado | Nenhum campo estruturado encontrado na FCA geral integrada ou no objeto canônico | `UNKNOWN` | `UNKNOWN` | 0/307 (0%) | 0/165 (0%) | `UNKNOWN` | Não confundir com o `Segmento` da FCA de valores mobiliários, que representa listagem. |
| Segmento de listagem (metadado distinto) | Sim, para parte do universo | CVM FCA de valores mobiliários 2025; metadado de listagem B3 carregado pela FCA | `Segmento` | `Novo Mercado` | 277/307 (90,2%) | 165/165 (100%) | `UNKNOWN` | Não é classificação econômica. A fonte FCA de valores mobiliários não alimenta os níveis econômicos do objeto canônico. |
| Descrição da atividade econômica (texto livre) | Sim, para parte do universo | CVM FCA de companhias abertas, arquivo geral 2025 | `Descricao_Atividade` | `A WEG SA é uma sociedade de participação não operacional (holding) e também sociedade de comando do Grupo WEG.` | 290/307 (94,5%) | 156/165 (94,5%) | `UNKNOWN` | Texto declaratório, variável e não normalizado; não equivale a subsetor/segmento codificado. Não está persistido como nível da taxonomia canônica. |
| Classificação econômica interna | Sim | Derivada internamente do setor CVM | `economic_sector_group` (derivado de `Setor_Atividade`) | `NON_FINANCIAL` | 307/307 (100%) | 165/165 (100%) | `UNKNOWN` | Grupo binário amplo (`FINANCIAL`, `NON_FINANCIAL` ou `UNDETERMINED`); não é uma taxonomia setorial detalhada. Neste universo já filtrado, todos são `NON_FINANCIAL`. |
| Fonte da classificação | Sim para o setor; não há fonte concorrente canônica | CVM FCA geral 2025 | `CVM_FCA_GENERAL_2025` / `sector_source_reference` | `fca_cia_aberta_2025.zip → fca_cia_aberta_geral_2025.csv`, linha 669 | 307/307 (100%) | 165/165 (100%) | `UNKNOWN` | B3/COTAHIST é usado para identidade/preços, não como taxonomia econômica. O campo `sector` do Brapi aparece apenas no fluxo de descoberta manual, sem lineage por emissor usado no ranking canônico. |
| Data/referência da classificação | Referência do formulário disponível; data de disponibilidade ausente | CVM FCA geral 2025 e referência global do snapshot | `Data_Referencia`, `Versao`, `ID_Documento`; snapshot `reference_date` | Referência `2025-01-01`, versão `2`, documento `152581`; disponibilidade `UNKNOWN` | Referência e identificadores em 307/307; data de disponibilidade 0/307 | Referência e identificadores em 165/165; data de disponibilidade 0/165 | `UNKNOWN` | `Data_Referencia` é referência do formulário, não comprovação de publicação/protocolo. Snapshot com referência global `2025-12-31`, um dia após o as-of do ranking. |

## Exemplo rastreável: WEGE3

O emissor CVM `005410` tem setor bruto `Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças`, proveniente de `Setor_Atividade` no arquivo geral da FCA 2025, linha 669. A linha registra `Data_Referencia=2025-01-01`, `Versao=2` e `ID_Documento=152581`; a data em que a informação ficou disponível continua `UNKNOWN`. A descrição livre informa que a WEG é uma holding e sociedade de comando do Grupo WEG. O agrupamento interno é `NON_FINANCIAL`. A FCA de valores mobiliários traz `Segmento=Novo Mercado`, que é segmento de listagem. Subsetor e segmento econômicos são `UNKNOWN`.

O arquivo de evidência por emissor contém esses valores, referências de linha, disponibilidade desconhecida e a classificação de listagem separada: [sector_taxonomy_issuer_audit.csv](C:/Projetos/income-analytics/docs/appendices/magic_formula_v12_2/sector_taxonomy_issuer_audit.csv).

## Conflitos e consistência entre anos

Não há dois provedores de taxonomia econômica concorrentes integrados ao ranking canônico, então não é possível afirmar que exista ou não conflito simultâneo entre provedores. A fonte setorial canônica observada é CVM. A classificação `sector` de Brapi não tem vínculo de fonte/data por emissor no ranking; não foi tratada como fonte comparável. `Segmento` da FCA de valores mobiliários é outro conceito.

Na comparação das versões FCA 2024 e 2025, dois dos 304 emissores com registro nos dois anos mudaram o setor reportado. São mudanças temporais de classificação da própria fonte, não conflitos simultâneos entre fontes; nenhum dos dois está entre as 165 ranqueadas:

| Emissor | FCA 2024 | FCA 2025 | Situação |
|---|---|---|---|
| APTI3 (CVM 012823) | `Metalurgia e Siderurgia` | `Agricultura (Açúcar, Álcool e Cana)` | Alteração entre referências anuais |
| FICT3 (CVM 015423) | `Sem Setor Principal` | `Alimentos` | Alteração entre referências anuais |

Entre os emissores ranqueados, não houve alteração setorial na comparação anual verificada (0/165). Isso não substitui uma reconciliação de todas as versões e datas de publicação dos formulários.

## Padronização e prontidão para filtros

O setor está disponível em todos os emissores, mas os rótulos ainda não formam uma taxonomia controlada pronta para filtros persistentes: a FCA 2025 contém 41 rótulos brutos distintos no conjunto examinado. A normalização atual remove apenas o prefixo `Emp. Adm. Part. - `; após essa transformação permanecem 25 rótulos distintos. O código interno também mantém listas de rótulos/variantes para agrupar setor financeiro e não financeiro.

Assim, um filtro exploratório pelo setor CVM bruto pode ser exibido com a origem claramente indicada. Para filtros duráveis, agregações consistentes ou comparação histórica, ainda falta uma tabela de mapeamento versionada que defina identificadores canônicos, aliases e validade temporal. Filtros por subsetor ou segmento econômico não são suportados com os dados atuais. O campo de segmento de listagem pode ser usado separadamente, com rótulo explícito de listagem.

## Veredito

- `SETOR`: disponível para 307/307 do universo e 165/165 do ranking; fonte CVM FCA; point-in-time `UNKNOWN`.
- `SUBSETOR`: `UNKNOWN`, sem campo estruturado/cobertura.
- `SEGMENTO ECONÔMICO`: `UNKNOWN`, sem campo estruturado/cobertura.
- `SEGMENTO DE LISTAGEM`: disponível para 277/307 e 165/165, mas é um conceito diferente.
- Conflito simultâneo entre provedores econômicos: não mensurável no pipeline integrado atual. Foram observadas duas mudanças entre as FCA 2024 e 2025, nenhuma no ranking.
- Prontidão: setor bruto pode servir a uma exploração simples; taxonomia estável para filtros históricos requer padronização explícita. Não há base para filtros econômicos por subsetor/segmento.

## Linhagem no código

- `src/income_analytics/application/magic_formula_universe.py`: lê `Setor_Atividade`, cria `economic_sector_group` e registra a referência da fonte.
- `src/income_analytics/application/magic_formula_investable_universe.py`: aplica normalização superficial do rótulo do setor.
- `src/income_analytics/infrastructure/magic_formula_universe_sources.py`: lê FCA geral e valores mobiliários para dados de universo; as fontes B3 de mercado não fornecem uma hierarquia econômica integrada.
- `src/income_analytics/infrastructure/brapi_asset_discovery.py`: recebe `sector` no fluxo de descoberta, sem lineage suficiente para tratá-lo como taxonomia canônica do ranking.
