# Financial Ledger

> **Version:** 1.0
>
> **Status:** Draft
>
> **Owner:** Income Analytics Architecture
>
> **Last Updated:** July 2026

---

# Purpose

The Financial Ledger is the central aggregate of the Income Analytics platform.

It represents the complete, immutable history of financial events associated with a single investment account.

The Financial Ledger is the only authoritative source for reconstructing the financial state of an account at any point in time.

---

# Architectural Vision

```
                 Account

                    │

                    ▼

            Financial Ledger

                    │

        Immutable Event Stream

                    │

     ┌──────────────┼──────────────┐

     ▼              ▼              ▼

 FinancialEvent  FinancialEvent  FinancialEvent

                    │

                    ▼

             Business Engines

                    │

                    ▼

               Read Models
```

---

# Why a Ledger?

Traditional investment applications persist derived information.

Examples:

- Current Position
- Average Price
- Portfolio Value
- Monthly Income
- Asset Allocation

Those values constantly change and are difficult to keep consistent.

Income Analytics persists only the financial history.

Everything else is reconstructed.

---

# Core Principles

## 1. Ledger is the Source of Truth

The Financial Ledger is the only authoritative source for investment history.

No derived information is authoritative.

---

## 2. Immutable History

Events are never modified.

Events are never deleted.

Corrections generate new events.

---

## 3. Chronological Order

Events inside a Ledger are always ordered.

Ordering priority:

1. occurred_at
2. imported_at
3. event_id

This guarantees deterministic reconstruction.

---

## 4. Deterministic Reconstruction

Running the same Ledger twice must always produce exactly the same financial state.

---

## 5. Account Isolation

Every Ledger belongs to exactly one Account.

```
XP Account

↓

Ledger

---------------------

Nubank Account

↓

Ledger

---------------------

Interactive Brokers

↓

Ledger
```

Each account evolves independently.

---

# Aggregate Root

Financial Ledger is the Aggregate Root of the financial domain.

Responsibilities:

- Accept Financial Events
- Preserve chronological consistency
- Guarantee event immutability
- Prevent duplicated events
- Provide event stream
- Support deterministic replay

---

# Financial Event Stream

The Ledger stores an ordered sequence of Financial Events.

Example:

```
2026-01-10

BUY PETR4

100 shares

↓

2026-02-15

DIVIDEND PETR4

R$120

↓

2026-03-02

BUY PETR4

50 shares

↓

2026-04-20

SELL PETR4

80 shares
```

The stream represents the complete financial history.

---

# Ledger Responsibilities

The Ledger is responsible for:

- Storing events
- Preserving order
- Detecting duplicates
- Providing replay capability
- Guaranteeing immutability

The Ledger is NOT responsible for:

- Position calculation
- Portfolio calculation
- Performance calculation
- Tax calculation
- Asset allocation

Those responsibilities belong to Business Engines.

---

# Event Lifecycle

```
Imported

↓

Validated

↓

Canonicalized

↓

Added to Ledger

↓

Processed

↓

Available for Analytics
```

Once an event enters the Ledger, it becomes part of the permanent financial history.

---

# Replay

One of the most important capabilities of the Ledger is replay.

```
Ledger

↓

Replay Events

↓

Position Engine

↓

Portfolio State
```

Replay allows:

- Historical reconstruction
- Bug correction
- Engine evolution
- Snapshot rebuilding

---

# Snapshot Strategy

Snapshots are optimization artifacts.

They are NOT authoritative.

```
Ledger

↓

Replay

↓

Snapshot
```

If a Snapshot is lost:

```
Replay Ledger

↓

Generate Snapshot Again
```

No information is lost.

---

# Portfolio Reconstruction

Portfolio is NOT persisted.

Portfolio is reconstructed.

```
Ledger

↓

Position Engine

↓

Portfolio Projection
```

Portfolio becomes a Read Model.

---

# Read Models

Business Engines generate projections.

Examples:

- Portfolio
- Current Position
- Historical Position
- Net Worth
- Cash Flow
- Income History
- Performance
- Asset Allocation

Read Models may be discarded and rebuilt at any time.

---

# Event Ordering

Events are processed in deterministic order.

Priority:

1. occurred_at
2. imported_at
3. event_id

This guarantees reproducible calculations.

---

# Duplicate Detection

Each Financial Event possesses a unique identity.

Duplicate detection may consider:

- External Transaction ID
- Import Batch
- Source System
- Event Hash

Duplicated events are rejected.

---

# Ledger Replay

```
Financial Ledger

↓

Replay

↓

Position Engine

↓

Income Engine

↓

Performance Engine

↓

Snapshot Engine

↓

Analytics
```

Replay is deterministic.

---

# Business Engines

Business Engines never modify the Ledger.

They only consume events.

```
Ledger

↓

Events

↓

Business Engines

↓

Read Models
```

---

# Multiple Ledgers

One investor may have multiple Ledgers.

Example:

```
Investor

├── XP Ledger

├── Nubank Ledger

├── Binance Ledger

└── Interactive Brokers Ledger
```

A consolidated Portfolio is built by combining projections from every Ledger.

---

# Future Capabilities

The Ledger enables:

- Event Replay
- Time Travel
- Historical Reconstruction
- Parallel Processing
- Incremental Snapshots
- Event Streaming
- Explainable Analytics
- AI Financial Assistant

---

# Architectural Rules

## Rule 1

Financial Ledger is the only source of truth.

---

## Rule 2

Financial Events are immutable.

---

## Rule 3

Business Engines never modify Ledger contents.

---

## Rule 4

Read Models are disposable.

---

## Rule 5

Portfolio is a projection.

---

## Rule 6

Snapshots are optimization artifacts.

---

## Rule 7

Every calculation must be reproducible.

---

# ADR-007

## Decision

Income Analytics adopts the Financial Ledger as the Aggregate Root of the financial domain.

The Ledger owns the immutable event stream.

Every business engine reconstructs financial knowledge by replaying Ledger events.

Derived information is never authoritative.

---

## Benefits

- Deterministic processing
- Immutable history
- Complete auditability
- Historical reconstruction
- Explainable calculations
- Independent business engines
- Easier testing
- Easier maintenance
- Event replay
- Future scalability

---

## Trade-offs

- More sophisticated event processing
- Replay may become expensive for large histories
- Snapshot optimization will eventually be required

---

# Mission Statement

> **The Financial Ledger is the immutable financial memory of an investment account. Every analytical insight produced by Income Analytics is derived from replaying this ledger, ensuring auditability, explainability and deterministic financial reconstruction.**