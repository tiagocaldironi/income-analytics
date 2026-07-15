Todo FinancialEvent deve representar uma transformação de estado, nunca um estado.

Consequências:

Nunca persistiremos posição da carteira.
Nunca persistiremos patrimônio.
Nunca persistiremos custo médio.
Nunca persistiremos rentabilidade.

Tudo será reconstruído.

O maior diferencial do projeto

Imagine um usuário perguntando:

"Por que meu patrimônio aumentou R$ 15.800 em abril?"

O sistema poderá responder:

Abril

+ Dividendos PETR4

+ R$ 540

+ Venda BBSE3

+ R$ 8.200

+ Valorização cambial IVV

+ R$ 2.430

+ Rendimentos Tesouro Selic

+ R$ 180

+ Valorização ativos

+ R$ 4.450

Nenhum aplicativo que conheço consegue explicar a composição da evolução patrimonial com esse nível de rastreabilidade.