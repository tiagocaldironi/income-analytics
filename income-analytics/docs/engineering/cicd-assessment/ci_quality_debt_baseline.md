# PR5.1A — Baseline da dívida de qualidade

Data: 28/10/2026. Escopo exclusivamente diagnóstico; nenhuma correção de produto, teste, fixture, manifest, hash ou configuração produtiva integra esta entrega.

Referência financeira: `develop@ca627ac72f110d0f4d62faaa9c51a08eaed54965`. CI analisada: [run 40692226171](https://github.com/tiagocaldironi/income-analytics/actions/runs/40692226171), PR #48, head `1bbd2d42686ab0c893790772a05a7845cfbc0295`, checkout de merge sintético `3f81a9eb5a7d3ae0accc2ad98d0f3a1bcefb70cd`. Não confundir o SHA do head com o checkout efetivamente testado.

Caminhos citados são relativos à aplicação `income-analytics/` dentro da raiz Git. Linhas referem-se à baseline avaliada. Estimativas são de trabalho técnico, sem prazo de aprovação externa, e não devem ser somadas por diagnóstico em cascata.

## Método e leitura do ledger

Fonte de contagem: `findings` dos artefatos Ruff/mypy do run. Cada ocorrência tem ID próprio, inclusive repetições na mesma linha/regra. Mensagens completas foram associadas por multiconjunto aos logs locais equivalentes; igualdade exata verificada. Não são mensagens extraídas dos artefatos sanitizados, que omitem payloads.

Cada linha herda causa-raiz, categoria, criticidade, tratamento e esforço do perfil indicado. Mensagem e arquivo:linha são evidência específica. O perfil descreve causa estática; impacto runtime só é comprovado no CODE-01. Demais suspeitas funcionais permanecem hipóteses. Esforço é por lote causal, nunca por linha. Código certificado precisa de revisão e regressões mesmo em mudanças de anotação.

## Ruff — 130 ocorrências, 15 módulos

| Regra | Quantidade | Causa comprovada |
| --- | --- | --- |
| E501 | 76 | Linha acima do limite configurado |
| E701 | 21 | Instruções após dois-pontos na mesma linha |
| E702 | 20 | Instruções separadas por ponto e vírgula |
| I001 | 13 | Imports fora da ordenação configurada |

**R-STYLE** — categoria estilo; criticidade baixa; tratamento: imports/formatação localizados, revisão do diff sem mudança comportamental; esforço 1–2 dias para os 15 módulos. Não aplicar correção global a migrations/código financeiro sem revisão. Este conjunto não contém diagnósticos F de nomes/uso; isso não atesta segurança dos módulos.

| Módulo | Total | Regras / quantidades |
| --- | --- | --- |
| src/income_analytics/api/onboarding_v2.py | 47 | E501=16; E701=19; E702=11; I001=1 |
| tests/security/test_firebase_authorization.py | 29 | E501=19; E702=7; I001=3 |
| scripts/rematerialize_magic_formula_v2.py | 17 | E501=16; I001=1 |
| tests/infrastructure/test_onboarding_v2_migration.py | 8 | E501=5; E701=1; E702=2 |
| alembic/versions/0009_pension_real_estate_classes.py | 6 | E501=5; I001=1 |
| alembic/versions/0027_contextual_onboarding_v2.py | 5 | E501=3; E701=1; I001=1 |
| alembic/versions/0012_pension_market_data.py | 4 | E501=3; I001=1 |
| alembic/versions/0014_b3_import_audit.py | 3 | E501=2; I001=1 |
| src/income_analytics/infrastructure/models.py | 3 | E501=3 |
| alembic/versions/0015_magic_formula_fundamentals_snapshots.py | 2 | E501=1; I001=1 |
| src/income_analytics/api/routers/portfolios.py | 2 | E501=2 |
| alembic/versions/0008_paid_income_brapi.py | 1 | I001=1 |
| alembic/versions/0010_portfolio_dashboard_snapshot.py | 1 | I001=1 |
| alembic/versions/0013_capital_flow_classification.py | 1 | I001=1 |
| src/income_analytics/api/routers/dashboard.py | 1 | E501=1 |

### Ledger Ruff

| ID | Arquivo:linha | Regra | Mensagem | Perfil |
| --- | --- | --- | --- | --- |
| R001 | alembic/versions/0008_paid_income_brapi.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R002 | alembic/versions/0009_pension_real_estate_classes.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R003 | alembic/versions/0009_pension_real_estate_classes.py:13 | E501 | Line too long (110 > 100) | R-STYLE |
| R004 | alembic/versions/0009_pension_real_estate_classes.py:16 | E501 | Line too long (108 > 100) | R-STYLE |
| R005 | alembic/versions/0009_pension_real_estate_classes.py:18 | E501 | Line too long (118 > 100) | R-STYLE |
| R006 | alembic/versions/0009_pension_real_estate_classes.py:20 | E501 | Line too long (132 > 100) | R-STYLE |
| R007 | alembic/versions/0009_pension_real_estate_classes.py:26 | E501 | Line too long (105 > 100) | R-STYLE |
| R008 | alembic/versions/0010_portfolio_dashboard_snapshot.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R009 | alembic/versions/0012_pension_market_data.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R010 | alembic/versions/0012_pension_market_data.py:25 | E501 | Line too long (112 > 100) | R-STYLE |
| R011 | alembic/versions/0012_pension_market_data.py:26 | E501 | Line too long (114 > 100) | R-STYLE |
| R012 | alembic/versions/0012_pension_market_data.py:27 | E501 | Line too long (130 > 100) | R-STYLE |
| R013 | alembic/versions/0013_capital_flow_classification.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R014 | alembic/versions/0014_b3_import_audit.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R015 | alembic/versions/0014_b3_import_audit.py:34 | E501 | Line too long (112 > 100) | R-STYLE |
| R016 | alembic/versions/0014_b3_import_audit.py:56 | E501 | Line too long (112 > 100) | R-STYLE |
| R017 | alembic/versions/0015_magic_formula_fundamentals_snapshots.py:3 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R018 | alembic/versions/0015_magic_formula_fundamentals_snapshots.py:27 | E501 | Line too long (155 > 100) | R-STYLE |
| R019 | alembic/versions/0027_contextual_onboarding_v2.py:2 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R020 | alembic/versions/0027_contextual_onboarding_v2.py:11 | E501 | Line too long (907 > 100) | R-STYLE |
| R021 | alembic/versions/0027_contextual_onboarding_v2.py:15 | E501 | Line too long (315 > 100) | R-STYLE |
| R022 | alembic/versions/0027_contextual_onboarding_v2.py:21 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R023 | alembic/versions/0027_contextual_onboarding_v2.py:21 | E501 | Line too long (114 > 100) | R-STYLE |
| R024 | scripts/rematerialize_magic_formula_v2.py:2 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R025 | scripts/rematerialize_magic_formula_v2.py:5 | E501 | Line too long (112 > 100) | R-STYLE |
| R026 | scripts/rematerialize_magic_formula_v2.py:6 | E501 | Line too long (111 > 100) | R-STYLE |
| R027 | scripts/rematerialize_magic_formula_v2.py:7 | E501 | Line too long (102 > 100) | R-STYLE |
| R028 | scripts/rematerialize_magic_formula_v2.py:8 | E501 | Line too long (112 > 100) | R-STYLE |
| R029 | scripts/rematerialize_magic_formula_v2.py:9 | E501 | Line too long (191 > 100) | R-STYLE |
| R030 | scripts/rematerialize_magic_formula_v2.py:13 | E501 | Line too long (114 > 100) | R-STYLE |
| R031 | scripts/rematerialize_magic_formula_v2.py:16 | E501 | Line too long (286 > 100) | R-STYLE |
| R032 | scripts/rematerialize_magic_formula_v2.py:25 | E501 | Line too long (130 > 100) | R-STYLE |
| R033 | scripts/rematerialize_magic_formula_v2.py:27 | E501 | Line too long (142 > 100) | R-STYLE |
| R034 | scripts/rematerialize_magic_formula_v2.py:29 | E501 | Line too long (138 > 100) | R-STYLE |
| R035 | scripts/rematerialize_magic_formula_v2.py:32 | E501 | Line too long (260 > 100) | R-STYLE |
| R036 | scripts/rematerialize_magic_formula_v2.py:34 | E501 | Line too long (139 > 100) | R-STYLE |
| R037 | scripts/rematerialize_magic_formula_v2.py:40 | E501 | Line too long (139 > 100) | R-STYLE |
| R038 | scripts/rematerialize_magic_formula_v2.py:43 | E501 | Line too long (156 > 100) | R-STYLE |
| R039 | scripts/rematerialize_magic_formula_v2.py:44 | E501 | Line too long (227 > 100) | R-STYLE |
| R040 | scripts/rematerialize_magic_formula_v2.py:45 | E501 | Line too long (280 > 100) | R-STYLE |
| R041 | src/income_analytics/api/onboarding_v2.py:2 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R042 | src/income_analytics/api/onboarding_v2.py:9 | E501 | Line too long (253 > 100) | R-STYLE |
| R043 | src/income_analytics/api/onboarding_v2.py:11 | E501 | Line too long (342 > 100) | R-STYLE |
| R044 | src/income_analytics/api/onboarding_v2.py:15 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R045 | src/income_analytics/api/onboarding_v2.py:16 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R046 | src/income_analytics/api/onboarding_v2.py:21 | E501 | Line too long (153 > 100) | R-STYLE |
| R047 | src/income_analytics/api/onboarding_v2.py:22 | E501 | Line too long (183 > 100) | R-STYLE |
| R048 | src/income_analytics/api/onboarding_v2.py:24 | E501 | Line too long (182 > 100) | R-STYLE |
| R049 | src/income_analytics/api/onboarding_v2.py:24 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R050 | src/income_analytics/api/onboarding_v2.py:26 | E501 | Line too long (216 > 100) | R-STYLE |
| R051 | src/income_analytics/api/onboarding_v2.py:26 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R052 | src/income_analytics/api/onboarding_v2.py:27 | E501 | Line too long (130 > 100) | R-STYLE |
| R053 | src/income_analytics/api/onboarding_v2.py:33 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R054 | src/income_analytics/api/onboarding_v2.py:33 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R055 | src/income_analytics/api/onboarding_v2.py:37 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R056 | src/income_analytics/api/onboarding_v2.py:38 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R057 | src/income_analytics/api/onboarding_v2.py:39 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R058 | src/income_analytics/api/onboarding_v2.py:41 | E501 | Line too long (1093 > 100) | R-STYLE |
| R059 | src/income_analytics/api/onboarding_v2.py:44 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R060 | src/income_analytics/api/onboarding_v2.py:50 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R061 | src/income_analytics/api/onboarding_v2.py:54 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R062 | src/income_analytics/api/onboarding_v2.py:56 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R063 | src/income_analytics/api/onboarding_v2.py:56 | E501 | Line too long (119 > 100) | R-STYLE |
| R064 | src/income_analytics/api/onboarding_v2.py:57 | E501 | Line too long (217 > 100) | R-STYLE |
| R065 | src/income_analytics/api/onboarding_v2.py:58 | E501 | Line too long (168 > 100) | R-STYLE |
| R066 | src/income_analytics/api/onboarding_v2.py:61 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R067 | src/income_analytics/api/onboarding_v2.py:63 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R068 | src/income_analytics/api/onboarding_v2.py:63 | E501 | Line too long (110 > 100) | R-STYLE |
| R069 | src/income_analytics/api/onboarding_v2.py:64 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R070 | src/income_analytics/api/onboarding_v2.py:67 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R071 | src/income_analytics/api/onboarding_v2.py:67 | E501 | Line too long (113 > 100) | R-STYLE |
| R072 | src/income_analytics/api/onboarding_v2.py:68 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R073 | src/income_analytics/api/onboarding_v2.py:71 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R074 | src/income_analytics/api/onboarding_v2.py:71 | E501 | Line too long (127 > 100) | R-STYLE |
| R075 | src/income_analytics/api/onboarding_v2.py:72 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R076 | src/income_analytics/api/onboarding_v2.py:72 | E501 | Line too long (207 > 100) | R-STYLE |
| R077 | src/income_analytics/api/onboarding_v2.py:72 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R078 | src/income_analytics/api/onboarding_v2.py:72 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R079 | src/income_analytics/api/onboarding_v2.py:72 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R080 | src/income_analytics/api/onboarding_v2.py:73 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R081 | src/income_analytics/api/onboarding_v2.py:76 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R082 | src/income_analytics/api/onboarding_v2.py:77 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R083 | src/income_analytics/api/onboarding_v2.py:78 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R084 | src/income_analytics/api/onboarding_v2.py:80 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R085 | src/income_analytics/api/onboarding_v2.py:81 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R086 | src/income_analytics/api/onboarding_v2.py:81 | E501 | Line too long (124 > 100) | R-STYLE |
| R087 | src/income_analytics/api/onboarding_v2.py:86 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R088 | src/income_analytics/api/routers/dashboard.py:607 | E501 | Line too long (108 > 100) | R-STYLE |
| R089 | src/income_analytics/api/routers/portfolios.py:240 | E501 | Line too long (119 > 100) | R-STYLE |
| R090 | src/income_analytics/api/routers/portfolios.py:260 | E501 | Line too long (113 > 100) | R-STYLE |
| R091 | src/income_analytics/infrastructure/models.py:721 | E501 | Line too long (204 > 100) | R-STYLE |
| R092 | src/income_analytics/infrastructure/models.py:723 | E501 | Line too long (112 > 100) | R-STYLE |
| R093 | src/income_analytics/infrastructure/models.py:739 | E501 | Line too long (112 > 100) | R-STYLE |
| R094 | tests/infrastructure/test_onboarding_v2_migration.py:11 | E501 | Line too long (117 > 100) | R-STYLE |
| R095 | tests/infrastructure/test_onboarding_v2_migration.py:12 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R096 | tests/infrastructure/test_onboarding_v2_migration.py:15 | E501 | Line too long (155 > 100) | R-STYLE |
| R097 | tests/infrastructure/test_onboarding_v2_migration.py:16 | E501 | Line too long (122 > 100) | R-STYLE |
| R098 | tests/infrastructure/test_onboarding_v2_migration.py:18 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R099 | tests/infrastructure/test_onboarding_v2_migration.py:22 | E501 | Line too long (120 > 100) | R-STYLE |
| R100 | tests/infrastructure/test_onboarding_v2_migration.py:23 | E701 | Multiple statements on one line (colon) | R-STYLE |
| R101 | tests/infrastructure/test_onboarding_v2_migration.py:23 | E501 | Line too long (107 > 100) | R-STYLE |
| R102 | tests/security/test_firebase_authorization.py:420 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R103 | tests/security/test_firebase_authorization.py:421 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R104 | tests/security/test_firebase_authorization.py:421 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R105 | tests/security/test_firebase_authorization.py:428 | E501 | Line too long (104 > 100) | R-STYLE |
| R106 | tests/security/test_firebase_authorization.py:429 | E501 | Line too long (103 > 100) | R-STYLE |
| R107 | tests/security/test_firebase_authorization.py:449 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R108 | tests/security/test_firebase_authorization.py:452 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R109 | tests/security/test_firebase_authorization.py:452 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R110 | tests/security/test_firebase_authorization.py:463 | E501 | Line too long (155 > 100) | R-STYLE |
| R111 | tests/security/test_firebase_authorization.py:473 | E501 | Line too long (192 > 100) | R-STYLE |
| R112 | tests/security/test_firebase_authorization.py:474 | E501 | Line too long (194 > 100) | R-STYLE |
| R113 | tests/security/test_firebase_authorization.py:476 | E501 | Line too long (103 > 100) | R-STYLE |
| R114 | tests/security/test_firebase_authorization.py:485 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R115 | tests/security/test_firebase_authorization.py:485 | E702 | Multiple statements on one line (semicolon) | R-STYLE |
| R116 | tests/security/test_firebase_authorization.py:487 | E501 | Line too long (102 > 100) | R-STYLE |
| R117 | tests/security/test_firebase_authorization.py:500 | E501 | Line too long (104 > 100) | R-STYLE |
| R118 | tests/security/test_firebase_authorization.py:501 | E501 | Line too long (112 > 100) | R-STYLE |
| R119 | tests/security/test_firebase_authorization.py:512 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R120 | tests/security/test_firebase_authorization.py:522 | E501 | Line too long (157 > 100) | R-STYLE |
| R121 | tests/security/test_firebase_authorization.py:523 | E501 | Line too long (122 > 100) | R-STYLE |
| R122 | tests/security/test_firebase_authorization.py:524 | E501 | Line too long (139 > 100) | R-STYLE |
| R123 | tests/security/test_firebase_authorization.py:555 | I001 | Import block is un-sorted or un-formatted | R-STYLE |
| R124 | tests/security/test_firebase_authorization.py:557 | E501 | Line too long (103 > 100) | R-STYLE |
| R125 | tests/security/test_firebase_authorization.py:563 | E501 | Line too long (127 > 100) | R-STYLE |
| R126 | tests/security/test_firebase_authorization.py:564 | E501 | Line too long (143 > 100) | R-STYLE |
| R127 | tests/security/test_firebase_authorization.py:568 | E501 | Line too long (115 > 100) | R-STYLE |
| R128 | tests/security/test_firebase_authorization.py:569 | E501 | Line too long (205 > 100) | R-STYLE |
| R129 | tests/security/test_firebase_authorization.py:574 | E501 | Line too long (120 > 100) | R-STYLE |
| R130 | tests/security/test_firebase_authorization.py:577 | E501 | Line too long (119 > 100) | R-STYLE |

## Mypy — 674 ocorrências, 54 módulos

**385** são funções/chamadas sem anotação (158+227), cerca de 57,1%. Somadas a genéricos, variáveis sem tipo e retornos Any, são 480; os outros 194 exigem análise de compatibilidade/narrowing/atributos. Não equivalem a 674 defeitos funcionais independentes. Não substituir contratos por Any/casts indiscriminados nem ignorar globalmente erros.

| Regra | Quantidade |
| --- | --- |
| no-untyped-call | 227 |
| no-untyped-def | 158 |
| type-arg | 65 |
| attr-defined | 52 |
| union-attr | 46 |
| arg-type | 34 |
| operator | 30 |
| no-any-return | 18 |
| assignment | 15 |
| var-annotated | 12 |
| return-value | 5 |
| index | 4 |
| type-var | 3 |
| misc | 2 |
| dict-item | 1 |
| import-untyped | 1 |
| no-redef | 1 |

### Perfis causais por ocorrência

| Perfil | Causa / certeza | Categoria | Criticidade | Tratamento | Esforço compartilhado |
| --- | --- | --- | --- | --- | --- |
| M-ANN | Função/chamada sem contrato estático; cascata de diagnóstico comprovada; impacto runtime não demonstrado. | tipagem | média | Anotar entradas/saídas reais, começando por produtores; preservar contratos e regressões. | 3–6 dias/lote |
| M-GEN | Coleções/variáveis sem parâmetros suficientes ou retorno Any; schema estático incompleto. | tipagem | média | Tipos concretos, TypedDict/dataclasses/Protocol e containers; não Any global. | 2–4 dias/lote |
| M-NULL | Operação/indexação/atributo sobre união/Optional sem refinamento. Validação ausente ou limite de inferência: runtime ainda hipótese. | tipagem | alta | Verificar ausência/entrada inválida e bindings após guard; preservar semântica financeira. | 2–5 dias/lote + revisão financeira |
| M-SHAPE | Objeto genérico/atributo/export não exposto no contrato estático; defeito runtime não provado salvo CODE-01. | tipagem | média | Definir DTO/Protocol/export explícito; confrontar campos reais. | 2–4 dias/lote |
| M-COMPAT | Assinatura/atribuição/retorno/container incompatível; schema inferido ou defeito real ainda não provado. | tipagem | alta | Rastrear produtor/consumidor, unidades e casos-limite; sem casts para aprovação artificial. | 2–5 dias/lote |
| M-REDEF | Nome anotado novamente no mesmo escopo; não prova cálculo duplicado. | tipagem | baixa | Anotação única/nomes distintos após revisão dos fluxos. | 1–2h |
| M-SDK | firebase_admin instalado sem contrato completo de tipos; import-untyped/herança Any. Não é credencial ausente. | tipagem | média | Fachada tipada/Protocol e stub revisado no limite SDK; preservar revogação/ownership. | 0,5–1 dia |
| CODE-01 | Parser CVM usa self.code inexistente na rejeição de schema; AttributeError confirmado em memória. | código | alta | Corrigir exceção em PR próprio, teste negativo e integração; não alterar cálculos. | 1–3h |

### Evidências e hipóteses de runtime

- `application/magic_formula_stocks.py:42–58`: any sobre tupla de valores Optional retorna cedo, mas não refina os atributos originais no mypy. Não presumir erro numérico nem editar motor congelado nesta fase.
- `domain/projectors/asset_composition_projector.py:75`: filtro target_weight não refina atributos do item; current_weight também é Optional no contrato. Verificar invariantes antes de alterar fórmulas.
- `infrastructure/b3_xlsx_import.py:40–48`: guard None in conjunto de colunas não refina cada variável. Preservar rejeição de cabeçalhos inválidos.
- `infrastructure/cvm_capital_structure.py:114–125`: multiplicador Optional já passa por validação de unidades; compreensão não refina atributo. Não inventar multiplicador ausente.
- `application/magic_formula_price_blocker_batch.py:234`: statuses é reutilizado para lista e depois dict; .values recebe dict nesse trecho. Diagnóstico não comprova chamada sobre lista em runtime.
- `domain/projectors/performance_projector.py:575–589`: duas anotações funding_by_currency em ramos com retorno antecipado; não comprova duplicação de fluxo de caixa.
- `application/executable_contribution.py:257,428`: quote/reference_date e diagnostics heterogêneo perdem precisão. Verificar ausência/staleness e schema; nunca usar preço zero para satisfazer tipo.
- `api/routers/dashboard.py:2450+`: serializer recebe object/tuple[object,...] e acessa campos de registros; dezenas de erros compartilham perda de estrutura. Revisar campos/sanitização ao definir DTO.
- `infrastructure/sqlite_repositories.py:1112–1114`: modelos distintos inferem base comum sem campos compartilhados expostos. Candidato: Protocol/helper específico, não cast universal.
- `application/magic_formula_contract.py` e consumidores: ADAPTER_VERSION importado de stocks sofre contrato de reexport implícito; diagnóstico não nega sua existência runtime.
- `infrastructure/firebase_identity.py:10,21`: ausência de py.typed/stub e Base Any. Não habilitar credenciais cloud nem ignorar todo SDK.
- `application/wealth_explanation.py`: dicionários heterogêneos/dict[str,object] propagam uniões para operadores/ordenação; runtime permanece hipótese até validar DTO/unidades.
- `infrastructure/cvm_historical_shares_document.py`: Element.find/findtext pode retornar None antes de conversão numérica/data; risco de entrada malformada não reproduzido nesta fase.
- `infrastructure/cvm_fundamentals_data.py:59`: CODE-01 confirmado, reprodução descrita na triagem. Exceção explícita aos attr-defined sem defeito demonstrado.

Auth/saas_security/firebase/upload_safety merecem revisão de segurança mesmo com perfil estático médio. Arquivos financeiros/congelados exigem regressão e certificação; perfil não autoriza mudança financeira.

### Agrupamento por módulo e regra

| Módulo | Total | Regras / quantidades |
| --- | --- | --- |
| src/income_analytics/api/routers/dashboard.py | 82 | arg-type=7; assignment=3; attr-defined=39; dict-item=1; index=2; misc=1; no-any-return=6; no-untyped-call=8; no-untyped-def=4; return-value=1; union-attr=9; var-annotated=1 |
| src/income_analytics/application/magic_formula_formal_qa.py | 51 | no-untyped-call=37; no-untyped-def=12; type-arg=1; var-annotated=1 |
| src/income_analytics/infrastructure/magic_formula_raw_verification.py | 46 | no-untyped-call=39; no-untyped-def=6; var-annotated=1 |
| src/income_analytics/application/historical_security_identity.py | 39 | no-untyped-call=34; no-untyped-def=5 |
| src/income_analytics/api/onboarding_v2.py | 37 | no-untyped-call=13; no-untyped-def=6; union-attr=18 |
| src/income_analytics/application/magic_formula_universe.py | 31 | index=1; no-untyped-call=20; no-untyped-def=9; var-annotated=1 |
| src/income_analytics/application/executable_contribution.py | 26 | attr-defined=1; no-untyped-call=8; no-untyped-def=9; operator=1; union-attr=6; var-annotated=1 |
| src/income_analytics/application/wealth_explanation.py | 24 | arg-type=2; attr-defined=4; no-untyped-call=4; no-untyped-def=4; operator=7; return-value=2; type-var=1 |
| src/income_analytics/infrastructure/sqlite_repositories.py | 24 | arg-type=8; attr-defined=3; no-any-return=3; no-untyped-call=3; no-untyped-def=6; var-annotated=1 |
| src/income_analytics/application/global_contribution_allocator.py | 23 | no-untyped-call=10; no-untyped-def=8; type-arg=3; var-annotated=2 |
| src/income_analytics/application/magic_formula_investable_universe.py | 19 | assignment=6; type-arg=13 |
| src/income_analytics/api/routers/auth.py | 18 | no-untyped-call=7; no-untyped-def=11 |
| src/income_analytics/application/magic_formula_stocks.py | 17 | arg-type=1; no-untyped-call=1; no-untyped-def=1; operator=10; type-arg=3; var-annotated=1 |
| src/income_analytics/application/income_starter.py | 16 | no-any-return=1; no-untyped-call=8; no-untyped-def=7 |
| src/income_analytics/application/magic_formula_ranking_validation.py | 16 | attr-defined=1; no-untyped-call=8; no-untyped-def=7 |
| src/income_analytics/application/magic_formula_eligibility_policy_v7.py | 15 | no-untyped-def=3; operator=4; type-arg=8 |
| src/income_analytics/infrastructure/cvm_historical_shares_document.py | 15 | arg-type=5; index=1; no-untyped-def=1; union-attr=8 |
| src/income_analytics/application/magic_formula_price_blocker_batch.py | 13 | assignment=1; attr-defined=1; no-untyped-call=7; no-untyped-def=4 |
| src/income_analytics/infrastructure/firebase_identity.py | 12 | import-untyped=1; misc=1; no-any-return=4; no-untyped-call=1; no-untyped-def=2; type-arg=3 |
| src/income_analytics/infrastructure/magic_formula_ranking_repository.py | 12 | no-untyped-call=6; no-untyped-def=6 |
| src/income_analytics/api/routers/portfolios.py | 11 | no-untyped-call=2; no-untyped-def=4; union-attr=5 |
| src/income_analytics/main.py | 9 | no-untyped-call=3; no-untyped-def=5; operator=1 |
| src/income_analytics/api/saas_security.py | 8 | no-untyped-call=3; no-untyped-def=5 |
| src/income_analytics/infrastructure/magic_formula_universe_repository.py | 8 | no-untyped-call=3; no-untyped-def=5 |
| src/income_analytics/application/magic_formula_price_availability_audit.py | 7 | type-arg=7 |
| src/income_analytics/application/magic_formula_screening.py | 7 | type-arg=7 |
| src/income_analytics/infrastructure/auth_repository.py | 7 | assignment=1; no-untyped-def=5; type-arg=1 |
| src/income_analytics/infrastructure/magic_formula_contract_repository.py | 7 | attr-defined=1; no-any-return=1; no-untyped-def=2; type-arg=3 |
| src/income_analytics/infrastructure/magic_formula_historical_price_sources.py | 7 | type-arg=6; var-annotated=1 |
| src/income_analytics/application/magic_formula_contract.py | 6 | type-arg=6 |
| src/income_analytics/application/paid_income.py | 5 | no-untyped-def=5 |
| src/income_analytics/application/portfolio_session.py | 5 | arg-type=3; assignment=1; return-value=1 |
| src/income_analytics/infrastructure/b3_xlsx_import.py | 5 | arg-type=5 |
| src/income_analytics/infrastructure/magic_formula_universe_sources.py | 5 | no-untyped-def=5 |
| src/income_analytics/application/historical_price.py | 4 | no-untyped-def=2; var-annotated=2 |
| src/income_analytics/application/historical_shares_units.py | 4 | no-untyped-call=1; no-untyped-def=3 |
| src/income_analytics/application/magic_formula_preview.py | 4 | no-untyped-call=1; type-arg=3 |
| src/income_analytics/application/cvm_magic_formula_normalization.py | 3 | arg-type=1; assignment=1; type-var=1 |
| src/income_analytics/application/magic_formula_canonical_ranking.py | 3 | no-any-return=3 |
| src/income_analytics/application/magic_formula_golden_evidence_builder.py | 3 | attr-defined=1; operator=1; type-arg=1 |
| src/income_analytics/domain/projectors/asset_composition_projector.py | 3 | operator=3 |
| src/income_analytics/domain/projectors/performance_projector.py | 3 | assignment=1; no-redef=1; operator=1 |
| src/income_analytics/application/issuer_market_cap.py | 2 | return-value=1; type-var=1 |
| src/income_analytics/application/magic_formula_activation_gate.py | 2 | no-untyped-def=2 |
| src/income_analytics/api/routers/income_starter.py | 1 | arg-type=1 |
| src/income_analytics/application/b3_import.py | 1 | arg-type=1 |
| src/income_analytics/application/magic_formula_accounting_evidence.py | 1 | assignment=1 |
| src/income_analytics/infrastructure/cvm_capital_structure.py | 1 | operator=1 |
| src/income_analytics/infrastructure/cvm_fundamentals_data.py | 1 | attr-defined=1 |
| src/income_analytics/infrastructure/database.py | 1 | no-untyped-def=1 |
| src/income_analytics/infrastructure/historical_price_audit_source.py | 1 | no-untyped-def=1 |
| src/income_analytics/infrastructure/irpf_xlsx_import.py | 1 | operator=1 |
| src/income_analytics/infrastructure/magic_formula_snapshot_repository.py | 1 | no-untyped-def=1 |
| src/income_analytics/infrastructure/upload_safety.py | 1 | no-untyped-def=1 |

### Ledger mypy

| ID | Arquivo:linha | Regra | Mensagem | Perfil |
| --- | --- | --- | --- | --- |
| M0001 | src/income_analytics/infrastructure/upload_safety.py:7 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0002 | src/income_analytics/domain/projectors/asset_composition_projector.py:75 | operator | Unsupported operand types for - ("Decimal" and "None") | M-NULL |
| M0003 | src/income_analytics/domain/projectors/asset_composition_projector.py:75 | operator | Unsupported operand types for - ("None" and "Decimal") | M-NULL |
| M0004 | src/income_analytics/domain/projectors/asset_composition_projector.py:75 | operator | Unsupported left operand type for - ("None") | M-NULL |
| M0005 | src/income_analytics/application/historical_shares_units.py:10 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0006 | src/income_analytics/application/historical_shares_units.py:107 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0007 | src/income_analytics/application/historical_shares_units.py:129 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0008 | src/income_analytics/application/historical_shares_units.py:162 | no-untyped-call | Call to untyped function "outstanding" in typed context | M-ANN |
| M0009 | src/income_analytics/application/magic_formula_screening.py:49 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0010 | src/income_analytics/application/magic_formula_screening.py:136 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0011 | src/income_analytics/application/magic_formula_screening.py:157 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0012 | src/income_analytics/application/magic_formula_screening.py:159 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0013 | src/income_analytics/application/magic_formula_screening.py:161 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0014 | src/income_analytics/application/magic_formula_screening.py:173 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0015 | src/income_analytics/application/magic_formula_screening.py:222 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0016 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:32 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0017 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:36 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0018 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:49 | var-annotated | Need type annotation for "found" | M-GEN |
| M0019 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:112 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0020 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:144 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0021 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:159 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0022 | src/income_analytics/infrastructure/magic_formula_historical_price_sources.py:160 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0023 | src/income_analytics/infrastructure/historical_price_audit_source.py:10 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0024 | src/income_analytics/application/paid_income.py:96 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0025 | src/income_analytics/application/paid_income.py:97 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0026 | src/income_analytics/application/paid_income.py:103 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0027 | src/income_analytics/application/paid_income.py:107 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0028 | src/income_analytics/application/paid_income.py:107 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0029 | src/income_analytics/application/magic_formula_price_availability_audit.py:18 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0030 | src/income_analytics/application/magic_formula_price_availability_audit.py:33 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0031 | src/income_analytics/application/magic_formula_price_availability_audit.py:34 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0032 | src/income_analytics/application/magic_formula_price_availability_audit.py:82 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0033 | src/income_analytics/application/magic_formula_price_availability_audit.py:85 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0034 | src/income_analytics/application/magic_formula_price_availability_audit.py:139 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0035 | src/income_analytics/application/magic_formula_price_availability_audit.py:162 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0036 | src/income_analytics/application/historical_price.py:10 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0037 | src/income_analytics/application/historical_price.py:86 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0038 | src/income_analytics/application/historical_price.py:89 | var-annotated | Need type annotation for "intersections" | M-GEN |
| M0039 | src/income_analytics/application/historical_price.py:89 | var-annotated | Need type annotation for "marginal" | M-GEN |
| M0040 | src/income_analytics/infrastructure/irpf_xlsx_import.py:126 | operator | "object" not callable | M-NULL |
| M0041 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:12 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0042 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:36 | union-attr | Item "None" of "Element[str] &#124; None" has no attribute "find" | M-NULL |
| M0043 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:37 | union-attr | Item "None" of "Element[str] &#124; None" has no attribute "findtext" | M-NULL |
| M0044 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:44 | union-attr | Item "None" of "Element[str] &#124; None" has no attribute "findtext" | M-NULL |
| M0045 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:44 | arg-type | Argument 1 to "strptime" of "datetime" has incompatible type "str &#124; Any &#124; None"; expected "str" | M-COMPAT |
| M0046 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:45 | union-attr | Item "None" of "Element[str] &#124; None" has no attribute "findtext" | M-NULL |
| M0047 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:45 | union-attr | Item "None" of "str &#124; Any &#124; None" has no attribute "zfill" | M-NULL |
| M0048 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:46 | union-attr | Item "None" of "Element[str] &#124; None" has no attribute "findtext" | M-NULL |
| M0049 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:46 | arg-type | Argument 3 to "sub" has incompatible type "str &#124; Any &#124; None"; expected "str" | M-COMPAT |
| M0050 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:51 | index | Value of type "str &#124; None" is not indexable | M-NULL |
| M0051 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:55 | arg-type | Argument 3 to "sub" has incompatible type "str &#124; None"; expected "str" | M-COMPAT |
| M0052 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:56 | arg-type | Argument 3 to "sub" has incompatible type "str &#124; None"; expected "str" | M-COMPAT |
| M0053 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:66 | union-attr | Item "None" of "Element[str] &#124; Any &#124; None" has no attribute "findtext" | M-NULL |
| M0054 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:67 | union-attr | Item "None" of "Element[str] &#124; Any &#124; None" has no attribute "findtext" | M-NULL |
| M0055 | src/income_analytics/infrastructure/cvm_historical_shares_document.py:84 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; Any &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0056 | src/income_analytics/application/global_contribution_allocator.py:19 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0057 | src/income_analytics/application/global_contribution_allocator.py:20 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0058 | src/income_analytics/application/global_contribution_allocator.py:23 | type-arg | Missing type arguments for generic type "tuple" | M-GEN |
| M0059 | src/income_analytics/application/global_contribution_allocator.py:26 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0060 | src/income_analytics/application/global_contribution_allocator.py:53 | no-untyped-call | Call to untyped function "_allocate" in typed context | M-ANN |
| M0061 | src/income_analytics/application/global_contribution_allocator.py:67 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0062 | src/income_analytics/application/global_contribution_allocator.py:93 | var-annotated | Need type annotation for "trace" (hint: "trace: list[<type>] = ...") | M-GEN |
| M0063 | src/income_analytics/application/global_contribution_allocator.py:97 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0064 | src/income_analytics/application/global_contribution_allocator.py:112 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0065 | src/income_analytics/application/global_contribution_allocator.py:117 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0066 | src/income_analytics/application/global_contribution_allocator.py:118 | no-untyped-call | Call to untyped function "signature" in typed context | M-ANN |
| M0067 | src/income_analytics/application/global_contribution_allocator.py:120 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0068 | src/income_analytics/application/global_contribution_allocator.py:147 | no-untyped-call | Call to untyped function "objective" in typed context | M-ANN |
| M0069 | src/income_analytics/application/global_contribution_allocator.py:150 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0070 | src/income_analytics/application/global_contribution_allocator.py:180 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0071 | src/income_analytics/application/global_contribution_allocator.py:183 | no-untyped-call | Call to untyped function "proposals" in typed context | M-ANN |
| M0072 | src/income_analytics/application/global_contribution_allocator.py:188 | no-untyped-call | Call to untyped function "transition" in typed context | M-ANN |
| M0073 | src/income_analytics/application/global_contribution_allocator.py:194 | no-untyped-call | Call to untyped function "objective" in typed context | M-ANN |
| M0074 | src/income_analytics/application/global_contribution_allocator.py:200 | no-untyped-call | Call to untyped function "expand" in typed context | M-ANN |
| M0075 | src/income_analytics/application/global_contribution_allocator.py:202 | var-annotated | Need type annotation for "best_by_ticker" (hint: "best_by_ticker: dict[<type>, <type>] = ...") | M-GEN |
| M0076 | src/income_analytics/application/global_contribution_allocator.py:209 | no-untyped-call | Call to untyped function "rank" in typed context | M-ANN |
| M0077 | src/income_analytics/application/global_contribution_allocator.py:234 | no-untyped-call | Call to untyped function "expand" in typed context | M-ANN |
| M0078 | src/income_analytics/application/global_contribution_allocator.py:235 | no-untyped-call | Call to untyped function "signature" in typed context | M-ANN |
| M0079 | src/income_analytics/application/cvm_magic_formula_normalization.py:142 | type-var | Value of type variable "_AddableT1" of "sum" cannot be "Decimal &#124; None" | M-COMPAT |
| M0080 | src/income_analytics/application/cvm_magic_formula_normalization.py:143 | assignment | Incompatible types in assignment (expression has type "Decimal &#124; None", target has type "Decimal") | M-COMPAT |
| M0081 | src/income_analytics/application/cvm_magic_formula_normalization.py:156 | arg-type | Argument 6 to "MetricLineage" has incompatible type "Decimal &#124; None"; expected "Decimal" | M-COMPAT |
| M0082 | src/income_analytics/application/issuer_market_cap.py:138 | type-var | Value of type variable "_AddableT1" of "sum" cannot be "object" | M-COMPAT |
| M0083 | src/income_analytics/application/issuer_market_cap.py:138 | return-value | Incompatible return value type (got "tuple[object, tuple[dict[str, object], ...]]", expected "tuple[Decimal, tuple[dict[str, object], ...]]") | M-COMPAT |
| M0084 | src/income_analytics/application/historical_security_identity.py:12 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0085 | src/income_analytics/application/historical_security_identity.py:19 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0086 | src/income_analytics/application/historical_security_identity.py:24 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0087 | src/income_analytics/application/historical_security_identity.py:34 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0088 | src/income_analytics/application/historical_security_identity.py:36 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0089 | src/income_analytics/application/historical_security_identity.py:40 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0090 | src/income_analytics/application/historical_security_identity.py:41 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0091 | src/income_analytics/application/historical_security_identity.py:42 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0092 | src/income_analytics/application/historical_security_identity.py:43 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0093 | src/income_analytics/application/historical_security_identity.py:47 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0094 | src/income_analytics/application/historical_security_identity.py:48 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0095 | src/income_analytics/application/historical_security_identity.py:53 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0096 | src/income_analytics/application/historical_security_identity.py:54 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0097 | src/income_analytics/application/historical_security_identity.py:56 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0098 | src/income_analytics/application/historical_security_identity.py:69 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0099 | src/income_analytics/application/historical_security_identity.py:73 | no-untyped-call | Call to untyped function "resolve" in typed context | M-ANN |
| M0100 | src/income_analytics/application/historical_security_identity.py:74 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0101 | src/income_analytics/application/historical_security_identity.py:105 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0102 | src/income_analytics/application/historical_security_identity.py:120 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0103 | src/income_analytics/application/historical_security_identity.py:130 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0104 | src/income_analytics/application/historical_security_identity.py:135 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0105 | src/income_analytics/application/historical_security_identity.py:145 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0106 | src/income_analytics/application/historical_security_identity.py:146 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0107 | src/income_analytics/application/historical_security_identity.py:147 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0108 | src/income_analytics/application/historical_security_identity.py:148 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0109 | src/income_analytics/application/historical_security_identity.py:149 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0110 | src/income_analytics/application/historical_security_identity.py:153 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0111 | src/income_analytics/application/historical_security_identity.py:154 | no-untyped-call | Call to untyped function "_class_matches_ticker_isin" in typed context | M-ANN |
| M0112 | src/income_analytics/application/historical_security_identity.py:161 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0113 | src/income_analytics/application/historical_security_identity.py:171 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0114 | src/income_analytics/application/historical_security_identity.py:176 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0115 | src/income_analytics/application/historical_security_identity.py:177 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0116 | src/income_analytics/application/historical_security_identity.py:183 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0117 | src/income_analytics/application/historical_security_identity.py:184 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0118 | src/income_analytics/application/historical_security_identity.py:186 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0119 | src/income_analytics/application/historical_security_identity.py:195 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0120 | src/income_analytics/application/historical_security_identity.py:196 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0121 | src/income_analytics/application/historical_security_identity.py:203 | no-untyped-call | Call to untyped function "resolve" in typed context | M-ANN |
| M0122 | src/income_analytics/application/historical_security_identity.py:204 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0123 | src/income_analytics/infrastructure/b3_xlsx_import.py:50 | arg-type | Argument 1 to "get" of "dict" has incompatible type "int &#124; None"; expected "int" | M-COMPAT |
| M0124 | src/income_analytics/infrastructure/b3_xlsx_import.py:53 | arg-type | Argument 1 to "get" of "dict" has incompatible type "int &#124; None"; expected "int" | M-COMPAT |
| M0125 | src/income_analytics/infrastructure/b3_xlsx_import.py:57 | arg-type | Argument 1 to "get" of "dict" has incompatible type "int &#124; None"; expected "int" | M-COMPAT |
| M0126 | src/income_analytics/infrastructure/b3_xlsx_import.py:58 | arg-type | Argument 1 to "get" of "dict" has incompatible type "int &#124; None"; expected "int" | M-COMPAT |
| M0127 | src/income_analytics/infrastructure/b3_xlsx_import.py:59 | arg-type | Argument 1 to "get" of "dict" has incompatible type "int &#124; None"; expected "int" | M-COMPAT |
| M0128 | src/income_analytics/application/magic_formula_investable_universe.py:55 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0129 | src/income_analytics/application/magic_formula_investable_universe.py:68 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0130 | src/income_analytics/application/magic_formula_investable_universe.py:98 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0131 | src/income_analytics/application/magic_formula_investable_universe.py:114 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0132 | src/income_analytics/application/magic_formula_investable_universe.py:150 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0133 | src/income_analytics/application/magic_formula_investable_universe.py:159 | assignment | Incompatible types in assignment (expression has type "int", target has type "str &#124; None") | M-COMPAT |
| M0134 | src/income_analytics/application/magic_formula_investable_universe.py:160 | assignment | Incompatible types in assignment (expression has type "int", target has type "str &#124; None") | M-COMPAT |
| M0135 | src/income_analytics/application/magic_formula_investable_universe.py:162 | assignment | Incompatible types in assignment (expression has type "Decimal &#124; None", target has type "str &#124; None") | M-COMPAT |
| M0136 | src/income_analytics/application/magic_formula_investable_universe.py:165 | assignment | Incompatible types in assignment (expression has type "Decimal &#124; None", target has type "str &#124; None") | M-COMPAT |
| M0137 | src/income_analytics/application/magic_formula_investable_universe.py:168 | assignment | Incompatible types in assignment (expression has type "int", target has type "str &#124; None") | M-COMPAT |
| M0138 | src/income_analytics/application/magic_formula_investable_universe.py:171 | assignment | Incompatible types in assignment (expression has type "int", target has type "str &#124; None") | M-COMPAT |
| M0139 | src/income_analytics/application/magic_formula_investable_universe.py:178 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0140 | src/income_analytics/application/magic_formula_investable_universe.py:218 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0141 | src/income_analytics/application/magic_formula_investable_universe.py:219 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0142 | src/income_analytics/application/magic_formula_investable_universe.py:221 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0143 | src/income_analytics/application/magic_formula_investable_universe.py:245 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0144 | src/income_analytics/application/magic_formula_investable_universe.py:257 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0145 | src/income_analytics/application/magic_formula_investable_universe.py:273 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0146 | src/income_analytics/application/magic_formula_investable_universe.py:283 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0147 | src/income_analytics/infrastructure/magic_formula_universe_sources.py:14 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0148 | src/income_analytics/infrastructure/magic_formula_universe_sources.py:23 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0149 | src/income_analytics/infrastructure/magic_formula_universe_sources.py:31 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0150 | src/income_analytics/infrastructure/magic_formula_universe_sources.py:31 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0151 | src/income_analytics/infrastructure/magic_formula_universe_sources.py:78 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0152 | src/income_analytics/infrastructure/cvm_fundamentals_data.py:59 | attr-defined | "CvmStatementParser" has no attribute "code" | CODE-01 |
| M0153 | src/income_analytics/application/magic_formula_contract.py:61 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0154 | src/income_analytics/application/magic_formula_contract.py:93 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0155 | src/income_analytics/application/magic_formula_contract.py:158 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0156 | src/income_analytics/application/magic_formula_contract.py:159 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0157 | src/income_analytics/application/magic_formula_contract.py:160 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0158 | src/income_analytics/application/magic_formula_contract.py:268 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0159 | src/income_analytics/application/magic_formula_accounting_evidence.py:98 | assignment | Incompatible types in assignment (expression has type "DerivedAccountingEvidence", variable has type "AccountingEvidenceComponent") | M-COMPAT |
| M0160 | src/income_analytics/application/magic_formula_activation_gate.py:34 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0161 | src/income_analytics/application/magic_formula_activation_gate.py:34 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0162 | src/income_analytics/application/b3_import.py:168 | arg-type | Argument 8 to "B3ImportBatch" has incompatible type "**dict[str, int]"; expected "datetime &#124; None" | M-COMPAT |
| M0163 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:29 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0164 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:35 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0165 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:42 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0166 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:73 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0167 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:84 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0168 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:92 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0169 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:92 | type-arg | Missing type arguments for generic type "tuple" | M-GEN |
| M0170 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:97 | operator | Unsupported operand type for unary - ("Decimal &#124; None") | M-NULL |
| M0171 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:99 | operator | Unsupported operand type for unary - ("Decimal &#124; None") | M-NULL |
| M0172 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:101 | operator | Unsupported operand type for unary - ("Decimal &#124; None") | M-NULL |
| M0173 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:103 | operator | Unsupported operand type for unary - ("Decimal &#124; None") | M-NULL |
| M0174 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:107 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0175 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:108 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0176 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:193 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0177 | src/income_analytics/application/magic_formula_eligibility_policy_v7.py:229 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0178 | src/income_analytics/infrastructure/cvm_capital_structure.py:125 | operator | Unsupported operand types for * ("Decimal" and "None") | M-NULL |
| M0179 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:18 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0180 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:27 | var-annotated | Need type annotation for "_csv_cache" (hint: "_csv_cache: dict[<type>, <type>] = ...") | M-GEN |
| M0181 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:29 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0182 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:30 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0183 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:34 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0184 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:41 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0185 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:49 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0186 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:80 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0187 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:81 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0188 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:84 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0189 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:87 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0190 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:98 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0191 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:99 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0192 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:112 | no-untyped-call | Call to untyped function "csv_rows" in typed context | M-ANN |
| M0193 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:120 | no-untyped-call | Call to untyped function "one" of "OfficialRawVerifier" in typed context | M-ANN |
| M0194 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:121 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0195 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:125 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0196 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:126 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0197 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:131 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0198 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:133 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0199 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:139 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0200 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:143 | no-untyped-call | Call to untyped function "receipt" in typed context | M-ANN |
| M0201 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:150 | no-untyped-call | Call to untyped function "csv_rows" in typed context | M-ANN |
| M0202 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:156 | no-untyped-call | Call to untyped function "one" of "OfficialRawVerifier" in typed context | M-ANN |
| M0203 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:157 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0204 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:163 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0205 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:165 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0206 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:166 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0207 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:171 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0208 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:180 | no-untyped-call | Call to untyped function "receipt" in typed context | M-ANN |
| M0209 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:192 | no-untyped-call | Call to untyped function "csv_rows" in typed context | M-ANN |
| M0210 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:195 | no-untyped-call | Call to untyped function "one" of "OfficialRawVerifier" in typed context | M-ANN |
| M0211 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:198 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0212 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:202 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0213 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:207 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0214 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:212 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0215 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:215 | no-untyped-call | Call to untyped function "receipt" in typed context | M-ANN |
| M0216 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:219 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0217 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:235 | no-untyped-call | Call to untyped function "one" of "OfficialRawVerifier" in typed context | M-ANN |
| M0218 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:236 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0219 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:241 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0220 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:242 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0221 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:247 | no-untyped-call | Call to untyped function "one" of "OfficialRawVerifier" in typed context | M-ANN |
| M0222 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:251 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0223 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:252 | no-untyped-call | Call to untyped function "require" in typed context | M-ANN |
| M0224 | src/income_analytics/infrastructure/magic_formula_raw_verification.py:253 | no-untyped-call | Call to untyped function "receipt" in typed context | M-ANN |
| M0225 | src/income_analytics/application/magic_formula_universe.py:52 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0226 | src/income_analytics/application/magic_formula_universe.py:56 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0227 | src/income_analytics/application/magic_formula_universe.py:64 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0228 | src/income_analytics/application/magic_formula_universe.py:71 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0229 | src/income_analytics/application/magic_formula_universe.py:77 | var-annotated | Need type annotation for "discarded" | M-GEN |
| M0230 | src/income_analytics/application/magic_formula_universe.py:90 | no-untyped-call | Call to untyped function "valid_date" in typed context | M-ANN |
| M0231 | src/income_analytics/application/magic_formula_universe.py:93 | no-untyped-call | Call to untyped function "digits" in typed context | M-ANN |
| M0232 | src/income_analytics/application/magic_formula_universe.py:100 | no-untyped-call | Call to untyped function "digits" in typed context | M-ANN |
| M0233 | src/income_analytics/application/magic_formula_universe.py:105 | no-untyped-call | Call to untyped function "digits" in typed context | M-ANN |
| M0234 | src/income_analytics/application/magic_formula_universe.py:120 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0235 | src/income_analytics/application/magic_formula_universe.py:175 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0236 | src/income_analytics/application/magic_formula_universe.py:188 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0237 | src/income_analytics/application/magic_formula_universe.py:197 | no-untyped-call | Call to untyped function "digits" in typed context | M-ANN |
| M0238 | src/income_analytics/application/magic_formula_universe.py:239 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0239 | src/income_analytics/application/magic_formula_universe.py:247 | no-untyped-call | Call to untyped function "valid_date" in typed context | M-ANN |
| M0240 | src/income_analytics/application/magic_formula_universe.py:248 | no-untyped-call | Call to untyped function "valid_date" in typed context | M-ANN |
| M0241 | src/income_analytics/application/magic_formula_universe.py:250 | no-untyped-call | Call to untyped function "valid_date" in typed context | M-ANN |
| M0242 | src/income_analytics/application/magic_formula_universe.py:264 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0243 | src/income_analytics/application/magic_formula_universe.py:290 | index | Value of type "Any &#124; None" is not indexable | M-NULL |
| M0244 | src/income_analytics/application/magic_formula_universe.py:300 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0245 | src/income_analytics/application/magic_formula_universe.py:301 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0246 | src/income_analytics/application/magic_formula_universe.py:366 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0247 | src/income_analytics/application/magic_formula_universe.py:367 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0248 | src/income_analytics/application/magic_formula_universe.py:368 | no-untyped-call | Call to untyped function "decimal_or_none" in typed context | M-ANN |
| M0249 | src/income_analytics/application/magic_formula_universe.py:415 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0250 | src/income_analytics/application/magic_formula_universe.py:420 | no-untyped-call | Call to untyped function "digits" in typed context | M-ANN |
| M0251 | src/income_analytics/application/magic_formula_universe.py:426 | no-untyped-call | Call to untyped function "accounting_readiness" in typed context | M-ANN |
| M0252 | src/income_analytics/application/magic_formula_universe.py:429 | no-untyped-call | Call to untyped function "market_readiness" in typed context | M-ANN |
| M0253 | src/income_analytics/application/magic_formula_universe.py:493 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0254 | src/income_analytics/application/magic_formula_universe.py:506 | no-untyped-call | Call to untyped function (unknown) in typed context | M-ANN |
| M0255 | src/income_analytics/application/magic_formula_universe.py:507 | no-untyped-call | Call to untyped function (unknown) in typed context | M-ANN |
| M0256 | src/income_analytics/application/magic_formula_ranking_validation.py:8 | attr-defined | Module "income_analytics.application.magic_formula_contract" does not explicitly export attribute "ADAPTER_VERSION" | M-SHAPE |
| M0257 | src/income_analytics/application/magic_formula_ranking_validation.py:27 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0258 | src/income_analytics/application/magic_formula_ranking_validation.py:32 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0259 | src/income_analytics/application/magic_formula_ranking_validation.py:90 | no-untyped-call | Call to untyped function "RankingGateBlocked" in typed context | M-ANN |
| M0260 | src/income_analytics/application/magic_formula_ranking_validation.py:94 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0261 | src/income_analytics/application/magic_formula_ranking_validation.py:100 | no-untyped-call | Call to untyped function "RankingGateBlocked" in typed context | M-ANN |
| M0262 | src/income_analytics/application/magic_formula_ranking_validation.py:101 | no-untyped-call | Call to untyped function "load_bound_inputs" in typed context | M-ANN |
| M0263 | src/income_analytics/application/magic_formula_ranking_validation.py:116 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0264 | src/income_analytics/application/magic_formula_ranking_validation.py:125 | no-untyped-call | Call to untyped function "RankingGateBlocked" in typed context | M-ANN |
| M0265 | src/income_analytics/application/magic_formula_ranking_validation.py:128 | no-untyped-call | Call to untyped function "RankingGateBlocked" in typed context | M-ANN |
| M0266 | src/income_analytics/application/magic_formula_ranking_validation.py:129 | no-untyped-call | Call to untyped function "load_bound_inputs" in typed context | M-ANN |
| M0267 | src/income_analytics/application/magic_formula_ranking_validation.py:133 | no-untyped-call | Call to untyped function "RankingGateBlocked" in typed context | M-ANN |
| M0268 | src/income_analytics/application/magic_formula_ranking_validation.py:137 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0269 | src/income_analytics/application/magic_formula_ranking_validation.py:174 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0270 | src/income_analytics/application/magic_formula_ranking_validation.py:178 | no-untyped-call | Call to untyped function "independent_rank_qa" in typed context | M-ANN |
| M0271 | src/income_analytics/application/magic_formula_ranking_validation.py:191 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0272 | src/income_analytics/application/magic_formula_formal_qa.py:23 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0273 | src/income_analytics/application/magic_formula_formal_qa.py:40 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0274 | src/income_analytics/application/magic_formula_formal_qa.py:60 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0275 | src/income_analytics/application/magic_formula_formal_qa.py:65 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0276 | src/income_analytics/application/magic_formula_formal_qa.py:71 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0277 | src/income_analytics/application/magic_formula_formal_qa.py:72 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0278 | src/income_analytics/application/magic_formula_formal_qa.py:75 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0279 | src/income_analytics/application/magic_formula_formal_qa.py:80 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0280 | src/income_analytics/application/magic_formula_formal_qa.py:86 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0281 | src/income_analytics/application/magic_formula_formal_qa.py:110 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0282 | src/income_analytics/application/magic_formula_formal_qa.py:111 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0283 | src/income_analytics/application/magic_formula_formal_qa.py:112 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0284 | src/income_analytics/application/magic_formula_formal_qa.py:117 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0285 | src/income_analytics/application/magic_formula_formal_qa.py:122 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0286 | src/income_analytics/application/magic_formula_formal_qa.py:124 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0287 | src/income_analytics/application/magic_formula_formal_qa.py:125 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0288 | src/income_analytics/application/magic_formula_formal_qa.py:126 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0289 | src/income_analytics/application/magic_formula_formal_qa.py:129 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0290 | src/income_analytics/application/magic_formula_formal_qa.py:138 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0291 | src/income_analytics/application/magic_formula_formal_qa.py:175 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0292 | src/income_analytics/application/magic_formula_formal_qa.py:176 | var-annotated | Need type annotation for "refs" (hint: "refs: list[<type>] = ...") | M-GEN |
| M0293 | src/income_analytics/application/magic_formula_formal_qa.py:183 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0294 | src/income_analytics/application/magic_formula_formal_qa.py:197 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0295 | src/income_analytics/application/magic_formula_formal_qa.py:204 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0296 | src/income_analytics/application/magic_formula_formal_qa.py:205 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0297 | src/income_analytics/application/magic_formula_formal_qa.py:209 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0298 | src/income_analytics/application/magic_formula_formal_qa.py:210 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0299 | src/income_analytics/application/magic_formula_formal_qa.py:234 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0300 | src/income_analytics/application/magic_formula_formal_qa.py:238 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0301 | src/income_analytics/application/magic_formula_formal_qa.py:246 | no-untyped-call | Call to untyped function "present" in typed context | M-ANN |
| M0302 | src/income_analytics/application/magic_formula_formal_qa.py:258 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0303 | src/income_analytics/application/magic_formula_formal_qa.py:265 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0304 | src/income_analytics/application/magic_formula_formal_qa.py:275 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0305 | src/income_analytics/application/magic_formula_formal_qa.py:279 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0306 | src/income_analytics/application/magic_formula_formal_qa.py:280 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0307 | src/income_analytics/application/magic_formula_formal_qa.py:286 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0308 | src/income_analytics/application/magic_formula_formal_qa.py:287 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0309 | src/income_analytics/application/magic_formula_formal_qa.py:288 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0310 | src/income_analytics/application/magic_formula_formal_qa.py:295 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0311 | src/income_analytics/application/magic_formula_formal_qa.py:298 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0312 | src/income_analytics/application/magic_formula_formal_qa.py:303 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0313 | src/income_analytics/application/magic_formula_formal_qa.py:304 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0314 | src/income_analytics/application/magic_formula_formal_qa.py:307 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0315 | src/income_analytics/application/magic_formula_formal_qa.py:308 | no-untyped-call | Call to untyped function "number" in typed context | M-ANN |
| M0316 | src/income_analytics/application/magic_formula_formal_qa.py:320 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0317 | src/income_analytics/application/magic_formula_formal_qa.py:322 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0318 | src/income_analytics/application/magic_formula_formal_qa.py:325 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0319 | src/income_analytics/application/magic_formula_formal_qa.py:349 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0320 | src/income_analytics/application/magic_formula_formal_qa.py:350 | no-untyped-call | Call to untyped function "equal" in typed context | M-ANN |
| M0321 | src/income_analytics/application/magic_formula_formal_qa.py:356 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0322 | src/income_analytics/application/magic_formula_formal_qa.py:387 | no-untyped-call | Call to untyped function "check" in typed context | M-ANN |
| M0323 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:17 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0324 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:32 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0325 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:46 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0326 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:47 | no-untyped-call | Call to untyped function "coverage" in typed context | M-ANN |
| M0327 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:69 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0328 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:79 | no-untyped-call | Call to untyped function "coverage" in typed context | M-ANN |
| M0329 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:83 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0330 | src/income_analytics/infrastructure/magic_formula_universe_repository.py:93 | no-untyped-call | Call to untyped function "read" in typed context | M-ANN |
| M0331 | src/income_analytics/application/magic_formula_price_blocker_batch.py:32 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0332 | src/income_analytics/application/magic_formula_price_blocker_batch.py:39 | no-untyped-call | Call to untyped function "_class_matches_ticker_isin" in typed context | M-ANN |
| M0333 | src/income_analytics/application/magic_formula_price_blocker_batch.py:43 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0334 | src/income_analytics/application/magic_formula_price_blocker_batch.py:47 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0335 | src/income_analytics/application/magic_formula_price_blocker_batch.py:47 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0336 | src/income_analytics/application/magic_formula_price_blocker_batch.py:90 | no-untyped-call | Call to untyped function "_source_hash" in typed context | M-ANN |
| M0337 | src/income_analytics/application/magic_formula_price_blocker_batch.py:122 | no-untyped-call | Call to untyped function "_directory_security_candidates" in typed context | M-ANN |
| M0338 | src/income_analytics/application/magic_formula_price_blocker_batch.py:172 | no-untyped-call | Call to untyped function "recover_price_from_exchange_identity" in typed context | M-ANN |
| M0339 | src/income_analytics/application/magic_formula_price_blocker_batch.py:230 | assignment | Incompatible types in assignment (expression has type "dict[str, Any]", variable has type "list[str]") | M-COMPAT |
| M0340 | src/income_analytics/application/magic_formula_price_blocker_batch.py:234 | attr-defined | "list[str]" has no attribute "values" | M-SHAPE |
| M0341 | src/income_analytics/application/magic_formula_price_blocker_batch.py:237 | no-untyped-call | Call to untyped function "coverage" in typed context | M-ANN |
| M0342 | src/income_analytics/application/magic_formula_price_blocker_batch.py:246 | no-untyped-call | Call to untyped function "gap_analysis" in typed context | M-ANN |
| M0343 | src/income_analytics/application/magic_formula_price_blocker_batch.py:247 | no-untyped-call | Call to untyped function "gap_analysis" in typed context | M-ANN |
| M0344 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:19 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0345 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:35 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0346 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:50 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0347 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:57 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0348 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:58 | no-untyped-call | Call to untyped function "validate_frozen_sample" in typed context | M-ANN |
| M0349 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:59 | no-untyped-call | Call to untyped function "_insert" in typed context | M-ANN |
| M0350 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:61 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0351 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:75 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0352 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:76 | no-untyped-call | Call to untyped function "read" in typed context | M-ANN |
| M0353 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:77 | no-untyped-call | Call to untyped function "validate_frozen_sample" in typed context | M-ANN |
| M0354 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:89 | no-untyped-call | Call to untyped function "compare_independent_qa" in typed context | M-ANN |
| M0355 | src/income_analytics/infrastructure/magic_formula_ranking_repository.py:115 | no-untyped-call | Call to untyped function "_insert" in typed context | M-ANN |
| M0356 | src/income_analytics/application/magic_formula_stocks.py:45 | operator | Unsupported operand types for - ("Decimal" and "None") | M-NULL |
| M0357 | src/income_analytics/application/magic_formula_stocks.py:45 | operator | Unsupported operand types for - ("None" and "Decimal") | M-NULL |
| M0358 | src/income_analytics/application/magic_formula_stocks.py:45 | operator | Unsupported left operand type for - ("None") | M-NULL |
| M0359 | src/income_analytics/application/magic_formula_stocks.py:46 | operator | Unsupported operand types for + ("None" and "Decimal") | M-NULL |
| M0360 | src/income_analytics/application/magic_formula_stocks.py:48 | operator | Unsupported operand types for - ("Decimal" and "None") | M-NULL |
| M0361 | src/income_analytics/application/magic_formula_stocks.py:48 | operator | Unsupported operand types for - ("None" and "Decimal") | M-NULL |
| M0362 | src/income_analytics/application/magic_formula_stocks.py:48 | operator | Unsupported left operand type for - ("None") | M-NULL |
| M0363 | src/income_analytics/application/magic_formula_stocks.py:48 | operator | Unsupported operand types for + ("Decimal" and "None") | M-NULL |
| M0364 | src/income_analytics/application/magic_formula_stocks.py:57 | operator | Unsupported operand types for / ("None" and "Decimal") | M-NULL |
| M0365 | src/income_analytics/application/magic_formula_stocks.py:58 | operator | Unsupported operand types for / ("None" and "Decimal") | M-NULL |
| M0366 | src/income_analytics/application/magic_formula_stocks.py:64 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0367 | src/income_analytics/application/magic_formula_stocks.py:70 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0368 | src/income_analytics/application/magic_formula_stocks.py:70 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0369 | src/income_analytics/application/magic_formula_stocks.py:76 | no-untyped-call | Call to untyped function "validate_frozen_sample" in typed context | M-ANN |
| M0370 | src/income_analytics/application/magic_formula_stocks.py:80 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0371 | src/income_analytics/application/magic_formula_stocks.py:83 | var-annotated | Need type annotation for "ranks" (hint: "ranks: dict[<type>, <type>] = ...") | M-GEN |
| M0372 | src/income_analytics/application/magic_formula_stocks.py:198 | arg-type | Argument 1 to "sorted" has incompatible type "list[dict[str, int &#124; Decimal &#124; str &#124; None]]"; expected "Iterable[dict[str, object]]" | M-COMPAT |
| M0373 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:13 | attr-defined | Module "income_analytics.application.magic_formula_contract" does not explicitly export attribute "ADAPTER_VERSION" | M-SHAPE |
| M0374 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:32 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0375 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:52 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0376 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:52 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0377 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:73 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0378 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:108 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0379 | src/income_analytics/infrastructure/magic_formula_contract_repository.py:188 | no-any-return | Returning Any from function declared to return "str" | M-GEN |
| M0380 | src/income_analytics/application/magic_formula_golden_evidence_builder.py:52 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0381 | src/income_analytics/application/magic_formula_golden_evidence_builder.py:89 | attr-defined | "object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable) | M-SHAPE |
| M0382 | src/income_analytics/application/magic_formula_golden_evidence_builder.py:185 | operator | Unsupported operand types for * ("Decimal" and "None") | M-NULL |
| M0383 | src/income_analytics/application/magic_formula_preview.py:13 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0384 | src/income_analytics/application/magic_formula_preview.py:45 | no-untyped-call | Call to untyped function "compare_independent_qa" in typed context | M-ANN |
| M0385 | src/income_analytics/application/magic_formula_preview.py:85 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0386 | src/income_analytics/application/magic_formula_preview.py:134 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0387 | src/income_analytics/application/executable_contribution.py:28 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0388 | src/income_analytics/application/executable_contribution.py:32 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0389 | src/income_analytics/application/executable_contribution.py:36 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0390 | src/income_analytics/application/executable_contribution.py:66 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0391 | src/income_analytics/application/executable_contribution.py:69 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0392 | src/income_analytics/application/executable_contribution.py:76 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0393 | src/income_analytics/application/executable_contribution.py:77 | no-untyped-call | Call to untyped function "ceil_units" in typed context | M-ANN |
| M0394 | src/income_analytics/application/executable_contribution.py:81 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0395 | src/income_analytics/application/executable_contribution.py:84 | no-untyped-call | Call to untyped function "floor_units" in typed context | M-ANN |
| M0396 | src/income_analytics/application/executable_contribution.py:89 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0397 | src/income_analytics/application/executable_contribution.py:93 | no-untyped-call | Call to untyped function "_build_executable_plan" in typed context | M-ANN |
| M0398 | src/income_analytics/application/executable_contribution.py:96 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0399 | src/income_analytics/application/executable_contribution.py:115 | var-annotated | Need type annotation for "class_values" (hint: "class_values: dict[<type>, <type>] = ...") | M-GEN |
| M0400 | src/income_analytics/application/executable_contribution.py:257 | operator | No overload variant of "__sub__" of "date" matches argument type "None" | M-NULL |
| M0401 | src/income_analytics/application/executable_contribution.py:285 | no-untyped-call | Call to untyped function "common_increment" in typed context | M-ANN |
| M0402 | src/income_analytics/application/executable_contribution.py:285 | union-attr | Item "None" of "Any &#124; None" has no attribute "price" | M-NULL |
| M0403 | src/income_analytics/application/executable_contribution.py:297 | union-attr | Item "None" of "Any &#124; None" has no attribute "price" | M-NULL |
| M0404 | src/income_analytics/application/executable_contribution.py:298 | union-attr | Item "None" of "Any &#124; None" has no attribute "effective_date" | M-NULL |
| M0405 | src/income_analytics/application/executable_contribution.py:299 | union-attr | Item "None" of "Any &#124; None" has no attribute "provider" | M-NULL |
| M0406 | src/income_analytics/application/executable_contribution.py:300 | union-attr | Item "None" of "Any &#124; None" has no attribute "price_timestamp" | M-NULL |
| M0407 | src/income_analytics/application/executable_contribution.py:301 | union-attr | Item "None" of "Any &#124; None" has no attribute "price_timestamp" | M-NULL |
| M0408 | src/income_analytics/application/executable_contribution.py:331 | no-untyped-call | Call to untyped function "allocate_quantities" in typed context | M-ANN |
| M0409 | src/income_analytics/application/executable_contribution.py:342 | no-untyped-call | Call to untyped function "cost" in typed context | M-ANN |
| M0410 | src/income_analytics/application/executable_contribution.py:370 | no-untyped-call | Call to untyped function "cost" in typed context | M-ANN |
| M0411 | src/income_analytics/application/executable_contribution.py:371 | no-untyped-call | Call to untyped function "cost" in typed context | M-ANN |
| M0412 | src/income_analytics/application/executable_contribution.py:428 | attr-defined | "Decimal" has no attribute "__iter__"; maybe "__int__"? (not iterable) | M-SHAPE |
| M0413 | src/income_analytics/application/magic_formula_canonical_ranking.py:476 | no-any-return | Returning Any from function declared to return "dict[str, Any]" | M-GEN |
| M0414 | src/income_analytics/application/magic_formula_canonical_ranking.py:527 | no-any-return | Returning Any from function declared to return "dict[str, Any] &#124; None" | M-GEN |
| M0415 | src/income_analytics/application/magic_formula_canonical_ranking.py:637 | no-any-return | Returning Any from function declared to return "dict[str, Any]" | M-GEN |
| M0416 | src/income_analytics/domain/projectors/performance_projector.py:193 | operator | Unsupported operand types for * ("None" and "int") | M-NULL |
| M0417 | src/income_analytics/domain/projectors/performance_projector.py:589 | no-redef | Name "funding_by_currency" already defined on line 575 | M-REDEF |
| M0418 | src/income_analytics/domain/projectors/performance_projector.py:595 | assignment | Incompatible types in assignment (expression has type "tuple[FinancialEvent, ...]", variable has type "Iterator[FinancialEvent]") | M-COMPAT |
| M0419 | src/income_analytics/application/wealth_explanation.py:82 | attr-defined | "object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable) | M-SHAPE |
| M0420 | src/income_analytics/application/wealth_explanation.py:84 | attr-defined | "object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable) | M-SHAPE |
| M0421 | src/income_analytics/application/wealth_explanation.py:88 | attr-defined | "object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable) | M-SHAPE |
| M0422 | src/income_analytics/application/wealth_explanation.py:93 | attr-defined | "object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable) | M-SHAPE |
| M0423 | src/income_analytics/application/wealth_explanation.py:122 | no-untyped-call | Call to untyped function "_flow_children" of "WealthExplanationService" in typed context | M-ANN |
| M0424 | src/income_analytics/application/wealth_explanation.py:131 | no-untyped-call | Call to untyped function "_children" of "WealthExplanationService" in typed context | M-ANN |
| M0425 | src/income_analytics/application/wealth_explanation.py:139 | no-untyped-call | Call to untyped function "_children" of "WealthExplanationService" in typed context | M-ANN |
| M0426 | src/income_analytics/application/wealth_explanation.py:145 | no-untyped-call | Call to untyped function "_children" of "WealthExplanationService" in typed context | M-ANN |
| M0427 | src/income_analytics/application/wealth_explanation.py:150 | type-var | Value of type variable "_AddableT1" of "sum" cannot be "object" | M-COMPAT |
| M0428 | src/income_analytics/application/wealth_explanation.py:150 | operator | Unsupported operand types for + ("Decimal" and "object") | M-NULL |
| M0429 | src/income_analytics/application/wealth_explanation.py:290 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0430 | src/income_analytics/application/wealth_explanation.py:305 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0431 | src/income_analytics/application/wealth_explanation.py:320 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0432 | src/income_analytics/application/wealth_explanation.py:320 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0433 | src/income_analytics/application/wealth_explanation.py:404 | operator | Unsupported operand types for + ("Decimal" and "str") | M-NULL |
| M0434 | src/income_analytics/application/wealth_explanation.py:404 | operator | Unsupported operand types for + ("Decimal" and "None") | M-NULL |
| M0435 | src/income_analytics/application/wealth_explanation.py:413 | operator | Unsupported operand types for < ("int" and "None") | M-NULL |
| M0436 | src/income_analytics/application/wealth_explanation.py:413 | operator | Unsupported operand types for > ("str" and "int") | M-NULL |
| M0437 | src/income_analytics/application/wealth_explanation.py:414 | arg-type | Argument "key" to "sorted" has incompatible type "Callable[[dict[str, bool &#124; str &#124; Decimal &#124; None]], bool &#124; str &#124; Decimal &#124; None]"; expected "Callable[[dict[str, bool &#124; str &#124; Decimal &#124; None]], SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]]" | M-COMPAT |
| M0438 | src/income_analytics/application/wealth_explanation.py:414 | return-value | Incompatible return value type (got "bool &#124; str &#124; Decimal &#124; None", expected "SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]") | M-COMPAT |
| M0439 | src/income_analytics/application/wealth_explanation.py:418 | operator | Unsupported operand types for > ("int" and "None") | M-NULL |
| M0440 | src/income_analytics/application/wealth_explanation.py:418 | operator | Unsupported operand types for < ("str" and "int") | M-NULL |
| M0441 | src/income_analytics/application/wealth_explanation.py:419 | arg-type | Argument "key" to "sorted" has incompatible type "Callable[[dict[str, bool &#124; str &#124; Decimal &#124; None]], bool &#124; str &#124; Decimal &#124; None]"; expected "Callable[[dict[str, bool &#124; str &#124; Decimal &#124; None]], SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]]" | M-COMPAT |
| M0442 | src/income_analytics/application/wealth_explanation.py:419 | return-value | Incompatible return value type (got "bool &#124; str &#124; Decimal &#124; None", expected "SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]") | M-COMPAT |
| M0443 | src/income_analytics/infrastructure/firebase_identity.py:9 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0444 | src/income_analytics/infrastructure/firebase_identity.py:10 | import-untyped | Skipping analyzing "firebase_admin": module is installed, but missing library stubs or py.typed marker | M-SDK |
| M0445 | src/income_analytics/infrastructure/firebase_identity.py:21 | misc | Class cannot subclass "Base" (has type "Any") | M-SDK |
| M0446 | src/income_analytics/infrastructure/firebase_identity.py:22 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0447 | src/income_analytics/infrastructure/firebase_identity.py:23 | no-untyped-call | Call to untyped function "AnonymousCredentials" in typed context | M-ANN |
| M0448 | src/income_analytics/infrastructure/firebase_identity.py:44 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0449 | src/income_analytics/infrastructure/firebase_identity.py:47 | no-any-return | Returning Any from function declared to return "dict[Any, Any]" | M-GEN |
| M0450 | src/income_analytics/infrastructure/firebase_identity.py:52 | no-any-return | Returning Any from function declared to return "str" | M-GEN |
| M0451 | src/income_analytics/infrastructure/firebase_identity.py:54 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0452 | src/income_analytics/infrastructure/firebase_identity.py:57 | no-any-return | Returning Any from function declared to return "dict[Any, Any]" | M-GEN |
| M0453 | src/income_analytics/infrastructure/firebase_identity.py:59 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0454 | src/income_analytics/infrastructure/firebase_identity.py:67 | no-any-return | Returning Any from function declared to return "dict[Any, Any]" | M-GEN |
| M0455 | src/income_analytics/infrastructure/database.py:28 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0456 | src/income_analytics/infrastructure/sqlite_repositories.py:496 | no-any-return | Returning Any from function declared to return "dict[str, object] &#124; None" | M-GEN |
| M0457 | src/income_analytics/infrastructure/sqlite_repositories.py:536 | no-untyped-call | Call to untyped function "_save_metadata" in typed context | M-ANN |
| M0458 | src/income_analytics/infrastructure/sqlite_repositories.py:588 | no-any-return | Returning Any from function declared to return "Asset &#124; None" | M-GEN |
| M0459 | src/income_analytics/infrastructure/sqlite_repositories.py:588 | no-untyped-call | Call to untyped function "_scoped_asset" in typed context | M-ANN |
| M0460 | src/income_analytics/infrastructure/sqlite_repositories.py:606 | no-any-return | Returning Any from function declared to return "Asset &#124; None" | M-GEN |
| M0461 | src/income_analytics/infrastructure/sqlite_repositories.py:606 | no-untyped-call | Call to untyped function "_scoped_asset" in typed context | M-ANN |
| M0462 | src/income_analytics/infrastructure/sqlite_repositories.py:654 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0463 | src/income_analytics/infrastructure/sqlite_repositories.py:666 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0464 | src/income_analytics/infrastructure/sqlite_repositories.py:896 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0465 | src/income_analytics/infrastructure/sqlite_repositories.py:899 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0466 | src/income_analytics/infrastructure/sqlite_repositories.py:903 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0467 | src/income_analytics/infrastructure/sqlite_repositories.py:906 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0468 | src/income_analytics/infrastructure/sqlite_repositories.py:911 | arg-type | Argument 1 to "Decimal" has incompatible type "str &#124; None"; expected "Decimal &#124; float &#124; str &#124; tuple[int, Sequence[int], int]" | M-COMPAT |
| M0469 | src/income_analytics/infrastructure/sqlite_repositories.py:1112 | attr-defined | "Base" has no attribute "detail" | M-SHAPE |
| M0470 | src/income_analytics/infrastructure/sqlite_repositories.py:1113 | attr-defined | "Base" has no attribute "financial_event_id" | M-SHAPE |
| M0471 | src/income_analytics/infrastructure/sqlite_repositories.py:1114 | attr-defined | "Base" has no attribute "detail" | M-SHAPE |
| M0472 | src/income_analytics/infrastructure/sqlite_repositories.py:1304 | arg-type | Argument "provider" to "MarketPrice" has incompatible type "str &#124; None"; expected "str" | M-COMPAT |
| M0473 | src/income_analytics/infrastructure/sqlite_repositories.py:1317 | var-annotated | Need type annotation for "result" (hint: "result: dict[<type>, <type>] = ...") | M-GEN |
| M0474 | src/income_analytics/infrastructure/sqlite_repositories.py:1563 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0475 | src/income_analytics/infrastructure/sqlite_repositories.py:1578 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0476 | src/income_analytics/infrastructure/sqlite_repositories.py:1601 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0477 | src/income_analytics/infrastructure/sqlite_repositories.py:1610 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0478 | src/income_analytics/infrastructure/sqlite_repositories.py:1736 | arg-type | Argument 1 to "SqliteAssetRepository" has incompatible type "str"; expected "UUID" | M-COMPAT |
| M0479 | src/income_analytics/infrastructure/sqlite_repositories.py:1751 | arg-type | Argument 1 to "SqliteAssetRepository" has incompatible type "str"; expected "UUID" | M-COMPAT |
| M0480 | src/income_analytics/infrastructure/magic_formula_snapshot_repository.py:20 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0481 | src/income_analytics/application/income_starter.py:82 | no-untyped-call | Call to untyped function "_validate_allocations" of "IncomeStarterRepository" in typed context | M-ANN |
| M0482 | src/income_analytics/application/income_starter.py:178 | no-untyped-call | Call to untyped function "_validate_proposal" of "IncomeStarterRepository" in typed context | M-ANN |
| M0483 | src/income_analytics/application/income_starter.py:247 | no-untyped-call | Call to untyped function "_validate_allocations" of "IncomeStarterRepository" in typed context | M-ANN |
| M0484 | src/income_analytics/application/income_starter.py:248 | no-untyped-call | Call to untyped function "_validate_allocation_sources" of "IncomeStarterRepository" in typed context | M-ANN |
| M0485 | src/income_analytics/application/income_starter.py:265 | no-untyped-call | Call to untyped function "_validate_allocations" of "IncomeStarterRepository" in typed context | M-ANN |
| M0486 | src/income_analytics/application/income_starter.py:419 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0487 | src/income_analytics/application/income_starter.py:457 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0488 | src/income_analytics/application/income_starter.py:457 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0489 | src/income_analytics/application/income_starter.py:470 | no-untyped-call | Call to untyped function "_validate_allocations" of "IncomeStarterRepository" in typed context | M-ANN |
| M0490 | src/income_analytics/application/income_starter.py:480 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0491 | src/income_analytics/application/income_starter.py:484 | no-any-return | Returning Any from function declared to return "IncomeStarterTemplateVersionRecord" | M-GEN |
| M0492 | src/income_analytics/application/income_starter.py:487 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0493 | src/income_analytics/application/income_starter.py:488 | no-untyped-call | Call to untyped function "_validate_allocations" of "IncomeStarterRepository" in typed context | M-ANN |
| M0494 | src/income_analytics/application/income_starter.py:489 | no-untyped-call | Call to untyped function "_validate_allocation_sources" of "IncomeStarterRepository" in typed context | M-ANN |
| M0495 | src/income_analytics/application/income_starter.py:493 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0496 | src/income_analytics/application/income_starter.py:514 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0497 | src/income_analytics/infrastructure/auth_repository.py:27 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0498 | src/income_analytics/infrastructure/auth_repository.py:27 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0499 | src/income_analytics/infrastructure/auth_repository.py:39 | type-arg | Missing type arguments for generic type "dict" | M-GEN |
| M0500 | src/income_analytics/infrastructure/auth_repository.py:85 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0501 | src/income_analytics/infrastructure/auth_repository.py:107 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0502 | src/income_analytics/infrastructure/auth_repository.py:115 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0503 | src/income_analytics/infrastructure/auth_repository.py:125 | assignment | Incompatible types in assignment (expression has type "ReturningInsert[tuple[int]]", variable has type "Insert") | M-COMPAT |
| M0504 | src/income_analytics/api/onboarding_v2.py:14 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0505 | src/income_analytics/api/onboarding_v2.py:18 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0506 | src/income_analytics/api/onboarding_v2.py:21 | no-untyped-call | Call to untyped function "positive" in typed context | M-ANN |
| M0507 | src/income_analytics/api/onboarding_v2.py:24 | no-untyped-call | Call to untyped function "positive" in typed context | M-ANN |
| M0508 | src/income_analytics/api/onboarding_v2.py:26 | no-untyped-call | Call to untyped function "positive" in typed context | M-ANN |
| M0509 | src/income_analytics/api/onboarding_v2.py:29 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0510 | src/income_analytics/api/onboarding_v2.py:32 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0511 | src/income_analytics/api/onboarding_v2.py:33 | no-untyped-call | Call to untyped function "facts" in typed context | M-ANN |
| M0512 | src/income_analytics/api/onboarding_v2.py:43 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0513 | src/income_analytics/api/onboarding_v2.py:44 | no-untyped-call | Call to untyped function "response" in typed context | M-ANN |
| M0514 | src/income_analytics/api/onboarding_v2.py:46 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0515 | src/income_analytics/api/onboarding_v2.py:50 | no-untyped-call | Call to untyped function "facts" in typed context | M-ANN |
| M0516 | src/income_analytics/api/onboarding_v2.py:53 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0517 | src/income_analytics/api/onboarding_v2.py:54 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0518 | src/income_analytics/api/onboarding_v2.py:59 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0519 | src/income_analytics/api/onboarding_v2.py:60 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "status" | M-NULL |
| M0520 | src/income_analytics/api/onboarding_v2.py:61 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0521 | src/income_analytics/api/onboarding_v2.py:64 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "selected_class" | M-NULL |
| M0522 | src/income_analytics/api/onboarding_v2.py:64 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0523 | src/income_analytics/api/onboarding_v2.py:65 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0524 | src/income_analytics/api/onboarding_v2.py:68 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "first_asset_at" | M-NULL |
| M0525 | src/income_analytics/api/onboarding_v2.py:68 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0526 | src/income_analytics/api/onboarding_v2.py:69 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0527 | src/income_analytics/api/onboarding_v2.py:72 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "analysis_at" | M-NULL |
| M0528 | src/income_analytics/api/onboarding_v2.py:72 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "first_asset_at" | M-NULL |
| M0529 | src/income_analytics/api/onboarding_v2.py:72 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "status" | M-NULL |
| M0530 | src/income_analytics/api/onboarding_v2.py:72 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "completed_at" | M-NULL |
| M0531 | src/income_analytics/api/onboarding_v2.py:72 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0532 | src/income_analytics/api/onboarding_v2.py:73 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0533 | src/income_analytics/api/onboarding_v2.py:75 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "status" | M-NULL |
| M0534 | src/income_analytics/api/onboarding_v2.py:76 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "dismissed_at" | M-NULL |
| M0535 | src/income_analytics/api/onboarding_v2.py:77 | no-untyped-call | Call to untyped function "emit" in typed context | M-ANN |
| M0536 | src/income_analytics/api/onboarding_v2.py:78 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0537 | src/income_analytics/api/onboarding_v2.py:82 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "last_step" | M-NULL |
| M0538 | src/income_analytics/api/onboarding_v2.py:83 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "updated_at" | M-NULL |
| M0539 | src/income_analytics/api/onboarding_v2.py:85 | union-attr | Item "None" of "OnboardingJourneyV2Record &#124; None" has no attribute "first_asset_at" | M-NULL |
| M0540 | src/income_analytics/api/onboarding_v2.py:87 | no-untyped-call | Call to untyped function "response" in typed context | M-ANN |
| M0541 | src/income_analytics/application/portfolio_session.py:869 | assignment | Incompatible types in assignment (expression has type "MarketPrice", variable has type "Money") | M-COMPAT |
| M0542 | src/income_analytics/application/portfolio_session.py:877 | arg-type | Argument 1 to "append" of "list" has incompatible type "Money"; expected "MarketPrice" | M-COMPAT |
| M0543 | src/income_analytics/application/portfolio_session.py:878 | arg-type | Argument 1 to "_remember_market_price" of "PortfolioSession" has incompatible type "Money"; expected "MarketPrice" | M-COMPAT |
| M0544 | src/income_analytics/application/portfolio_session.py:945 | return-value | Incompatible return value type (got "tuple[object, tuple[str, ...], tuple[str, ...]]", expected "tuple[int, tuple[str, ...], tuple[str, ...]]") | M-COMPAT |
| M0545 | src/income_analytics/application/portfolio_session.py:945 | arg-type | Argument 1 to "tuple" has incompatible type "object"; expected "Iterable[str]" | M-COMPAT |
| M0546 | src/income_analytics/api/saas_security.py:67 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0547 | src/income_analytics/api/saas_security.py:77 | no-untyped-call | Call to untyped function "api_routes" in typed context | M-ANN |
| M0548 | src/income_analytics/api/saas_security.py:88 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0549 | src/income_analytics/api/saas_security.py:88 | no-untyped-def | Function is missing a type annotation for one or more parameters | M-ANN |
| M0550 | src/income_analytics/api/saas_security.py:99 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0551 | src/income_analytics/api/saas_security.py:110 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0552 | src/income_analytics/api/saas_security.py:126 | no-untyped-call | Call to untyped function "bounded_body" in typed context | M-ANN |
| M0553 | src/income_analytics/api/saas_security.py:169 | no-untyped-call | Call to untyped function "api_routes" in typed context | M-ANN |
| M0554 | src/income_analytics/api/routers/auth.py:30 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0555 | src/income_analytics/api/routers/auth.py:44 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0556 | src/income_analytics/api/routers/auth.py:57 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0557 | src/income_analytics/api/routers/auth.py:63 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0558 | src/income_analytics/api/routers/auth.py:83 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0559 | src/income_analytics/api/routers/auth.py:84 | no-untyped-call | Call to untyped function "require_firebase" in typed context | M-ANN |
| M0560 | src/income_analytics/api/routers/auth.py:97 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0561 | src/income_analytics/api/routers/auth.py:98 | no-untyped-call | Call to untyped function "require_firebase" in typed context | M-ANN |
| M0562 | src/income_analytics/api/routers/auth.py:134 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0563 | src/income_analytics/api/routers/auth.py:135 | no-untyped-call | Call to untyped function "require_firebase" in typed context | M-ANN |
| M0564 | src/income_analytics/api/routers/auth.py:146 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0565 | src/income_analytics/api/routers/auth.py:147 | no-untyped-call | Call to untyped function "require_firebase" in typed context | M-ANN |
| M0566 | src/income_analytics/api/routers/auth.py:158 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0567 | src/income_analytics/api/routers/auth.py:159 | no-untyped-call | Call to untyped function "require_firebase" in typed context | M-ANN |
| M0568 | src/income_analytics/api/routers/auth.py:177 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0569 | src/income_analytics/api/routers/auth.py:181 | no-untyped-call | Call to untyped function "fresh_current_identity" in typed context | M-ANN |
| M0570 | src/income_analytics/api/routers/auth.py:200 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0571 | src/income_analytics/api/routers/auth.py:205 | no-untyped-call | Call to untyped function "fresh_current_identity" in typed context | M-ANN |
| M0572 | src/income_analytics/api/routers/dashboard.py:145 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0573 | src/income_analytics/api/routers/dashboard.py:155 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0574 | src/income_analytics/api/routers/dashboard.py:158 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0575 | src/income_analytics/api/routers/dashboard.py:176 | no-untyped-call | Call to untyped function "_PortfolioRepositoryProxy" in typed context | M-ANN |
| M0576 | src/income_analytics/api/routers/dashboard.py:179 | no-untyped-call | Call to untyped function "_PortfolioRepositoryProxy" in typed context | M-ANN |
| M0577 | src/income_analytics/api/routers/dashboard.py:246 | misc | Generator has incompatible item type "tuple[str, str, str]"; expected "tuple[str, str, None]" | M-COMPAT |
| M0578 | src/income_analytics/api/routers/dashboard.py:605 | no-untyped-call | Call to untyped function "build_executable_plan" in typed context | M-ANN |
| M0579 | src/income_analytics/api/routers/dashboard.py:609 | no-any-return | Returning Any from function declared to return "dict[str, object]" | M-GEN |
| M0580 | src/income_analytics/api/routers/dashboard.py:1302 | no-any-return | Returning Any from function declared to return "dict[str, object]" | M-GEN |
| M0581 | src/income_analytics/api/routers/dashboard.py:1309 | no-any-return | Returning Any from function declared to return "dict[str, object]" | M-GEN |
| M0582 | src/income_analytics/api/routers/dashboard.py:1371 | no-any-return | Returning Any from function declared to return "dict[str, object] &#124; None" | M-GEN |
| M0583 | src/income_analytics/api/routers/dashboard.py:1378 | assignment | Incompatible default for parameter "request" (default has type "None", parameter has type "Request[State]") | M-COMPAT |
| M0584 | src/income_analytics/api/routers/dashboard.py:1402 | assignment | Incompatible default for parameter "request" (default has type "None", parameter has type "Request[State]") | M-COMPAT |
| M0585 | src/income_analytics/api/routers/dashboard.py:1483 | arg-type | Argument "label" to "AssetCompositionInput" has incompatible type "str &#124; None"; expected "str" | M-COMPAT |
| M0586 | src/income_analytics/api/routers/dashboard.py:1499 | arg-type | Argument "label" to "AssetCompositionInput" has incompatible type "str &#124; None"; expected "str" | M-COMPAT |
| M0587 | src/income_analytics/api/routers/dashboard.py:1631 | union-attr | Item "int" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "__iter__" (not iterable) | M-NULL |
| M0588 | src/income_analytics/api/routers/dashboard.py:1631 | union-attr | Item "Decimal" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "__iter__" (not iterable) | M-NULL |
| M0589 | src/income_analytics/api/routers/dashboard.py:1631 | union-attr | Item "None" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "__iter__" (not iterable) | M-NULL |
| M0590 | src/income_analytics/api/routers/dashboard.py:1632 | index | Invalid index type "str &#124; Decimal &#124; Any &#124; None" for "dict[str, AssetCompositionItem]"; expected type "str" | M-NULL |
| M0591 | src/income_analytics/api/routers/dashboard.py:1632 | index | Invalid index type "str" for "str"; expected type "SupportsIndex &#124; slice[SupportsIndex &#124; None, SupportsIndex &#124; None, SupportsIndex &#124; None]" | M-NULL |
| M0592 | src/income_analytics/api/routers/dashboard.py:1633 | union-attr | Item "str" of "dict[str, str &#124; Decimal &#124; Any &#124; None] &#124; str &#124; Any" has no attribute "update" | M-NULL |
| M0593 | src/income_analytics/api/routers/dashboard.py:1645 | union-attr | Item "dict[str, object]" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "extend" | M-NULL |
| M0594 | src/income_analytics/api/routers/dashboard.py:1645 | union-attr | Item "int" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "extend" | M-NULL |
| M0595 | src/income_analytics/api/routers/dashboard.py:1645 | union-attr | Item "str" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "extend" | M-NULL |
| M0596 | src/income_analytics/api/routers/dashboard.py:1645 | union-attr | Item "Decimal" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "extend" | M-NULL |
| M0597 | src/income_analytics/api/routers/dashboard.py:1645 | union-attr | Item "None" of "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None" has no attribute "extend" | M-NULL |
| M0598 | src/income_analytics/api/routers/dashboard.py:1671 | arg-type | Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None]], list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal]"; expected "Callable[[dict[str, list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal &#124; None]], SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]]" | M-COMPAT |
| M0599 | src/income_analytics/api/routers/dashboard.py:1671 | return-value | Incompatible return value type (got "list[dict[str, str &#124; Decimal &#124; Any &#124; None]] &#124; dict[str, object] &#124; int &#124; str &#124; Any &#124; Decimal", expected "SupportsDunderLT[Any] &#124; SupportsDunderGT[Any]") | M-COMPAT |
| M0600 | src/income_analytics/api/routers/dashboard.py:1940 | arg-type | Argument 1 to "setdefault" of "MutableMapping" has incompatible type "object"; expected "str" | M-COMPAT |
| M0601 | src/income_analytics/api/routers/dashboard.py:2202 | no-untyped-call | Call to untyped function "get" in typed context | M-ANN |
| M0602 | src/income_analytics/api/routers/dashboard.py:2207 | no-untyped-call | Call to untyped function "get" in typed context | M-ANN |
| M0603 | src/income_analytics/api/routers/dashboard.py:2225 | no-untyped-call | Call to untyped function "get" in typed context | M-ANN |
| M0604 | src/income_analytics/api/routers/dashboard.py:2236 | no-untyped-call | Call to untyped function "get" in typed context | M-ANN |
| M0605 | src/income_analytics/api/routers/dashboard.py:2247 | no-any-return | Returning Any from function declared to return "dict[str, object]" | M-GEN |
| M0606 | src/income_analytics/api/routers/dashboard.py:2452 | attr-defined | "object" has no attribute "id" | M-SHAPE |
| M0607 | src/income_analytics/api/routers/dashboard.py:2453 | attr-defined | "object" has no attribute "status" | M-SHAPE |
| M0608 | src/income_analytics/api/routers/dashboard.py:2454 | attr-defined | "object" has no attribute "file_name" | M-SHAPE |
| M0609 | src/income_analytics/api/routers/dashboard.py:2455 | attr-defined | "object" has no attribute "report_type" | M-SHAPE |
| M0610 | src/income_analytics/api/routers/dashboard.py:2457 | attr-defined | "object" has no attribute "total_rows" | M-SHAPE |
| M0611 | src/income_analytics/api/routers/dashboard.py:2458 | attr-defined | "object" has no attribute "new_rows" | M-SHAPE |
| M0612 | src/income_analytics/api/routers/dashboard.py:2459 | attr-defined | "object" has no attribute "duplicate_rows" | M-SHAPE |
| M0613 | src/income_analytics/api/routers/dashboard.py:2460 | attr-defined | "object" has no attribute "review_rows" | M-SHAPE |
| M0614 | src/income_analytics/api/routers/dashboard.py:2461 | attr-defined | "object" has no attribute "unsupported_rows" | M-SHAPE |
| M0615 | src/income_analytics/api/routers/dashboard.py:2462 | attr-defined | "object" has no attribute "invalid_rows" | M-SHAPE |
| M0616 | src/income_analytics/api/routers/dashboard.py:2466 | attr-defined | "object" has no attribute "source_row" | M-SHAPE |
| M0617 | src/income_analytics/api/routers/dashboard.py:2467 | attr-defined | "object" has no attribute "status" | M-SHAPE |
| M0618 | src/income_analytics/api/routers/dashboard.py:2468 | attr-defined | "object" has no attribute "detail" | M-SHAPE |
| M0619 | src/income_analytics/api/routers/dashboard.py:2469 | attr-defined | "object" has no attribute "event_date" | M-SHAPE |
| M0620 | src/income_analytics/api/routers/dashboard.py:2470 | attr-defined | "object" has no attribute "event_type" | M-SHAPE |
| M0621 | src/income_analytics/api/routers/dashboard.py:2471 | attr-defined | "object" has no attribute "income_type" | M-SHAPE |
| M0622 | src/income_analytics/api/routers/dashboard.py:2472 | attr-defined | "object" has no attribute "source_symbol" | M-SHAPE |
| M0623 | src/income_analytics/api/routers/dashboard.py:2473 | attr-defined | "object" has no attribute "normalized_symbol" | M-SHAPE |
| M0624 | src/income_analytics/api/routers/dashboard.py:2474 | attr-defined | "object" has no attribute "institution" | M-SHAPE |
| M0625 | src/income_analytics/api/routers/dashboard.py:2475 | attr-defined | "object" has no attribute "market" | M-SHAPE |
| M0626 | src/income_analytics/api/routers/dashboard.py:2476 | attr-defined | "object" has no attribute "quantity" | M-SHAPE |
| M0627 | src/income_analytics/api/routers/dashboard.py:2477 | attr-defined | "object" has no attribute "unit_price" | M-SHAPE |
| M0628 | src/income_analytics/api/routers/dashboard.py:2478 | attr-defined | "object" has no attribute "total_value" | M-SHAPE |
| M0629 | src/income_analytics/api/routers/dashboard.py:2479 | attr-defined | "object" has no attribute "quantity_status" | M-SHAPE |
| M0630 | src/income_analytics/api/routers/dashboard.py:2480 | attr-defined | "object" has no attribute "financial_status" | M-SHAPE |
| M0631 | src/income_analytics/api/routers/dashboard.py:2481 | attr-defined | "object" has no attribute "occurrence_index" | M-SHAPE |
| M0632 | src/income_analytics/api/routers/dashboard.py:2496 | attr-defined | "object" has no attribute "normalized_symbol" | M-SHAPE |
| M0633 | src/income_analytics/api/routers/dashboard.py:2497 | attr-defined | "object" has no attribute "normalized_symbol" | M-SHAPE |
| M0634 | src/income_analytics/api/routers/dashboard.py:2532 | attr-defined | "object" has no attribute "income_type" | M-SHAPE |
| M0635 | src/income_analytics/api/routers/dashboard.py:2626 | assignment | Incompatible types in assignment (expression has type "object", variable has type "B3ImportBatch &#124; None") | M-COMPAT |
| M0636 | src/income_analytics/api/routers/dashboard.py:2627 | arg-type | Argument 1 to "create_batch" of "SqliteB3ImportRepository" has incompatible type "None"; expected "B3ImportBatch" | M-COMPAT |
| M0637 | src/income_analytics/api/routers/dashboard.py:2629 | attr-defined | "object" has no attribute "status" | M-SHAPE |
| M0638 | src/income_analytics/api/routers/dashboard.py:2630 | arg-type | Argument 1 to "save_record" of "SqliteB3ImportRepository" has incompatible type "object"; expected "B3ImportedRecord" | M-COMPAT |
| M0639 | src/income_analytics/api/routers/dashboard.py:2682 | dict-item | Dict entry 2 has incompatible type "str": "str &#124; None"; expected "str": "str" | M-COMPAT |
| M0640 | src/income_analytics/api/routers/dashboard.py:2687 | attr-defined | "object" has no attribute "add" | M-SHAPE |
| M0641 | src/income_analytics/api/routers/dashboard.py:2704 | attr-defined | "object" has no attribute "save_record_in_session" | M-SHAPE |
| M0642 | src/income_analytics/api/routers/dashboard.py:2969 | no-untyped-call | Call to untyped function "get" in typed context | M-ANN |
| M0643 | src/income_analytics/api/routers/dashboard.py:3699 | var-annotated | Need type annotation for "valuation_by_date" (hint: "valuation_by_date: dict[<type>, <type>] = ...") | M-GEN |
| M0644 | src/income_analytics/api/routers/dashboard.py:3706 | no-any-return | Returning Any from function declared to return "PortfolioProjection" | M-GEN |
| M0645 | src/income_analytics/api/routers/dashboard.py:3708 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0646 | src/income_analytics/api/routers/dashboard.py:3845 | arg-type | Argument "performance_at" to "build_performance_comparison" has incompatible type "Callable[[date, date], object]"; expected "Callable[[date, date], PerformanceProjection]" | M-COMPAT |
| M0647 | src/income_analytics/api/routers/dashboard.py:4348 | attr-defined | "object" has no attribute "as_of" | M-SHAPE |
| M0648 | src/income_analytics/api/routers/dashboard.py:4349 | attr-defined | "object" has no attribute "base_currency" | M-SHAPE |
| M0649 | src/income_analytics/api/routers/dashboard.py:4350 | attr-defined | "object" has no attribute "invested_wealth" | M-SHAPE |
| M0650 | src/income_analytics/api/routers/dashboard.py:4351 | attr-defined | "object" has no attribute "strategy_distance" | M-SHAPE |
| M0651 | src/income_analytics/api/routers/dashboard.py:4352 | attr-defined | "object" has no attribute "valuation_status" | M-SHAPE |
| M0652 | src/income_analytics/api/routers/dashboard.py:4353 | attr-defined | "object" has no attribute "issues" | M-SHAPE |
| M0653 | src/income_analytics/api/routers/dashboard.py:4362 | attr-defined | "object" has no attribute "class_allocations" | M-SHAPE |
| M0654 | src/income_analytics/api/routers/portfolios.py:108 | union-attr | Item "None" of "Principal &#124; None" has no attribute "user_id" | M-NULL |
| M0655 | src/income_analytics/api/routers/portfolios.py:194 | union-attr | Item "None" of "Principal &#124; None" has no attribute "user_id" | M-NULL |
| M0656 | src/income_analytics/api/routers/portfolios.py:199 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0657 | src/income_analytics/api/routers/portfolios.py:213 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0658 | src/income_analytics/api/routers/portfolios.py:248 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0659 | src/income_analytics/api/routers/portfolios.py:252 | no-untyped-call | Call to untyped function "read" in typed context | M-ANN |
| M0660 | src/income_analytics/api/routers/portfolios.py:252 | union-attr | Item "None" of "Portfolio &#124; None" has no attribute "name" | M-NULL |
| M0661 | src/income_analytics/api/routers/portfolios.py:256 | no-untyped-def | Function is missing a return type annotation | M-ANN |
| M0662 | src/income_analytics/api/routers/portfolios.py:260 | no-untyped-call | Call to untyped function "update" in typed context | M-ANN |
| M0663 | src/income_analytics/api/routers/portfolios.py:260 | union-attr | Item "None" of "Portfolio &#124; None" has no attribute "name" | M-NULL |
| M0664 | src/income_analytics/api/routers/portfolios.py:260 | union-attr | Item "None" of "Principal &#124; None" has no attribute "user_id" | M-NULL |
| M0665 | src/income_analytics/api/routers/income_starter.py:86 | arg-type | Argument 4 to "adopt" of "IncomeStarterRepository" has incompatible type "dict[str, Decimal] &#124; Any &#124; dict[Any, Any]"; expected "dict[str, str &#124; Decimal]" | M-COMPAT |
| M0666 | src/income_analytics/main.py:65 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0667 | src/income_analytics/main.py:68 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0668 | src/income_analytics/main.py:69 | no-untyped-call | Call to untyped function "serve_portfolio" in typed context | M-ANN |
| M0669 | src/income_analytics/main.py:71 | no-untyped-call | Call to untyped function "authorize_request" in typed context | M-ANN |
| M0670 | src/income_analytics/main.py:82 | no-untyped-call | Call to untyped function "serve_portfolio" in typed context | M-ANN |
| M0671 | src/income_analytics/main.py:85 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0672 | src/income_analytics/main.py:112 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0673 | src/income_analytics/main.py:140 | no-untyped-def | Function is missing a type annotation | M-ANN |
| M0674 | src/income_analytics/main.py:172 | operator | Unsupported operand types for - ("float" and "object") | M-NULL |

## Reconciliação e limites

R001–R130 e M0001–M0674 sem exclusões/supressões; agrupamentos preservam repetições. Os 24 casos Python e FE-01 estão na [triagem](ci_failure_triage.md). Esta baseline não é allowlist executável, não altera exit codes nem transforma dívida em sucesso. Python, Node, Ruff, mypy e CERT_48 continuam reprovados.

Diagnóstico estático não substitui teste comportamental, auditoria de acesso ou certificação. Cobertura de linha não mede correção financeira. Node não é E2E real de browser. Skips externos continuam lacuna explícita.
