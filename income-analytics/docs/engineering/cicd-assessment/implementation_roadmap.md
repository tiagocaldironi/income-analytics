# PR5 — roadmap incremental proposto

Data: 28/10/2026. Este documento é uma proposta, **não um registro de implementação**. A Fase 0 entrega apenas os seis documentos desta pasta. Nenhum workflow, build, migration, instalação, commit ou deploy foi executado.

Base: [assessment](cicd_readiness_assessment.md), [dependências](repository_and_dependencies.md), [testes](testing_and_quality_gates.md), [infraestrutura](infrastructure_and_security.md).

## Ordem e condições de avanço

| Etapa | Trilho | Prioridade e esforço relativo | Depende de | Saída verificável proposta |
|---|---|---|---|---|
| 1 | Baseline e governança | P0, pequeno/médio | Revisão desta Fase 0 | Fonte de integração/release e política de certificação definidas; inventário de diferenças locais preservado. |
| 2 | CI automatizada | P0, médio | 1; dependências de teste revisadas | Checks reproduzíveis de Python/Node, lint e tipos, com resultados completos e falhas visíveis. |
| 3 | Gate financeiro | P0, esforço a estimar após revisão independente | 1; pode ocorrer em paralelo conceitual com 2 | Pendência LF/CRLF reconciliada formalmente; evidências e gate aprovados, sem mascarar falhas. |
| 4 | Build/empacotamento | P1, médio | 1–2; runtime mínimo resolvido | Artefato imutável testado em ambiente limpo e identificado por SHA/digest. |
| 5 | CD homologação | P1, médio/grande | 2 e 4; estado/identidade segregados | Deploy repetível do artefato, migration ensaiada e restore demonstrado, com smokes e E2E. |
| 6 | Segurança e observabilidade operacional | P1, médio | Inicia em 1–2; exigências de release concluídas antes de 7 | Secrets, permissões, logs, alertas, readiness, backup/RPO/RTO e incidentes documentados e testados. |
| 7 | CD produção | P2, médio/grande | 2–6 aprovadas, incluindo 3 | Promoção aprovada do mesmo artefato, backup consistente, smoke e rollback auditáveis. |
| 8 | Manutenção contínua | P2, recorrente | 7 | Revisão de dependências, restauração periódica, métricas de release, capacidade e segurança. |

Esforço relativo não é prazo nem promessa de custo; depende do runner, host, contas e critérios aprovados. Cada etapa pode ser um PR separado. Não há necessidade de novos serviços pagos implícita.

## 1. Baseline e governança

**Estado atual: PARTIAL.** Evidências: `develop@ca627ac`, checkout original divergente, branches `codex/*`, tags variadas, proteção ausente.

Proposta:

1. Adotar explicitamente um SHA de referência e preservar as alterações locais como trabalho separado; não fazer reset/merge incidental.
2. Documentar integração, revisão, release/tag, rollback e responsáveis. Considerar a raiz Git com aplicação em `income-analytics/`.
3. Definir nomes estáveis dos checks que poderão se tornar obrigatórios; ativar a exigência depois de haver execução confiável, evitando um bloqueio sem check existente.
4. Definir segregação de evidência pública, privada e sintética antes de qualquer upload de artefato.

Aceite: política revisada e fontes identificáveis; nenhuma divergência silenciosa entre SHA testado e candidato. Não é obrigatório renomear branches ou adotar GitFlow completo.

## 2. CI automatizada

**Estado atual: MISSING para engenharia.** Evidências: ausência de `.github/workflows`, apenas Dependency Graph remoto, `.ai/workflows/dev-qa.md` textual.

Proposta de primeira CI:

