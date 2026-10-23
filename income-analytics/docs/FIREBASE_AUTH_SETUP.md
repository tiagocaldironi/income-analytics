# Firebase Authentication — configuração do Income

Decisão da Fase 2: Firebase Authentication para identidade; FastAPI e SQLite continuam responsáveis por sessão, autorização e dados financeiros. Nenhum projeto, serviço pago, banco em nuvem, cobrança ou deploy é criado pelo código. O cadastro permanece fechado por padrão.

## Serviços necessários e custo

Usar um projeto Firebase **Spark**, somente Authentication, com Google e Email/Password. Não são necessários Firestore, Realtime Database, Storage, Hosting, Cloud Functions, Cloud Run, telefone/SMS, Identity Platform ou billing. As dependências de Firestore/Storage instaladas transitivamente pelo Admin SDK não ativam esses produtos.

Em consulta à documentação oficial em 23/10/2026, o Spark lista **1.000 mensagens de verificação/dia**, **150 mensagens de recuperação de senha/dia** e **100 novas contas/hora/IP**. São limites do provedor, adicionais aos controles do Income. Email-link sign-in é outro produto e não é usado. Ver [limites oficiais](https://firebase.google.com/docs/auth/limits).

Authentication básico e Authentication com Identity Platform têm condições distintas. O upgrade para Identity Platform introduz limites/cobrança próprios (inclusive limites de usuários ativos); não fazê-lo nesta fase. Não associar uma conta de faturamento nem migrar para Blaze sem autorização. Outros produtos Google Cloud, SMS, infraestrutura de hospedagem e fornecedores de mercado podem gerar custos separados. Conferir [preços Firebase](https://firebase.google.com/pricing), [planos Spark/Blaze](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans) e [Authentication/Identity Platform](https://firebase.google.com/docs/auth) antes de qualquer lançamento; não há promessa de uso ilimitado gratuito.

O Admin SDK verifica revogação/conta desativada em cada request autenticado. Isso acrescenta chamadas de usuário ao provedor e está sujeito às quotas da API; monitorar antes de aumentar usuários/workers. Limites do Income não substituem os limites comerciais dos fornecedores.

## Configuração manual do projeto

1. Criar/selecionar o projeto Spark e registrar um aplicativo Web. Não habilitar Analytics ou produtos adicionais apenas para fazer login.
2. Authentication → Sign-in method: ativar Google (configurar e-mail de suporte) e Email/Password. Deixar outros provedores, login anônimo, telefone e email-link desativados.
3. Authentication → Settings → User account linking: escolher **contas distintas para provedores distintos com o mesmo e-mail**. Isso evita a vinculação automática do Firebase descrita em [Users](https://firebase.google.com/docs/auth/users/) e [configuração de contas por e-mail](https://support.google.com/firebase/answer/9134820). O Income adiciona um segundo controle: um método novo no mesmo UID precisa de confirmação explícita no backend.
4. Configurar política de senha e proteção contra enumeração de e-mails, quando disponíveis no projeto, e personalizar mensagens de verificação/recuperação com domínio e remetente válidos.
5. Authorized domains: somente o domínio HTTPS real do Income e os domínios de desenvolvimento necessários. Adicionar `localhost` explicitamente para desenvolvimento; projetos novos podem não incluí-lo. Não usar curingas nem domínios não controlados. Configurar o domínio `authDomain` do aplicativo e redirects autorizados de Google conforme [Google sign-in](https://firebase.google.com/docs/auth/web/google-signin).
6. Manter o service account exclusivamente no backend, fora do Git e do diretório estático. Preferir Application Default Credentials/workload identity em infraestrutura que ofereça isso; no desenvolvimento autorizado, apontar para um JSON privado por `GOOGLE_APPLICATION_CREDENTIALS`. Nunca colar a chave no frontend, `.env` versionado, PR ou chat. Restringir permissões e rotacionar conforme o procedimento da organização.

## Variáveis

| Variável | Uso |
|---|---|
| `INCOME_AUTH_MODE=firebase` | Ativa a fronteira SaaS. `local` preserva o uso pessoal existente e nunca é permitido com `INCOME_ENV=production` |
| `INCOME_ENV=production` | Exige HTTPS e rejeita o emulador |
| `INCOME_APP_ORIGIN=https://income.example.com` | Origem exata, sem caminho; Host/origem de writes devem corresponder |
| `INCOME_ANALYTICS_DATABASE` | Caminho absoluto do SQLite financeiro revisado; não é banco Firebase |
| `FIREBASE_PROJECT_ID` | Projeto que emite as identidades verificadas |
| `FIREBASE_WEB_API_KEY` | Identificador público Web, com restrições de API/referrer adequadas no console |
| `FIREBASE_AUTH_DOMAIN` | Domínio autorizado do fluxo de autenticação |
| `FIREBASE_WEB_APP_ID` | App Web registrado no projeto |
| `GOOGLE_APPLICATION_CREDENTIALS` | Caminho de credencial Admin privada, se não houver ADC/workload identity |
| `INCOME_PUBLIC_SIGNUP_ENABLED=0` | Default efetivo: fechado; somente `1` permite criar usuários internos novos |
| `FIREBASE_AUTH_EMULATOR_HOST` | Somente desenvolvimento com projeto `demo-*`; **não definir em produção** |

O endpoint `/api/auth/config` expõe apenas os identificadores públicos Web. A interface não mostra detalhes de configuração. Os arquivos de service account nunca são servidos por `/static`.

## Desenvolvimento sem projeto pago

Usar o emulador oficial, que emite tokens não assinados aceitos **apenas** pelo Admin SDK configurado para o emulador. Essa configuração é recusada fora de `INCOME_ENV=development` e sem Project ID `demo-*`. Ver [documentação do emulador](https://firebase.google.com/docs/emulator-suite/connect_auth).

Na pasta do projeto, com Node e npm/pnpm disponíveis:

```powershell
pnpm dlx firebase-tools@14.24.2 emulators:start --only auth --project demo-income-saas --config firebase.json
```

O `firebase.json` prende o Auth Emulator a `127.0.0.1:9099` e não inicia UI ou outros produtos. Não exportar usuários do emulador para produção. O fluxo Google emulado utiliza credenciais sintéticas; não testa consentimento, redirects e domínio de um projeto Google real.

Em outro terminal, **usar um arquivo SQLite descartável**, nunca o banco pessoal:

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:INCOME_ANALYTICS_DATABASE = "$env:TEMP\income-firebase-development.db"
py -3.14 -m alembic upgrade head
$env:INCOME_AUTH_MODE = "firebase"
$env:INCOME_ENV = "development"
$env:INCOME_APP_ORIGIN = "http://localhost:8002"
$env:FIREBASE_PROJECT_ID = "demo-income-saas"
$env:FIREBASE_AUTH_EMULATOR_HOST = "127.0.0.1:9099"
$env:FIREBASE_WEB_API_KEY = "emulator"
$env:FIREBASE_AUTH_DOMAIN = "localhost"
$env:FIREBASE_WEB_APP_ID = "demo-income-saas"
$env:INCOME_PUBLIC_SIGNUP_ENABLED = "1"
py -3.14 -m uvicorn income_analytics.main:app --app-dir src --host 127.0.0.1 --port 8002
```

A exceção HTTP e cookies sem Secure só existe no loopback, com `INCOME_ENV=development`. Produção usa nomes `__Host-income_session` e `__Host-income_csrf`, HttpOnly, Secure, SameSite=Strict, Path=/ e sem Domain. Não desativar Secure para acessar a sessão SaaS por HTTP via LAN/Tailscale; usar HTTPS corretamente configurado.

## Produção: procedimento ainda não executado

1. Aprovar projeto Spark, configuração dos provedores/domínios, credenciais e as evidências de segurança/legado. Resolver o gate de hashes certificados separadamente, sem editar o manifesto para obter verde.
2. Parar escritores e jobs. Fazer backup consistente via SQLite backup API e verificar restore/integridade em cópia. Não copiar somente o `.db` aberto com WAL em atividade.
3. Ensaiar `alembic upgrade head` na cópia. Verificar os registros e outputs financeiros antes/depois; só então executar o migrador controlado no banco aprovado. No modo SaaS o processo **não executa upgrade nem stamp automáticos** e recusa um schema desatualizado.
4. Configurar HTTPS/reverse proxy, origem exata, rede/volumes privados e trusted proxy IPs explícitos. Não aceitar `X-Forwarded-*` de qualquer cliente. Não servir raiz do projeto, backups ou banco. Revisar permissões de arquivos e logs.
5. Iniciar com `INCOME_PUBLIC_SIGNUP_ENABLED=0`. Jobs locais que percorrem carteiras e configurações globais ficam desativados em SaaS; não reativá-los por flag genérica. Atualização de referência em serviço exige principal e revisão próprios.
6. Validar Google real, senha, e-mails reais, expiração, desativação, vinculação, logout/revogação e matriz A/B no staging privado com o projeto selecionado. O emulador não substitui essa etapa.
7. Só após aprovação explícita habilitar cadastro e exposição pública. Este trabalho não fez merge, deploy, contratação ou mudança no banco pessoal.

Se houver downgrade após uso, restaurar backup revisado ou criar migração de reversão sem perda. A migração 0025 recusa apagar sessões/auditoria/metadados privados usados. O script de vínculo legado é operador-only, não é endpoint nem etapa de onboarding; ver [segurança e legado](FIREBASE_AUTH_SECURITY.md).

SDKs usados: Admin Python `>=7.7,<8`; Web ESM fixado em `13.1.0`, carregando apenas App/Auth, com persistência em memória desde a inicialização. Versão verificada nas [notas oficiais](https://firebase.google.com/support/release-notes/js). Revisar atualizações de segurança e repetir os testes antes de promover versões.

O kill switch do Income bloqueia a criação do usuário interno e o acesso ao banco financeiro; ele não desativa a API de cadastro do próprio Firebase se os provedores do projeto estiverem habilitados. Manter staging/configuração restritos e considerar as quotas/medidas antiabuso do provedor antes de expor o projeto.
