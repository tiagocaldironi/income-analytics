# Finding Engine V2 — relatório final

FINDING_ENGINE_V2 = PASS (escopo fechado do motor; suíte global não está verde)

Execução real em 23/09/2026, após reinício do Uvicorn (PID 20932).
GET http://127.0.0.1:8000/api/portfolio/intelligence = HTTP 200.
A aplicação usa prefixo /api; /portfolio/intelligence sem esse prefixo retorna 404.
Site http://127.0.0.1:8000/ = HTTP 200.

## Contrato matemático

PORTFOLIO_DRIFT_FORMULA = (1/2) × Σ_classe |peso_atual − peso_alvo|.
PORTFOLIO_DRIFT_UNIT = fração adimensional [0,1], apresentada como percentual.
PORTFOLIO_DRIFT_INTERPRETATION = distância total de variação entre a distribuição
dos ativos investidos e a política-alvo. Com pesos normalizados, equivale à fração
do valor investido que precisaria mudar de classe para atingir a distribuição,
sem custos ou fluxos. Não é volatilidade, rentabilidade ou recomendação de operação.
PORTFOLIO_DRIFT_THRESHOLD_SEMANTICS = referência técnica Income de 0,10 (10%);
a regra dispara estritamente acima desse valor. Os alvos de classe pertencem
à política do usuário e são separados da referência técnica.

deviation_pp = 100 × (current_weight − target_weight).
drift = Σ |deviation_pp| / 200. A decomposição real abaixo reconcilia com o total;
comparações independentes usam tolerância decimal de 1e-24 para arredondamento
aritmético, sem alterar o valor publicado.

RISK_COVERAGE_FORMULA = Σ valor_em_BRL dos ativos abertos com alguma observação
persistida de preço economicamente disponível / Σ valor_em_BRL de todos os ativos
investidos abertos.
RISK_COVERAGE_DENOMINATOR = valor de mercado consolidado em BRL das posições
investidas abertas; exclui caixa. Renda fixa por curva entra no denominador,
mas a curva derivada não é tratada como série persistida de preços.
Essa cobertura mede presença de série, não suficiência estatística: o projetor
de risco ainda exige pelo menos dois ativos e três datas comuns para covariância.
Portanto 76,31% não significa que 76,31% do risco esteja mensurado.

COUNTRY_CONCENTRATION usa país do cadastro do ativo, não exposição econômica
look-through. 70% é referência técnica do Income, nunca meta do usuário.
NOT_APPLICABLE/UNKNOWN/UNCLASSIFIED não viram concentração. Dimensões com
classificação incompleta são suprimidas (peso classificado mínimo 0,999999).

## Semântica temporal, materialidade e qualidade

comparison_as_of = as_of − 90 dias corridos. A reconstrução utiliza effective_date;
created_at não participa da comparação. Eventos, preços e FX posteriores ao corte
não são usados; preço atual sem data também não substitui preço histórico.
A comparação aplica a política atual nas duas datas e declara explicitamente
CURRENT_POLICY_APPLIED_TO_BOTH_DATES: não afirma conhecer uma política histórica.
Classificações do cadastro também não possuem versionamento histórico neste fluxo.

change = current_value − comparison_value, em fração; change_pp = 100 × change.
Exemplo: comparação 91% e atual 96,28% resultam em +0,0528 e +5,28 p.p.
Isso não é variação relativa percentual. Valores internos são Decimal; a API
preserva precisão em strings decimais. PERCENTAGE significa fração a multiplicar
por 100 apenas na apresentação. PERCENTAGE_POINTS já está em p.p.

Para drift e país: NEW cruza a referência de baixo para cima; WORSENING/IMPROVING
exigem mudança maior que 1 p.p. em módulo, com ambos os estados acima da referência;
PERSISTENT cobre mudanças de até 1 p.p. inclusive. RESOLVED está suportado no domínio
quando o estado antes acima volta à referência ou abaixo, mas não é inventado na
lista de findings ativos. Histórico não defensável resulta em UNKNOWN e valores
de comparação/change nulos. Não há atribuição causal especulativa: causes = [].

