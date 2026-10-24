# Auditoria de arquitetura SaaS multiusuário — Fase 1

**Data:** 23/10/2026. **Resultado:** base multiportfólio existente e reaproveitável; **não pronta para usuários independentes nem para publicação na internet**. A segurança atual depende de acesso confiável à instalação local/rede privada. O plano comercial Free/Pro ainda não existe no backend.

## 1. Escopo, revisão e método

Repositório remoto configurado: `tiagocaldironi/income-analytics`. Base Git: `27fcd4d70dad7026a6f3089c0810c78e4b2ac4ac`, branch de trabalho `codex/income-starter-guided-strategies`, com mudanças anteriores não commitadas. A auditoria examina **o workspace real**, incluindo apresentação de estratégias, temas e salvamento assíncrono. Esses componentes não devem ser presumidos como já incluídos em uma branch-base limpa de um futuro PR SaaS.

Foram lidos middleware, routers, modelos, repositórios, sessão de aplicação, migrações, integrações, frontend, caches, jobs, testes e documentos de certificação. O inventário de produção foi coletado via `sqlite3` em modo somente leitura, sem importar a aplicação nem disparar Alembic. Os probes de escrita/exclusão usaram exclusivamente o banco temporário configurado em `tests/conftest.py`. Não foram lidos/exibidos valores de segredos, publicados dados privados, alterados dados legados, trocados hashes ou implementado login.

Entregas complementares:

- [Inventário das 35 tabelas e relacionamentos](SAAS_MULTIUSER_DATA_INVENTORY.md).
- [Inventário das 96 rotas explícitas](SAAS_MULTIUSER_ENDPOINT_INVENTORY.md).
- [Plano técnico, decisões e matriz de testes](SAAS_MULTIUSER_IMPLEMENTATION_PLAN.md).
- Coletor reproduzível: [scripts/audit_saas_architecture.py](../scripts/audit_saas_architecture.py), que não importa módulos com inicialização de banco.

A inspeção estática é abrangente para as rotas declaradas e o esquema atual; os probes dinâmicos são amostras dirigidas. Não representam pentest completo nem certificação de segurança. Tabelas criadas por SQL fora de `models.py` foram incluídas pelo inventário SQLite.

## 2. O que já existe

| Capacidade | Estado real e evidência | Reaproveitamento |
|---|---|---|
| Múltiplas carteiras | `Portfolio`, `portfolios`, `portfolio_assets`, ciclo de criar/renomear/arquivar/restaurar em `api/routers/portfolios.py` | Preservar UUIDs, moeda, datas e contratos; adicionar proprietário |
| Escopo de carteira | `main.py:portfolio_request_context` resolve `X-Portfolio-Id`; `portfolio_context.py` usa ContextVar; repositórios recebem carteira | Inserir autenticação/ownership antes de construir `PortfolioSession`; header continua apenas seletor |
| Integridade entre registros | Migração `0019_portfolio_domain_foundation` e modelos possuem FKs compostas para evento/ativo/importação | Manter invariantes; não substituir filtros SQL por filtragem no navegador |
| Sessão financeira | `PortfolioSession` é estado da aplicação para uma carteira, não sessão de login | Não renomear seu papel nem usar `account_id` como identidade humana |
| Dashboard e performance | Snapshot persistido por carteira, comparação cacheada com carteira/revisão, TWR e histórico existentes | Manter cálculos e respostas douradas; proteger entrada e publicação |
| Salvamento assíncrono | `application/dashboard_refresh.py`, receipt e status no router; worker carrega uma sessão nova por carteira | Adicionar contexto de titular/serviço e coordenação distribuída antes de vários workers |
| Starter e Primeiros Passos | Versões, DRAFT/PUBLISHED, evidências financeira/regulatória, adoção e progresso separados | Preservar governança; vincular papéis a atores autenticados sem transformar plano em permissão editorial |
| Importações | B3 preview/apply/history e IRPF; fingerprint e FKs por carteira | Conservar auditoria e deduplicação; autorização indireta e limites de carga adicionais |
| Migrações | Alembic real até `0023_income_starter_guided_journey`; migração 0019 já introduziu carteira padrão | Fazer expansão incremental; não recriar o esquema nem repetir backfill MAIN como vínculo de usuário |
| Mercado e Magic Formula | Preços, índices, câmbio, documentos públicos e snapshots/QA separados do ledger | Compartilhar somente referências devidamente classificadas e licenciadas |

