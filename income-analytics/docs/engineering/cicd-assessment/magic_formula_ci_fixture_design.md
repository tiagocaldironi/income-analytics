# PR5.1C — Desenho da fixture CI Magic Formula

Data: 28/10/2026. Base de código PR #48: `1bbd2d42686ab0c893790772a05a7845cfbc0295`; base financeira `ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Branch isolada `codex/pr51c-magic-formula-references`. Sem commit, push, merge ou deploy. O PR5.1B não está integrado: seus quatro arquivos locais foram copiados explicitamente para esta branch, preservando o worktree B.


## Implementado e aprovado

- tests/fixtures/cvm/receipt_index_2025_v1/dfp_cia_aberta_2025.csv.gz: membro CVM original, gzip mtime=0, sem mudança de linha/coluna. Atribuição/licença no README adjacente.
- ci/magic_formula_references.py: verified_payload verifica VERIFIED + ci_approved antes de abrir candidatos, limita caminhos à árvore de fixtures CVM, confere digest comprimido e descomprimido. Ausência retorna REFERENCE_MISSING; divergência REFERENCE_DIGEST_MISMATCH/REFERENCE_CONTENT_MISMATCH; referência pendente REFERENCE_NOT_APPROVED. Sem rede, fallback, DB ou geração financeira.
- provision_receipt_index cria ZIP derivado determinístico, com único membro, só abaixo do TEMP efetivo e sem sobrescrever arquivo existente. Não altera diretório data/ nem a constante DFP_ARCHIVE do produto. Não afirma equivalência do ZIP derivado com o ZIP oficial completo.
- Nove testes em tests/infrastructure/test_magic_formula_ci_reference_bundle.py cobrem digests, schema, determinismo, leitura de datas pelo consumidor existente, recusa de overwrite/destino externo, arquivo ausente/corrompido e recusa dos três inputs não aprovados. Fixtures de testes negativos são apenas alterações temporárias de metadados, nunca novos snapshots históricos.

Integração efetiva: o workflow existente executa ci/run.py python, que coleta tests/. Logo esses nove testes e a fixture versionável entram na CI sem mudança de workflow. Nenhum secret, URL de download, banco de origem ou diretório pessoal foi adicionado ao workflow. Não há provisionamento dos quatro inputs históricos incompletos; os 22 testes continuam falhando explicitamente. Testes novos aprovados não contam como recuperação daqueles casos.

## Política de falha e de artefatos

Manifesto novo de proveniência é allowlist de referências aprovadas, não allowlist de falhas. Um item VERIFIED com ci_approved=false permanece recusado (caso do V12.2 autenticado com permissão pendente). Não há exceção de Ruff/mypy, skip/xfail nem transformação de erro em sucesso.

O runner mantém reports por SHA com status/contagens e remove payloads de logs/JUnit. Não incluir gzip/JSONs brutos/SQLite nos artifacts atuais; somente os campos sanitizados já permitidos. Os arquivos de fixture aprovados pertencem ao checkout versionável, não a download mutável por PR. Logs brutos locais permanecem em TEMP.

## Desenho concreto pendente do pack histórico

Este desenho não está ativado e não aprova nenhuma referência bloqueada.

1. **Pack imutável:** CSVs e JSON V12.2 originais autenticados; export JSON dos documentos universo necessários com SHA de bytes e document_digest, source IDs e rowids/timestamps originais. Separar digest lógico de digest do container. Preservar toda a lista results e provenance; nenhum recalculador participa do provisionamento.
2. **Raiz por execução:** pytest factory cria diretório aleatório abaixo do TEMP. Não aceitar symlink/junction para data/ pessoal/produtivo; nenhum path absoluto de usuário no manifesto distribuído. CSVs/JSONs em staging somente leitura; DB exclusivo nesse diretório.
3. **Schema SQLite:** criar tabela/triggers a partir do contrato conhecido do repositório em DB novo, sem migrations produtivas. Inserir documentos exportados em transação com rowid explícito e colunas originais; recomputar/verificar digest antes e após a inserção, sem reconstruir informações financeiras. Validar integridade, quantidade de snapshots, cobertura e IDs. Negar duplicate-ID divergente; segunda provisionamento em destino existente falha, não sobrescreve.
4. **Ordenação:** preservar todos os registros necessários à linhagem e os dois registros empatados autênticos. SELECT created_at DESC,rowid DESC deve reproduzir o resultado original. Um par sintético serve só a teste unitário separado, nunca ao contrato histórico.
5. **Injeção de caminhos nos testes:** fixtures dedicadas às famílias afetadas direcionam referências e CWD de staging apenas para esses testes. Atenção: build_canonical_snapshot captura caminhos nos defaults da função; trocar somente UNIVERSE_DB depois da importação não redireciona o default. Preferir passar parâmetros existentes por fixture/wrapper de teste revisado; jamais modificar cálculo para acomodar staging. API deve continuar lendo JSON persistido no seu SQLite temporário, sem chamar build.
6. **Falha explícita:** qualquer licença/dependência/digest pendente impede provisionamento. Não baixar ou recalcular arquivos novos, não substituir por golden mais recente. Manter execução dos testes históricos e seu erro visível até recuperação aprovada.
7. **Controles:** verificar triggers UPDATE/DELETE, leitura por ID/digest, idempotência append-only do ranking e evento de publicação; testes de negócio mantêm expectativas intactas. O provisionador não aprova release nem muda tool_status/ranking_status do universo.

## Estratégia por tipo de fonte

| Tipo | Estratégia | Situação |
| --- | --- | --- |
| Índice DFP2025 | Fixture mínima versionável, atribuição ODbL, digest fixo, ZIP derivado temporário só para datas | Implementado |
| ZIPs CVM anuais completos | Arquivo content-addressed recuperado de origem controlada ou acervo, validado por digest anterior; uso só se replay exigir, com minimização/atribuição | Conteúdo autenticado; não incluído inteiro |
| JSON V12.2 / universo ed8a | Bytes históricos exatos, distribuição sujeita à permissão do material incorporado | Autenticados; não aprovados CI |
| CSV V8/V9.2 / predecessores DB | Recuperar âncora histórica independente; não inferir identidade por contagens/IDs | Bloqueiam pack completo |
| COTAHIST e identidades B3 | Permissão/licença aplicável antes de distribuir; eventual acervo privado controlado também depende dessa permissão | Bloqueado; privado não contorna licença |
| Evidências de ações/identidade | Pack por documento com origem, data, hash e decisão; não incorporar dados de pessoas por conveniência | Inventário por documento pendente |
| Dados sintéticos | Permitidos em contratos unitários claramente distintos, sem IDs históricos autênticos | Não substituem golden histórico |

Processos futuros de atualização de mercado ficam separados da CI de PR: aquisição com autorização, origem allowlist, cache content-addressed e conferência do digest esperado. Não usar latest/URL mutável como verdade financeira. Ambiente de PR não recebe credencial produtiva nem acesso a buckets/DB de carteira.

## Critérios ainda não atendidos

Os 22 casos não podem exercer suas asserções históricas em checkout limpo com o conjunto atual aprovado. O pack DB/CSVs e permissão B3 continuam bloqueadores; isto é entrega parcial comprovada, não CI histórica estabilizada. Não reduzir falhas apenas porque os novos testes de referência passaram. CERT_48 e o manifest de identidade permanecem intocados.
