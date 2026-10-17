# Recuperação de identidade e preço histórico — 23/09/2026

**PARTIAL, com uma recuperação publicada na prévia.** CMIN3 foi recuperado a partir
do ticker inválido `25585` declarado no FCA. O código não contém exceções por emissor:
aplica a mesma política de evidência a declarações inválidas, com rejeição de
ambiguidades, conflito de CNPJ/CVM/ISIN, classes incompatíveis, datas inadequadas e
eventos que exigem análise própria. Os outros 37 bloqueadores permanecem explícitos.

## Resultado persistido

```text
HISTORICAL_PRICE_RECOVERY_PHASE = PARTIAL
PRICE_ONLY_BLOCKERS_BEFORE = 38
PRICE_ONLY_BLOCKERS_RESOLVED = 1
PRICE_ONLY_BLOCKERS_AFTER = 37
HISTORICAL_PRICE_READY_BEFORE = 230
HISTORICAL_PRICE_READY_AFTER = 231
HISTORICAL_PRICE_GAPS_AFTER = 76
FULL_DATA_READY_BEFORE = 178
FULL_DATA_READY_AFTER = 179
FULL_DATA_COVERAGE_BEFORE = 57.98%
FULL_DATA_COVERAGE_AFTER = 58.31%
RANKABLE_BEFORE = 174
RANKABLE_AFTER = 175
UNRANKABLE = 4
UNRANKABLE_REASON = NON_POSITIVE_INVESTED_CAPITAL
SOURCE_GAP_CONFIRMED = 10
IMPLEMENTATION_GAP_FOUND = 0
IMPLEMENTATION_GAP_FIXED = 0
SECURITY_MAPPING_GAP_FOUND = 1
SECURITY_MAPPING_GAP_FIXED = 1
CORPORATE_ACTION_CASES = 2
LISTING_DATE_CASES = 0
UNKNOWN_CASES = 25
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
PERSISTED_READBACK = PASS
TESTS_PASSED = 244
TESTS_FAILED = 0
CHANGED_FILES_LINT = PASS
PRE_EXISTING_LINT = NOT_RERUN
MAGIC_FORMULA_PREVIEW = ACTIVE
RANKING_GATE = BLOCKED
RANKING_STATUS = INACTIVE
TOOL_STATUS = VALIDATION_REQUIRED
```

SOURCE_GAP_CONFIRMED conserva o escopo da apuração anterior: ausência de negócio
na janela do arquivo anual para o ticker consultado. Não significa inexistência
de preço em qualquer fonte. Nenhuma suspeita adicional do cadastro atual foi
promovida automaticamente a causa histórica comprovada. Os 25 UNKNOWN ainda
exigem investigação; não foram reclassificados como source gap.

Snapshot anterior: `6d418683-6c09-4cfd-a67b-a4cc54718ddd`.
Snapshot novo: `b3aa341e-7074-4d53-93f3-b3b88d247c19`.
Backup SQLite consistente, fechado e relido antes da gravação:
`tmp/price-recovery-identity-v1/universe-before-publication.db`.
O snapshot anterior não foi alterado. A transação de gravação foi encerrada;
o read-back ocorreu primeiro em outra conexão e depois em outro processo.

## Recuperação comprovada

| Emissor / CVM | issuer_id | Ticker histórico | Preço | Data efetiva | Origem |
|---|---|---|---|---|---|
| CSN Mineração / 025585 | d5f0aa85-a0d2-5521-b052-1f82b89a664a | CMIN3 | R$ 5,45 | 30/12/2025 | COTAHIST_A2025.ZIP, COTAHIST_A2025.TXT, linha 1692364 |

Referência solicitada: 31/12/2025. Política inalterada:
`MAGIC_FORMULA_HISTORICAL_PRICE_V1`, última negociação até a referência dentro de
sete dias corridos. ISIN: `BRCMINACNOR2`; CNPJ: `08902291000115`.

A capa do aviso oficial de oferta identifica CNPJ/ticker/ISIN e ações ordinárias;
a assinatura data o documento em 22/01/2021. A resposta B3 consultada em 23/09/2026
confirma o mesmo CVM/CNPJ/ISIN e início da negociação em 18/02/2021. Ela serve de
corroboração, nunca como fonte de preço nem como prova histórica isolada. A série
anual oficial de 2025 contém o mesmo ISIN, sem conflito entre os registros usados.

Foram preservados issuer_id, security_id interno, declaração FCA original e o
ticker declarado no campo `declared_ticker`. Accounting, quantidades de capital e
seu lineage permanecem iguais. A vigência passa a usar o início de negociação
comprovado, sem antecipar a oferta ou extrapolar a janela. A nova cadeia de
lineage inclui arquivo e hash do PDF, páginas, URL/data da aquisição, resposta B3,
hash, ticker, ISIN, referência, data efetiva, linha bruta, preço e regra aplicada.
O instante de processamento está no novo snapshot; aquisições têm timestamps próprios.

