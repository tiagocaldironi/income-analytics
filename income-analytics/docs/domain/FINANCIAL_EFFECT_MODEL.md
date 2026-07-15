# Financial Effect Model (FEM)

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

The Financial Effect Model (FEM) defines the canonical behavioral model of every Financial Event.

Instead of processing events by their type (BUY, SELL, DIVIDEND...), the platform processes the **financial effects** produced by each event.

This approach dramatically reduces coupling between event types and business engines while making the system extensible and deterministic.

---

# Architectural Vision

```
                Financial Event

                       │

                       ▼

               Effect Resolver

                       │

      ┌────────────────┼────────────────┐

      ▼                ▼                ▼

 Position Effect   Cash Effect   Income Effect

      ▼                ▼                ▼

 Cost Effect      Tax Effect     FX Effect

      └────────────────┼────────────────┘

                       ▼

               Business Engines

                       ▼

                 Read Models
```

---

# Why Effects?

Traditional systems execute logic like:

```python
if event.type == BUY:
    ...

elif event.type == SELL:
    ...

elif event.type == DIVIDEND:
    ...
```

As the number of event types grows, complexity increases dramatically.

Instead, Income Analytics processes behaviors.

Every Financial Event declares **which effects it produces**.

Business engines consume effects, not event types.

---

# Design Principles

## 1. Events describe facts

Financial Events describe what happened.

---

## 2. Effects describe consequences

Effects describe what changed because the event occurred.

---

## 3. Engines consume effects

Business engines never need to know event names.

They only react to financial effects.

---

## 4. Event Types become metadata

Adding a new Financial Event should require little or no modification to business engines.

---

# Financial Effects

The platform recognizes the following canonical effects.

---

# Position Effect

Represents changes in asset ownership.

Examples:

- Buy
- Sell
- Split
- Reverse Split
- Bonus Shares
- Subscription
- Conversion

Produces:

- Quantity changes
- Position timeline

Consumed by:

- Position Engine
- Snapshot Engine
- Performance Engine

---

# Cash Effect

Represents money entering or leaving an account.

Examples:

- Deposit
- Withdrawal
- Dividend
- Buy
- Sell
- Fees
- Taxes

Produces:

- Cash balance
- Cash flow history

Consumed by:

- Snapshot Engine
- Performance Engine
- Goal Engine

---

# Income Effect

Represents passive income generation.

Examples:

- Dividend
- Interest
- Treasury Income
- Coupon
- FII Income
- Staking Reward

Produces:

- Monthly income
- Annual income
- Passive income history

Consumed by:

- Income Engine
- Goal Engine

---

# Cost Basis Effect

Represents changes in acquisition cost.

Examples:

- Buy
- Split
- Bonus Shares
- Subscription

Produces:

- Average Cost
- Cost Basis

Consumed by:

- Performance Engine
- Tax Engine

---

# Tax Effect

Represents taxable events.

Examples:

- Sell
- Redemption
- Withholding Tax
- Income Tax

Produces:

- Taxable gains
- Tax liabilities

Consumed by:

- Tax Engine

---

# FX Effect

Represents foreign exchange exposure.

Examples:

- Foreign Asset Purchase
- Currency Exchange
- Foreign Dividend

Produces:

- FX Gain
- FX Loss
- Currency Allocation

Consumed by:

- FX Engine
- Performance Engine

---

# Fee Effect

Represents operational costs.

Examples:

- Brokerage Fee
- Exchange Fee
- Custody Fee
- Administration Fee

Produces:

- Operational Expenses

Consumed by:

- Performance Engine

---

# Effect Matrix

| Effect | Position | Cash | Income | Cost | Tax | FX |
|---------|:-------:|:----:|:------:|:----:|:---:|:--:|
| Position Effect | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Cash Effect | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Income Effect | ❌ | ✅ | ✅ | ❌ | Depends | ❌ |
| Cost Basis Effect | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Tax Effect | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| FX Effect | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Fee Effect | ❌ | ✅ | ❌ | Depends | ❌ | ❌ |

---

# Event Mapping

## BUY

Effects:

- Position Effect
- Cash Effect
- Cost Basis Effect

---

## SELL

Effects:

- Position Effect
- Cash Effect
- Tax Effect

---

## DIVIDEND

Effects:

- Cash Effect
- Income Effect

---

## INTEREST

Effects:

- Cash Effect
- Income Effect

---

## SPLIT

Effects:

- Position Effect
- Cost Basis Effect

---

## BONUS SHARE

Effects:

- Position Effect
- Cost Basis Effect

---

## DEPOSIT

Effects:

- Cash Effect

---

## WITHDRAWAL

Effects:

- Cash Effect

---

## BROKERAGE FEE

Effects:

- Cash Effect
- Fee Effect

---

## FOREIGN DIVIDEND

Effects:

- Cash Effect
- Income Effect
- FX Effect

---

# Processing Model

```
Financial Event

↓

Effect Resolver

↓

Position Effect

↓

Position Engine

────────────────────

Financial Event

↓

Effect Resolver

↓

Income Effect

↓

Income Engine

────────────────────

Financial Event

↓

Effect Resolver

↓

Cash Effect

↓

Snapshot Engine
```

Each engine processes only the effects relevant to its responsibility.

---

# Business Advantages

This model provides:

- Low coupling
- High cohesion
- Open/Closed Principle
- Easy extensibility
- Deterministic processing
- Explainable calculations

---

# Example

## BUY Event

```
BUY PETR4

100 shares

R$ 32.50
```

Produces:

```
Position Effect

+100 shares

────────────────

Cash Effect

- R$ 3,250.00

────────────────

Cost Basis Effect

Average Cost Updated
```

---

## DIVIDEND

```
Dividend

PETR4

R$ 320
```

Produces:

```
Cash Effect

+320

───────────────

Income Effect

Dividend Income +320
```

---

## SPLIT

```
Split

1 → 2
```

Produces:

```
Position Effect

Quantity ×2

───────────────

Cost Basis Effect

Average Cost ÷2
```

---

# Engine Independence

Business engines never know event names.

They only process effects.

```
BUY

↓

Effects

↓

Position Engine
```

Instead of:

```
BUY

↓

Position Engine
```

This architecture makes the platform extensible without increasing engine complexity.

---

# Future Effects

The model can be extended with additional effects without modifying existing engines.

Examples:

- ESG Effect
- Risk Effect
- Liquidity Effect
- Credit Effect
- Inflation Effect

---

# ADR-006

## Decision

Income Analytics adopts the Financial Effect Model (FEM) as the internal behavioral model used by every business engine.

Financial Events describe facts.

Financial Effects describe consequences.

Business Engines consume Financial Effects.

---

## Benefits

- Reduced coupling
- Increased maintainability
- Generic business engines
- Easier event extensibility
- Explainable analytics
- Better Domain-Driven Design alignment

---

# Mission Statement

> **Financial Events describe facts. Financial Effects describe consequences. Business Engines transform those consequences into financial knowledge.**