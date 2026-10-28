# PR5.1C — Inventário de referências Magic Formula

Data: 28/10/2026. Base de código PR #48: `1bbd2d42686ab0c893790772a05a7845cfbc0295`; base financeira `ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Branch isolada `codex/pr51c-magic-formula-references`. Sem commit, push, merge ou deploy. O PR5.1B não está integrado: seus quatro arquivos locais foram copiados explicitamente para esta branch, preservando o worktree B.


## Resultado e critérios de confiança

**Recuperação parcial; CI histórica ainda BLOCKED.** Os arquivos existem no workspace anterior, mas existência e checksums calculados hoje não autenticam publicações passadas. Nove entradas possuem conteúdo autenticado por âncoras anteriores; só uma está aprovada para inclusão/provisionamento CI: o índice CVM DFP2025. Duas referências são RECOVERABLE, sete BLOCKED, uma REJECTED. VERIFIED significa origem/integridade comprovadas no escopo descrito; não implica licença, dependências completas, certificação financeira ou aprovação CI. O campo ci_approved é separado e false por padrão.

O [manifesto de proveniência](magic_formula_reference_provenance.json) enumera os 19 itens com SHA-256/digests, schema, origem, responsáveis, datas, consumidores, cadeia e ações pendentes. É um manifesto novo de engenharia, sem modificar manifests congelados.

## Preparação Git e fontes pesquisadas

- O conector GitHub confirmou PR #48 aberto, draft, não mesclado, head 1bbd2d4 e base ca627ac. Não presumimos integração de B.
- develop local continua em 11c110b; origin/develop e a base confirmada do PR apontam para ca627ac. Nenhuma branch existente foi atualizada/rebaseada/resetada.
- B continua no mesmo HEAD com parser, teste frontend, testes parser e relatório sem commit. C foi criado do HEAD exato e recebeu cópia byte a byte desses quatro arquivos. Os três documentos A continuam no worktree A, sem alteração.
- Busca pelos caminhos exatos dos quatro inputs em todos os refs locais alcançáveis: nenhuma versão histórica recuperada. Tags enumeradas no manifesto foram verificadas via histórico alcançável. Apêndices de outras certificações existentes no Git não contêm esses inputs.
- GitHub Releases: lista vazia. Actions: 18 artefatos de CI sanitizados, sem pack histórico de referências. Não confundir relatórios atuais sem payload com snapshots originais.
- Os candidatos foram localizados em C:/Projetos/income-analytics. Arquivos de evidência foram lidos, sem executar seus geradores. O DB específico de universos foi aberto mode=ro&immutable=1, sem WAL presente; continha apenas uma tabela de snapshots, oito registros. SHA antes/depois idêntico. Não foi lido o banco de carteiras nem acessado o worktree produtivo.

## Inventário por referência

| ID | Estado | Aprovada CI | Origem/caminho | Identificador/digest disponível |
| --- | --- | --- | --- | --- |
| ranking-v12.2 | VERIFIED | False | docs/appendices/magic_formula_v12_2/ranking_snapshot.json | mf-f1ee50809c83979ba221d84e |
| universe-v8 | RECOVERABLE | False | docs/appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv | ed8a9235-ee14-4a97-93fd-0dbcd87113fb |
| universe-v9.2 | RECOVERABLE | False | docs/appendices/magic_formula_v9_2/methodological_universe.csv | ed8a9235-ee14-4a97-93fd-0dbcd87113fb |
| universe-db | BLOCKED | False | data/magic_formula/universe_snapshots.db | c3f906e32aac085a196b7def498660e2d7e02d463ce36496c11c582dc905f744 |
| universe-ed8a | VERIFIED | False | price blockers batch recovery V3 | ed8a9235-ee14-4a97-93fd-0dbcd87113fb |
| universe-6d418 | BLOCKED | False | Historical discovery/recovery; see universe-db | Ver manifesto |
| universe-tied-rows | BLOCKED | False | Historical discovery/recovery; see universe-db | Ver manifesto |
| cvm-dfp-2023 | VERIFIED | False | data/cvm/dfp_cia_aberta_2023.zip | 9b301ce4bb1b6b351435a683784deec9d38c3f90ab6f2cb01729c12a9abf5bde |
| cvm-dfp-2024 | VERIFIED | False | data/cvm/dfp_cia_aberta_2024.zip | f52caa45b6fc202334d7b87bb9bb24830280f5ff6a29b8b8557894b26fed1be8 |
| cvm-dfp-2025 | VERIFIED | False | data/cvm/dfp_cia_aberta_2025.zip | de8b7be1cdae032a402ab33916015c74fdc30f0bc64be3f38a4b5dd1d43f6d79 |
| cvm-itr-2025 | VERIFIED | False | data/cvm/itr_cia_aberta_2025.zip | 33818c4d8b755961010d7353accad4dfe2659b2b2e035493d8a838e88289a491 |
| cvm-fca-2024 | VERIFIED | False | data/cvm/fca_cia_aberta_2024.zip | 55ad239eee3a922e25a599f72eb835e0e0a0ae50de0b50c738997143302f5e49 |
| cvm-fca-2025 | VERIFIED | False | data/cvm/fca_cia_aberta_2025.zip | dbbbda515a98d402ff0b0fb2808d15f3d81b029e0c61de8b95655323604d1192 |
| cvm-dfp-2025-index | VERIFIED | True | CVM original member; lossless gzip(mtime=0) packaging in PR5.1C | a99e5d1db1c0f62bf1090452a41ed7df8bd3b20ecd2df699ccd16c8fc963cc94 |
| cotahist-2025 | BLOCKED | False | data/cotahist/COTAHIST_A2025.ZIP | 6cc0ad851c8f605ca30418acac48be81f1767f6ed05b4f563772d06ae448047d |
| cotahist-2022-2024 | BLOCKED | False | B3 | Ver manifesto |
| historical-shares-evidence | BLOCKED | False | Historical generation scripts | Ver manifesto |
| v6-v7-v9-lineage | BLOCKED | False | Historical generation scripts | Ver manifesto |
| synthetic-historical-replacement | REJECTED | False | None | Ver manifesto |

