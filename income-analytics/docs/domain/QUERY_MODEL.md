# Query Model

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

The Query Model defines the analytical capabilities of Income Analytics.

Instead of designing the platform around REST endpoints, the system is designed around business questions.

Every API endpoint, dashboard widget, report, or AI-generated response should ultimately answer one or more queries defined in this document.

---

# Design Principles

## Knowledge over CRUD

Income Analytics is not designed to expose database entities.

It is designed to answer financial questions.

Examples:

- How much did I earn this month?
- What was my portfolio value last year?
- Which investments generated passive income?
- Why did my net worth change?

---

## Deterministic Answers

Every query must produce reproducible results when executed against the same Financial Ledger.

---

## Explainability

Every answer must be traceable back to the Financial Events that produced it.

The platform should always be capable of explaining **why** a given result was produced.

---

# Query Categories

The platform organizes queries into business capabilities.

---

# Portfolio Queries

Questions related to investment positions.

Examples:

- What is my current portfolio?
- What was my portfolio on a specific date?
- Which assets do I own?
- How many shares of PETR4 do I own?
- Which assets are inactive?

Produces:

- Portfolio Projection
- Position Projection

---

# Performance Queries

Questions related to investment returns.

Examples:

- What is my total return?
- What is my annual return?
- What is my unrealized gain?
- What is my realized gain?
- Which asset generated the highest return?

Produces:

- Performance Projection

---

# Income Queries

Questions related to passive income.

Examples:

- How much dividend income did I receive this month?
- How much passive income did I receive this year?
- Which asset generated the highest income?
- Monthly dividend evolution.
- Annual passive income history.

Produces:

- Income Projection

---

# Cash Flow Queries

Questions related to money movement.

Examples:

- How much cash did I deposit?
- How much cash did I withdraw?
- Cash balance evolution.
- Monthly cash flow.
- Cash available today.

Produces:

- Cash Flow Projection

---

# Allocation Queries

Questions related to portfolio distribution.

Examples:

- Allocation by Asset Type.
- Allocation by Currency.
- Allocation by Country.
- Allocation by Institution.
- Allocation by Sector.

Produces:

- Allocation Projection

---

# Historical Queries

Questions that reconstruct financial history.

Examples:

- Portfolio on a specific date.
- Net worth on a specific date.
- Asset allocation on a specific date.
- Passive income history.
- Position history.

Produces:

- Historical Snapshots

---

# Tax Queries

Questions related to taxation.

Examples:

- Taxable gains.
- Cost Basis.
- DARF calculations.
- Tax withheld.
- Monthly taxable events.

Produces:

- Tax Projection

---

# Goal Queries

Questions related to financial planning.

Examples:

- Passive income forecast.
- Retirement projection.
- Financial independence progress.
- Goal completion percentage.

Produces:

- Goal Projection

---

# Explainability Queries

Questions that explain financial results.

Examples:

Why did my net worth increase?

Which events generated my passive income?

Why did my average cost change?

Why did my portfolio allocation change?

Which events affected my cash balance?

Produces:

- Explainable Financial Report

---

# AI Queries

Questions intended for conversational AI.

Examples:

How much did I earn last month?

Which investment performed best?

What are my biggest positions?

How much did I invest in ETFs?

How much income came from FIIs?

How much did currency appreciation contribute to my returns?

These queries combine multiple Business Engines.

---

# Query Pipeline

```
Financial Ledger

        │

        ▼

Business Engines

        │

        ▼

Read Models

        │

        ▼

Query Services

        │

        ▼

REST API

Dashboard

AI Assistant
```

---

# Query Characteristics

Every query should satisfy the following principles.

## Deterministic

The same Financial Ledger always produces the same answer.

---

## Explainable

Every answer can be traced back to Financial Events.

---

## Reproducible

Results can be regenerated at any time.

---

## Read Only

Queries never modify domain data.

---

# Example Queries

## Current Portfolio

Question:

> What assets do I currently own?

Consumes:

- Financial Ledger
- Position Engine

Produces:

- Portfolio Projection

---

## Historical Portfolio

Question:

> What was my portfolio on December 31st, 2025?

Consumes:

- Financial Ledger
- Snapshot Engine

Produces:

- Historical Snapshot

---

## Monthly Passive Income

Question:

> How much passive income did I receive in June?

Consumes:

- Income Engine

Produces:

- Income Projection

---

## Net Worth Evolution

Question:

> How did my net worth evolve over time?

Consumes:

- Snapshot Engine
- Performance Engine

Produces:

- Net Worth Timeline

---

## Currency Exposure

Question:

> What percentage of my portfolio is exposed to USD?

Consumes:

- FX Engine
- Allocation Engine

Produces:

- Currency Allocation

---

## Explain Portfolio Growth

Question:

> Why did my portfolio increase by R$15,000 this month?

Consumes:

- Performance Engine
- Income Engine
- Cash Flow Engine

Produces:

An explainable report describing every contributing Financial Event.

---

# Query Classification

| Category | Examples |
|-----------|----------|
| Portfolio | Current Position, Historical Position |
| Performance | Total Return, Annual Return |
| Income | Dividends, Interest, Passive Income |
| Cash Flow | Deposits, Withdrawals, Cash Balance |
| Allocation | Asset Allocation, Country Allocation |
| Tax | Cost Basis, Taxable Gains |
| Planning | Goals, Retirement |
| Explainability | Why?, Which Events?, Historical Reconstruction |

---

# Query Philosophy

The platform is question-driven.

Business capabilities are defined by the questions users need answered, not by database tables or REST resources.

---

# Future Queries

Examples planned for future versions:

- What would my portfolio look like if I had reinvested every dividend?
- How much did inflation reduce my purchasing power?
- What is my projected passive income in five years?
- Which investments are underperforming their benchmark?
- What percentage of my returns came from foreign exchange?
- Which investment has generated the highest risk-adjusted return?
- Simulate selling a position and estimate tax impacts.
- Compare my portfolio with a benchmark over any historical period.

---

# ADR-012

## Decision

Income Analytics adopts a **Question-Driven Architecture**.

The platform is designed around business questions rather than CRUD operations or REST resources.

Business Engines generate knowledge.

Query Services organize and expose that knowledge.

---

# Mission Statement

> **Income Analytics transforms immutable financial history into answers. Every feature exists to answer a financial question with deterministic, explainable, and reproducible results.**