Materialidade determinística: excesso sobre a referência >= a própria referência
é HIGH para exposição/estratégia; excesso >1 p.p. é MEDIUM, demais LOW. Para
qualidade, a magnitude é 1 − cobertura: >1 p.p. MEDIUM, demais LOW.
should_surface exige magnitude >0,1 p.p. e valuation atual completo, salvo os
próprios avisos de qualidade. Não há score opaco. As razões estão no payload.

PARTIAL nos três findings reais decorre da comparação histórica limitada; não
significa ausência de valuation atual. Os flags current_valuation_complete e
comparison_valuation_complete distinguem essas situações.

## Carteira real e revisão de produto

| Finding | Valor atual | Trajetória | USEFUL | MISLEADING | REDUNDANT |
|---|---:|---|---|---|---|
| PORTFOLIO_DRIFT | 39,14% | UNKNOWN | YES | NO | NO |
| COUNTRY_CONCENTRATION | 84,31% Brasil | UNKNOWN | YES | NO | NO |
| INCOMPLETE_RISK_COVERAGE | 76,31% | UNKNOWN | YES | NO | NO |

- PORTFOLIO_DRIFT — REASON: quantifica a distância da política 60% ações Brasil /
  40% FIIs, com decomposição por classe auditável. Não afirma evolução histórica
  nem sugere compras/vendas. Distinto da concentração geográfica.
- COUNTRY_CONCENTRATION — REASON: informa o país cadastrado predominante e sua
  referência técnica, com sujeito Brasil explícito; não confunde 70% com alvo.
- INCOMPLETE_RISK_COVERAGE — REASON: evidencia limitação analítica. Numerador,
  denominador e does_not_guarantee_covariance evitam interpretá-la como medida de
  risco coberto. Não deve ser usada isoladamente como selo de análise de risco.

Essas avaliações consideram o contrato completo e suas ressalvas estruturadas.
O redesign definitivo permanece pendente para revisão de produto.

A comparação real de 25/06/2026 contém 39 posições abertas, apenas 2 com valuation
disponível (5,13% de cobertura por quantidade de posições, não por valor).
Assim, não é defensável fabricar a exposição ou o drift histórico: UNKNOWN
nos três resultados é o comportamento correto. O motor calcula trajetórias
conhecidas nos casos testados com dados suficientes.

Correção relevante: os pesos anteriores somavam BRL e USD nominais. O contexto
dos findings agora consome a conversão em moeda-base já existente. Por isso os
valores anteriores (como cobertura de risco de 72,95%) não foram congelados como
expectativa. Foram recalculados e reconciliados em BRL. Os projetores globais de
reconciliação/Entender e suas fórmulas não foram alterados.

## Contagens reais

SURFACED_FINDINGS_COUNT = 3
NEW_COUNT = 0
WORSENING_COUNT = 0
IMPROVING_COUNT = 0
PERSISTENT_COUNT = 0
RESOLVED_COUNT = 0
UNKNOWN_COUNT = 3
DATA_QUALITY_COMPLETE = 0
DATA_QUALITY_PARTIAL = 3
DATA_QUALITY_INSUFFICIENT = 0
DATA_QUALITY_LIMITED_COUNT = 3
CAUSES_AVAILABLE_COUNT = 0

## Validação

- pytest focado final: 22 passed (15 casos Finding Engine V2 + 7 PortfolioSession).
- pytest completo: 529 passed, 3 failed, 25 errors. Falhas fora da implementação:
  duas expectativas de frontend legado (B3/Entender), e teste de estado dos cinco
  issuers Petrobras; os 25 erros de setup são GOLDEN_EVIDENCE_DEFECT:SCHEMA_HEAD
  no módulo Petrobras. Não foram corrigidos neste escopo. Esta rodada precedeu
  o último teste adicional de compatibilidade da regra de contribuição de risco;
  a rodada focada final acima cobre esse ajuste.
