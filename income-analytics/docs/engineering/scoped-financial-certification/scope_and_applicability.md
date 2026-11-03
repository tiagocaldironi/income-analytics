# PR69 / PR62 — parecer de aplicabilidade financeira

Estado: **SUBMETIDO PARA REVISÃO; NÃO APROVADO FINANCEIRAMENTE**.

A solicitação do proprietário restringe a decisão deste release às funcionalidades
novas e suas dependências. Não constitui aprovação financeira independente do
CERT_48. Não há substituição de certificado, manifesto, hash ou expectativa.

## Fronteira do release

Baseline funcional: develop `b642709a8ea3e89ebc27e2ae3c9ccbf7d4bccde4`.
Implementação funcional: PR62 `eaae4df0f1f370bebd20d4299fd5e536de90d6f2`.
O PR69 incorpora esse head e acrescenta governança/CI; não promove duas vezes o PR62.
As mudanças desta certificação se limitam a CI, testes adicionais e documentação.

Incluídos: grupos de apresentação Tesouro/bancários; nomes e ordenação; entrada,
venda parcial, edição auditável e importação de títulos tradicionais; simulação
em centitítulos; projeção, custo médio, resultado, câmbio, fluxos, performance,
isolamento por carteira, persistência, reconstrução do snapshot e recuperação
descartável. A matriz de código alterado original está em
`../release-policy-65/impact_matrix.json`.

