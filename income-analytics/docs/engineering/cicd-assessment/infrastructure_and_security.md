# PR5 — Fase 0: infraestrutura, persistência e segurança

Data: 28/10/2026. Referência de código: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`. Diagnóstico sem deploy, migration, instalação, alteração de configuração ou leitura de valores de secrets. Metodologia e estados em [architecture_inventory.md](architecture_inventory.md).

## Infraestrutura identificada

| Dimensão | Estado | Evidência verificável |
|---|---|---|
| Execução de produção | PARTIAL | Launcher externo `%LOCALAPPDATA%/IncomeAnalytics/Start-Income-HTTPS.ps1`; usa Python 3.14, `uvicorn income_analytics.main:app --app-dir src --host 127.0.0.1 --port 8002`, proxy headers com peer confiável `127.0.0.1`. Processo compatível identificado. |
| Código de produção | PARTIAL | Worktree `C:/Users/tiago/.codex/worktrees/firebase-official-merge/Projetos/income-analytics`, HEAD detached `ca627ac`. Não é um artefato instalado e promovido por digest. |
| TLS e acesso | PARTIAL | Leitura de `tailscale serve status --json`: TCP 443, um handler web, sem AllowFunnel. É publicação privada pela rede Tailscale, não hospedagem pública geral comprovada. ACLs da tailnet e configuração do console não foram auditadas. |
| Persistência do app | READY, escopo de existência | Arquivo SQLite fora do worktree publicado, em `C:/Projetos/income-analytics/income_analytics.db`; selecionado por `INCOME_ANALYTICS_DATABASE`. Existência e metadados lidos sem consultar posições ou eventos. |
| Recursos de referência | PARTIAL | `data/` ignorado pelo Git; no worktree avaliado é link para dados locais. Há repositórios/snapshots auxiliares de mercado/Magic Formula. Um clone limpo não comprova a disponibilidade desses dados. |
| Supervisor e reinício automático | UNKNOWN | Processo e launcher existem; não foi comprovada política de serviço/tarefa, recovery após reboot, conta de serviço ou limites de recursos. Não confundir arquivos antigos de setup com supervisor ativo. |
| Docker/Compose/IaC | MISSING | Sem Dockerfile, Compose ou infraestrutura como código versionada identificada. Não foram instaladas ferramentas. |
| Deploy e rollback de app | PARTIAL | Documentos de release descrevem corte manual; launcher fica fora do Git. Nenhuma promoção automatizada ou registro de artefato imutável identificado. |
| Alta disponibilidade | MISSING no desenho identificado | Produção observada depende de host Windows, processo e SQLite local. Não há configuração versionada de réplicas/failover identificada. Não significa que HA seja requisito obrigatório da primeira CI. |

O processo Uvicorn 8002 e a prévia 8003 foram identificados por metadados de processos. Isso não é verificação nova de login, gravação, entrega de e-mail, disponibilidade de dados ou SLA. Não foram efetuadas requisições autenticadas nem operações financeiras.

## Banco, migrations e persistência

**PARTIAL — ciclo de schema:**

- `infrastructure/database.py` escolhe o arquivo por `INCOME_ANALYTICS_DATABASE`; default relativo `income_analytics.db`. A variável `DATABASE_URL` do `.env.example` não é a variável usada por esse código.
- Há 27 revisões em `alembic/versions/`, um head `0027_contextual_onboarding_v2`, obtido por análise AST, sem chamar Alembic.
- Abertura direta do banco existente com URI SQLite `mode=ro` retornou revisão `0027_contextual_onboarding_v2`, 46 tabelas e `journal_mode=delete`. Não foi rodado `upgrade`, `downgrade`, `stamp`, `integrity_check` ou teste de restauração.
- `main.py` chama `initialize_database()` no carregamento. Em SaaS, `database.py` confere a revisão e falha se não for o head. Em modo local, pode executar `stamp`/`upgrade` automaticamente. Importar o app não é uma ação garantidamente sem efeitos de escrita.
- Alembic está no extra `dev`, apesar do uso no startup; lacuna de runtime detalhada em [repository_and_dependencies.md](repository_and_dependencies.md).

**PARTIAL — concorrência:** SQLite habilita FKs por conexão (`database.py`), mas a conexão somente de leitura usada pelo diagnóstico não atesta a configuração de cada conexão do processo vivo. `journal_mode=delete` foi observado; não se alterou para WAL. Escritas concorrentes, jobs e múltiplos workers precisam de capacidade medida antes de qualquer escala. Não se recomenda mudar banco ou journal como efeito lateral do PR5 Fase 0.

**PARTIAL — separação entre código e estado:** o DB principal persiste fora do checkout publicado, mas `data/`, diretórios de referência, caches e launchers dependem de caminhos do usuário. Um rollback Git não restaura schema, registros financeiros, identidades Firebase ou referências auxiliares. A futura unidade de backup/release precisa listar esses estados explicitamente.

## Backup e restauração

| Capacidade | Estado | Evidência / limite |
|---|---|---|
| Backup antes de mudanças específicas | PARTIAL | `scripts/bind_legacy_portfolio.py` exige manutenção e diretório de backup para apply; usa `sqlite3.backup` e verifica integridade. Outros scripts de recuperação também criam backups. Não foram executados. |
| Backup de migration no modo local | PARTIAL | `database.py` contém `shutil.copy2` antes de upgrade em certas condições. A cópia simples de arquivo aberto não comprova backup consistente sob escrita concorrente. |
| Ensaios históricos | PARTIAL | `docs/CONSOLIDATED_RELEASE_2026_10_24.md` relata ensaio em cópia; `docs/FIREBASE_AUTH_VALIDATION.md` descreve roundtrip anterior. São históricos, não ensaios desta fase. |
| Backups locais de operação | PARTIAL | Diretórios de backups/rehearsals/releases em `%LOCALAPPDATA%/IncomeAnalytics/`. Apenas nomes/presença foram inventariados; conteúdo sensível, idade, recuperabilidade e cobertura não foram auditados. |
| Retenção, cifragem e cópia fora do host | UNKNOWN | Nenhuma política executável ou evidência suficiente identificada; não presumir ausência de mecanismos externos não auditados. |
| Runbook genérico e periódico de restore | MISSING no repositório | Há orientação para rollback de vínculo de owner em `docs/FIREBASE_AUTH_SECURITY.md`, mas não um procedimento de recuperação integral com periodicidade, responsáveis e evidência automática. |
| RPO/RTO aprovados | MISSING | Não foram identificadas metas formais de perda de dados e tempo de recuperação. |

Uma futura restauração deve ocorrer em destino isolado, com validação de schema/FKs/ledger/read models e autorização, antes de substituir estado produtivo. Parar escritores e definir rollback de dados é distinto de voltar o SHA da aplicação. Nenhum procedimento foi executado agora.

## Configuração e variáveis — somente nomes, sem valores

| Grupo | Variáveis identificadas | Fonte e avaliação |
|---|---|---|
| Modo e origem | `INCOME_AUTH_MODE`, `INCOME_ENV`, `INCOME_APP_ORIGIN`, `INCOME_PUBLIC_SIGNUP_ENABLED` | `infrastructure/auth_config.py`, launcher e `docs/FIREBASE_AUTH_SETUP.md`. PARTIAL: validação existe; configuração por ambiente não está inteiramente versionada. |
| Persistência | `INCOME_ANALYTICS_DATABASE`, `INCOME_ANALYTICS_COTAHIST_CACHE` | `database.py`, `b3_cotahist_market_data.py`. PARTIAL: caminhos precisam ser explícitos e separados por ambiente. |
| Identidade web | `FIREBASE_PROJECT_ID`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_APP_ID` | `api/routers/auth.py`, setup e launcher. Configuração Web é entregue ao cliente por desenho; não equivale à chave privada Admin. Restrições de API/domínios no console: UNKNOWN nesta avaliação. |
| Identidade backend | `GOOGLE_APPLICATION_CREDENTIALS` / ADC | `firebase_identity.py` e launcher externo. PARTIAL: credencial fica fora do código; IAM, validade, rotação e ACL do arquivo não foram comprovados. Conteúdo não foi aberto. |
| Emulador e testes cloud | `FIREBASE_AUTH_EMULATOR_HOST`, `INCOME_RUN_FIREBASE_EMULATOR_TESTS`, `INCOME_RUN_FIREBASE_LIVE_TESTS` | `auth_config.py`, `firebase.json`, testes security. PARTIAL: opt-in e rejeição de emulador em produção existem; serviço não iniciado nesta fase. |
| Dados externos | `BRAPI_TOKEN`, `TWELVE_DATA_API_KEY` | Adaptadores `infrastructure/brapi_*`, `twelve_data_us_market_data.py`. UNKNOWN: presença/validade/quotas reais não foram consultadas. |
| Operação e profiling | `INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS`, `INCOME_ANALYTICS_PERF_LOG` | `main.py`; PARTIAL: logging de requests/SQL é opcional, jobs locais têm kill switch e são desativados em SaaS. |
| Testes e cobertura financeira | `INCOME_ANALYTICS_TESTING`, `INCOME_PERFORMANCE_COVERAGE_GOOD`, `INCOME_PERFORMANCE_COVERAGE_MINIMUM` | `tests/conftest.py`, `application/performance_coverage.py`. PARTIAL: testes isolam DB; limiares financeiros não são cobertura de testes e não devem ser reconfigurados pela esteira. |