### 2.1 Identidade e autenticação: ausentes

Não foram encontradas tabelas de usuários, identidades externas, sessões de login, recuperação, roles, memberships ou assinaturas; não há dependências `Depends`/`Security` de autenticação nas 96 declarações de rotas. Não existem validação de bearer token, cookie de sessão autenticada, expiração/revogação ou usuário administrador autenticado no caminho HTTP.

`MAIN_PORTFOLIO_ID` é um UUID determinístico para compatibilidade legada, não um usuário. O middleware verifica existência e estado ACTIVE da carteira; quem pode informar outro UUID válido pode selecioná-la. Na ausência do header, há fallback para MAIN. As rotas `/api/portfolios*` ainda passam por uma exceção explícita do middleware e usam repositório sem filtro por titular.

`localStorage["income.activePortfolioId"]` escolhe a carteira; os temas também ficam em armazenamento local. Nenhum desses valores prova identidade. O token de contexto Python chamado `portfolio_token` é um token de ContextVar, não um token de autenticação. Um header Authorization arbitrário é ignorado pela instalação atual; isso foi reproduzido em teste.

### 2.2 Dados atuais e preservação

O banco consultado contém **duas carteiras**, **1.416 eventos financeiros**, **88 ativos**, **88 vínculos de ativos**, oito lotes B3 e 2.286 linhas auditadas. Há 54 objetivos por ativo e oito objetivos de classe. O progresso da jornada tem um registro. Esses totais são fotografia da coleta, não valores a fixar como regra de produto.

Revisão Alembic `0023_income_starter_guided_journey`; `PRAGMA integrity_check = ok`; zero violações de FK. Há somente um snapshot para duas carteiras: o snapshot é derivado e sua ausência não autoriza recriar o ledger. Não inferir que as duas carteiras pertençam à mesma pessoa nem identificar o proprietário pelo nome da carteira.

Posições e históricos são projeções, não uma nova tabela a migrar para usuários. A simulação de aporte não é persistida. Ainda não há entidade genérica de metas, relatórios/exports de conta ou conexões bancárias.

## 3. Achados priorizados

A severidade considera o uso como SaaS proposto. Ela não afirma que a instalação já esteja pública: hoje o acesso observado é local/LAN/Tailscale. Uma rede privada limita quem alcança o servidor, mas não cria isolamento entre as pessoas que o alcançam.

