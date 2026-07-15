# Domain Documentation

Welcome to the **Income Analytics Domain Documentation**.

This directory contains the architectural decisions, business concepts, and domain specifications that define the financial core of the platform.

Unlike traditional documentation, these documents are considered **living artifacts** and evolve together with the source code.

---

# Purpose

The objective of this documentation is to ensure that every developer, architect, business stakeholder, and AI agent shares the same understanding of the financial domain.

The documentation defines:

- Business concepts
- Architectural principles
- Canonical models
- Domain rules
- Processing pipeline
- Design decisions

Code implementation should always follow these specifications.

---

# Documentation Roadmap

The recommended reading order is presented below.

```
README
    │
    ▼
UBIQUITOUS_LANGUAGE
    │
    ▼
CANONICAL_FINANCIAL_EVENT_MODEL
    │
    ▼
FINANCIAL_EFFECT_MODEL
    │
    ▼
FINANCIAL_EVENT_PROCESSING
    │
    ▼
FINANCIAL_LEDGER
    │
    ▼
DOMAIN_MODEL
    │
    ▼
BUSINESS_RULES
```

Each document builds upon concepts introduced in the previous one.

---

# Documentation Structure

```
docs/

├── adr/
│   ├── ADR-001.md
│   ├── ADR-002.md
│   └── ...
│
├── architecture/
│   ├── SOFTWARE_ARCHITECTURE.md
│   └── ...
│
└── domain/
    ├── README.md
    ├── UBIQUITOUS_LANGUAGE.md
    ├── CANONICAL_FINANCIAL_EVENT_MODEL.md
    ├── FINANCIAL_EFFECT_MODEL.md
    ├── FINANCIAL_EVENT_PROCESSING.md
    ├── FINANCIAL_LEDGER.md
    ├── DOMAIN_MODEL.md
    ├── BUSINESS_RULES.md
    └── GLOSSARY.md
```

---

# Domain Documentation

## UBIQUITOUS_LANGUAGE.md

Defines the official business vocabulary used throughout the platform.

Topics include:

- Investor
- Account
- Asset
- Portfolio
- Financial Event
- Financial Ledger
- Financial Effect
- Read Models
- Business Engines

This document should be read first.

---

## CANONICAL_FINANCIAL_EVENT_MODEL.md

Defines the canonical representation of every financial event.

Topics include:

- Event Categories
- Event Types
- Behavioral Matrix
- Event Lifecycle
- Architectural Rules

This document specifies the language spoken by every integration.

---

## FINANCIAL_EFFECT_MODEL.md

Defines the financial consequences produced by events.

Topics include:

- Position Effect
- Cash Effect
- Income Effect
- Tax Effect
- FX Effect
- Cost Basis Effect

Business Engines consume Effects instead of Event Types.

---

## FINANCIAL_EVENT_PROCESSING.md

Defines the complete event processing pipeline.

Topics include:

- Validation
- Canonical Validation
- Business Rules
- Engine Dispatch
- Position Engine
- Income Engine
- Performance Engine
- Snapshot Engine

---

## FINANCIAL_LEDGER.md

Defines the immutable financial history.

Topics include:

- Aggregate Root
- Event Stream
- Replay
- Snapshot Strategy
- Event Ordering
- Immutability

This document describes the central financial aggregate of the platform.

---

## DOMAIN_MODEL.md *(Planned)*

Will describe the conceptual model of the domain.

Topics:

- Aggregates
- Entities
- Value Objects
- Relationships
- Bounded Contexts

---

## BUSINESS_RULES.md *(Planned)*

Business rules independent from implementation.

Examples:

- Sell quantity validation
- Fixed-income redemption rules
- Tax rules
- Average cost rules
- Corporate actions

---

## GLOSSARY.md *(Planned)*

Alphabetical reference for every business term used by the platform.

---

# Architectural Layers

```
                    Domain Knowledge

                         │

                         ▼

              Ubiquitous Language

                         │

                         ▼

           Canonical Financial Event Model

                         │

                         ▼

             Financial Effect Model

                         │

                         ▼

          Financial Event Processing

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

                 REST API / Dashboard
```

---

# Guiding Principles

Income Analytics follows the following principles:

- Domain-Driven Design (DDD)
- Clean Architecture
- Event-Driven Design
- Immutable Financial History
- Deterministic Processing
- Explainable Analytics
- Canonical Data Modeling

---

# Documentation Principles

Every document in this directory must:

- Be implementation independent whenever possible.
- Describe business concepts before technical implementation.
- Avoid framework-specific terminology.
- Be understandable by both technical and business audiences.
- Evolve together with the domain.

---

# Source of Truth

The platform defines different levels of truth.

| Level | Source of Truth |
|---------|----------------|
| Financial History | Financial Ledger |
| Financial Facts | Financial Events |
| Business Meaning | Ubiquitous Language |
| Event Semantics | Canonical Financial Event Model |
| Event Consequences | Financial Effect Model |
| Processing Rules | Financial Event Processing |
| Portfolio State | Read Models (Derived) |

---

# Living Documentation

This documentation is considered part of the source code.

Whenever the domain evolves:

1. Update the documentation.
2. Review the architectural decisions.
3. Implement the corresponding code.
4. Update the automated tests.

Documentation should always evolve before implementation whenever major architectural changes are introduced.

---

# Vision

Income Analytics is not a traditional investment tracker.

Its mission is to reconstruct the complete financial history of an investor from immutable financial events, producing explainable, deterministic, and auditable financial analytics.

The documentation in this directory captures the knowledge required to achieve that vision.