Excluídos funcionalmente: construir/publicar rankings Magic Formula; resolução de
capital social e preços de ações para esses rankings; recuperar referências
históricas ausentes; conversão de contratos legados para títulos; negociação
RendA+/Educa+ (#63); execução de ordens em corretora; nova fonte de preços;
homologação de uma carteira real; deploy ou restauração produtiva.

## Dependências efetivas e critérios de prova

| Fluxo | Caminho de cálculo/persistência | Evidência executável |
|---|---|---|
| Compra/venda/edição | `dashboard.create_treasury_trade/amend_treasury_trade` → `PortfolioSession.register_trade/amend_treasury_trade` → `treasury.validate_trade/validate_title_history` → entidades/effects/`PortfolioProjector` | `tests/api/test_treasury.py`, `tests/application/test_treasury.py`, `tests/infrastructure/test_treasury_revisions.py`, testes de domínio |
| Importação | `dashboard.apply_b3_import` → `B3ImportService`, parser decimal, resolução explícita de ativos, validação de títulos, transação SQLite | `tests/api/test_b3_import_contract.py`, `tests/application/test_b3_import_dedup.py`, parser e repositório de importação |
| Grupos/patrimônio | `_build_portfolio_holdings` → projeção e `base_currency_valuation`, apresentação aditiva; classe persistida FIXED_INCOME preservada | testes API e frontend Treasury; novo `test_scoped_treasury_certification.py` |
| Simulação | `build_executable_plan` → `allocate_quantities`, `ContributionTargetAllocator`, `HypotheticalPortfolioProjector` | testes executable/global allocator, domínio; orçamento/custos/frações/preço/FX/residual e ausência de escrita |
| TWR e fluxos compartilhados | `PortfolioSession.performance` → `PerformanceProjector`, eventos, cotações e FX com data | testes performance integrity, multicurrency, implicit opening, cash flows, reconstrução e portfolio return concepts |
| Persistência/revisões | SQLite por carteira, atualização otimista e histórico de revisões | treasury revisions, portfolio scope/owner, persistence reconstruction; staging/rollback já separado |

A seleção completa, independente de status PASS/FAIL, está em
`ci/scoped-financial-policy.json`. Inclui todos os testes de domínio e aceitação,
além dos módulos explícitos de API, aplicação e infraestrutura. O avaliador exige
ao menos um resultado por alvo, todas as dependências e funções enumeradas
efetivamente executadas, nenhum skip/falha/erro, inventário sem duplicatas e
integridade byte a byte dos 41 arquivos. Falta de teste/dependência bloqueia.

`ci/scoped_financial_trace.py` registra somente nomes de módulo/função; nenhum
argumento, valor ou dado pessoal. Classes, thunks de anotação do Python 3.14 e
builders dataclass aparecem separadamente em `import_definitions`. Chamadas aos
métodos financeiros, inclusive gerados quando usados, permanecem em
`dependency_calls`. O controle negativo comprova a distinção classe/método.

## CERT_48: argumento restrito de não aplicabilidade

O teste `test_shares_unit_020_frozen_engine` verifica identidade de bytes dos três
módulos `magic_formula_stocks.py`, `magic_formula_ranking_validation.py` e
`magic_formula_contract.py`. Eles calculam métricas EY/ROC, validam amostras de
ranking e resolvem elegibilidade/linhagem de evidências. Não são os projetores
genéricos de carteira ou TWR. A análise histórica da divergência LF/CRLF permanece
em `../financial-certification/cert48_provenance_analysis.md`; equivalência de
newline não é aprovação de procedência.

Há uma dependência de **importação**: `dashboard.py` importa
`magic_formula_canonical_ranking`, e o aplicativo também registra rotas Magic
Formula. Não se alega isolamento de módulos no pacote inteiro. Os caminhos
alterados de Tesouro, importação, holdings e simulação não chamam as funções de
ranking/QA/contrato, nem recebem seus resultados. As rotas de ranking são outras
funções (`magic_formula_stocks`, `magic_formula_stock_detail`, `magic_formula_fiis`).
`rebuild_portfolio_dashboard_snapshot` contém projeção, performance, holdings,
histórico e alocação; não chama essas rotas. A revisão de imports em
`portfolio_session.py`, `treasury.py`, `executable_contribution.py`,
`global_contribution_allocator.py` e projetores do domínio confirma a separação.

A instrumentação dos casos incluídos verifica esse argumento: execução de
qualquer função dos três módulos congelados torna o parecer técnico BLOCKED.
Definições importadas continuam visíveis. O teste de identidade de preço
`test_versioned_official_identity_and_price_recovery` usa fixtures de recuperação
de preço/identidade da Magic Formula; essas fixtures não são fonte de cotação dos
títulos. Os testes de importação e simulação usam preços explícitos/sintéticos e
validam ausência, defasagem e inconsistência sem inventar cotação.

**Conclusão proposta:** CERT_48 e as referências históricas listadas não são
pré-requisitos semânticos dos cálculos deste escopo. Isso não certifica Magic
Formula, não autoriza sua promoção e não resolve #57/#58. Um parecer independente
deve aprovar precisamente essa fronteira antes de retirar esses bloqueios da
decisão de release. Se concluir que o pacote compartilhado torna a dependência
aplicável, o release continua bloqueado ou deve ser reduzido formalmente.

## Histórico visível e dívida específica

Os 24 IDs exatos são preservados na política proposta com SHA de referência,
status, causa e issue individualmente rastreável: 22 referências em #58; duas
verificações de identidade em #57. A proveniência por caso também consta em
`candidate_python.json` e `comparison.json` de `release-policy-65`, e na matriz
`magic_formula_historical_cases.csv` de `financial-certification`.

Não se infere histórico por nome de arquivo ou por reprovação. Exige-se o mesmo ID,
status e causa observados no baseline PR62 (merge `bb2db51085ee3ca6c5d9eadbbd439dab0b31cf96`).
Uma resolução PASS é registrada; causa nova, erro novo, caso ausente ou falha fora
da lista bloqueiam o parecer. O job Financial abrangente e Full Python continuam
executados, com falhas/erros originais e conclusões originais. Nenhum xfail, skip,
mock financeiro ou exclusão global foi introduzido.

## Limites da evidência

Testes e rastreamento são amostras finitas, não prova formal de todos os inputs,
threads, plugins ou configurações de produção. A revisão estática e as fronteiras
operacionais complementam o rastreamento. O profiler cobre o processo principal
dos testes e os workers criados após a instalação do hook (incluindo as rotas
síncronas FastAPI); jobs externos permanecem desabilitados. Esses jobs não são certificados.
A confirmação de 41 hashes prova preservação, não acurácia financeira original.
Os exemplos independentes são sintéticos e não substituem conciliação de carteira
real ou dados oficiais de corretora. Aprovação local não substitui CI hospedada.

Não há chave de aprovação neste avaliador. Sua decisão financeira é NO_GO até
revisão externa e implementação revisada da ativação; Engineering/Security e o
procedimento de promoção continuam requisitos separados. Falhas históricas não
são mais problemas a corrigir nesta execução: são propostas documentadas de
exclusão do gate decisório, pendentes da aprovação exigida.