- Trigger de PR e integração na branch aprovada; trabalhar no subdiretório correto.
- Provisionar Python 3.14 e versão de Node explicitamente suportada, inicialmente alinhada ao ambiente observado. Começar com runner compatível com o uso Windows; só declarar suporte Linux após validar `TEMP`, paths e testes.
- Revisar dependências declaradas e congelar um conjunto de CI reproduzível. Corrigir a lacuna Alembic/runtime em mudança própria; revisar `httpx2`, imports `httpx`/`requests` e ferramentas auxiliares.
- Executar Ruff sem autofix, mypy, testes Python e todos os `.mjs`, propagando qualquer exit code de falha. Tratar dívidas existentes explicitamente, sem alegar que checks focados aprovam o repositório todo.
- Garantir DB exclusivo por job, modo de testes, jobs externos desativados e nenhuma credencial/banco produtivo. Fixtures e testes determinísticos devem ser a base de PRs.
- Produzir relatórios de testes/cobertura e anexos sintéticos por allowlist; não publicar `.db`, estado de auth, dados financeiros ou diretórios inteiros de evidências locais.
- Separar em jobs/suítes os testes offline, o Auth Emulator e o teste cloud real. PRs não confiáveis não recebem secrets Admin; o teste live atual tem projeto específico e precisa de desenho antes de adoção.

Aceite: execução em checkout limpo, resultados vinculados ao commit, skips e falhas reportados, nenhuma dependência de credenciais locais. CI pode começar vermelha para expor a pendência financeira; não remover nem marcar o gate como aprovado artificialmente.

## 3. Reconciliação da certificação financeira

**Estado atual: BLOCKED.** Evidências: `test_shares_unit_020_frozen_engine`, `shares_unit_v1/manifest.json`, `CERT_48`, tabela de hashes do assessment.

Proposta:

1. Preservar manifest original, bytes, objetos Git e relatórios de referência.
2. Revisar de forma independente a proveniência da certificação e a semântica esperada do hash: bytes certificados, normalização autorizada ou baseline nova formalmente recertificada.
3. Demonstrar por que há expectativa CRLF em um arquivo e LF nos demais; configurar somente checkout não resolve todos.
4. Se qualquer alteração futura for necessária, fazê-la em escopo separado com autorização, revisão e regressões financeiras completas. Não atualizar hashes/expected só para obter verde, nem excluir o teste do gate de release.
5. Vincular a decisão e os resultados ao SHA candidato; manifests históricos de revisão anterior não certificam automaticamente a release nova.

Aceite: procedimento reproduzível, evidência independente, aprovação registrada e gate financeiro íntegro. Enquanto isso, a pipeline pode validar outros aspectos, mas promoção certificada de produção permanece bloqueada.

## 4. Build e empacotamento

**Estado atual: PARTIAL; runtime mínimo BLOCKED.** Evidências: setuptools declarado, Alembic dev-only, execução por fontes, dados/launcher externos.

Proposta:

1. Escolher empacotamento adequado ao alvo: wheel acompanhado de assets/migrations/runbook ou imagem de container. Não criar Docker apenas por convenção.
2. Provar instalação mínima de runtime sem depender das bibliotecas globais da máquina ou do extra de desenvolvimento.
3. Inspecionar artefato: HTML/CSS/JS/SVG, ECharts, migrations e recursos necessários. Separar dados privados e snapshots de referência do pacote de código, com provisão documentada e versionada quando adequada.
4. Definir migrações como ação controlada de release; impedir que o smoke/build acione auto-upgrade no banco errado.
5. Identificar release por versão + SHA + digest e gerar inventário/SBOM do artefato; definir retenção e verificação de integridade. Licença raiz vazia requer decisão para redistribuição.
6. Fazer smoke em instalação limpa com banco sintético. Falta de fontes externas deve produzir diagnóstico controlado, não dados inventados.

Aceite: mesmo artefato testado e promovível, nenhum secret no pacote e startup com dependências completas. Não assumir que setuptools inclui todos os assets sem inspecionar a saída.

## 5. CD para homologação

**Estado atual: MISSING como esteira/ambiente independente comprovado.** Evidências: GitHub Environments vazio, prévia local sem definição completa reproduzível.

Proposta:

- Definir destino acessível ao runner, conta de serviço mínima, origem autorizada e banco de homologação próprio.
- Usar identidades sintéticas/projeto segregado ou emulador apropriado; não copiar sessões ou credenciais de usuários de produção.
- Provisionar referências necessárias com dados de teste e licenças/quotas respeitadas.
- Promover o artefato da etapa 4, nunca reconstruir silenciosamente outro candidato durante deploy.
- Ensaiar schema em cópia e testar recuperação antes de manutenção real. Validar saldo/eventos com fixtures, FKs, ownership, dados ausentes e rejeições de autorização.
- Incluir navegação desktop/mobile, login/logout, operação sintética, cotações simuladas, histórico/paginação/exclusão e temas. Diferenciar Node/VM de navegador real.
- Medir tempos e consultas em cenário pareado. Readiness deve comprovar dependências locais fundamentais sem depender de disponibilidade de todos os fornecedores a cada probe.

Aceite: deploy/rollback repetível, E2E com evidência do artefato, estado isolado, nenhum efeito produtivo e critérios objetivos de promoção. A homologação pode validar partes antes da reconciliação financeira, mas não liberar produção certificada por isso.

## 6. Segurança e observabilidade

**Estado atual: PARTIAL.** Evidências: auth/CSRF/ownership existentes; secret scanning ativo; Dependabot updates desativado; logs/perf opcionais, health simples e backups específicos.

Proposta transversal:

- CI com permissões mínimas, dependências/actions revisadas e fixadas, revisão de cadeia de fornecimento, SAST/SCA e política explícita de severidade.
- Secrets e credenciais segregados por ambiente; preferir identidade de workload quando o alvo permitir. Manter ADC/service account fora de artefatos, logs e diretório estático. Documentar IAM/ACL/rotação e recuperação de acesso.
- Preservar verificação de revogação, CSRF, origem e ownership; não “otimizar” CD enfraquecendo auth.
- Logs estruturados sem dados sensíveis; retenção e acesso definidos; métricas de latência, erro, disco/DB, bloqueios de escrita e fornecedores.
- Definir alertas e responsáveis, probes de liveness/readiness, versão da release observável e critérios de rollback.
- Aprovar RPO/RTO e retenção; backup SQLite consistente e restauração periódica em destino isolado. Avaliar cópia fora do host e cifragem sem presumir que já existam.

Aceite: evidência de controles e alertas acionáveis, restore demonstrado e política de incidentes. Não confundir feature habilitada no GitHub com ausência de vulnerabilidades comprovada.

## 7. CD para produção

**Estado atual: MISSING como pipeline.** Há operação privada manual existente; este plano não autoriza deploy nesta fase.

Pré-condições propostas:

1. CI e homologação aprovadas no candidato exato; certificação financeira reconciliada, revisão de segurança e recuperação aprovadas.
2. Backup consistente antes de alteração e janela de manutenção definida quando houver schema/estado; plano de rollback de aplicação e dados compatível.
3. Promoção por Environment protegido/aprovação humana e execução de identidade mínima; controle de concorrência para impedir duas releases no mesmo banco.
4. Deploy do mesmo artefato/digest de homologação, com configuração produtiva segregada. Manter acesso Tailscale privado e signup fechado salvo decisão separada explícita.
5. Smoke/readiness de produção sem criar ou excluir lançamentos reais só para testar; observação inicial de erros e latência.
6. Registro de versão, schema, evidências de gates, aprovação, backup e resultado. Não restaurar um DB antigo automaticamente sobre escritas mais novas.

Aceite: implantação rastreável e recuperável, sem perda/alteração financeira indevida, com observação e decisão clara sobre rollback. O primeiro CD pode continuar exigindo aprovação humana; automação não implica publicação irrestrita.

## 8. Manutenção e acompanhamento

**Estado atual: UNKNOWN para rotina operacional completa.** Proposta: calendário de atualização/revisão de dependências, ensaios de recuperação, validação de quotas/licenças, revisão de permissões, orçamento de desempenho e métricas de falhas/tempo de recuperação de deploy. Cada rotina deve produzir evidência datada, sem inventar baseline nem sobrescrever manifests financeiros.

## Recorte recomendado do próximo PR5

Começar por **baseline + CI offline reproduzível**, com a pendência financeira visível e tratada separadamente, acompanhado da revisão de dependências. Não incluir no mesmo PR inicial mudança de regra financeira, troca de banco, abertura de cadastro, migração de produção ou migração para cloud. Build, homologação e produção avançam somente com seus próprios critérios de aceite e aprovação de escopo.
