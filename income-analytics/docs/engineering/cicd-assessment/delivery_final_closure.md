# PR7 — Entrega controlada, homologação técnica e recuperação

Implementação em validação. O encerramento depende da evidência hospedada,
integração protegida e repetição da entrega após o merge. Não há autorização
produtiva, mesmo quando a homologação técnica passa.

## Preflight comprovado

PR6 [#51](https://github.com/tiagocaldironi/income-analytics/pull/51) integrado;
baseline atual consultada remotamente:
`develop@cc71b0be65d6fe34b97cd3305dfc7956c9a4a065`.
Run de push [40856571402](https://github.com/tiagocaldironi/income-analytics/actions/runs/40856571402),
attempt 1, workflow `399392307`, `.github/workflows/ci-offline.yml`, evento push
em develop. Engineering/build success; conclusão global failure pelos diagnósticos
financeiros/de qualidade explícitos, não dispensados.

Artefato inicial A `12890060783`, package SHA-256
`5fe747f55179b82e166761cd7c8adca0a643123bc809086c716e19ee0ddd38b2`.
Digest do transporte GitHub
`sha256:bc67e06ee29949c642a259c6fce074c2d32af91e0e1452900e0dc47d8f7fd7ee`;
manifest SHA-256 `008b349f9a2f17332292fdf0cad2fd690a5d00ef21a37e8f7e0124ce367cee04`.
Esses valores pertencem ao commit integrado, não ao merge sintético do PR6.
Proveniência/digests foram novamente consultados e conferidos pela API.

Ruleset `26078982` ativo, sem bypass: PR obrigatório, Engineering do app 15368,
branch atualizada, conversas resolvidas, proteção contra exclusão/force push.
Default branch confirmada: develop. Worktree e branch PR7 isolados; originais
preservados. Nenhum relatório histórico PR5/PR6 é reescrito.

## Arquitetura executável

```text
CI governance (push develop)
  -> Engineering + Reproducible build
  -> workflow_run completed (mesmo quando diagnóstico opcional falha)
  -> delivery-validation.yml, controlador de revisão confiável
  -> origem + jobs + relatórios + digests + ancestry verificados
  -> CANDIDATE_CREATED
  -> copiar ZIP por SHA, sem recompilar
  -> Windows descartável: instalar A e B em venvs separados, loopback
  -> smoke + backup online + restore + rollback + bloqueio de schema + limpeza
  -> STAGING_VALIDATED -> PROMOTION_ELIGIBLE (somente engenharia técnica)
  -> PRODUCTION_NOT_AUTHORIZED; release financeiro BLOCKED
```

Arquivos: `ci/delivery.py` (decisões/capacidade de acesso/SQLite),
`ci/delivery_stage.py` (instalação e processos), `ci/delivery_pipeline.py`
(aquisição e orquestração), `ci/test_delivery.py` (regressões e rejeições).
Reutilizam o verificador, GUARD e wheelhouse do PR6, sem mudar seu pacote,
dependências, cálculos, fixtures ou migrations.

O workflow separado `.github/workflows/delivery-validation.yml` tem somente
`contents: read` e `actions: read`, Windows 2025 hospedado, Python 3.14.7,
Actions fixadas por SHA e checkout sem credenciais persistidas. Não há runner
produtivo, secrets produtivos, deploy remoto, GitHub Release, Tailscale, alteração
de configurações GitHub ou implementação de execução produtiva.

## Confiança e promoção imutável

Antes de extrair/executar código, consultar API GitHub pelo repositório fixo:

1. Repository/head_repository próprios, workflow ID/path permitidos.
2. Build automático push/develop concluído; commit esperado ancestral de develop.
3. Engineering e build com conclusão success no attempt declarado.
4. Relatórios do mesmo run, checkout/event SHA, identidade limpa, gate Engineering
   consistente e build duplo/manifest aprovados. Release/financeiro continuam BLOCKED.
5. Artifact ID do run, nome com SHA esperado, não expirado, criado no attempt atual.
6. Digest SHA-256 do envelope GitHub antes de extrair, allowlist de nomes/limites.
7. Digest do ZIP interno, `.sha256`, manifest interno/externo, políticas e fingerprint.

Não há fallback para build local, origem desconhecida, PR não integrado ou outro
commit. API só usa GET em host fixo e remove Authorization nos redirects de blobs;
erros são códigos sanitizados, sem token, corpo privado ou URL assinada em logs.

`candidate.json` registra repository, source commit, build run/attempt, artifact
ID/digest, package SHA, manifest SHA, política de build/governança, fingerprint,
target, status e referências de evidência. O digest do envelope, do pacote e do
manifest são identidades diferentes. Timestamp/identidade do workflow ficam no
relatório de execução, fora do ZIP imutável.

O pacote é copiado por bytes para homologação e para retenção; igualdade de SHA é
obrigatória. Um slot/identificador lógico existente não pode ser sobrescrito.
Antes de cada start, conferir pointer, digest do pacote e hashes de todos os arquivos
extraídos. O processo também exige importar a aplicação de seu próprio `src/`.
Assim, health de outra versão ou simples rename de diretório não comprova rollback.

## Validação pré-merge segura

O workflow novo só passa a receber workflow_run quando instalado na default branch.
Antes disso, o CI chama o mesmo `delivery_pipeline.py` em um job
`CD / Staging validation`, após Engineering/build, com permissões somente leitura.

Nesse modo `premerge`, apenas o run PR corrente pode ser usado no ensaio.
O artefato é verificado e exercitado, mas o estado é **PROMOTION_BLOCKED** com
`PR_UNMERGED_PREMERGE_TEST_ONLY`. Não se produz pacote elegível retido. A tentativa
de tratar o mesmo PR como candidato de delivery é rejeitada. Esse ensaio prova a
mecânica sem afirmar publicação produtiva ou promoção de código não integrado.

Após merge, workflow_run usa exclusivamente o run push/develop e repete toda a
validação; não reaproveita a declaração de aprovação do preview.

## Homologação e isolamento

Raiz nova `TemporaryDirectory`, instalada somente sob capacidade `Workspace`.
Todos os caminhos SQLite/instalação são confinados a essa raiz; caminhos externos,
symlinks/junctions, inclusive diretórios produtivos conhecidos, são rejeitados.
Não há argumento CLI para selecionar banco real ou caminho produtivo.

Instalar wheels offline (`--no-index --require-hashes --only-binary`), venvs A/B
separados, verificar `pip check`, aplicar migrations somente no SQLite novo,
importar backend e executar Uvicorn em `127.0.0.1`/porta dinâmica. Verificar
`/health`, `/` e CSS, schema e conteúdo instalado.

Ambiente do subprocesso é reconstruído por allowlist: HOME/cache/SQLite temporários,
local/development/testing, signup/jobs externos desligados, ADC inexistente.
Overrides de credenciais/configuração produtiva são rejeitados. Token GitHub não
entra no ambiente da aplicação. Guarda de sockets Python nega conexões/DNS/UDP
externos; não é um firewall de SO para código nativo e não certifica cloud/CDNs.

Servidor recebe sinal de parada por arquivo de controle próprio. Uvicorn encerra
graciosamente e SQLAlchemy libera conexões; timeout/necessidade de parada forçada
é falha observável. Cleanup emergencial trata somente processos criados pelo
workspace, confirma porta liberada e remove a raiz. Falha de limpeza bloqueia o gate.

## Backup e restore

1. Migrations e dados sintéticos novos, sem dados pessoais/carteira real.
2. Writer WAL aberto e dados committed; backup por `sqlite3.Connection.backup`.
3. Conferir SHA do arquivo, PRAGMA integrity_check, head Alembic e assinatura
   semântica de schemas/linhas; não usar cópia ingênua de banco aberto.
4. Alterar estado de origem, observar que a assinatura deixa de coincidir.
5. Com app parado, verificar novamente backup/digest/schema/estado antes de restaurar.
6. Restaurar via API SQLite e exigir a assinatura anterior exata e integridade/head.

Backup ausente/corrompido/inacessível, digest errado, estado incompleto, schema
errado ou app ainda aberto provocam falha. Apenas hashes/resultados são publicados;
bancos e backups ficam na raiz descartável e são removidos.

Essa é a mecânica em homologação técnica, não ensaio de restauração do SQLite real.

## Rollback e schema

A é o artefato técnico conhecido do PR6, conferido e iniciado antes do ensaio.
B é o novo artefato, com outro commit/digest; versões distintas não significam que
este PR altera comportamento financeiro. Não há rebuild nem modificação dos ZIPs.

Instalar A, registrar digest/estado, backup/restore, instalar B, selecionar B,
iniciar e verificar saúde/static. Exercitar HTTP 404 em rota de health injetada e
startup com alvo ASGI inexistente; ambos falham realmente, sem editar o pacote B.
Encerrar B, conferir compatibilidade, selecionar A, conferir bytes/arquivos,
reiniciar A e exigir saúde, static, pointer, schema e estado anteriores.

Compatibilidade automática é conservadora: **mesma identidade de todas as migrations
e mesmo head no banco**. Diferença, mesmo aparentemente aditiva, bloqueia rollback
automático e exige plano separado. Não há downgrade. Um segundo cenário altera
somente o head no banco sintético: comprova o bloqueio e executa separadamente a
restauração já validada desse banco de teste. BLOCKED não é convertido em PASS;
o gate reconhece explicitamente que o bloqueio seguro foi comprovado.

## Gates e auditoria

| Nível | Decisão |
|---|---|
| A — CI / Engineering | Testes, build, identidade e ausência de regressão; obrigatório na develop. |
| B — CD / Staging validation | Origem/digests, instalação, saúde, backup, restore, rollback, bloqueio seguro de schema, negativos e cleanup completos. NOT_RUN/falta de evidência falham. |
| C — Release financeiro/produtivo | BLOCKED / PRODUCTION_NOT_AUTHORIZED, independentemente de A/B. |

Estados distinguem CANDIDATE_CREATED, STAGING_VALIDATED, STAGING_FAILED,
PROMOTION_ELIGIBLE, PROMOTION_BLOCKED e PRODUCTION_NOT_AUTHORIZED. Elegibilidade é
somente engenharia de homologação. Nenhum check Release PASS é criado.

Relatórios JSON mantêm PASS, FAIL, NOT_RUN, BLOCKED e EXPECTED_FAILURE_OBSERVED;
não confundem falha injetada observada com saúde real aprovada. Planos não executados
permanecem NOT_RUN, schema incompatível BLOCKED, downgrade/rebuild NOT_RUN.

Relatórios de entrega e cópia imutável tecnicamente validada: 90 dias no Actions.
Preview: somente relatórios, 14 dias. Artefatos fonte do PR6/CI têm retenção 14 dias;
origem expirada/ausente bloqueia nova aquisição, sem rebuild silencioso. A cópia
retida de delivery não é aceita automaticamente como novo build de origem.

## Operação e recuperação

Automaticamente: concluir CI em push/develop dispara a entrega, que valida os gates
individualmente apesar da conclusão global failure pelos débitos já conhecidos.

Repetir manualmente `delivery-validation.yml` com `build_run_id` e `source_commit`
exatos de push/develop; opcionalmente selecionar `previous_build_run_id` e
`previous_source_commit` de outra versão conhecida e confiável, sujeita às mesmas
verificações. Sem esses inputs A permanece fixada no PR6 para ensaio reproduzível.

É necessário manter os artefatos fonte disponíveis ou atualizar a referência A
para um novo build validado antes da expiração. Retenção/espelhamento durável e
recuperação a partir de mídia arquivada exigem política futura; nenhuma cópia sem
proveniência ou artefato local é aceita para contornar expiração.

Se falhar: consultar validation.json e seus códigos, preservar a evidência,
verificar run/attempt/commit/IDs/digests, corrigir a causa e repetir a entrega sobre
o mesmo artefato. Sem schema compatível, não forçar troca nem downgrade; construir
plano específico de restauração e testá-lo separadamente. Nenhum desses comandos
deve ser direcionado à produção.

## Resultados e limitações

Preflight PR6 remoto e aquisição real aprovados. Ensaio local de componentes entre
dois ZIPs já existentes: instalação, saúde, backup online/WAL, restore, falhas
injetadas, rollback com reinício A, bloqueio de schema e limpeza aprovados.
O primeiro ensaio identificou I/O em SQLite após encerramento abrupto; a camada
passou a encerrar Uvicorn/conexões graciosamente, e o ensaio foi repetido com sucesso.
Essa medição local não representa promoção de PR não integrado.

Evidências hospedadas, PR integrado e run pós-merge: pendentes nesta revisão.
O relatório final incluirá os runs, commits, artifact IDs e digests reais; nenhuma
conclusão será inferida apenas do desenho ou dos testes locais.

Pendências fora do escopo: CERT_48, identidade financeira e referências históricas;
Firebase/cloud, validação funcional completa, certificação de backup/rollback
produtivo, inventário completo de segurança e autorização explícita de produção.
Nenhum dado produtivo, launcher HTTPS, Tailscale Serve ou processo produtivo é
acessado/modificado. Não há deploy nem release para usuários finais.