- A primeira rodada completa encontrou restrição no diretório temporário padrão.
  A rodada acima foi repetida com --basetemp em tmp dentro do projeto.
- Ruff: engine, contrato, PortfolioSession e testes V2 passam. No arquivo amplo
  dashboard.py permanecem I001 no bloco de imports, F401 (SessionFactory) e F601
  (unvalued_positions duplicado em outro endpoint), fora do trecho V2.
- mypy --follow-imports=silent: PASS no engine e contrato. Incluindo session e
  dashboard: 49 erros em trechos fora do V2 (2 em session:796, 47 no dashboard).
- node --check intelligence.js: PASS.
- git diff --check: PASS; avisos de conversão LF/CRLF, sem erros de whitespace.
- Read-back HTTP repetido: determinístico. Conferência independente do país,
  denominador/numerador de cobertura e decomposição do drift: PASS.

Logs completos em tmp/finding-v2-pytest-complete.txt,
tmp/finding-v2-targeted-tests.txt, tmp/finding-v2-mypy.txt e tmp/finding-v2-ruff.txt.
Não se declara a suíte global PASS.

## Arquivos e escopo

- src/income_analytics/domain/read_models/portfolio_intelligence.py — campos V2.
- src/income_analytics/domain/projectors/portfolio_diagnostic_engine.py —
  enriquecimento determinístico, trajetória, evidências, materialidade e decomposição.
- src/income_analytics/application/portfolio_session.py — contexto em moeda-base
  e reconstrução econômica de 90 dias, sem fallback de preço atual sem data.
- src/income_analytics/api/routers/dashboard.py — serialização do contrato V2.
- src/income_analytics/api/static/js/features/intelligence.js — adaptação mínima
  de consumo: categorias V2, should_surface e evidências percentuais legíveis.
  Layout preservado; nenhum redesign de Pontos de Atenção ou alteração em Entender.
- tests/application/test_finding_engine_v2.py — casos de trajetória, campos,
  reconciliação, FX/preços/eventos futuros, dados ausentes e serialização.
- docs/FINDING_ENGINE_V2_FINAL_REPORT.md — este relatório com payload integral.
- tmp/validate-finding-v2.py, tmp/finding-engine-v2-real.json e
  tmp/finding-engine-v2-audit.json — evidência reproduzível da validação local.

Worktree já continha numerosas mudanças de outras fases. Elas foram preservadas.
Não houve reset, commit ou push. Sem GenAI, novos providers, backfill ou ranking.

Serviço reiniciado com --lifespan off para não disparar os jobs automáticos de
refresh/backfill durante esta validação. Site e API estão online; os jobs de
startup ficam desativados nesta instância até um reinício normal autorizado.

## Auditoria independente da carteira real

```json
{
  "endpoint": "http://127.0.0.1:8000/api/portfolio/intelligence",
  "economic_as_of": "2026-09-23",
  "comparison_as_of": "2026-06-25",
  "base_currency": "BRL",
  "invested_market_value": "90706.86960356930503859173286",
  "risk_covered_market_value": "69220.348422416716",
  "current_positions": 41,
  "comparison_open_positions": 39,
  "comparison_valued_positions": 2,
  "comparison_valuation_coverage": "0.05128205128205128205128205128",
  "comparison_unvalued_assets": [
    "ALZR11",
    "AMT",
    "AWK",
    "BBAS3",
    "BBSE3",
    "BTC",
    "BTHF11",
    "BTLG11",
    "CAT",
    "CMIG4",
    "CPTS11",
    "CXSE3",
    "DLR",
    "GARE11",
    "GGRC11",
    "HFOF11",
    "HSML11",
    "ITSA4",
    "JPM",
    "KLBN3",
    "KO",
    "MCD",
    "MXRF11",
    "PEP",
    "PETR4",
    "PG",
    "PLD",
    "PLTR",
    "RURA11",
    "SAPR3",
    "SNAG11",
    "SWK",
    "TAEE3",
    "VISC11",
    "VIVT3",
    "WEGE3",
    "XPSF11"
  ],
  "determinism": "PASS",
  "independent_country_reconciliation": "PASS",
  "independent_risk_coverage_reconciliation": "PASS",
  "drift_decomposition_reconciliation": "PASS",
  "surfaced_findings_count": 3,
  "trajectories": {
    "UNKNOWN": 3
  },
  "data_quality": {
    "PARTIAL": 3
  },
  "causes_available_count": 0
}
```

