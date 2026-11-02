# PR5.1A — Plano incremental de estabilização

Data: 28/10/2026. Escopo exclusivamente diagnóstico; nenhuma correção de produto, teste, fixture, manifest, hash ou configuração produtiva integra esta entrega.

Referência financeira: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`. CI analisada: [run 40692226171](https://github.com/tiagocaldironi/income-analytics/actions/runs/40692226171), PR #48, head `1bbd2d42686ab0c893790772a05a7845cfbc0295`, checkout de merge sintético `3f81a9eb5a7d3ae0accc2ad98d0f3a1bcefb70cd`. Não confundir o SHA do head com o checkout efetivamente testado.

Caminhos citados são relativos à aplicação `income-analytics/` dentro da raiz Git. Linhas referem-se à baseline avaliada. Estimativas são de trabalho técnico, sem prazo de aprovação externa, e não devem ser somadas por diagnóstico em cascata.

## Decisão proposta

A infraestrutura offline expõe dívida com relatórios reproduzíveis, mas o produto ainda não tem evidência suficiente para certificar/promover release. **Não declarar CI verde nem aprovar release financeiro.** CERT_48 e divergência das fixtures de identidade permanecem bloqueadoras de certificação. Snapshots ausentes não se resolvem com credenciais ou bancos produtivos.

Merge de entrega estritamente documental/infraestrutura isolada pode receber análise separada do mantenedor: todos os checks vermelhos devem permanecer visíveis e eventual decisão explícita não equivale a certificação financeira. Não se propõe waiver automático, mudança de branch protection, novos skips, allowlist executável que ignore erros antigos ou conversão de job reprovado em sucesso.

## Bloqueadores e dívida

| Classe | Ocorrências / condição | Consequência proposta |
| --- | --- | --- |
| Bloqueador de merge de mudança funcional afetada | CODE-01; regressão nova de segurança/isolation/runtime; alteração financeira sem evidência independente | Corrigir/testar antes de merge no escopo afetado. Ausência de exploração não autoriza relaxar ownership/validações. |
| Bloqueador de CI integralmente verde | 22 ocorrências Python por fixture; FE-01; 130 Ruff e 674 mypy reportados | Checks seguem reprovados durante saneamento; dívida antiga não vira aprovação automática. Comparar relatórios para distinguir regressões sem esconder resultados. |
| Bloqueador de release/certificação | CERT_48 + PY-ID, proveniência de referências e contratos financeiros sem validação completa | Reconciliação independente e gates íntegros aprovados; EOL aparente, cobertura ou atualização de hash não certificam. |
| Dívida não bloqueadora de comportamento, isoladamente | R-STYLE, M-ANN/M-GEN e narrowing sem defeito runtime demonstrado | Priorizar por fronteira/risco; correções pequenas. Jobs atuais continuam vermelhos, mesmo sem defeito funcional comprovado em cada diagnóstico. |
| Lacuna de release SaaS | 4 skips Emulator e 1 live; Node sem browser real | Validar integração em ambiente segregado; não exigir credencial produtiva em PR offline. |

## Lotes propostos para PRs futuros

Estimativas se sobrepõem entre tipos/fixtures; não somar por diagnóstico. Papéis abaixo são responsáveis propostos, não autorização de merge. Todos os lotes exigem diff/revisão próprios.

| Ordem / lote | Responsável proposto | Ação e dependência | Esforço | Evidência de saída |
| --- | --- | --- | --- | --- |
| P0 — preservar evidências | Engenharia / mantenedor | Conservar run/SHA/ledgers; confirmar escopo isolado de cada PR, checks sem credenciais/banco real. Sem ativar proteção agora. | 0,5 dia | Resultados por SHA; isolamento/redação aprovados; nenhuma alteração financeira indevida. |
| P1 — rejeição CVM | Backend + revisor financeiro | Corrigir CODE-01 em PR pontual; testar ZIP/cabeçalho inválido e exceção esperada; sem mudar fórmulas. Independente da recuperação de referências. | 1–3h | Erro de domínio correto; entradas válidas e regressões preservadas; verificar ausência de persistência parcial quando aplicável. |
| P1 — contrato frontend | Frontend / produto | Alinhar duas asserções obsoletas ao contrato aprovado; manter XSS, sinais, nulos, zero, ordenação e ausência de mutação. | 1–3h | 30 suítes existentes + autoteste aprovados; valores renderizados preservados. |
| P1 — CERT_48 / identidade | Revisor independente de certificação | Inventariar bytes originais/cadeia de custódia, LF/CRLF/binários e decidir política formal. Nenhum hash alterado só para CI. | 1–3 dias técnicos; aprovação UNKNOWN | Parecer rastreável; teste frozen continua executado; pendência só encerra com evidência e decisão formal. |
| P2 — referências herméticas | Backend / responsável por dados públicos | Inventariar V8→V9→V9.2→V12.2/universo; recuperar fontes aprovadas e fixtures mínimas independentes em PR autorizado. Separar contrato sintético/replay público sem ocultar testes. | 3–8 dias + aprovações | 22 ocorrências resolvidas offline; sem arquivos pessoais; ID/digest/temporalidade/latest/empates reproduzidos; expectativas independentemente auditadas. |
| P2 — contratos de tipos nas fronteiras | Backend / segurança | DTO/Protocol em serialização, repositories e Firebase; verificar None/entrada externa antes de casts; começar por produtores. Depende de contratos testados. | 2–5 dias | Redução causal reportada; ownership/revogação/escape e rejeição de schema preservados; sem ignore global. |
| P3 — anotações/narrowing financeiro | Backend + revisor financeiro | M-ANN/M-GEN por lote; M-NULL/M-COMPAT com casos negativos; arquivos congelados só sob certificação. Não alterar fluxo de caixa nem preencher cotação ausente com zero. | 3–6 dias + revisão certificada | Redução por módulo; regressões financeiras e certificação para cada alteração financeira. |
| P3 — estilo | Engenharia | R-STYLE localizado; migrations só revisão estática, sem execução produtiva; separar formatação de função. | 1–2 dias | Ruff 130→0 sem exclusões globais e sem mudança comportamental/diff financeiro incidental. |
| P4 — consolidar gates | Mantenedor / QA | Após saneamento e execuções limpas, propor ativação gradual de checks em develop em etapa própria. | 0,5–1 dia | Duas ou mais execuções consecutivas reproduzíveis por SHA, nomes estáveis e skips explícitos. CERT pendente não vira aprovado. |

## Checks obrigatórios recomendados, sem ativação

Os rótulos abaixo são capacidades propostas, não novos jobs implementados. Consultar os nomes efetivos no workflow existente. A inspeção anterior não identificou proteção obrigatória/ruleset em develop; Actions vermelho sozinho não prova bloqueio de merge aplicado. Esta entrega não muda configurações GitHub.

| Gate / capacidade | Adequação ao PR offline | Pré-condição / política |
| --- | --- | --- |
| Instalação runtime lock/checkout limpo | Obrigatório após confirmar estabilidade; runtime atual passou | Python3.14/Node24; nenhum arquivo pessoal, chamada externa de produto ou credencial produtiva; pytest fora de runtime. |
| Infraestrutura de teste, SQLite, guardas de rede/redação | Obrigatório; guardas atuais aprovadas | TEMP canonicalizado e DB temporário; falha de isolamento nunca tratada como dívida tolerável. |
| Python determinístico e regressões financeiras | Obrigatório como objetivo; hoje reprovado/reportado | Referências independentes e integridade resolvidas; não selecionar só verdes e chamar de suíte completa. |
| Frontend Node completo + autoteste | Obrigatório após FE-01 revisado | Preservar contrato aprovado e segurança; não equivale a browser E2E. |
| Ruff/mypy completos | Obrigatórios após saneamento/estabilidade | Enquanto vermelhos, manter diagnóstico visível; sem exceção global, ignore_errors ou continue-on-error para mascarar. |
| CERT_48 / integridade de fixtures | Sempre executar/reportar; promoção bloqueada | Não dispensar frozen. Mudança financeira exige certificação, não apenas relatório informativo. |
| Cobertura | Informativa inicialmente | 80,69% não justifica meta arbitrária nem prova correção. Definir meta após avaliar caminhos críticos. |
| Firebase Emulator | Separado; obrigatório para mudanças de auth após ambiente comprovado | Projeto demo, sem produção; quatro skips atuais não cobertos; provedor determinístico não substitui integração. |
| Firebase cloud/live | Fora de PR offline; validação controlada de release SaaS | Ambiente segregado/autorizado; secrets indisponíveis a forks; skip não é aprovação. |

## CI, build, CD, segurança e observabilidade

- **CI:** estabilizar contratos/fixtures/tipos/estilo, reportar por SHA e manter falhas/skips. Offline significa execução de produto sem chamadas externas; aquisição inicial de dependências em registries permanece provisionamento do runner.
- **Build/empacotamento:** instalação limpa tem evidência runtime/lock. Build de artefato implantável imutável exige etapa própria; não presumir Docker/CD pelo planejamento.
- **CD homologação:** fora desta fase. Depende de artefato identificado, ambiente segregado, configuração/secrets, smoke tests e plano de dados/restauração aprovados.
- **CD produção:** fora desta fase e bloqueado pela certificação. Requer reconciliação independente, aprovação, rollback/restauração validados. Nenhum launcher/processo produtivo alterado.
- **Segurança/observabilidade:** reports sanitizados; erros de entrada externa sem payload; ownership/revogação com contratos tipados. Telemetria/alertas com redaction em etapa própria; nunca DB de carteira nos artifacts.

## Verificação das próximas entregas

Comandos relevantes da baseline: python -m ruff check ., python -m mypy src, python -m pytest, runner Node do workflow e execução dedicada de test_shares_unit_020_frozen_engine. Usar isolamento do workflow/dependências travadas; não apontar para banco produtivo. Os comandos completos e variáveis estão em `.github/workflows/` na raiz Git e runners CI versionados; não improvisar ignores.

Em cada PR: registrar head/checkout SHA, contagem antes/depois por perfil/módulo, aprovados/reprovados/skips, revisão financeira/segurança e ausência de alterações não autorizadas de evidências. Mudança de quantidade coletada exige justificativa. Redução estática sem teste comportamental não encerra hipótese runtime.

## Recomendação

Prosseguir com CODE-01 e FE-01 em correções pequenas, recuperar referências com auditoria e investigar CERT_48 independentemente desde o início. Depois reduzir dívida por fronteira/módulo, mantendo relatórios completos. Release financeiro continua bloqueado até certificação e validações independentes. Esta entrega altera apenas três documentos, **sem commit automático, merge, deploy, migration ou correção de código**.
