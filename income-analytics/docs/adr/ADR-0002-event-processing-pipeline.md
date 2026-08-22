# ADR-0002 — Event Processing Pipeline

- **Status:** Accepted
- **Data:** 2026-07-15

## Contexto

O Income Analytics adota Event Sourcing como modelo de persistência do domínio.

O Financial Ledger representa a fonte única da verdade (Source of Truth), armazenando todos os Financial Events em ordem cronológica.

Entretanto, usuários não consomem eventos. Eles consomem projeções como:

- Carteira
- Posições
- Caixa
- Dividendos
- Rentabilidade

Era necessário definir uma arquitetura que transformasse eventos em projeções mantendo baixo acoplamento e alta extensibilidade.

---

## Decisão

O pipeline de processamento será composto pelas seguintes etapas:

```
FinancialEvent
        │
        ▼
FinancialEffectFactory
        │
        ▼
FinancialEffects
        │
        ▼
Effect Engines
        │
        ▼
Projection Builder
        │
        ▼
Read Models
```

### FinancialEvent

Representa um fato imutável ocorrido no domínio.

Exemplos:

- BUY
- SELL
- DIVIDEND
- SPLIT

---

### FinancialEffectFactory

Traduz um FinancialEvent em um ou mais FinancialEffects.

Exemplo:

BUY

↓

- PositionEffect
- CashEffect
- CostBasisEffect

A Factory conhece apenas regras de tradução entre eventos e efeitos.

---

### FinancialEffects

Representam as consequências de um evento.

São imutáveis e independentes de qualquer projeção.

---

### Effect Engines

Cada Engine conhece apenas um tipo de efeito.

Exemplos:

- PositionEffectEngine
- CashEffectEngine
- IncomeEffectEngine
- CostBasisEffectEngine

Os Engines nunca interpretam FinancialEvents.

---

### Projection Builder

Coordena todo o pipeline.

Responsabilidades:

- percorrer os eventos do Ledger;
- utilizar a FinancialEffectFactory;
- distribuir os efeitos para os Engines;
- montar os Read Models.

Não contém regras de negócio.

---

### Read Models

Representam a visão atual do domínio.

Exemplos:

- PortfolioProjection
- PositionProjection
- CashProjection
- IncomeProjection

Read Models são somente leitura e não contêm regras de negócio.

---

## Consequências

### Benefícios

- Baixo acoplamento.
- Alta coesão.
- Engines independentes.
- Fácil inclusão de novos FinancialEventType.
- Fácil inclusão de novos Read Models.
- Alta testabilidade.

### Trade-offs

- Maior número de classes.
- Pipeline de processamento mais elaborado.

O ganho de extensibilidade justifica essa complexidade adicional.

---

## Fluxo completo

```
FinancialLedger
        │
        ▼
FinancialEvent
        │
        ▼
FinancialEffectFactory
        │
        ▼
FinancialEffects
        │
        ├────────► PositionEffectEngine
        ├────────► CashEffectEngine
        ├────────► IncomeEffectEngine
        ├────────► CostBasisEffectEngine
        └────────► TaxEffectEngine
                      │
                      ▼
              ProjectionBuilder
                      │
                      ▼
             PortfolioProjection
```