# Issue 61 — diagnóstico e plano incremental

Requisitos oficiais: [Issue #61](https://github.com/tiagocaldironi/income-analytics/issues/61), descrição completa e comentários consultados em 02/11/2026. Sem comentários ou anexos visuais na issue. A implementação usa os componentes Income V2 existentes, sem reproduzir uma referência visual não disponível.

## Estado inicial e concorrência

- Baseline: `develop@b642709a8ea3e89ebc27e2ae3c9ccbf7d4bccde4`.
- Branch isolada: `codex/issue61-tesouro-direto`. Nenhuma alteração local foi transportada de outro checkout.
- Checkout principal: `codex/income-starter-guided-strategies`, com alterações de interface, operações, dashboard e persistência. Preservado integralmente.
- PR12: worktree `pr12-complete-closure`, com alterações não publicadas de tipagem e certificação. Preservado; não é baseline nem dependência desta implementação. Há sobreposição potencial de integração em `dashboard.py`, `portfolio_session.py`, `executable_contribution.py` e no ledger de qualidade. Resolver somente em revisão posterior autorizada.
- PR concorrente aberto #39: altera `b3_report_parser.py` e seus testes. Esses dois arquivos não foram modificados aqui; a importação reutiliza o parser existente e valida títulos no momento de aplicar o lote.
- Os workflows na raiz Git são `.github/workflows/ci-offline.yml` e `delivery-validation.yml`. O primeiro separa engenharia, certificação financeira e diagnósticos; o segundo valida entrega sem autorizar produção. Não foram alterados.
- As pendências de release já possuem issues próprias: [CERT_48 #57](https://github.com/tiagocaldironi/income-analytics/issues/57), [referências históricas #58](https://github.com/tiagocaldironi/income-analytics/issues/58) e [mypy #59](https://github.com/tiagocaldironi/income-analytics/issues/59). Não foram duplicadas ou encerradas.

## O que já existia

| Componente | Evidência | Lacuna relevante |
|---|---|---|
| Minha Carteira V2 | `src/income_analytics/api/static/js/features/portfolio.js` | Busca, filtros, ordenações explícitas, tabela responsiva e detalhes acessíveis já existiam. A ordenação inicial era por nome; a identidade principal mostrava ticker técnico. |
| Read model consolidado | `api/routers/dashboard.py::_build_portfolio_holdings` | Já preservava classe financeira, pesos, metas e métricas projetadas. Não tinha subgrupos visuais de Tesouro. |
| Taxonomia | `domain/enums/asset_type.py`, `domain/enums/fixed_income.py` | Já havia `TREASURY` e `TESOURO_DIRETO`. Não é necessário criar enum/classe financeira ou migrar ativos. |
| Quantidades e valores | `domain/value_objects/quantity.py`, `domain/entities/financial_event.py` | Já usam Decimal. Não é necessário modificar a multiplicação financeira nem os projetores certificados. |
| Cadastro bancário | `PortfolioSession.register_fixed_income_asset` | Cada aplicação começa com quantidade 1 e preço igual ao principal. Esse contrato **não equivale** a um título de Tesouro. |
| Compras/vendas | `PortfolioSession.register_trade` | Preserva Decimal, mas o fluxo de interface encaminhava toda renda fixa para aplicação/resgate por valor. |
| Importação B3 | `infrastructure/b3_report_parser.py`, `application/b3_import.py`, `dashboard.py::apply_b3_import` | Parser decimal, prévia, resolução explícita e aplicação transacional já existiam. Faltava validar incremento/valor financeiro e cobertura das vendas de títulos resolvidos. |
| Simulação | `application/executable_contribution.py`, `global_contribution_allocator.py` | Alocador global e regras por instrumento já existem. Não foram duplicados. Tesouro caía na exigência de termos bancários por valor. |
| Histórico | `get_asset_transactions`, `SqliteFinancialEventRepository` | Listagem e exclusão já existiam. Faltava edição de títulos com revisão auditável e proteção contra atualização obsoleta. |

## Plano apresentado antes das alterações

1. Separar apresentação de identidade financeira, mantendo `FIXED_INCOME` persistida e seus cálculos.
2. Expor taxonomia/nome/unidade explícitos; ordenar cada grupo por saldo em moeda-base, mantendo busca e escolha do usuário.
3. Acrescentar fronteiras decimais para operações, importação e simulação; proteger contratos legados contra conversão implícita.
4. Acrescentar edição versionada com rastreabilidade e isolamento por carteira.
5. Validar invariantes, regressões, interface e integridade dos 41 arquivos; publicar PR com limites e bloqueios, sem merge/deploy.

## Regra operacional e limites

Fonte oficial consultada: [Regras e regulamento do Tesouro Direto](https://tesourodireto.com.br/sobre-o-tesouro/regras-e-regulamento), aplicações tradicionais em múltiplos de 0,01 título. Não se presume mínimo financeiro fixo arbitrário, cotação ou condição de corretora verificada. Restrições adicionais informadas na simulação continuam sendo aplicadas.

Operações suportadas nesta etapa: títulos tradicionais Selic, IPCA+ e Prefixado identificados com vencimento, incluindo variantes com juros semestrais. RendA+ e Educa+ podem ser identificados visualmente, mas negociação permanece bloqueada: suas restrições específicas, incluindo carência, exigem tratamento próprio. Identificações desconhecidas usam fallback explícito.

Registrar movimentações históricas no Income não envia ordens ao Tesouro ou à corretora. Preços informados não são cotações inventadas pelo sistema. Quantidade × preço é preservada em Decimal; a comparação do valor bruto importado/informado ocorre em centavos com arredondamento HALF_UP. Custos não podem ser disfarçados como divergência de valor bruto.

## Dependência do motor congelado

Nenhuma alteração nos 41 arquivos imutáveis é necessária para os fluxos em unidades de título. O projetor histórico tolera certos débitos sem cobertura para extratos incompletos; essa regra permanece intacta. Uma validação de entrada específica de Tesouro rejeita vendas descobertas antes da projeção, inclusive quando uma edição retroativa invalidaria uma venda posterior.

Contratos legados permanecem em unidades de contrato, com preços identificados como tal e negociação de títulos bloqueada. Converter esses registros exige conciliar títulos, quantidade, preço unitário e principal com fontes independentes. Se essa conciliação exigir mudar convenções financeiras, deverá seguir certificação separada. Nenhuma conversão, recálculo de expectativa ou reescrita de histórico foi realizada para forçar compatibilidade.
