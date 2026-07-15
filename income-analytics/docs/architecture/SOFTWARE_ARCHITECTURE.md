# Software Architecture

> **Projeto:** Income Analytics
>
> **Versão:** 0.1.0
>
> **Status:** Em construção
>
> **Última atualização:** Julho/2026

---

# 1. Objetivo

O Income Analytics é uma plataforma para consolidação, interpretação e análise de eventos financeiros pessoais.

O objetivo do sistema não é apenas armazenar investimentos, mas representar fielmente toda a linha do tempo financeira do investidor, permitindo responder perguntas sobre patrimônio, rentabilidade, renda passiva, evolução patrimonial, desempenho por ativo e progresso de metas financeiras.

---

# 2. Visão do Produto

O sistema deverá responder perguntas como:

- Quanto ganhei este mês?
- Quanto recebi em dividendos?
- Quanto recebi em renda fixa?
- Quanto recebi em Tesouro Direto?
- Quanto da minha rentabilidade veio da valorização cambial?
- Quanto falta para atingir meu primeiro milhão?
- Qual era meu patrimônio em qualquer data?
- Quanto receberei de renda passiva no próximo mês?
- Qual ativo gerou maior retorno?

---

# 3. Princípios Arquiteturais

## 3.1 Transactions representam a verdade

Todas as informações financeiras serão registradas como eventos.

Exemplos:

- Compra
- Venda
- Dividendo
- Juros sobre Capital Próprio
- Rendimento
- Cupom
- Amortização
- Transferência
- Split
- Bonificação

O sistema nunca utilizará Position como fonte da verdade.

---

## 3.2 Position é derivada

Posições atuais serão calculadas a partir das Transactions.

Elas nunca serão cadastradas manualmente.

---

## 3.3 Patrimônio é derivado

O patrimônio é consequência das posições.

Ele nunca será persistido como dado de origem.

---

## 3.4 API como única porta de entrada

Nenhum consumidor acessará diretamente o banco de dados.

Todos os clientes deverão consumir exclusivamente a API.

Consumidores previstos:

- Dashboard
- Streamlit
- Aplicativo Mobile
- Inteligência Artificial
- Integrações futuras

---

## 3.5 Domínio independente

A camada Domain não conhecerá tecnologias externas.

Ela não poderá depender de:

- FastAPI
- SQLAlchemy
- Pandas
- PostgreSQL
- SQLite
- Requests

O domínio deverá ser implementado apenas utilizando Python.

---

# 4. Filosofia do Sistema

O Income Analytics será orientado a eventos financeiros.

Não modelaremos investimentos.

Modelaremos acontecimentos.

Exemplo:

Compra

↓

Compra

↓

Dividendo

↓

Venda

↓

JCP

↓

Rendimento

↓

Transferência

↓

Resgate

A partir desses eventos será possível reconstruir qualquer estado da carteira.

---

# 5. Arquitetura

```
                        API

                         │

              ┌──────────┴───────────┐

              ▼                      ▼

        Command Services      Query Services

              │                      │

              └──────────┬───────────┘

                         ▼

                  Domain Model

                         ▼

                 Infrastructure

                         ▼

                    Database
```

---

# 6. Bounded Contexts

O sistema será dividido em seis contextos.

## Portfolio Management

Responsável por:

- Carteiras
- Contas
- Corretoras

---

## Transaction Management

Responsável por:

- Compras
- Vendas
- Dividendos
- Rendimentos
- Transferências
- Eventos financeiros

Este será o Core Domain.

---

## Market Data

Responsável por:

- Ativos
- Moedas
- Instituições
- Cotações
- Taxas de câmbio

---

## Performance

Responsável por cálculos.

Exemplos:

- Patrimônio
- Rentabilidade
- Renda Passiva
- Dividend Yield
- Alocação

Nenhuma informação deste contexto será cadastrada.

Tudo será calculado.

---

## Goals

Responsável por objetivos financeiros.

Exemplos:

- Primeiro milhão
- Independência financeira
- Meta anual
- Meta de renda passiva

---

## Import

Responsável por importação de informações.

Conectores previstos:

- Nubank
- XP
- BTG
- Inter
- CSV
- OFX
- PDF

---

# 7. Modelo Conceitual

```
Portfolio

│

├── Account

│      │

│      ├── Broker

│      │

│      └── FinancialEvent

│                │

│                └── Asset

│                         │

│                         ├── Currency

│                         ├── AssetType

│                         └── Institution

│

├── Goal

│

└── Snapshot
```

---

# 8. Core Domain

O núcleo do sistema será o registro e processamento de eventos financeiros.

O sistema será orientado ao conceito de Financial Event Ledger.

Todas as funcionalidades deverão derivar deste conceito.

---

# 9. Entidades

- Portfolio
- Account
- Broker
- Asset
- Institution
- Currency
- FinancialEvent
- Snapshot
- Goal

---

# 10. Value Objects

- Money
- Quantity
- Percentage
- AssetType
- TransactionType
- ExchangeRate
- Ticker

---

# 11. Casos de Uso

- Criar carteira
- Criar conta
- Registrar ativo
- Registrar evento financeiro
- Importar extrato
- Consultar patrimônio
- Consultar posições
- Consultar renda passiva
- Consultar evolução patrimonial
- Consultar metas
- Simular investimentos

---

# 12. Invariantes

O sistema deverá garantir:

- Todo evento pertence a uma conta.
- Toda conta pertence a uma carteira.
- Todo ativo possui uma moeda.
- Todo ativo possui um tipo.
- Todo evento possui uma data.
- Todo evento possui um tipo.
- Nenhuma Position poderá ser alterada diretamente.
- Nenhum patrimônio poderá ser persistido como fonte da verdade.

---

# 13. Roadmap Arquitetural

Sprint 1

- Fundação
- API
- FastAPI
- Swagger

Sprint 2

- Domain Model
- Entities
- Value Objects

Sprint 3

- Persistência

Sprint 4

- Importadores

Sprint 5

- Motor Financeiro

Sprint 6

- Dashboard

Sprint 7

- Inteligência Artificial

---

# 14. Decisões Arquiteturais

As decisões relevantes serão registradas em:

```

docs/adr/

```

Cada ADR deverá conter:

- Contexto
- Problema
- Alternativas
- Decisão
- Consequências

---

# 15. Objetivo de Longo Prazo

Construir uma plataforma de nível profissional para consolidação de patrimônio, renda passiva e análise financeira, utilizando princípios modernos de Engenharia de Software, Domain-Driven Design, Clean Architecture, testes automatizados, CI/CD e Inteligência Artificial.