| ID | Prioridade | Evidência e impacto | Tratamento específico |
|---|---|---|---|
| S01 | **P0** | `main.py:portfolio_request_context`, `portfolios.py:list_portfolios`, `SqlitePortfolioRepository.list/get`: sem usuário/owner. Cliente lista todas as carteiras e lê outra ao trocar o header | Principal autenticado + consulta por `(portfolio_id, owner_user_id)`; lista só do titular; negar MAIN implícita em SaaS |
| S02 | **P0** | POST/DELETE de operação, política e simulação funcionam com o UUID de outra carteira; o reset também não autentica o solicitante | Dependência de propriedade antes de qualquer escrita; autorização indireta por evento/ativo/lote/regra; manter FKs |
| S03 | **P0** | `PortfolioSession._reclassify_market_traded_asset` persiste em `assets`, cadastro global por ticker; probe alterou a classificação visível de A a partir de B | Curadoria canônica privilegiada ou override explicitamente privado; usuário comum não pode mudar a referência financeira dos demais |
| S04 | **P0** | `PUT /market-prices/{ticker}`, benchmark/FX write e ingestões têm efeitos em referências globais, sem fronteira de privilégio | Separar cotação particular da cotação oficial; ingestão por serviço autorizado, com proveniência, quotas e revisão |
| S05 | **P0** | `paid_income_provider_settings` é singleton `id=1`, token `Text`; `/settings/paid-income` permite troca/remoção global sem autenticação | Resolver modelo plataforma/BYO, secret manager e ACL por titular quando aplicável; nunca migrar o mesmo token para todas as contas |
| S06 | **P1** | Não há login, e-mail verificado, recuperação, expiração, revogação ou proteção de admin | Escolher IdP após ADR; autenticação verificada e sessão segura no backend |
| S07 | **P1** | `assets` mistura títulos públicos e identificadores particulares; ticker global único; `market_prices` também contém valores particulares/manuais | Inventariar namespace, origem e visibilidade; preservar IDs/eventos; não presumir que todas as linhas de preços sejam públicas |
| S08 | **P1** | `portfolio.js:renderHoldingRow` interpola `title`, `title.slice` e `subtitle` em HTML sem escape de texto; atributos próximos são escapados, mas o corpo não | Substituir sinks por DOM/textContent ou escape contextual; prova com marcação inerte, sem execução de script; revisar também tooltips/importações e aplicar CSP |
| S09 | **P1** | `_b3_preview_cache[(portfolio_id,batch_id)]` é melhor que cache global sem chave, mas falta autorização do titular, TTL e quota; aliases `/imports/b3/*` coexistem com `/api/imports/b3/*` | Proteger os dois caminhos; chave de job/artefato validada no servidor; objeto privado com expiração e limite de tamanho/descompressão |
| S10 | **P1** | Jobs percorrem todas as carteiras; paid-income usa configuração global. Fila de dashboard é em memória/daemon por processo | Principal de serviço, contexto owner/carteira explícito e revalidação; locks duráveis, retry/idempotência; não usar contexto do request anterior |
| S11 | **P1** | Não há entitlements, quotas de APIs ou controle de consumo por pessoa; endpoints acionam fontes externas | Free padrão com recursos manuais completos; capacidades futuras fechadas; quotas técnicas por custo, não limite artificial de carteira/ativos |
| S12 | **P1** | `initialize_database` faz upgrade no startup e usa `stamp(head)` quando encontra `assets` sem Alembic; backup usa cópia de arquivo | Migrador de deploy separado, backup consistente/restauração testada e reconhecimento explícito de baseline legado; não rodar stamp/upgrade cego no SaaS |
| S13 | **P1** | Gate histórico V2 e teste `test_shares_unit_020_frozen_engine` não estão verdes | Registrar causa de bytes/line endings, fechar o processo de certificação separadamente sem alterar manifesto para “passar” |
| S14 | **P1** | Não há audit trail de ações administrativas, política de retenção/exclusão ou fronteira de exports; logs de integrações podem conter detalhes livres | Ator, ação, recurso, resultado e motivo sem payload financeiro/token; proteger arquivos e definir retenção/incidentes antes do lançamento |
| S15 | **P2** | Tema/seleção e caches no navegador não são namespaced por usuário; `_cached_performance_comparison` e filas têm carteira/revisão mas não ciclo de conta | Limpar no logout/troca de usuário; invalidar ownership transfer; não colocar bearer/refresh tokens em localStorage |
| S16 | **P2** | `SqlitePortfolioDataRepository.clear` não inclui `portfolio_strategy_metadata` nem `income_starter_journey_progress` | Revisar exclusão completa e retenção: “reset da carteira” não é uma implementação pronta de exclusão de conta LGPD |
| S17 | **P2** | Cache canônico, dados MF e health são globais; backend local depende de SQLite e threads | Governança/licenças, métricas sem PII e limites de concorrência; validar Postgres/worker no estágio de escala |
| S18 | **P3** | Consentimentos bancários, conexões, reconciliação e billing ainda não existem | Preparar contratos e estados; não criar conexão fictícia nem vender Pro nesta fase |

### 3.1 Validações dinâmicas executadas

Arquivo [tests/audit/test_saas_readiness_characterization.py](../tests/audit/test_saas_readiness_characterization.py): quatro probes em banco descartável, usando quatro carteiras e dois clientes HTTP **anônimos**. Como não existe User, não se pode afirmar que eram dois usuários autenticados.

- Lista sem login inclui as carteiras dos dois clientes; header de carteira permite leitura de patrimônio alheio; Authorization inválido não impede acesso.
- Usando o header de B, A consegue gravar fluxo, mudar política, consultar análise/simulação e excluir evento. Usando somente a carteira A, a exclusão por ID de evento B retorna 404: há escopo de carteira, mas falta ownership humano.
- Despesas essenciais e reserva da jornada de B são lidas por A com o mesmo bypass.
- Reclassificação de ativo listado de B muda a classe retornada em A: efeito global confirmado além da falta de login.

[tests/frontend/saas_xss_characterization.mjs](../tests/frontend/saas_xss_characterization.mjs) demonstra que uma marcação inerte no nome de renda fixa vira HTML no corpo da linha. Não foi executado exploit nem carregado payload no banco real.

**Testes de caracterização passando significam vulnerabilidades reproduzidas, não segurança aprovada.** Devem ser substituídos/invertidos para expectativas de negação/escape nos PRs de proteção. Os testes atuais de escopo/multiportfólio continuam úteis, mas não certificam acesso entre usuários.