**PARTIAL — template de ambiente:** `.env.example` lista apenas uma fração dos nomes atuais e inclui nomes antigos (`APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL`, `DATABASE_URL`). Não há carregador dotenv identificado no caminho principal; não presumir que criar `.env` configure automaticamente o serviço. O launcher configura variáveis diretamente. A documentação futura deve indicar quais variáveis são públicas, privadas, obrigatórias e proibidas por ambiente sem incluir seus valores.

## Controles de segurança comprovados

| Controle | Estado | Evidência / limitação |
|---|---|---|
| Firebase validado no servidor | READY, mecanismo | `firebase_identity.py`: assinatura, expiração e revogação no fluxo normal; não há JWT artesanal. Configuração e disponibilidade cloud permanecem externas. |
| Ownership e sessão local | READY, mecanismo | `saas_security.py`, `auth_repository.py`, `auth_context.py`; owner por carteira, hashes de sessão e contexto server-side. Testes em `tests/security/`. Não é pentest novo. |
| CSRF, origem e cookies | READY, mecanismo | `saas_security.py`, `auth_config.py`, roteador auth; origem exata, CSRF em escrita, cookies seguros no HTTPS. Não relaxar esses controles para tornar o deploy fácil. |
| Headers e limite de corpo/rate | PARTIAL | CSP/HSTS em `main.py`, `upload_safety.py`, limites em `saas_security.py`. Não substituem WAF, quotas ou proteção de borda; retenção e política operacionais não foram auditadas. |
| Secrets fora do Git | PARTIAL | `.gitignore` ignora padrões de service accounts e `.env`; launcher aponta para credencial externa. Nenhum nome de service account rastreado encontrado; não houve scan completo do histórico. |
| GitHub secret scanning | READY, recurso configurado | API `security_and_analysis`: secret scanning e push protection habilitados. Recursos para non-provider patterns/validity checks aparecem desativados. Não foram lidos alerts ou valores. |
| Atualizações de vulnerabilidade | PARTIAL | Dependency Graph ativo; API indica Dependabot security updates desativado. Nenhum scan de vulnerabilidades foi executado, nem se declara “sem vulnerabilidades”. |
| SAST, SCA de release e SBOM | MISSING | Nenhum pipeline versionado ou política de bloqueio identificada. |
| IAM, rotação e recovery de identidade | UNKNOWN | Sem auditoria de permissões do projeto Firebase, ACLs, rotação e procedimentos de incidente nesta fase. |

