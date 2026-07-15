# Domain Model

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

This document presents the conceptual model of the Income Analytics domain.

It describes the primary domain objects and their relationships independently of implementation details.

---

# Conceptual Model

```
                     Investor

                          │

        ┌─────────────────┴─────────────────┐

        ▼                                   ▼

    Account                          Institution

        │

        ▼

 Financial Ledger

        │

        ▼

 Financial Event

        │

        ▼

 Financial Effect

        │

        ▼

 Business Engines

        │

        ▼

 Read Models

 ├── Portfolio
 ├── Position
 ├── Snapshot
 ├── Performance
 ├── Allocation
 ├── Cash Flow
 └── Passive Income
```

---

# Domain Objects

## Investor

Represents the owner of one or more investment accounts.

---

## Account

Represents an investment account maintained by a financial institution.

Each Account has exactly one Financial Ledger.

---

## Institution

Represents the organization responsible for maintaining an Account or issuing Assets.

---

## Asset

Represents a financial instrument.

Examples:

- Stock
- ETF
- Treasury Bond
- Cryptocurrency

---

## Financial Ledger

Represents the immutable history of an investment account.

Acts as the Aggregate Root of the Financial Ledger Context.

---

## Financial Event

Represents a historical financial fact.

Examples:

- Buy
- Sell
- Dividend
- Deposit
- Withdrawal

Financial Events are immutable.

---

## Financial Effect

Represents the financial consequences of a Financial Event.

Examples:

- Position Effect
- Cash Effect
- Income Effect
- Tax Effect
- FX Effect

---

# Business Engines

Business Engines transform Financial Events into financial knowledge.

Examples:

- Position Engine
- Income Engine
- Performance Engine
- Snapshot Engine
- FX Engine
- Tax Engine

---

# Read Models

Read Models are optimized projections.

Examples:

- Portfolio
- Position
- Allocation
- Performance
- Cash Flow
- Net Worth

Read Models are disposable and reproducible.

---

# Relationships

```
Investor

│

├── Account

│      │

│      ▼

│ Financial Ledger

│      │

│      ▼

│ Financial Event

│      │

│      ▼

│ Financial Effect

│      │

│      ▼

│ Business Engines

│      │

│      ▼

│ Read Models

│
├── Asset
│
├── Institution
│
├── Broker
│
└── Currency
```

---

# Aggregate Roots

## Master Data Context

- Asset
- Institution
- Broker
- Currency
- Account

---

## Financial Ledger Context

- Financial Ledger

---

# Value Objects

Examples include:

- Money
- Ticker
- CurrencyCode
- Percentage
- Quantity
- ExchangeRate

---

# Entities

Examples include:

- Financial Event
- Asset
- Institution
- Broker
- Currency
- Account

---

# Domain Services

Future Domain Services include:

- Event Processor
- Event Replay
- Average Cost Calculator
- FX Calculator
- Tax Calculator
- Portfolio Consolidator

---

# Read Model Pipeline

```
Financial Ledger

↓

Financial Events

↓

Financial Effects

↓

Business Engines

↓

Read Models

↓

API
```

---

# Domain Philosophy

The domain is centered around immutable financial history.

Knowledge is reconstructed rather than stored.

Financial Events describe facts.

Financial Effects describe consequences.

Business Engines produce knowledge.

Read Models expose knowledge.

---

# Domain Principles

- Facts are immutable.
- Events are the source of truth.
- Read Models are disposable.
- Business engines are deterministic.
- Financial history is reproducible.
- Portfolio is a projection.
- Snapshots are optimization artifacts.

---

# ADR-011

## Decision

Income Analytics models financial history through immutable Financial Events stored in a Financial Ledger.

Every analytical capability is derived by deterministic processing of those events.

---

# Mission Statement

> **The Domain Model of Income Analytics transforms immutable financial history into explainable financial knowledge through deterministic processing and domain-driven design.**