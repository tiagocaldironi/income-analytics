# Firebase e isolamento multiusuário — Fase 2

Este incremento se apoia no PR de fundações da Fase 1. Firebase autentica; o UUID interno continua sendo a identidade do Income e `portfolios.owner_user_id` define o acesso. Não se usa UID Firebase como FK do ledger nem e-mail como critério de fusão. O plano inicial é FREE, resolvido pelo servidor; Pro, pagamentos e integração bancária não são ativados.

## Fronteira HTTP e achados P0

| Achado da Fase 1 | Controle implementado em modo Firebase |
|---|---|
| S01 — enumeração/leitura de carteiras | Cookie verificado pelo Admin SDK, conta interna ativa, sessão local válida; lista/get filtrados por owner em SQL |
| S02 — escrita por UUID alheio | Validação antes de handlers/parse de operações; cobre todas as rotas registradas, aliases B3 e recursos indiretos; rota nova desconhecida é negada |
| S03 — classificação global | Novos ativos recebem namespace interno por carteira; ticker lógico e UUIDs financeiros permanecem no domínio. Reclassificação/nome são metadados privados; não regravam o cadastro canônico legado |
| S04 — referências globais | Preços manuais/sob demanda do usuário são armazenados em `portfolio_market_prices`; benchmark/FX/backfills e cotas globais exigem claim específico `MARKET_CURATOR`; logs legados globais são suprimidos das respostas de contas comuns |
| S05 — credencial global | Toda família `/settings/paid-income`, inclusive leitura/teste/sync, é indisponível em SaaS. Nenhum token singleton é mostrado, copiado ou migrado; jobs locais não o executam |

O modo local continua destinado à instalação pessoal privada. Nunca implantar uma base SaaS como `INCOME_AUTH_MODE=local`; `INCOME_ENV=production` recusa esse modo. Os controles acima não são retroativamente prometidos para a instância local que continua em uso.

`api/saas_security.py` é a fronteira default-deny. Autentica antes de construir `PortfolioSession`, impõe seleção explícita de carteira e usa o mesmo owner para lifecycle e nome único. Não existe fallback para MAIN no modo SaaS. Referências públicas conhecidas podem ser consultadas sem selecionar carteira, mas exigem conta autenticada. Docs/OpenAPI são ocultos nesse modo. O shell e assets estáticos contêm código, nunca registros financeiros.

O namespace de persistência `@<portfolio UUID>:<ticker>` permite que duas contas cadastrem o mesmo identificador privado sem colisão e sem revelar o nome escolhido pela outra. Não se renomeiam ativos legados nem eventos. Essa implementação é para o SQLite atual; uma futura troca de banco exige revisar índices, comprimento físico do ticker e estratégia de namespace. Cotações globais só são reutilizadas por ticker lógico com proveniência pública permitida; valores legados ambíguos não viram referência pública por estarem na tabela global.

Caches financeiros no servidor só são consumidos depois do ownership. Objetos mutáveis de eventos não são compartilhados entre requests SaaS. Atualizações de dashboard continuam no contexto da carteira autorizada. Jobs locais não percorrem MAIN/carteiras no startup nem quando chamados diretamente em SaaS; seu futuro substituto precisa revalidar titular, serviço e lease. Não há worker Pro habilitado.

Preview B3 no SaaS é persistido por carteira no banco, em vez do cache global em RAM: funciona entre workers sem publicar conteúdo e reaproveita deduplicação/FKs existentes. Aliases com e sem `/api` passam pelo mesmo controle. Importações têm teto de corpo/arquivo, expansão ZIP, XML e linhas; não extraem arquivos em diretório público. Backup e uploads não têm rota de download.

## Sessão, CSRF, métodos e navegador

- Web SDK com `inMemoryPersistence`; nenhum ID token/refresh token vai para localStorage, sessionStorage ou HTML. Somente um identificador interno de usuário e seleção visual de carteira podem estar no armazenamento do navegador.
- POST de token recente (auth_time até cinco minutos), e-mail verificado e provedor Google/password. Token é validado pelo Admin SDK com revogação. A identidade é mapeada por projeto/issuer + subject; UID diferente com mesmo e-mail gera usuário interno diferente.
- Cookie Firebase dura seis horas. Cada request privado exige assinatura/expiração/revogação válidas, conta Firebase não desativada, conta interna ativa e hash de sessão existente no SQLite. O cookie de transporte combina o JWT Firebase com nonce local aleatório; o SDK verifica o JWT e o banco exige o hash do valor completo. Isso impede reativar um cookie encerrado se o Firebase repetir o mesmo JWT no mesmo segundo. O banco só armazena hash desse valor e do CSRF.
- CSRF inclui Origin exata, cookie HttpOnly, token retornado por endpoint same-origin, header e vínculo com a sessão nos writes privados. Cookies `__Host-` impedem Domain/path alternativos em HTTPS. Host arbitrário e corpos grandes também são rejeitados.
- Logout remove o registro local e os cookies; reapresentar o cookie removido falha. “Encerrar todos os acessos” apaga sessões locais do titular e revoga refresh tokens no Firebase. Recuperação de senha também segue a revogação do provedor.
- Cada identidade mantém métodos aprovados. Adicionar método exige login recente pelo método já autorizado, mesmo UID e confirmação de dois minutos consumida atomicamente. O servidor consulta os provedores reais do Firebase, sem aceitar uma lista do browser. Não se transfere carteira nem se unem usuários por e-mail.
- Adicionar uma senha pode revogar o cookie Firebase anterior. Somente o POST de conclusão da vinculação aceita sua assinatura/expiração sem exigir revogação; ainda exige sessão local, CSRF, conta interna ativa, confirmação de uso único e **ID token recente, não revogado e do mesmo UID**. Nenhuma API financeira usa essa exceção. Isso permite concluir o handoff sem aceitar uma sessão revogada como acesso geral.
- A UI apaga seleção antiga ao trocar usuário, limpa estado no logout, notifica outras abas e elimina a tela financeira após 401. BFCache força nova validação. Novo usuário vê carteira vazia; nenhum login reivindica legado.

