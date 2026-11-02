# CERT_48 — análise de proveniência

Estado: **BLOCKED**. Baseline `c76132b4398434fb8a196f895b78b7f46ed3845e`. O manifest original permanece intacto.

| Arquivo | Esperado | Bytes exatos Git / observado | Resultado |
| --- | --- | --- | --- |
| src/income_analytics/application/magic_formula_stocks.py | `27b58d132b461afe867ca2af05757b1309739c40156549ac0bf1785ae5ad27a4` | `44fe1057b14dc45d13e0d302d7b24e361921ee2dab87b1dfde674c30dc344a9d` | MISMATCH |
| src/income_analytics/application/magic_formula_ranking_validation.py | `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37` | `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37` | MATCH |
| src/income_analytics/application/magic_formula_contract.py | `9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f` | `9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f` | MATCH |
| tests/fixtures/cvm/price_identity_v1/cotahist-record.txt | `67fdbb7e6f3e56f235635240b3c4057876afb20b055b11562bdf532c457a45d9` | `3890cfc22c50bb9ff0cdb35af7f754fa3bf5f47ee4022a3769ff1f88913b9293` | MISMATCH |
| tests/fixtures/cvm/price_identity_v1/current-directory.json | `d0c14ea112fc242b17b87e590a0f93fa272d9e8f88d4605bc8a0f2ab4b1eafad` | `931cc5afc0683d998e69e6300f271ab92982f85cf309d50cceafb37f2cf12fe7` | MISMATCH |
| tests/fixtures/cvm/price_identity_v1/issuer-before.json | `a4b0734c50046306f46448bd3f496fad2c20e98923cd38307b5fd3f7a5c1edfc` | `14eb2403e55a2d2017caaf7cdde16238dd455a48f94d9ec26d250b94a6c36b8a` | MISMATCH |
| tests/fixtures/cvm/price_identity_v1/offer-identity.json | `10924734efc14d6d247f8e57d6683bb3b158dd451ebad3ca3f72b3dfb8411057` | `6446ab9e39d8fefbb065d194f3809a944890261505fa6d406ab7aa8fa0e2b56c` | MISMATCH |
| tests/fixtures/cvm/price_identity_v1/offer-notice.pdf | `eb07e089b89841c770aab32c91fe3e772210a5477e2c52f876f01bd5a511f64e` | `eb07e089b89841c770aab32c91fe3e772210a5477e2c52f876f01bd5a511f64e` | MATCH |

O motor `magic_formula_stocks.py` corresponde ao esperado apenas após conversão LF→CRLF; `ranking_validation` e `contract` correspondem aos blobs LF. Os quatro textos de identidade também exigem CRLF para coincidir. Nenhuma política única de checkout resolve o conjunto. As variantes foram comparadas em memória; não foram usadas para substituir bytes certificados ou redefinir expectativas.

O worktree novo inicialmente sofreu conversão de transporte do Git Windows. Sua medição foi 74P/14F/9E/0S. Depois, os **bytes exatos de cada blob Git** foram escritos somente no checkout descartável, e a baseline hospedada foi reproduzida: 73P/15F/9E/0S. Index refresh com core.autocrlf=false gerou zero diff contra HEAD. Originais/outros worktrees não foram normalizados. Configuração observada: `file:C:/Program Files/Git/etc/gitconfig	core.autocrlf true`. Atributos específicos: `tests/fixtures/cvm/price_identity_v1/offer-notice.pdf: diff: astextplain`.

Histórico: os arquivos/manifests entraram no commit `4d5781ce1d09b8317207f653e0bde8e5a4580cc9`; versões acessíveis por arquivo e hashes estão na matriz. Buscaram-se refs remotas atualizadas, tags e objetos alcançáveis; nenhum blob original CRLF aprovado nem autoridade canônica independente foi recuperado. Não foram examinados objetos apagados/inacessíveis ou backups pessoais.

O gate histórico `docs/appendices/multiportfolio_v2_certification_closure/release_gate.json` é INCOMPLETE e lista CERT_48. Seus subcampos PASS têm escopo V2 e não resolvem a ressalva final. `magic_formula_reconciliation.json` declara falha de bytes preexistente apesar de ranking agregado coincidente; isso comprova conflito documental, não aprovação original. Não foi localizada assinatura/ata independente capaz de autenticar o pacote misto.

Artefatos GitHub: 229 inventariados, releases 0, nenhum pacote original histórico identificado. Pacotes PR6–PR8 representam checkouts Git de engenharia, não a versão aprovada perdida. Metadados locais têm hashes próprios, não substituem a aprovação independente.

Decisão: **não há prova suficiente para corrigir representação como transporte certificado**. Mantêm-se manifest, testes e CERT_48 bloqueados. Material exato necessário: pacote original dos três arquivos congelados com cadeia de custódia/ato de aprovação, ou autoridade canônica independente capaz de ligar cada hash existente aos bytes aprovados; em paralelo, originais dos quatro textos de identidade e sua cadeia B3/temporal.