Fonte documental:
[aviso oficial B3](https://www.b3.com.br/data/files/22/E1/42/82/7CE477108F39C077AC094EA8/CSN%20Mineracao%20-%20Aviso%20ao%20Mercado.pdf).
Os limites de uso das fontes constam no relatório Phase 01: consulta pública não
equivale a licença irrestrita de redistribuição comercial. Não foi integrada nova
fonte de cotações: o preço continua vindo exclusivamente do COTAHIST já aprovado.

## Validação e impacto

- Extração automática com pypdf; conferência independente com pdfplumber e revisão
  visual das páginas 1 e 44 do PDF original.
- Conferência independente da linha bruta anual, incluindo mercado à vista,
  ticker, ISIN, data e preço; comparação com o provedor B3 existente.
- Reexecução com registros e emissores invertidos, sem diferença no resultado.
- Igualdade integral de todos os emissores não recuperados, incluindo Golden Five.
- Mesma engine e cálculo da prévia; nenhum arquivo do algoritmo foi alterado.
  A entrada de CMIN3 pode alterar posições relativas, como previsto no preview.
- 243 testes em `tests/application` e nos testes de preço B3/auditoria, mais um
  teste offline da fixture oficial: 244 testes distintos aprovados. Após a publicação,
  os cinco testes de preview/fixture foram repetidos e passaram.
- Lint passou nos nove arquivos Python alterados. Lint global não foi reexecutado.

Não foi criado QA canônico artificial para CMIN3: `canonical_status` continua
`NOT_RESOLVED` e `canonical_ranking_eligible` continua false. A recuperação altera
o universo de dados da prévia, não autoriza o ranking produtivo. Os PASS acima são
regressões do contrato existente, não uma nova certificação canônica de todo o universo.

## Arquivos e reprodução

Código novo:

- `src/income_analytics/application/historical_security_identity.py`
- `scripts/collect_b3_identity_evidence.py`
- `scripts/extract_b3_offer_identity.py`
- `scripts/prepare_historical_identity_recovery.py`
- `scripts/readback_identity_recovery.py`
- `scripts/publish_identity_recovery.py`

Testes:

- `tests/application/test_historical_security_identity.py`: 11 casos de recuperação,
  preservação e rejeição de provas conflitantes/incompletas.
- `tests/infrastructure/test_historical_identity_fixture.py`: replay da fixture
  oficial versionada `tests/fixtures/cvm/price_identity_v1` sem rede.
- `tests/application/test_magic_formula_preview.py`: baseline fixado no snapshot
  original e novo teste dos contadores derivados do snapshot corrente.

Artefatos de evidência:

- `data/magic_formula/price_recovery_identity/20260923T102111856750Z/manifest.json`:
  38 respostas arquivadas, 34 com CVM/CNPJ coincidentes e quatro não confirmadas.
- `tmp/price-recovery-identity-v1/readback-report.json`: preço e validação da proposta.
- `tmp/price-recovery-identity-v1/publication.json`: backup e recibo da gravação.
- `tmp/price-recovery-identity-v1/persisted-readback.json`: novo processo/conexões.
- `tmp/price-recovery-identity-v1/live-preview.json`: resposta real do site já com
  179/307, 58,31%, 175 ranqueáveis, 128 aguardando dados completos e gate bloqueado.
- `tmp/price-recovery-identity-v1/remaining-blockers.json` e `.md`: lista individual
  dos 37 casos restantes, seus tickers, dimensões, fontes e diagnóstico inicial.

Preparação e read-back são separados da publicação. O publicador exige o hash da
proposta validada, igualdade do snapshot pai e backup novo, recusando sobrescrevê-lo.
Não reexecutar a publicação já concluída. Para reproduzir o preparo, usar uma cópia
do banco no estado pai: o script recusa um baseline corrente diferente.
O extrator requer Python com pypdf; o read-back recebe `--pdf-python` apontando para
um runtime com pdfplumber. A aplicação principal continua em Python 3.14.

## Worktree e trabalho restante

Nenhum reset, clean, restore, commit ou edição de .gitignore foi realizado.
Havia 154 entradas agregadas ao retomar. Antes deste novo relatório foram
inventariadas 155 entradas: 86 SOURCE_CODE, 11 TESTS, 15 DATABASE/MIGRATION,
2 VALIDATED_DATASET, 1 GENERATED_DATA, 35 DOCUMENTATION, 2 CACHE,
1 TEMPORARY_ARTIFACT e 2 UNKNOWN. Diretórios untracked são contados como entradas,
não como seus arquivos individuais. Inventário completo em
`tmp/price-recovery-identity-v1/worktree-inventory.json`.

Preservados os candidatos a ignore da fase anterior, sujeitos à revisão individual;
as novas fontes arquivadas e fixtures são evidência, não lixo a remover.

Próximo trabalho: comprovar temporalmente os outros vínculos sugeridos pelo
cadastro B3. JBS/Marfrig exigem tratamento de evento societário; cadastro atual ou
similaridade de nomes não autorizam sua recuperação automática. Nenhuma das outras
37 empresas recebeu preço, FULL_DATA_READY ou posição artificialmente.
