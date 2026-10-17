# Recuperação de preço histórico — Phase 01

Atualização de 23/09/2026: uma recuperação foi publicada, elevando a cobertura a
179/307 (58,31%). Ver [recuperação de identidade V1](MAGIC_FORMULA_PRICE_IDENTITY_RECOVERY_V1.md).
Os números abaixo preservam o relatório histórico de 20/09/2026.

Apuração de 20/09/2026. **PARTIAL**: diagnóstico reproduzível dos 38 bloqueadores,
regressões e read-back concluídos; nenhuma recuperação admitida na prévia.
Não houve gravação no banco de produção ou alteração da fórmula, das identidades,
dos preços, do capital, do gate ou da política de sete dias.

## Baseline e resultado

Snapshot: `6d418683-6c09-4cfd-a67b-a4cc54718ddd`, referência `2025-12-31`.
O script exige igualdade integral entre o arquivo congelado e o snapshot mais
recente lido do banco em conexão somente leitura. Divergência interrompe a auditoria.
O read-back anterior foi reexecutado em processo independente e novas conexões,
incluindo recálculo de cobertura, ordem invertida e round-trip em banco temporário.

```text
HISTORICAL_PRICE_RECOVERY_PHASE = PARTIAL
PRICE_ONLY_BLOCKERS_BEFORE = 38
PRICE_ONLY_BLOCKERS_RESOLVED = 0
PRICE_ONLY_BLOCKERS_AFTER = 38
HISTORICAL_PRICE_READY_BEFORE = 230
HISTORICAL_PRICE_READY_AFTER = 230
HISTORICAL_PRICE_GAPS = 77
FULL_DATA_READY_BEFORE = 178
FULL_DATA_READY_AFTER = 178
FULL_DATA_COVERAGE_BEFORE = 57.98%
FULL_DATA_COVERAGE_AFTER = 57.98%
RANKABLE_BEFORE = 174
RANKABLE_AFTER = 174
UNRANKABLE = 4
UNRANKABLE_REASON = NON_POSITIVE_INVESTED_CAPITAL
UNIVERSE = 307
MAX_FULL_DATA_READY_AFTER_PRICE = 216
MAX_FULL_DATA_COVERAGE_AFTER_PRICE = 70.36%
CURRENT_PRICE_PROXY_USED = false
MANUAL_PRICE_USED = false
DATA_IMPUTATION_USED = false
ISSUER_HARDCODE_USED = false
GOLDEN_FIVE_PRICE_REGRESSION = PASS
GOLDEN_FIVE_CAPITAL_REGRESSION = PASS
GOLDEN_FIVE_FULL_DATA_READY = 5/5
GOLDEN_FIVE_REGRESSION = PASS
DETERMINISM_STATUS = PASS
LINEAGE_STATUS = PASS
RANKING_ENGINE_REGRESSION = PASS
PRICE_READBACK = PASS
TESTS_PASSED = 231
TESTS_FAILED = 0
CHANGED_FILES_LINT = PASS
MAGIC_FORMULA_PREVIEW = ACTIVE
RANKING_GATE = BLOCKED
RANKING_STATUS = INACTIVE
```

Os PASS de regressão comprovam preservação do baseline existente; não certificam
novos emissores nem transformam o QA da prévia em QA canônico individual.
Endpoint verificado: `http://127.0.0.1:8000/api/tools/magic-formula/stocks`.
Nenhum preço novo foi publicado; a lista de recuperados e de preços recuperados é vazia.

## Dataset e causas

Dataset completo: `tmp/price-recovery-phase1/price-only-blockers.json`.
Lista legível de todos os 38 emissores e classes bloqueantes:
`tmp/price-recovery-phase1/blockers-table.md`.
Inclui issuer_id, CVM, CNPJ, security_id, ticker declarado, ticker histórico quando
há registro, datas, janela, prontidão contábil/security/capital, source references,
registros anuais e hashes dos insumos. Ticker atual não comprovado permanece null.

A classificação automática inicial resulta em 11 SOURCE_MISSING_DATE e 27 UNKNOWN,
com categorias primárias disjuntas. Uma classe que já possui negociação na janela
é AVAILABLE e não entra como causa desconhecida. SOURCE_MISSING_DATE descreve
somente a ausência na janela para o ticker consultado, não prova ausência em todas
as fontes ou inexistência de evento societário.

A pesquisa documental complementa esse diagnóstico, sem alterar automaticamente
identidades ou preços:

| Caso | Causa documental | Evidência e pendência |
|---|---|---|
| JBS (020575) | CORPORATE_ACTION | Circular B3 determina exclusão de JBSS3 após 06/06/2025. Não substituir ação por BDR sem validar a nova security e sua relação com capital/accounting. |
| Marfrig (020788) | CORPORATE_ACTION | B3 informa negociação como MBRF3 a partir de 23/09/2025 após incorporação. FCA declarado como ADR não basta para vincular a série e o capital histórico. |
| CSN Mineração (025585) | SECURITY_MAPPING_GAP | FCA usa 25585 como ticker; B3 identifica CMIN3 desde o IPO em 18/02/2021. Falta integrar evidência temporal de identidade e revalidar toda a cadeia antes de recuperar preço. |

Após esses refinamentos documentais, as causas primárias são:

```text
SOURCE_GAP_CONFIRMED = 10 (escopo: janela no arquivo anual para o ticker declarado)
IMPLEMENTATION_GAP_FOUND = 0 (pipeline produtivo; nenhum comprovado)
IMPLEMENTATION_GAP_FIXED = 0
SECURITY_MAPPING_GAP_FOUND = 1 (com evidência documental)
SECURITY_MAPPING_GAP_FIXED = 0
CORPORATE_ACTION_CASES = 2
LISTING_DATE_CASES = 0 (nenhum comprovado)
UNKNOWN_CASES = 25
```