## V12.2 — conteúdo publicado recuperado, distribuição pendente

O JSON local tem 2.873.203 bytes, SHA-256 08d8776ee27af53c54c36efd9768fbc40e190f6f0ea0e0c18ec549199ff7cad0. ID mf-f1ee50809c83979ba221d84e, as-of 2025-12-30, criado 2026-10-16T11:26:06.928076+00:00. As 165 linhas e sua ordem permanecem nos bytes originais; nenhuma empresa, posição, preço, indicador ou data foi gerada.

Verificação independente em stdlib, sem importar ranking_digest nem calcular EY/ROC: SHA do JSON ordenado com separadores default, UTF-8 e ensure_ascii=False, sobre os campos de contexto+results, reproduz ranking_hash f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3. O conteúdo completo sem created_at/snapshot_content_hash reproduz 18a8631490f3a340575df3234acc26065a467b701c9a999cd3eaed859bb82db7. Ambos já constam em docs/MAGIC_FORMULA_POINT_IN_TIME_RANKING_AND_RELEASE_V12_2.md:24 na baseline. O SHA de bytes observado agora é novo metadado, não uma âncora histórica independente por si só.

A âncora preserva results, provenance, price/filing/shares lineage e contexto. O snapshot referencia ed8a…/0e46…, política 96d5… e supersede mf-783598cd7f717527425123eb (V11 invalidada por look-ahead). Não usar V11 como substituto. Os setores expostos pela API são enriquecimento separado: _company_metadata_for_data_snapshot lê o universo pelo ID/digest do ranking; a taxonomia setorial não deve ser inventada ou inserida no snapshot para os testes. O bloqueio atual do pack DB impede validar esse enriquecimento em checkout limpo.

Os testes API persistem o JSON em SQLite temporário e leem o snapshot publicado; não foi alterado nenhum caminho para recalcular ranking na leitura. Autenticação do JSON não recertifica sua metodologia nem autoriza redistribuição dos dados B3 incorporados. Não incluído no pack CI enquanto essa permissão e a linhagem DB necessária permanecerem pendentes.

## V6 → V7 → V8 → V9 → V9.2

V6 lê ed8a… e separa 360 = 35 exclusões financeiras + 18 fora de baseline + 307. V7 refina seleção de segurança/identidade e taxonomia. V8 resolve reviews S4/L3 com COTAHIST e dez FRE; V9 ativa a política; V9.2 reconstitui a baseline e recalcula determinismo, sem mudar fórmulas. A limitação histórica V7 foi aceita como UNRESOLVABLE nos documentos V9.2; não reabrimos a alegação de equivalência de IDs de testes V7 nem a apresentamos como prova recuperada.

Os dois CSVs candidatos têm 307 linhas, com 180 ELIGIBLE_COMPLETE, 63 ELIGIBLE_DATA_BLOCKED, 45 LIQUIDITY_FAIL e 19 BUYABLE_SECURITY_REVIEW. Denominadores documentados: 243 e 262; coberturas 180/243 e 180/262. Schemas, hashes observados e versões estão no manifesto. V8 usa methodological_status_v8; V9.2 usa methodological_status. Não renomear colunas ou mudar expectativas dos testes.

