# Financial Event Processing

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

This document defines how Financial Events are processed inside the Income Analytics platform.

It specifies the processing pipeline, validation rules, business responsibilities, and how each engine contributes to reconstructing an investor's financial history.

The goal is to ensure that every Financial Event follows a deterministic, auditable and reproducible lifecycle.

---

# Architectural Vision

```
                     Financial Event

                           │

                           ▼

                 Validation Engine

                           │

                           ▼

              Canonical Validation Engine

                           │

                           ▼

               Business Rules Engine

                           │

            ┌──────────────┼──────────────┐
            ▼              ▼              ▼

      Position Engine  Income Engine  Snapshot Engine

            │              │              │

            └──────────────┼──────────────┘

                           ▼

                Analytics Query Layer
```

---

# Processing Principles

## 1. Events are immutable

A Financial Event represents a historical fact.

Once persisted, it is never modified.

Corrections are represented by new events.

---

## 2. Processing is deterministic

Given the same sequence of events, the system must always produce exactly the same result.

No calculation may depend on external mutable state.

---

## 3. Processing is idempotent

Processing the same event multiple times must never generate duplicated results.

Each event is processed exactly once.

---

## 4. Business engines are independent

Each engine has a single responsibility.

No engine should modify another engine's internal state.

---

# Processing Pipeline

Every Financial Event follows the same lifecycle.

```
Financial Event

        │

        ▼

Validation

        │

        ▼

Canonical Validation

        │

        ▼

Business Rules

        │

        ▼

Engine Dispatch

        │

 ┌──────┼────────┬─────────┐

 ▼      ▼        ▼         ▼

Position Income Snapshot Performance

        │

        ▼

Analytics
```

---

# Step 1 — Validation Engine

Responsible for validating the event integrity.

Examples:

- Required fields
- Invalid dates
- Invalid quantity
- Invalid amount
- Unknown account
- Unknown asset

If validation fails:

- Event is rejected
- Processing stops

---

# Step 2 — Canonical Validation

Ensures the event complies with the Canonical Financial Event Model.

Examples:

- BUY requires quantity
- SELL requires quantity
- DIVIDEND requires amount
- SPLIT requires ratio
- APPLICATION requires amount

This stage validates business structure, not business rules.

---

# Step 3 — Business Rules Engine

Responsible for validating domain rules.

Examples:

Cannot sell more shares than currently owned.

Cannot redeem more than invested.

Cannot apply negative quantity.

Cannot transfer to the same account.

Cannot process duplicated external transaction.

---

# Step 4 — Engine Dispatch

Once validated, the event is delivered to every engine interested in its behavior.

The Financial Event does not know the engines.

The engines subscribe to event characteristics.

---

# Position Engine

## Responsibility

Reconstruct portfolio positions.

Produces:

- Current Quantity
- Historical Quantity
- Position Timeline

Consumes events:

- BUY
- SELL
- SPLIT
- REVERSE_SPLIT
- BONUS_SHARE
- SUBSCRIPTION
- CONVERSION

Does not process:

- DIVIDEND
- DEPOSIT
- WITHDRAWAL

---

# Income Engine

## Responsibility

Calculate passive income.

Produces:

- Dividends
- Interest
- Coupons
- Monthly Income
- Annual Income

Consumes:

- DIVIDEND
- INTEREST_ON_EQUITY
- FII_INCOME
- FIXED_INCOME_INTEREST
- TREASURY_INTEREST
- STAKING_REWARD

---

# Snapshot Engine

## Responsibility

Reconstruct portfolio state for any date.

Produces:

- Portfolio Snapshot
- Historical Net Worth
- Historical Allocation
- Historical Cash Balance

Consumes:

Every Financial Event.

---

# Performance Engine

## Responsibility

Calculate investment performance.

Produces:

- Total Return
- Annual Return
- Time Weighted Return
- Money Weighted Return
- Unrealized Gain
- Realized Gain

Consumes:

Every Financial Event.

---

# FX Engine

## Responsibility

Calculate currency exposure.

Produces:

- FX Gain
- FX Loss
- Currency Allocation
- FX Contribution

Consumes:

Events associated with foreign assets.

---

# Tax Engine (Future)

## Responsibility

Tax calculation.

Produces:

- Taxable Gain
- Tax Reports
- DARF calculations
- Cost Basis

Consumes:

- BUY
- SELL
- REDEMPTION

---

# Goal Engine (Future)

## Responsibility

Financial planning.

Produces:

- Goal Progress
- Passive Income Forecast
- Retirement Forecast
- Financial Independence Metrics

---

# Event Behaviors

Instead of checking specific event names, engines evaluate event capabilities.

Example:

```
BUY

affects_position = true

affects_cash = true

affects_income = false

affects_average_cost = true
```

Example:

```
DIVIDEND

affects_position = false

affects_cash = true

affects_income = true

affects_average_cost = false
```

This allows engines to remain generic and independent from specific event types.

---

# Engine Responsibilities

| Engine | Responsibility |
|----------|----------------|
| Validation Engine | Validate event integrity |
| Canonical Validation | Validate CFEM compliance |
| Business Rules Engine | Validate domain rules |
| Position Engine | Portfolio reconstruction |
| Income Engine | Passive income calculation |
| Snapshot Engine | Historical reconstruction |
| Performance Engine | Investment performance |
| FX Engine | Currency impact |
| Tax Engine | Tax calculation |
| Goal Engine | Financial planning |

---

# Processing Example

## BUY Event

```
BUY

↓

Validation

↓

Canonical Validation

↓

Business Rules

↓

Position Engine

+100 shares

↓

Snapshot Engine

Portfolio updated

↓

Performance Engine

Average cost updated

↓

Analytics
```

---

## DIVIDEND Event

```
DIVIDEND

↓

Validation

↓

Canonical Validation

↓

Income Engine

Passive Income

↓

Snapshot Engine

Cash updated

↓

Analytics
```

---

## SPLIT Event

```
SPLIT

↓

Validation

↓

Position Engine

Quantity updated

↓

Performance Engine

Average price recalculated

↓

Snapshot Engine

Portfolio reconstructed
```

---

# Processing Guarantees

The processing pipeline guarantees:

- Deterministic execution
- Idempotent execution
- Immutable history
- Explainable calculations
- Complete auditability
- Historical reconstruction
- Engine independence

---

# Architectural Rules

## Rule 1

Every engine has a single responsibility.

---

## Rule 2

Engines never communicate directly.

All communication occurs through Financial Events.

---

## Rule 3

Engines never modify Financial Events.

Events are immutable.

---

## Rule 4

Derived data is never the source of truth.

Only Financial Events are authoritative.

---

## Rule 5

Every calculation must be reproducible.

Running the same event history twice must produce exactly the same result.

---

# Future Evolution

Future processing capabilities include:

- Parallel event processing
- Event replay
- Incremental snapshots
- Event versioning
- Distributed processing
- Real-time streaming
- AI-assisted financial explanations

---

# Mission Statement

> **The Financial Event Processing pipeline transforms immutable financial events into explainable financial knowledge while preserving reproducibility, auditability and deterministic behavior.**