O sink conhecido de nome/subtítulo em `renderHoldingRow` foi escapado e ganhou regressão executável. CSP impede scripts inline, objetos, frames externos não previstos e submissões para outra origem; mantém apenas hosts necessários ao SDK e bibliotecas existentes. Isso não substitui uma revisão ampla de segurança de frontend antes do lançamento.

## Limites e operação

Contadores SQLite atômicos, compartilhados entre workers do mesmo banco: 300 requests/min/IP, 40 requests/min/IP para auth, 240 requests/min/usuário, 60 writes/min/usuário, 20 POSTs de importação/dia/usuário, 200 solicitações de mercado/dia/usuário e 5.000/dia na plataforma. São limites técnicos iniciais, não restrições comerciais ao número de carteiras/ativos. Há teto de 128 KiB para JSON comum, 8 MiB para corpo de importação, 6 MiB para arquivo e 5.000 linhas por lote B3; ZIP tem limites de entradas/expansão e rejeita DTD/entities.

Contadores usam hash da chave, retidos por no máximo cerca de dois dias; hashing de IP não é anonimização forte. Não se confia em headers de IP arbitrários. Ajustar reverse proxy e retenção ao ambiente. Rate limiting local não substitui proteção de borda/WAF, quotas do Firebase, monitoramento ou licença de fontes de mercado. Não há Redis ou serviço pago necessário nesta implementação.

Papéis de curadoria são claims customizados do Admin SDK, administrados fora da UI comum. Plano PRO não concede curadoria ou acesso financeiro alheio. Os papéis operacional, revisão financeira e revisão regulatória da Fase 1 não se tornam um bypass genérico de ownership. O workflow editorial Starter permanece independente, com os gates de publicação existentes.

## Vínculo legado: procedimento explícito

`scripts/bind_legacy_portfolio.py` não é importado pelas rotas. O default é dry-run. Exige carteira, usuário interno ativo, projeto/UID Firebase esperado, operador UUID e referência de confirmação aprovada. Não busca por e-mail/nome nem reivindica dados no primeiro login. Reatribuir carteira já pertencente a outro usuário é proibido.

Antes de aplicar, confirmar titular e ator em procedimento administrativo privado, verificar referências compartilhadas e ensaiar outputs financeiros em cópia. O script recusa preços manuais legados compartilhados de proveniência ambígua. Essa recusa exige um plano específico de curadoria; não deve ser contornada publicando esses preços ou inventando um proprietário.

```powershell
py -3.14 scripts/bind_legacy_portfolio.py --database C:\copia\income.db --portfolio-id UUID_CARTEIRA --owner-id UUID_INTERNO --firebase-project-id PROJETO --firebase-uid UID_CONFIRMADO --confirmed-by UUID_OPERADOR --reason REFERENCIA_PRIVADA_APROVADA
```

`--apply --maintenance --backup-directory C:\backups-privados` só entra depois da confirmação/revisão. Apply reserva o escritor, faz backup consistente antes da mudança, grava apenas owner + auditoria (ator, recurso e hash da evidência), verifica FKs e faz commit. A evidência completa fica no registro privado de mudança, não em logs financeiros. Repetir o mesmo vínculo é idempotente. Rollback após aplicação usa o backup revisado em janela de manutenção, com escritores parados; nunca restaurar cegamente sobre um banco em uso.

O teste de legado usa um banco temporário com evento financeiro: dry-run não altera owner, apply preserva o ledger, backup mantém o estado anterior, UID errado é rejeitado e repetição não muda a propriedade. Nenhum vínculo foi executado no banco pessoal.

## Validação e limites desta entrega

Os testes em `tests/security/` separam um IdP double determinístico dos testes que realmente falam com o emulador Firebase e o Admin SDK. O emulador cobre senha, e-mail não confirmado/confirmado, dois UIDs, quatro carteiras, Google sintético, vínculo e revogação. O double permite ataques adicionais de Host, CSRF, corpo, cookies, conta suspensa, expiração, seleção forjada e toda a matriz de rotas.

```powershell
$env:INCOME_RUN_FIREBASE_EMULATOR_TESTS="1"
py -3.14 -m pytest -q tests/security
node tests/frontend/firebase_auth_session.mjs
node tests/frontend/multiportfolio_context_v2.mjs
node tests/frontend/saas_xss_characterization.mjs
```

Sem opt-in e emulador, os quatro testes reais ficam explicitamente skipped. Não contar skipped como aprovação. Ver [registro de validação](FIREBASE_AUTH_VALIDATION.md) para resultados e evidências desta execução.

Permanecem necessários para lançamento: projeto Firebase real e domínios/credenciais, validação de OAuth e entrega real de e-mails, revisão de infraestrutura/abuso/licenças, procedimento de legado aprovado e gate de certificação financeira reconciliado. A falha histórica de bytes CRLF/LF do manifesto não foi corrigida alterando arquivos certificados. Não há merge/deploy automático nem cadastro público de produção ativado.