## 4. APIs, serviços, caches e arquivos

O [anexo de rotas](SAAS_MULTIUSER_ENDPOINT_INVENTORY.md) cobre Minha Carteira, Entender, Estratégia, Simular, Operações, Starter, Magic Formula, configurações, importações e ausência atual de exports dedicados. Não há campo `user_id` autenticado a ser manipulado hoje: falta a entidade. No desenho futuro, body/header/query não poderão definir o titular nem o plano efetivo.

- `SqliteFinancialEventRepository`, regras, alvos, detalhes privados e B3 recebem `portfolio_id`; reaproveitar e exigir contexto autorizado em sua construção.
- `_cached_performance_comparison` inclui carteira e revisão na chave. O cache não mistura carteiras pelo simples parâmetro de período; o risco remanescente é acesso a uma chave de carteira não autorizada e invalidação em mudança de titular.
- A fila de dashboard recém-adicionada mantém workers por carteira e protege a publicação contra reconstrução ultrapassada no mesmo processo. Não possui distribuição/coordenação multiprocesso nem principal de serviço. Não generalizar essa garantia a um cluster.
- B3 usa base64 em memória e cache de preview com chave composta. O arquivo não é publicado por um diretório de downloads. São necessários limites de corpo, quantidade de linhas, taxa de chamadas, memória, ZIP e retenção. `raw_payload`, instituição e nome de arquivo são privados.
- COTAHIST usa `data/cotahist` e arquivos de fonte pública. Pode ser cache global com atualização atômica, checksums e licença. Não reutilizar esse diretório para uploads privados.
- `/static` monta somente a pasta de frontend, não a raiz do banco/dados. Não há prova de exposição direta de `.db` por esse mount. A proteção de backup e volumes continua necessária no deployment.
- Escritas/reclassificações globais e refresh devem ser distribuídas por papel de curadoria/serviço; uma ação manual do Free pode solicitar atualização limitada sem receber poder de editar referência canônica.

## 5. Segredos, administração e governança

Foram identificados os nomes `BRAPI_TOKEN` e `TWELVE_DATA_API_KEY` lidos no backend. Nenhum valor de variável ou arquivo `.env` foi coletado. `.gitignore` ignora `.env`, `.db`, `backups`, `data` e temporários; isso não comprova ausência de segredo em toda a história Git, CI ou infraestrutura. Fazer varredura de histórico/redação de logs em ambiente controlado antes do lançamento.

O token BRAPI de paid-income também pode ser persistido em texto no singleton. A coleta encontrou **zero linhas** nessa tabela: é uma vulnerabilidade de modelo/API, sem afirmação de que credenciais reais estejam atualmente armazenadas ali. Há duas arquiteturas legítimas a decidir: chave licenciada da plataforma em secret manager inacessível a usuários, ou BYO key privada por usuário. Credenciais bancárias futuras sempre exigem vínculo de usuário/consentimento; não são equivalentes ao token comercial de dados de mercado.

Não existe “admin” autenticado. Starter possui autor, revisor, aprovador financeiro/regulatório e publisher gravados, além de gates de validação no código (`application/income_starter.py`), mas esses identificadores editoriais não substituem papéis/identidade verificáveis. O catálogo atual inclui DRAFT para educação. Uma futura versão pública só deve oferecer conteúdo aprovado/publicável; a visualização educacional autenticada pode manter DRAFT com as restrições atuais, sem adoção ou percentuais inventados.

Admin operacional não deve herdar leitura de finanças privadas. Suporte deve operar metadados mínimos e ações auditadas; eventual acesso excepcional exige um procedimento separado, com finalidade, escopo e revogação. Aprovação financeira/regulatória não deve virar um wildcard de acesso administrativo.

## 6. Alternativas de identidade e decisão pendente

Comparação consultada em fontes oficiais em 23/10/2026. Custos são dimensões para orçamento, não proposta comercial nem contratação. Não foi escolhido nem instalado um IdP.

