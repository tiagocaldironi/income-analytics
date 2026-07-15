# Use Cases

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

This document defines the business use cases supported by the Income Analytics platform.

A Use Case represents a business capability from the perspective of an external actor (user, integration, scheduler, or AI assistant).

The platform is designed around business capabilities rather than CRUD operations.

---

# Architectural Vision

```
User

    │

    ▼

Use Case

    │

    ▼

Application Layer

    │

    ▼

Domain Model

    │

    ▼

Financial Ledger

    │

    ▼

Business Engines

    │

    ▼

Read Models

    │

    ▼

Response
```

---

# Design Principles

## User-Centric

Every use case exists because a user or external system needs a business capability.

---

## Intent-Oriented

Use Cases represent intentions.

Examples:

✔ Register Buy

✔ Register Dividend

✔ Explain Portfolio Growth

Instead of:

✘ Create Transaction

✘ Update Portfolio

✘ Delete Position

---

## Technology Independent

A Use Case may be executed by:

- REST API
- CLI
- Background Job
- Scheduler
- AI Assistant
- Batch Import
- Message Queue

---

## Command Query Responsibility Segregation (CQRS)

The platform naturally separates use cases into:

- Commands
- Queries

Commands modify the domain.

Queries never modify the domain.

---

# Command Use Cases

Commands modify the Financial Ledger.

---

## Account Management

### Register Account

Creates a new investment account.

---

### Disable Account

Marks an account as inactive.

---

# Asset Management

### Register Asset

Creates a new financial asset.

---

### Update Asset Metadata

Updates reference information.

---

### Register Institution

Creates a financial institution.

---

### Register Broker

Creates a broker.

---

# Financial Events

### Register Buy

Registers an asset purchase.

Produces:

- Financial Event
- Position Effect
- Cash Effect
- Cost Basis Effect

---

### Register Sell

Registers an asset sale.

Produces:

- Financial Event
- Position Effect
- Cash Effect
- Tax Effect

---

### Register Dividend

Registers a dividend payment.

Produces:

- Cash Effect
- Income Effect

---

### Register Interest on Equity

Registers JCP income.

---

### Register FII Income

Registers REIT income.

---

### Register Deposit

Registers a cash deposit.

---

### Register Withdrawal

Registers a cash withdrawal.

---

### Register Split

Registers a stock split.

---

### Register Reverse Split

Registers a reverse split.

---

### Register Bonus Shares

Registers bonus shares.

---

### Register Subscription

Registers a subscription operation.

---

### Register Redemption

Registers a fixed-income redemption.

---

### Register Fixed Income Interest

Registers interest accrued on fixed-income investments.

---

# Import

### Import XP Statement

Imports transactions exported from XP.

---

### Import Nubank Statement

Imports transactions exported from Nubank.

---

### Import B3 Statement

Imports transactions exported from B3.

---

### Import Binance Statement

Imports transactions exported from Binance.

---

### Validate Imported Events

Validates imported events before processing.

---

### Reprocess Import

Reprocesses previously imported events.

---

# Query Use Cases

Queries never modify the domain.

---

# Portfolio

### Get Current Portfolio

Returns the current investment portfolio.

---

### Get Portfolio by Date

Returns the reconstructed portfolio for a specific date.

---

### Get Asset Position

Returns the current position of an asset.

---

### Get Historical Position

Returns historical position evolution.

---

# Performance

### Get Performance

Returns investment performance.

---

### Get Performance by Asset

Returns performance of a specific asset.

---

### Get Unrealized Gain

Returns unrealized gains.

---

### Get Realized Gain

Returns realized gains.

---

# Passive Income

### Get Passive Income

Returns passive income summary.

---

### Get Monthly Income

Returns monthly income.

---

### Get Annual Income

Returns annual income.

---

### Get Income by Asset

Returns income grouped by asset.

---

# Allocation

### Get Asset Allocation

Returns allocation by asset.

---

### Get Allocation by Currency

Returns allocation by currency.

---

### Get Allocation by Country

Returns allocation by country.

---

### Get Allocation by Institution

Returns allocation by institution.

---

# Cash Flow

### Get Cash Balance

Returns current cash balance.

---

### Get Cash Flow

Returns cash flow history.

---

### Get Deposit History

Returns deposits.

---

### Get Withdrawal History

Returns withdrawals.

---

# Historical

### Get Historical Snapshot

Returns reconstructed financial state.

---

### Get Net Worth History

Returns historical net worth.

---

### Get Portfolio Timeline

Returns portfolio evolution.

---

# Explainability

### Explain Portfolio Growth

Explains why the portfolio value changed.

---

### Explain Performance

Explains investment performance.

---

### Explain Income

Explains passive income composition.

---

### Explain Cash Flow

Explains cash balance variation.

---

### Explain Allocation

Explains allocation changes.

---

### Explain Average Cost

Explains average cost evolution.

---

# Tax

### Get Cost Basis

Returns acquisition cost.

---

### Get Taxable Gain

Returns taxable gains.

---

### Get Tax Report

Returns tax report.

---

# Planning

### Get Retirement Projection

Returns retirement forecast.

---

### Get Passive Income Forecast

Returns projected passive income.

---

### Get Goal Progress

Returns financial goal progress.

---

# AI Assistant

### Ask Financial Question

Answers natural language financial questions.

---

### Explain Investment

Explains a specific investment.

---

### Compare Assets

Compares two or more assets.

---

### Suggest Portfolio Improvements

Suggests improvements based on user objectives.

---

### Simulate Investment

Simulates investment scenarios.

---

# Use Case Classification

| Category | Command | Query |
|------------|:------:|:-----:|
| Register Buy | ✅ | |
| Register Sell | ✅ | |
| Register Dividend | ✅ | |
| Import Statement | ✅ | |
| Get Portfolio | | ✅ |
| Get Performance | | ✅ |
| Get Income | | ✅ |
| Get Allocation | | ✅ |
| Explain Performance | | ✅ |
| Simulate Investment | | ✅ |

---

# Actors

## Investor

Primary user of the platform.

Capabilities:

- Register investments
- Analyze portfolio
- Track income
- Ask AI questions

---

## Import Adapter

Imports external statements.

Examples:

- XP
- Nubank
- B3
- Binance

---

## Scheduler

Executes background tasks.

Examples:

- Snapshot generation
- Portfolio reconstruction
- Market synchronization

---

## AI Assistant

Consumes Query Use Cases.

Provides natural language responses.

---

# Future Use Cases

Examples planned for future versions:

- Import Interactive Brokers Statement
- Synchronize Market Prices
- Rebuild Entire Ledger
- Export Portfolio
- Export Tax Report
- Compare Portfolio with Benchmark
- Detect Portfolio Concentration Risk
- Recommend Portfolio Rebalancing
- Simulate Currency Exposure
- Explain Dividend Growth

---

# Architectural Rules

## Rule 1

Commands always modify the Financial Ledger.

---

## Rule 2

Queries never modify the Financial Ledger.

---

## Rule 3

Every Command produces one or more Financial Events.

---

## Rule 4

Queries consume Read Models.

---

## Rule 5

Business Engines are never invoked directly by users.

They are orchestrated through Application Services.

---

# ADR-013

## Decision

Income Analytics adopts a Use Case–driven Application Layer.

Business capabilities are modeled as Commands and Queries.

The platform naturally follows the CQRS architectural pattern.

---

# Mission Statement

> **Every feature in Income Analytics exists to fulfill a business capability. Commands record immutable financial facts, while Queries transform those facts into explainable financial knowledge.**