As demais suspeitas de ticker são UNKNOWN. Similaridade de nome e formato inválido
são pistas, não autorização para substituir ticker. Não se atribui SOURCE_PARSER_GAP
sem demonstrar registro válido rejeitado pelo parser. Os dois erros corrigidos nesta
fase pertenciam ao script de investigação e não recuperaram preços produtivos.

## Fontes avaliadas

| Fonte | Cobertura, formato e identidade | Reprodução e limites | Decisão |
|---|---|---|---|
| B3 COTAHIST | Histórico desde 1986, diário, ZIP/TXT; ticker, ISIN, mercado, classe, preços e negócios | Arquivo anual local com SHA-256 e referências de linha. Cotações sem ajuste por eventos; exige identidade e data corretas. Página pública não implica licença irrestrita de redistribuição. | Manter fonte já integrada e política V1. |
| B3 BDI | Boletins datados, PDFs com tabelas por seção e identificação dos ativos | Arquivar documento e hash; tabelas de empréstimos, índices ou volume zero não equivalem a fechamento. Extração/semântica variam por seção. Direitos de redistribuição precisam ser verificados antes de distribuir dados. | Usar como pesquisa/contraprova; não integrar preço nesta fase. |
| B3 Empresas Listadas | Cadastro atual por CVM/CNPJ, ticker e ISIN; portal web | Cadastro mutável; não prova sozinho vigência histórica em 2025. Automação deve preservar resposta bruta, instante e evidência temporal independente. | Candidata a identidade; sem substituição automática. |
| CVM FCA | ZIP/CSV anual versionado, CNPJ, classe, ticker declarado, datas e documento | Artefato oficial local reproduzível; declarações podem conter placeholder ou ticker inadequado. Não fornece cotação. | Preservar declaração e registrar divergência. |
| Circulares B3 | Documentos datados de eventos societários e mudança de negociação | Fonte primária por evento; arquivamento/hash necessário para futura integração. Não fornecem necessariamente preço ou cadeia completa de capital. | Evidência de causa, sem converter automaticamente securities. |

Fontes consultadas:

- [B3: histórico e semântica das cotações](https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/historical-data/equities/historical-quote-data/).
- [B3: IPO de CSN Mineração](https://www.b3.com.br/pt_br/noticias/csn.htm).
- [B3: evento Marfrig/BRF](https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Detail?agencia=15&dataNoticia=2025-09-18+05%3A27%3A40&idNoticia=3073281).
- [B3: circular de incorporação JBS](https://www.b3.com.br/data/files/FB/A5/34/34/663179106B8BCB69AC094EA8/CL%20007-2025-VNC_ING%20TRAT%20DAS%20CARTEIRAS%20DE%20%C3%8DNDICES%20DA%20B3%20INCORPJBS%20SA%20JBSS3%20PELA%20JBS%20PART%20SOC%20SA%20JBS%20PA.pdf).

## Alterações e validação

- `scripts/audit_magic_formula_price_only_blockers.py`: janela inclusiva 24–31/12,
  mercado à vista, distinção AVAILABLE/UNKNOWN, bloqueio por baseline divergente,
  identificação explícita de pistas não verificadas e hashes de lineage.
- `tests/application/test_price_only_blocker_audit.py`: cinco testes novos cobrindo
  data sem negociação, limites da janela, futuro, classe disponível e pista de nome.
- Este relatório e os artefatos locais de diagnóstico/inventário.

Executados: `tests/application` e `tests/infrastructure/test_historical_price_audit_source.py`
(229 PASS); `tests/infrastructure/test_b3_cotahist_market_data.py` (2 PASS).
Ruff passou nos dois arquivos Python alterados nesta fase. Houve aviso preexistente
de criação do cache pytest; não houve falha de teste. Lint global não foi executado
nem foram corrigidos problemas não relacionados.

O read-back regenerou `tmp/historical-price-phase3/readback-report.json` e confirmou
igualdade integral dos emissores com o snapshot pai, preservando finanças e lineage.

## Worktree e pendências

Inventário detalhado em `tmp/price-recovery-phase1/worktree-inventory.json`, coletado
antes da criação deste relatório. Unidade: entradas de `git status --short`, com
diretórios untracked agregados; não é contagem recursiva de arquivos.

```text
WORKTREE_TOTAL_ITEMS = 153
SOURCE_CODE_COUNT = 85
TEST_COUNT = 11
DATABASE_MIGRATION_COUNT = 15
VALIDATED_DATASET_COUNT = 2
GENERATED_DATA_COUNT = 1
DOCUMENTATION_COUNT = 34
CACHE_LOG_TEMP_COUNT = 3
UNKNOWN_COUNT = 2
```

UNKNOWN corresponde a `.env.example` e `.gitignore` (configuração fora da taxonomia).
`data/` e `tmp/` agregam conteúdos mistos; revisar arquivo a arquivo antes de ignorar.
Candidatos a ignore: diretórios temporários `.pytest-basetemp-*`, `.pytest-tmp-*` e
caches locais brutos CVM, preservando fixtures versionadas e evidências necessárias.
Nenhuma mudança no .gitignore, reset, clean, remoção de trabalho ou commit foi feita.
O inventário inclui o script de auditoria já iniciado nesta mesma fase em interação
anterior; não permite atribuir todos os arquivos agregados a uma fase específica.

Próxima ação: arquivar provas de identidade temporal B3/CVM, implementar vínculo
genérico com rejeição de ambiguidades e validar security/capital/accounting antes de
admitir qualquer preço. Permanecem 25 causas não comprovadas e 38 recuperações
pendentes. A fase não está concluída como recuperação de cobertura.