| Alternativa | Segurança e integração real com esta stack | Custo/complexidade | Migração e consequências |
|---|---|---|---|
| Supabase Auth | Sessões com access/refresh tokens e recuperação/verificação; backend precisa validar identidade e manter ownership próprio | Plano Free consultado inclui 50 mil MAU; produção anuncia Pro a partir de US$25/mês. Avaliar e-mail, regiões, add-ons e políticas de sessão | Não obriga mover o ledger para Supabase; manter user_id interno e mapear identidade externa. Disponibilidade/limites do projeto e configuração de sessões precisam ser validados |
| Auth0 | Serviço de identidade/OIDC; expiração, HTTPS e política de revogação continuam sendo responsabilidade da integração correta | Custos por MAU/recursos do plano; cotar MFA, domínios e exportações para a escala estimada. Menos operação de identidade própria | Reduz implementação de credenciais; hooks/claims exclusivos geram dependência. Mapeamento issuer/sub evita usar o ID do fornecedor como FK financeira |
| Clerk | Gestão de sessão/JWT e interfaces de conta; verificar compatibilidade com frontend vanilla e FastAPI | Página consultada usa MRU, não MAU; Hobby tem 50 mil MRU por app e limites específicos; custo cresce com usuários recorrentes/add-ons | A arquitetura padrão documenta cookie de sessão acessível ao SDK JS. Não assumir que ela satisfaz automaticamente a proposta BFF HttpOnly; definir fronteira e trade-off antes de adotar |
| Keycloak operado pela equipe | OIDC, gestão de sessão e fluxos de cadastro/verificação/recuperação disponíveis | Operar banco, upgrades, disponibilidade, e-mail, backup e resposta a incidentes; maior esforço operacional | Controle da infraestrutura e configuração; migração de identidades/sessões ainda requer projeto e testes. Evitar operá-lo apenas para eliminar custo aparente de assinatura |

