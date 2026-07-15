# ADR-001 — Domain First

## Status

Accepted

## Context

O Income Analytics será um sistema financeiro de longo prazo.

Mudanças frequentes de tecnologia (ORM, banco de dados, framework web) são esperadas.

## Decision

Toda regra de negócio será implementada primeiro na camada Domain.

A camada Domain não poderá depender de:

- FastAPI
- SQLAlchemy
- SQLite
- PostgreSQL
- Requests
- Pandas

## Consequences

- Domínio independente.
- Maior testabilidade.
- Facilidade para trocar infraestrutura.
- Menor acoplamento.