# PR 4 — Onboarding contextual V2

## Branch, base e diagnóstico

Branch codex/contextual-onboarding-v2, base develop bc14255e3ef666e4e1d61ac816201228925d4aa1. O PR 2 (#24) já estava mesclado. O PR 3 (#25) estava aberto e foi mesclado somente após autorização explícita do usuário. Os PRs de identidade e pizza (#26/#27) não foram incorporados a este escopo. Este é um único PR de onboarding, sem merge automático.

Inventário realizado antes das alterações:

| Fluxo | Base existente | Complemento V2 |
|---|---|---|
| Firebase/primeiro acesso | Login, sessão HttpOnly e criação de carteira | Depois da criação, encaminha à Minha Carteira para intenção e jornada |
| Carteiras | Criação e ownership funcionais | Reutilizados; nenhuma segunda carteira é criada pelo onboarding |
| Cadastro | Modal global de operações e validações reais por classe | Contexto inicial da classe e ajuda específica; evento de confirmação após gravação |
| Minha Carteira | Cartões, quatro análises e Meus Ativos | Guia contextual e conquistas, sem recriar indicadores/gráficos |
| Income Starter | Jornada educacional independente | Link para quem escolhe começar a investir |
| Ajuda | Metodologia e navegação existentes | Ação para reabrir o guia sem repetir a intenção salva |
| Progresso antigo | portfolio_onboarding, passos 1–4, ACTIVE/SKIPPED/COMPLETED | Mantido para compatibilidade; V2 separa preferência, fatos e estado geral |

## Comportamento entregue

Três intenções, persistidas por identidade interna: STARTING, EXISTING e ORGANIZE. A escolha não define perfil de risco. Agora não registra adiamento sem impedir uso do Income. Usuários com investimentos existentes seguem para análises; uma segunda carteira compartilha a intenção pessoal e tem progresso independente.

Jornada principal: intenção → carteira pronta com nome real → classe suportada → formulário existente → conquista confirmada → exploração de análise válida. O catálogo inclui Ações Brasil, FIIs, ETFs brasileiros/internacionais, Renda Fixa, Ações internacionais, REITs, Cripto, Outros, Previdência e Imóveis. Tesouro não é inventado como classe independente: continua dentro dos produtos suportados pelo cadastro de Renda Fixa.

As três conquistas têm identificador, título, descrição, ícone e estado próprios. Carteira criada vem da carteira autorizada. Primeiro investimento exige evento BUY confirmado e posição real no snapshot existente. A primeira análise exige interação (mouse, teclado ou swipe) e disponibilidade novamente validada no servidor. Carregamento da página não conclui conquistas. A evolução só é elegível com valores históricos positivos; a composição exige avaliação disponível para os ativos atuais. Painéis de performance e rendimentos continuam independentes: nesta versão o direcionamento inicial e a comprovação de exploração usam composição ou evolução conservadoramente validadas.

SKIPPED, DISMISSED e COMPLETED ocultam o guia; Ajuda permite retomar. Um cancelamento/erro do formulário não produz confirmação. A exclusão do único investimento reflete ausência atual e preserva a data histórica da conquista em campo separado. Respostas antigas e progresso de outra carteira são descartados. Erro ao salvar não é tratado como conclusão. Sessão expirada segue o tratamento central existente.

## Persistência, migração e endpoints

Migração 0027_contextual_onboarding_v2, após 0026. Cria somente:

- onboarding_preferences_v2: identidade, intenção, escolha/adiamento e versão.
- onboarding_journeys_v2: usuário/carteira, versão, estado, última etapa, classe e datas.
- onboarding_events_v2: chave idempotente usuário/carteira/versão/nome de evento e data.

Preserva integralmente as tabelas anteriores e copia decisões SKIPPED/COMPLETED do guia antigo, sem inventar conquistas de análise. O progresso ACTIVE da experiência antiga permanece guardado na tabela legada; a nova jornada deriva seu próximo passo dos fatos reais. Downgrade é bloqueado se houver metadados V2 a preservar.

Reutiliza /api/portfolios e todos os endpoints financeiros. Mantém os endpoints legados de onboarding. Adiciona GET e PUT /api/portfolios/{portfolio_id}/onboarding-v2. PUT aceita ações limitadas; não aceita user_id, proprietário ou estado arbitrário de conquista. Ownership é validado antes da leitura, e CSRF/sessão seguem a proteção existente.

Eventos locais: onboarding_started, onboarding_intent_selected, onboarding_first_asset_started, onboarding_first_asset_completed, onboarding_analysis_explored, onboarding_skipped e onboarding_completed. Sem montantes, tickers, saldos, retornos ou analytics externo. Chave única evita eventos duplicados por repetição da mesma ação na jornada.

## Arquivos e componentes

- api/onboarding_v2.py: derivação de fatos do snapshot/eventos já existentes e transições de apresentação.
- api/routers/portfolios.py: contratos e endpoints com ownership existente.
- infrastructure/models.py e alembic/versions/0027_contextual_onboarding_v2.py: metadados isolados.
- portfolio-guidance-v2.js: jornada adaptativa e componente reutilizável renderOnboardingAchievements.
- portfolio-view-v2.js: instrumenta interação real das análises; não muda cálculos.
- portfolio.js: inicialização e invalidação do guia por consulta/carteira.
- operations.js: sinal de confirmação depois do fluxo real de gravação.
- account.js e api.js: encaminhamento de primeiro acesso e cliente central com CSRF.
- icons.js e portfolio-v2.css: ícones decorativos, tokens, estados e layout responsivo.
- Testes de autorização, migração, UI assíncrona, teclado/toque e regressão.

## Testes e evidências

79 testes Python passaram, incluindo migração, dois usuários Firebase simulados, intenção em nova sessão da mesma identidade, segunda carteira, acesso cruzado, CSRF/logout, erro de cadastro, confirmação real, ausência de cotação, análise válida, exclusão do único investimento e idempotência. A comparação dos registros financeiros antes/depois de ações de onboarding é idêntica. O teste de migração compara todas as tabelas anteriores e verifica integridade/FKs.

Comando principal:

```text
py -3.14 -m pytest tests/infrastructure/test_onboarding_v2_migration.py tests/security/test_firebase_authorization.py tests/security/test_firebase_headers.py tests/security/test_legacy_binding.py tests/acceptance/test_frontend_modules.py tests/api/test_asset_transactions.py tests/application/test_capital_applied.py tests/api/test_portfolio_return_concepts.py tests/acceptance/test_portfolio_performance_mvp.py tests/acceptance/test_portfolio_allocation_mvp.py -q
```

Doze scripts Node passaram: onboarding_v2, holdings_v2, portfolio_alignment, portfolio_v2, portfolio_loading_regression, portfolio_redesign_v1, multiportfolio_context_v2, saas_xss_characterization, portfolio_insights_v2, firebase_auth_session, firebase_account_menu e firebase_account_contrast. A integração teclado/swipe foi repetida após a instrumentação final. Sintaxe JS/Python e git diff --check passaram.

No navegador: carteira nova de teste, intenção, classe, modal real com ajuda e classe correta, registro de VALID11 apenas no banco descartável, primeira conquista após gravação, análise por interação e guia oculto após conclusão. Reabertura pela Ajuda sem repetir intenção; claro/escuro, 1440px e 390px, sem overflow horizontal. AX confirma nomes de controles e estados; foco é mantido no título nas transições e na análise ao explorar.

Todos os testes visuais usam SQLite descartável e usuário local de validação. Os testes HTTP de identidade usam dois sujeitos Firebase determinísticos, sem contas reais ou dados pessoais. Nenhuma migração foi executada no banco pessoal ou serviço produtivo.

## Limites e riscos residuais

- Novo login Google real não foi repetido nesta entrega; a integração de identidade foi testada com o provedor determinístico e a base de sessões existente.
- Árvore de acessibilidade e navegação por teclado foram verificadas; não houve auditoria completa em NVDA/VoiceOver.
- Há falha preexistente de hash certificado CRLF/LF registrada no PR 2. Motor e manifesto não foram alterados, e não se declara certificação integral resolvida.
- A disponibilidade do primeiro investimento/análise depende de snapshot VALID. Enquanto estiver indisponível, a jornada não inventa progresso; atualização financeira existente restaura os fatos.
- Eventos de interação comprovam a ação observada pela aplicação, não atenção ou compreensão do usuário; o endpoint valida disponibilidade financeira e ownership.
- Publicação futura requer aprovação para aplicar 0027, backup e ensaio da migração antes de reiniciar o serviço. Este PR não publica nem altera o banco pessoal.

## Validação manual

1. Em ambiente descartável, aplicar migrações e iniciar a aplicação com autenticação de teste apropriada. Não apontar para o banco pessoal.
2. Fazer primeiro acesso, criar carteira e escolher Já tenho investimentos.
3. Conferir nome real, escolher FII e abrir o formulário; cancelar deve manter o progresso sem concluir investimento.
4. Reabrir, registrar um investimento de teste com os campos válidos e conferir a conquista após confirmação.
5. Abrir uma análise disponível: o guia conclui e desaparece. Se faltar avaliação/histórico, deve informar que as análises dependem de dados.
6. Em Ajuda, retomar; alterar intenção pela ação própria, pular e reabrir. Recarregar ou iniciar outra sessão deve preservar a escolha.
7. Criar segunda carteira: mesma intenção, conquistas independentes. Alternar rapidamente não pode mostrar o progresso anterior.
8. Excluir a única operação de teste e verificar ausência atual sem apagar a data histórica da conquista.
9. Repetir com outro usuário: carteiras e progresso do primeiro devem ser inacessíveis.

## Capturas

- [Intenção desktop escuro](evidence/onboarding-v2/intent-desktop-dark.png)
- [Intenção mobile escuro](evidence/onboarding-v2/intent-mobile-dark.png)
- [Intenção mobile claro](evidence/onboarding-v2/intent-mobile-light.png)
- [Carteira criada](evidence/onboarding-v2/wallet-ready.png)
- [Escolha de classe](evidence/onboarding-v2/classes.png)
- [Cadastro assistido](evidence/onboarding-v2/assisted-registration.png)
- [Primeira conquista](evidence/onboarding-v2/first-achievement.png)
- [Primeira análise](evidence/onboarding-v2/first-analysis.png)
- [Componente de progresso claro](evidence/onboarding-v2/progress-light.png)
- [Carteira vazia](evidence/onboarding-v2/empty-wallet.png)