Fontes: [Supabase sessões](https://supabase.com/docs/guides/auth/sessions), [Supabase preços](https://supabase.com/pricing), [Auth0 boas práticas de tokens](https://github.com/auth0/docs/blob/master/articles/best-practices/token-best-practices.md), [Auth0 preços](https://auth0.com/pricing), [Clerk sessões](https://clerk.com/docs/guides/how-clerk-works/overview), [Clerk preços](https://clerk.com/pricing), [Keycloak administração](https://www.keycloak.org/docs/latest/server_admin/index.html).

**Recomendação arquitetural proposta, ainda não aprovada:** identidade gerenciada, com identidade interna independente e backend responsável por autorização. Para o frontend vanilla servido pelo FastAPI, avaliar um BFF de mesma origem com sessão opaca HttpOnly, sem implementar criptografia/senhas próprias. Comparar Supabase Auth e Auth0 na prova de conceito; Clerk e Keycloak continuam alternativas com os trade-offs acima. A recomendação não é uma seleção automática de fornecedor.

Decidir: residência/processamento de dados, orçamento por uso, e-mail transacional, MFA de staff, revogação efetiva, portabilidade e condições contratuais. Não é necessário comprar ferramentas para concluir esses documentos.

## 7. Migração e certificação

A estratégia detalhada está no plano. O ponto central é **adicionar ownership sobre a carteira existente**, não recalcular o histórico ou atribuir MAIN ao primeiro login.

A revisão 0019 fez atribuição de dados antigos à carteira local MAIN. Isso não comprova identidade da pessoa e não pode ser repetido como “primeiro usuário”. Duas carteiras atuais e todos os dependentes devem entrar num manifesto administrativo privado, com identidade confirmada, dry-run e auditoria de vínculo. Nenhuma delas foi vinculada nesta fase.

`database.py:initialize_database` hoje migra durante inicialização e `stamp(head)` em certos bancos sem controle Alembic. Para SaaS, separar essa rotina do startup de todos os web workers. O backup existente por cópia de arquivo não deve ser a única evidência de restauração de um SQLite ativo/WAL. Usar backup online consistente ou janela de escrita suspensa e testar restore numa cópia antes do corte.

### 7.1 Gate de hashes reproduzido

A certificação histórica [V2 closure](INCOME_ANALYTICS_MULTIPORTFOLIO_V2_CERTIFICATION_CLOSURE.md) permanece `INCOMPLETE`. O teste `test_shares_unit_020_frozen_engine` foi executado e **falhou**. O manifesto contém três fontes:

| Fonte | Hash bruto atual versus manifesto | Evidência adicional |
|---|---|---|
| `magic_formula_stocks.py` | Coincide | O hash do manifesto coincide com os bytes atuais CRLF, não com a versão LF |
| `magic_formula_ranking_validation.py` | Diverge | Normalizar CRLF→LF faz coincidir com o hash esperado |
| `magic_formula_contract.py` | Diverge | Normalizar CRLF→LF faz coincidir com o hash esperado |

Para as três fontes, o conteúdo normalizado LF é igual ao blob da base Git auditada. Isso explica a divergência observada como representação de bytes/line endings, sem provar uma alteração de algoritmo. **O teste bruto continua falhando**; não foi ignorado, o manifesto não foi editado e nenhuma fonte financeira foi normalizada nesta fase. Uma reconciliação de baseline/certificação deve ter processo e revisão próprios.

Sem migração executada, equivalência financeira antes/depois de ownership está **NOT_RUN**. Os testes de regressão existentes que passaram nesta auditoria não autorizam declarar uma migração inexistente certificada.

## 8. Evidências e decisão da Fase 1

Execução dirigida final: quatro probes de caracterização + testes de escopo, multiportfólio e fila de salvamento: **18 testes Python passaram**. O teste de manifesto foi executado separadamente: **1 falha conhecida**, detalhada acima. O probe Node confirma HTML não escapado. Nenhuma suíte completa/pentest foi declarada como executada nesta fase.

Para reproduzir:

```powershell
py -3.14 -m pytest tests/audit/test_saas_readiness_characterization.py tests/infrastructure/test_portfolio_scope.py tests/api/test_local_multiportfolio_v2.py tests/api/test_operation_fast_save.py -q
py -3.14 -m pytest tests/application/test_historical_shares_units.py::test_shares_unit_020_frozen_engine -q
node tests/frontend/saas_xss_characterization.mjs
```

**Decisão:** preparar fundações neutras em PR de rascunho, sem ativar login nem atribuir legado. ADRs e certificação bloqueiam autorização, implantação e migração de titularidade; não impedem revisar tipos e DDL aditivo inativos. O sistema permanece sem proteção HTTP de usuários.

Há trabalho reaproveitável suficiente para uma evolução incremental. A principal lacuna é a composição de identidade, propriedade e política de acesso ao redor dos serviços existentes; não é o motor financeiro.


## Fundações neutras preparadas em rascunho

Branch `codex/saas-multiuser-foundations`, baseada em `123f0d457f6af58660e3b9eddb2b1597e0f07b0d` de `codex/income-starter-v2-research-governance`. Essa base já contém 0023; o PR é empilhado nela. As mudanças locais anteriores de interface/salvamento não foram copiadas. Os inventários de 35 tabelas/96 rotas retratam o workspace auditado antes desta migração, não o esquema futuro.

Incremento mínimo implementado: `users(id,status)`, `auth_identities(id,user_id,issuer,subject)` com unicidade, `portfolios.owner_user_id` nullable, roundtrip do owner no repositório e no ciclo de carteira, predicado de propriedade que nega anônimo/inativo/legado/terceiro e tipos de papéis/capacidades em `domain/saas.py`. Free mantém os recursos manuais; conexão, sincronização e conciliação permanecem indisponíveis também no Pro. O predicado não está conectado às rotas: isso ainda não é autorização HTTP.

Não há adaptador de IdP, sessão, repositório de cadastro, grant comercial, claim de legado ou cobrança. Os modelos mais completos propostos no plano são trabalho futuro. A migração 0024 não cria usuários e não atribui carteiras. O migrador automático local existente aplicaria DDL ao iniciar essa branch; ela não foi iniciada contra o banco em uso e não está pronta para implantação SaaS.

Validação: **33 testes Python passaram**, cobrindo políticas, migração SQLite temporária com ida/volta, lifecycle, isolamento atual e quatro probes de caracterização. Ruff dos arquivos alterados passou. O probe Node confirmou o sink HTML conhecido, sem executar script. O gate de hashes congelados foi repetido: mesma falha CRLF/LF já documentada, sem alterar motor ou manifesto. Probes permissivos demonstram vulnerabilidades; não são aprovação da matriz futura de autorização.

Ensaio adicional em backup consistente somente leitura do banco real: upgrade 0023→0024 e downgrade preservaram hashes de conteúdo das **34 tabelas de dados** (excluída alembic_version), integrity_check OK, zero violações de FK. A cópia temporária foi removida. Nenhuma migração ou atribuição foi feita no banco original. O downgrade recusa apagar identidades se users já contiver registros; após ativação exige plano de restore/reversão revisado.

```powershell
py -3.14 -m pytest -q tests/domain/test_saas_foundations.py tests/infrastructure/test_saas_foundation_migration.py tests/infrastructure/test_saas_portfolio_owner.py tests/infrastructure/test_portfolio_scope.py tests/api/test_local_multiportfolio_v2.py tests/audit/test_saas_readiness_characterization.py
```
