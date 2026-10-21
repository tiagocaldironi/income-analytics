# Income Starter — Arrojada

**Estado:** proposta editorial em DRAFT; não aprovada, não publicada e não adotável.
**Alocação Income proposta:** nenhuma. Percentuais não foram cadastrados no catálogo.

## Referências quantitativas consultadas

| Fonte original | Categorias e percentuais publicados | Limite para uso no Income |
|---|---|---|
| [Charles Schwab — Asset allocation models](https://advisorservices.schwab.com/node/114011) | Exemplo agressivo: 95% ações, 5% caixa. | Exemplo ilustrativo, com horizonte de 15 anos ou mais na página consultada; mercado e instrumentos dos EUA. |
| [Vanguard — Portfolio diversification](https://investor.vanguard.com/investor-resources-education/portfolio-management/diversifying-your-portfolio) | Mix agressivo comum: 80% ações / 20% títulos. | Estratégia comum genérica; depende de objetivos, horizonte e tolerância e não garante resultado. |

Os exemplos divergem em 15 pontos percentuais de exposição acionária e no uso de caixa versus títulos. Uma carteira de maior risco também pode sofrer perdas expressivas; “arrojada” não significa risco adequado para qualquer pessoa com prazo longo.

## Decisões metodológicas próprias ainda pendentes

- Definir critérios de horizonte, necessidade de saque, capacidade financeira de perda e concentração; não inferir adequação pelo nome ou idade.
- Definir exposição geográfica, cambial, setorial e imobiliária para as classes de produto Income.
- Determinar como renda fixa contribuiria para liquidez e diversificação mesmo em objetivo de crescimento.
- Classificar ETFs e previdência por subjacentes apenas com evidência atual e datada; composições não disponíveis não podem ser inventadas.
- Resolver classe caixa (`CASH` não é aceita no motor atual) e política de rebalanceamento.
- Validar concentração máxima, risco de perdas, metodologia e avisos com responsáveis independentes.

| Categoria econômica candidata | Percentual da fonte | Percentual Income candidato | Situação |
|---|---:|---:|---|
| Ações | 80–95% nos exemplos citados | Não definido | Sem mapeamento aprovado para Brasil, internacional, ETFs ou imobiliário listado. |
| Títulos / renda fixa | 0–20% nas fontes citadas | Não definido | O exemplo Schwab consultado não usa esse bucket; Vanguard usa. |
| Caixa | 0–5% nos exemplos citados | Não definido | `CASH` não é suportado pelo editor de alocação atual. |

Faixas sintetizam referências distintas e não representam um conjunto de pesos compatível, uma proposta editorial final ou recomendação Income.

## Limitações e cobertura

O Income não possui evidência integrada suficiente de look-through para todas as classes. Uma classe de produto pode conter múltiplas exposições econômicas. A implementação da taxonomia complementar não preenche lacunas: dados sem fonte e data permanecem desconhecidos, e exposições somadas precisam totalizar 100% para evitar dupla contagem.

## Bloqueios de homologação

1. Definir o mandato de risco e as salvaguardas de concentração e liquidez.
2. Mapear exposições econômicas para os produtos Income sem presumir a natureza de ETF/previdência.
3. Documentar pesos Income por classe e fonte específica; não converter percentuais internacionais automaticamente.
4. Concluir revisão financeira independente e revisão regulatória independente, ambas com identidade/data.
5. Publicar somente nova versão autorizada após todos os gates. Esta versão segue DRAFT e sem percentuais.