Repositório público exige cuidado com artefatos de CI: não publicar banco, exports de carteira, payloads autenticados, perfis com valores pessoais ou snapshots reais. `docs/appendices/` é parcialmente rastreado apesar do ignore, então o ignore não é um controle suficiente de publicação.

## Observabilidade e ambientes

**PARTIAL — observabilidade:** `main.py::profile_request` e `infrastructure/request_profiling.py` medem tempo, consultas e tamanho da resposta quando habilitados; `application/provider_health.py` e histórico de refresh registram saúde de provedores. `/health` retorna apenas `{"status":"ok"}` (`api/routers/health.py`); não comprova schema, disco, DB, dados de referência ou Firebase. Não foram encontrados exporters/alertas/dashboards operacionais versionados nem readiness funcional de release. Retenção e centralização de logs: UNKNOWN.

| Ambiente futuro | Estado atual | Requisitos mínimos antes de CD |
|---|---|---|
| Desenvolvimento | PARTIAL | Python 3.14 e Node definidos, dependências reproduzíveis, DB descartável, variáveis documentadas e jobs controlados. Evidência atual: launcher LAN, pytest e frontend Node. |
| Homologação | MISSING como ambiente independente comprovado | Artefato candidato, SQLite e referências próprios, identidade/projeto separado ou emulador adequado, origem HTTPS autorizada, testes sintéticos, restore/rollback e logs. Prévia local não basta como prova. |
| Produção | PARTIAL, operação privada existente | Artifact/SHA revisado, gate financeiro reconciliado, migração revisada fora do startup local, backup consistente, segredos segregados, aprovação, smoke e rollback com estado protegido. Nada disso deve abrir acesso público implicitamente. |

O alvo inicial pode continuar sendo Windows + Tailscale + SQLite. Docker, cloud pública, PostgreSQL, Redis e novos serviços pagos não são pré-requisitos presumidos. A escolha do alvo e os níveis de disponibilidade precisam ser aprovados antes do desenho de CD.