## Payload V2 real completo, sem omissão de findings

evidence conserva o mapa legado; structured_evidence é a evidência humana V2.

```json
{
  "as_of": "2026-09-23",
  "counts": {
    "info": 1,
    "attention": 2,
    "high_attention": 0
  },
  "findings": [
    {
      "code": "PORTFOLIO_DRIFT",
      "category": "STRATEGY",
      "severity": "ATTENTION",
      "title": "Desvio da política-alvo",
      "description": "Desvio da política-alvo.",
      "evidence": {
        "drift": "0.3914165460536653773858624262",
        "threshold": "0.10"
      },
      "as_of": "2026-09-23",
      "logical_key": "PORTFOLIO_DRIFT:PORTFOLIO:ALLOCATION_POLICY",
      "current_value": "0.3914165460536653773858624262",
      "comparison_value": null,
      "comparison_as_of": "2026-06-25",
      "change": null,
      "change_pp": null,
      "decomposition": [
        {
          "asset_class": "BRAZILIAN_STOCK",
          "label": "Ações Brasil",
          "current_weight": "0.3333981222389136489661817527",
          "target_weight": "0.6",
          "deviation_pp": "-26.66018777610863510338182473"
        },
        {
          "asset_class": "CRYPTO",
          "label": "Cripto",
          "current_weight": "0.09371077836305612785272870472",
          "target_weight": "0",
          "deviation_pp": "9.371077836305612785272870472"
        },
        {
          "asset_class": "FII",
          "label": "FIIs",
          "current_weight": "0.2751853317074209736479558211",
          "target_weight": "0.4",
          "deviation_pp": "-12.48146682925790263520441789"
        },
        {
          "asset_class": "FIXED_INCOME",
          "label": "Renda fixa",
          "current_weight": "0.2368786540099835709168721077",
          "target_weight": "0",
          "deviation_pp": "23.68786540099835709168721077"
        },
        {
          "asset_class": "INTERNATIONAL",
          "label": "Exterior",
          "current_weight": "0.05595065517926654415771101960",
          "target_weight": "0",
          "deviation_pp": "5.595065517926654415771101960"
        },
        {
          "asset_class": "US_REIT",
          "label": "REITs EUA",
          "current_weight": "0.004876458501359134458550594175",
          "target_weight": "0",
          "deviation_pp": "0.4876458501359134458550594175"
        }
      ],
      "subject": {
        "dimension": "PORTFOLIO",
        "key": "ALLOCATION_POLICY",
        "label": "Política de alocação"
      },
      "reference": {
        "type": "INCOME_TECHNICAL_THRESHOLD",
        "value": "0.10",
        "policy": {
          "type": "USER_ALLOCATION_POLICY",
          "targets": {
            "BRAZILIAN_STOCK": "0.6",
            "CRYPTO": "0",
            "FII": "0.4",
            "FIXED_INCOME": "0",
            "INTERNATIONAL": "0",
            "US_REIT": "0"
          }
        },
        "comparison_basis": "CURRENT_POLICY_APPLIED_TO_BOTH_DATES"
      },
      "trajectory": "UNKNOWN",
      "materiality": "HIGH",
      "materiality_reasons": [
        "EXCESS_AT_LEAST_REFERENCE"
      ],
      "should_surface": true,
      "structured_evidence": [
        {
          "type": "CURRENT_VALUE",
          "label": "Distância agregada à política de alocação",
          "value": "0.3914165460536653773858624262",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        },
        {
          "type": "REFERENCE",
          "label": "Referência técnica do Income",
          "value": "0.10",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        }
      ],
      "causes": [],
      "data_quality": {
        "status": "PARTIAL",
        "issues": [
          "INSUFFICIENT_COMPARISON_VALUATION"
        ],
        "current_valuation_complete": true,
        "comparison_valuation_complete": false
      }
    },
    {
      "code": "COUNTRY_CONCENTRATION",
      "category": "EXPOSURE",
      "severity": "ATTENTION",
      "title": "Concentração de exposição",
      "description": "Concentração de exposição.",
      "evidence": {
        "key": "BR",
        "weight": "0.8431006550593529205250888068",
        "threshold": "0.70",
        "reference_type": "INCOME_TECHNICAL_THRESHOLD"
      },
      "as_of": "2026-09-23",
      "logical_key": "COUNTRY_CONCENTRATION:COUNTRY:BR",
      "current_value": "0.8431006550593529205250888068",
      "comparison_value": null,
      "comparison_as_of": "2026-06-25",
      "change": null,
      "change_pp": null,
      "decomposition": [],
      "subject": {
        "dimension": "COUNTRY",
        "key": "BR",
        "label": "Brasil"
      },
      "reference": {
        "type": "INCOME_TECHNICAL_THRESHOLD",
        "value": "0.70"
      },
      "trajectory": "UNKNOWN",
      "materiality": "MEDIUM",
      "materiality_reasons": [
        "REFERENCE_BREACH"
      ],
      "should_surface": true,
      "structured_evidence": [
        {
          "type": "CURRENT_VALUE",
          "label": "Exposição atual",
          "value": "0.8431006550593529205250888068",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        },
        {
          "type": "REFERENCE",
          "label": "Referência técnica do Income",
          "value": "0.70",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        }
      ],
      "causes": [],
      "data_quality": {
        "status": "PARTIAL",
        "issues": [
          "INSUFFICIENT_COMPARISON_VALUATION"
        ],
        "current_valuation_complete": true,
        "comparison_valuation_complete": false
      }
    },
    {
      "code": "INCOMPLETE_RISK_COVERAGE",
      "category": "DATA_QUALITY",
      "severity": "INFO",
      "title": "Cobertura de risco incompleta",
      "description": "Cobertura de risco incompleta.",
      "evidence": {
        "coverage": "0.7631213459900164290831278922"
      },
      "as_of": "2026-09-23",
      "logical_key": "INCOMPLETE_RISK_COVERAGE:PORTFOLIO:RISK_COVERAGE",
      "current_value": "0.7631213459900164290831278922",
      "comparison_value": null,
      "comparison_as_of": "2026-06-25",
      "change": null,
      "change_pp": null,
      "decomposition": [],
      "subject": {
        "dimension": "PORTFOLIO",
        "key": "RISK_COVERAGE",
        "label": "Cobertura de risco"
      },
      "reference": {
        "type": "ANALYSIS_COMPLETENESS",
        "value": "1",
        "denominator": "BASE_CURRENCY_MARKET_VALUE_OF_OPEN_INVESTED_POSITIONS",
        "numerator": "MARKET_VALUE_OF_POSITIONS_WITH_ANY_PERSISTED_PRICE_SERIES",
        "does_not_guarantee_covariance": true
      },
      "trajectory": "UNKNOWN",
      "materiality": "MEDIUM",
      "materiality_reasons": [
        "DATA_COVERAGE_LIMITED"
      ],
      "should_surface": true,
      "structured_evidence": [
        {
          "type": "CURRENT_VALUE",
          "label": "Peso dos ativos com série de preços",
          "value": "0.7631213459900164290831278922",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        },
        {
          "type": "REFERENCE",
          "label": "Completude esperada",
          "value": "1",
          "unit": "PERCENTAGE",
          "as_of": "2026-09-23"
        }
      ],
      "causes": [],
      "data_quality": {
        "status": "PARTIAL",
        "issues": [
          "INSUFFICIENT_COMPARISON_VALUATION",
          "INCOMPLETE_RISK_COVERAGE"
        ],
        "current_valuation_complete": true,
        "comparison_valuation_complete": false
      }
    }
  ]
}
```