Contagens iguais não autenticam as 307 identidades/classificações. Não foi localizada âncora independente do CSV completo ou digest por linha. Audit_manifest/activation_record locais apontam para fontes mas não fornecem essa prova independente; não foram promovidos a verdade apenas por coexistirem com o CSV. A origem é RECOVERABLE e requer evidência independente dos outputs ou replay auditado das fontes congeladas, mantendo o resultado esperado independente do código sob teste.

Geradores: audit_magic_formula_policy_review_resolution_v8.py lê V7 buyable_security_issuer_summary_307/security_candidates_010/commerce_taxonomy_37/blockers_v7_31 e V6 eligibility/liquidity; audit_magic_formula_methodology_activation_v9.py produz V9; audit_magic_formula_baseline_activation_v9_2.py lê V9 e produz V9.2. Nenhum desses geradores foi executado.

## Banco histórico e ordenação

Schema não usa Alembic: MagicFormulaUniverseRepository.initialize cria magic_formula_universe_snapshots e triggers de UPDATE/DELETE que abortam IMMUTABLE_UNIVERSE_SNAPSHOT. Colunas/DDL e oito registros estão no manifesto, sem copiar document_json ou DB binário. Repositório lê readonly e valida document_digest/coverage.

O conteúdo ed8a9235-ee14-4a97-93fd-0dbcd87113fb bate com 0e46baad7108a01b972459b1736ec28a67a2c932fcac10344432569b24a586d9 já registrado em documentos Git. Todos os outros sete registros batem com seus próprios digests armazenados, mas isso só prova autoconsistência. Para 6d418683-6c09-4cfd-a67b-a4cc54718ddd recuperamos ID e candidato, sem âncora independente do conteúdo completo. IDs históricos documentados não autenticam um documento arbitrário com aquele ID.

rowids 6/7 (9dd05e5a… e c458573e…) compartilham created_at 2026-10-12T18:40:11.188115+00:00; latest usa created_at DESC,rowid DESC. Os digests/ordem desses registros ainda precisam de prova independente. Não geramos empates sintéticos com os IDs históricos para satisfazer auditoria. Resultado: DB completo BLOCKED, apesar de ed8a isoladamente autenticado.

## CVM/B3, licenças e minimização

As seis cópias CVM DFP2023/2024/2025, ITR2025, FCA2024/2025 existem. A concatenação na ordem do gerador, precedida pelo digest ed8a, reproduz source_manifest_hash contido no snapshot V12.2 autenticado. DFP2025 também bate com manifest congelado phase2_v1 anterior. Isso autentica as versões locais; não torna a URL atual uma cópia imutável. Nenhum download de dataset foi executado.

Os portais oficiais [DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp), [ITR](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr) e [FCA](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca) declaram ODbL; atribuição à CVM é preservada na fixture aprovada. Fontes são atualizadas semanalmente: recuperação futura deve validar o digest histórico e rejeitar arquivo novo divergente, sem atualizar golden. FCA completo inclui anexos de contatos: não copiar indiscriminadamente por ser público.

A página oficial [Cotações históricas B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/) e seus [Termos de Uso](https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/) não demonstram autorização de redistribuição para este pack. Há restrições expressas; não presumimos licença aberta porque o arquivo pode ser consultado. Não foi localizada licença/autorização específica do projeto. Foi solicitado ao usuário indicar eventual documento; isso permanece bloqueador de distribuição, sem afirmar parecer jurídico definitivo sobre todos os usos derivados.

A fixture aprovada contém somente o membro original dfp_cia_aberta_2025.csv, 157.823 bytes, comprimido sem perdas (23.358 bytes). Sem seleção de empresas, valores esperados calculados ou dados de carteira. O ZIP temporário derivado é explicitamente index-only; não substitui o ZIP DFP completo nem pode alegar seu hash.

## Próximos desbloqueios

1. Localizar permissão B3 aplicável e registrar seu escopo, em vez de presumir autorização geral.
2. Recuperar autenticação independente das linhas V8/V9.2 e dos snapshots predecessores/empates.
3. Exportar só documentos públicos aprovados e seus rowids/timestamps para pack imutável; nunca publicar o DB de origem.
4. Provisionar todo o pack em SQLite temporário, validar digest/coverage e só então executar asserções históricas.
5. Manter CERT_48/identidade fora desta entrega e sem mudança de hash.
