# Bounded Contexts

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

This document defines the Bounded Contexts of the Income Analytics platform.

Each context encapsulates a specific business capability, owns its own model, and evolves independently.

The objective is to maximize cohesion, reduce coupling, and clearly separate responsibilities across the domain.

---

# Domain Overview

```
                    Income Analytics

┌────────────────────────────────────────────┐

        Master Data Context

└────────────────────────────────────────────┘

                    │

                    ▼

┌────────────────────────────────────────────┐

      Financial Ledger Context

└────────────────────────────────────────────┘

                    │

                    ▼

┌────────────────────────────────────────────┐

         Analytics Context

└────────────────────────────────────────────┘

            │               │

            ▼               ▼

     Tax Context     Planning Context
```

---

# Core Domain

The **Financial Ledger Context** is the Core Domain of Income Analytics.

Every other context depends directly or indirectly on it.

---

# Master Data Context

## Purpose

Manage static business reference data.

---

## Responsibilities

- Assets
- Asset Types
- Institutions
- Brokers
- Exchanges
- Markets
- Currencies
- Accounts

---

## Aggregate Roots

- Asset
- Institution
- Broker
- Currency
- Account

---

## Owns

- Reference data
- Classification
- Market metadata

---

## Does NOT Own

- Financial Events
- Portfolio
- Positions
- Performance

---

# Financial Ledger Context

## Purpose

Maintain the immutable financial history of investment accounts.

---

## Responsibilities

- Financial Ledger
- Financial Events
- Event Stream
- Financial Effects
- Event Processing
- Business Rules

---

## Aggregate Root

Financial Ledger

---

## Owns

- Immutable event stream
- Event ordering
- Event replay
- Event consistency

---

## Does NOT Own

- Portfolio
- Performance
- Snapshots
- Tax reports

---

# Analytics Context

## Purpose

Generate analytical projections.

---

## Responsibilities

- Portfolio
- Position
- Performance
- Allocation
- Cash Flow
- Passive Income
- Net Worth
- Historical Views

---

## Read Models

- Portfolio
- Position
- Snapshot
- Allocation
- Income History

---

Analytics never modifies Financial Events.

---

# Tax Context

## Purpose

Calculate tax obligations.

---

## Responsibilities

- Cost Basis
- Taxable Gains
- Income Tax
- DARF
- Tax Reports

Consumes Financial Events.

Produces tax projections.

---

# Planning Context

## Purpose

Support long-term financial planning.

---

## Responsibilities

- Financial Goals
- Retirement Planning
- Passive Income Targets
- Forecasts
- Simulations

Consumes analytical projections.

---

# Context Relationships

```
Master Data

↓

Financial Ledger

↓

Analytics

↓

Planning

↓

User Interface
```

Tax Context consumes both Ledger and Analytics.

---

# Context Communication

Contexts communicate only through public contracts.

Examples:

- Events
- Queries
- Application Services

No context accesses another context's internal model.

---

# Shared Concepts

Shared identifiers include:

- AssetId
- AccountId
- CurrencyCode

Business objects are never shared directly.

---

# Strategic Design

| Context | Classification |
|----------|----------------|
| Financial Ledger | Core Domain |
| Master Data | Supporting |
| Analytics | Supporting |
| Tax | Supporting |
| Planning | Generic |

---

# Future Contexts

Possible future contexts include:

- Market Data
- Notification
- AI Assistant
- Reporting
- Authentication

---

# Architectural Principles

- High Cohesion
- Low Coupling
- Explicit Boundaries
- Independent Evolution
- Immutable Financial History
- Event-Driven Processing

---

# ADR-010

## Decision

Income Analytics adopts multiple Bounded Contexts to isolate business capabilities and reduce coupling.

The Financial Ledger Context is the Core Domain.

All analytical capabilities are derived from immutable financial events.

---

# Mission Statement

> **Each Bounded Context owns a single business capability and evolves independently while collaborating through explicit contracts.**