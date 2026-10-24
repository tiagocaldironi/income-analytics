# Validação da Fase 2 — Firebase Authentication

Ambiente: Windows, Python 3.14, SQLite, Node 24, Firebase Admin Python 7.7.0 e Auth Emulator oficial em `127.0.0.1:9099`, projeto fictício `demo-income-saas`. Nenhuma credencial ou conta de produção foi criada/utilizada. As mudanças foram feitas em worktree isolada, empilhadas nas fundações da Fase 1.

## Resultados executados

| Verificação | Resultado |
|---|---|
| Regressão dirigida ampla | **134 testes Python passaram**: domínio, segurança, persistência, multiportfólio, TWR/múltiplas moedas, reconstrução histórica, explicação patrimonial e contratos do frontend |
| Rechecagem após endurecer cookie/revogação e offload de I/O | **26 testes passaram**: segurança, API multiportfólio local e escopo persistido. São testes repetidos/adicionais, não somar como contagem de casos únicos |
| Firebase real emulado — **4 testes passaram**, incluindo ações OOB de verificação e recuperação | Dois usuários de senha distintos, e-mail obrigatório, quatro carteiras, Google sintético, confirmação de vinculação, conta desativada e revogação pelo Admin SDK aprovados |
| Cliente BFF Node | CSRF, troca de token somente em memória, seleção de carteira e limpeza de logout passaram |
| Regressão HTML | Nome de ativo com marcação inerte é escapado; não se torna elemento HTML |
| Migração em cópia consistente do banco pessoal | `0023 → 0025 → 0023`; hashes de conteúdo das **34 tabelas de dados** preservados, `integrity_check=ok`, zero violações de FK. Cópia removida; origem não migrada |
| Vínculo legado em banco temporário | Dry-run, confirmação do UID/projeto, backup anterior, ledger idêntico, idempotência e rejeição de UID errado aprovados |
| Motor/manifesto | Nenhum arquivo certificado ou cálculo foi modificado; gate bruto de hashes conserva **uma falha anterior** de CRLF/LF |

A execução ampla ocorreu antes dos testes extras de replay de JWT idêntico e da ação OOB de recuperação; a rechecagem dirigida cobre o endurecimento subsequente. Não foi executado nem declarado um pentest ou a suíte completa de todo o repositório.

Comando da regressão ampla:

```powershell
$env:INCOME_RUN_FIREBASE_EMULATOR_TESTS="1"
py -3.14 -m pytest -q tests/security tests/domain tests/infrastructure/test_portfolio_scope.py tests/infrastructure/test_saas_foundation_migration.py tests/infrastructure/test_saas_portfolio_owner.py tests/api/test_local_multiportfolio_v2.py tests/acceptance/test_frontend_modules.py tests/acceptance/test_portfolio_performance_mvp.py tests/acceptance/test_multicurrency_twr_base_currency.py tests/acceptance/test_persistence_reconstruction.py tests/acceptance/test_implicit_opening_capital_performance.py tests/application/test_historical_portfolio_reconstruction.py tests/application/test_wealth_explanation.py
node tests/frontend/firebase_auth_session.mjs
node tests/frontend/multiportfolio_context_v2.mjs
node tests/frontend/saas_xss_characterization.mjs
```

A contagem ao repetir o comando aumenta com os casos extras adicionados depois da execução ampla. Os testes reais exigem emulador + opt-in; skipped não é aprovação de Firebase.

## Falha preexistente preservada

`tests/application/test_historical_shares_units.py::test_shares_unit_020_frozen_engine` foi repetido e falhou pela mesma divergência bruta:

- `magic_formula_ranking_validation.py`: esperado `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37`, atual CRLF `039656c877d516ce2e2cdcf5d6bba7efadf948a92958875ecd140a16349ce83d`.
- A análise LF/CRLF já está registrada na auditoria da Fase 1. Não se editou arquivo financeiro ou manifesto para fazer o teste passar.

Esse gate permanece pendente de reconciliação formal e impede declarar certificação financeira completa para lançamento. Os testes financeiros dirigidos aprovados não substituem a certificação.

## Navegador e interface

Validação manual no navegador sobre API/banco descartáveis, sem registros reais: entrada → primeira carteira vazia → Operações → conta → logout → novo login. SDK Web atualizado para 13.1.0, inicializado diretamente com persistência em memória. Não houve erros no console ao concluir o acesso.

Telas de entrada verificadas em **1280×900** e **390×844**, temas claro/escuro; no mobile, `scrollWidth == clientWidth == 390`. Formulários têm labels, foco visível, controles com área de toque, feedback de erro/status e prevenção de submissão concorrente. A evidência visual acompanha o PR de interface, separado do PR da API.

O fluxo de Google no emulador usa identidade sintética. OAuth/consentimento Google real, domínio autorizado e entrega real de mensagens continuam dependentes do projeto Firebase selecionado. A documentação de custos/configuração não significa que um projeto tenha sido provisionado.

## Gate de liberação

Cadastro público de produção permanece fechado por padrão. Nenhum merge, deploy, migração do banco em uso, vínculo de carteira real, billing ou integração bancária foi executado. Exigir projeto e configuração reais, revisão de infraestrutura/limites/licenças, validação privada com duas contas reais e fechamento da pendência de certificação antes de publicar.
