# Income Starter — Conservadora

**Estado:** proposta editorial em DRAFT; não aprovada, não publicada e não adotável.
**Alocação Income proposta:** nenhuma. Percentuais não foram cadastrados no catálogo.

## Referências quantitativas consultadas

| Fonte original | Categorias e percentuais publicados | Limite para uso no Income |
|---|---|---|
| [Charles Schwab — Asset allocation models](https://advisorservices.schwab.com/node/114011) | Exemplo conservador: 20% ações, 50% títulos, 30% caixa. | A própria fonte descreve exemplos ilustrativos para contexto dos EUA, não carteira real nem recomendação. |
| [Charles Schwab International — Hypothetical performance](https://international.schwab.com/node/12201) | Exemplo conservador: 30% ações, 50% títulos, 20% caixa. | Outro exemplo da mesma instituição, com pesos diferentes; reforça que não existe uma composição única. |
| [Vanguard — Portfolio diversification](https://investor.vanguard.com/investor-resources-education/portfolio-management/diversifying-your-portfolio) | Mix conservador comum: 40% ações / 60% títulos. | Categorias amplas e contexto de mercado dos EUA; não detalha caixa nem classes de produto Income. |

As fontes originais permitem discutir cenários econômicos em termos de ações, títulos e caixa. Elas não justificam converter os pesos diretamente em classes Income.

## Decisões metodológicas próprias ainda pendentes

- Determinar se “conservadora” será definida por objetivo, risco, horizonte ou combinação explícita desses fatores; o rótulo sozinho não representa suitability.
- Definir como separar risco de crédito, duração, inflação, liquidez, país e moeda dentro de renda fixa.
- Definir o tratamento de ETFs e previdência pelos ativos subjacentes, sem supor que todo produto pertence a uma classe econômica única.
- Resolver a ausência de uma classe `CASH` na política de alocação atual; caixa não será remapeado silenciosamente.
- Definir faixas/classes Income e método de rebalanceamento após análise financeira e regulatória.

| Categoria econômica candidata | Percentual da fonte | Percentual Income candidato | Situação |
|---|---:|---:|---|
| Ações | 20–40% nos exemplos citados | Não definido | Sem mapeamento aprovado para ações Brasil, exterior, ETF ou FII. |
| Títulos / renda fixa | 50–60% | Não definido | A categoria ampla não representa os riscos distintos dos produtos Income. |
| Caixa | 0–30% nos exemplos citados | Não definido | `CASH` não é suportado pela política de ativos investidos. |

Os intervalos acima apenas resumem exemplos de terceiros; não são uma distribuição proposta ou recomendação Income.

## Cobertura e riscos de classificação

A taxonomia de produto Income existe, mas ainda não há fonte integrada comprovando look-through econômico dos ativos. ETFs, previdência e fundos com composição desconhecida devem permanecer `UNCLASSIFIED`/`UNKNOWN`. Não usar classe `OTHER` como aproximação, não estimar pesos e não contar duas vezes a mesma exposição.

## Bloqueios de homologação

1. Aprovar metodologia brasileira e relação entre objetivo, horizonte, risco e liquidez.
2. Definir tratamento de caixa e mapeamento de produtos para exposições econômicas.
3. Documentar pesos Income com fontes e justificativa específica por classe.
4. Revisão financeira independente e revisão regulatória documentadas, cada qual com identidade e data.
5. Somente então abrir uma nova versão para `IN_REVIEW`; esta versão permanece DRAFT.
