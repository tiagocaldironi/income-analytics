# Magic Formula Stocks — estrutura de capital e preço

## Modelo auditável

`ShareClassCapital` representa uma classe negociável, e não apenas o emissor:
`issuer_id`, `security_id`, ticker, classe, quantidade em circulação, data de
referência, fonte, referência da fonte, instante de obtenção e status.

O parser oficial `CvmCapitalCompositionParser` lê a composição de capital do
DFP. O adaptador só produz classes normalizadas quando recebe um mapeamento
explícito CNPJ → security ID/ticker/classe e um multiplicador de quantidade
documentado. Não há inferência por nome da companhia.

As ações em tesouraria são deduzidas da quantidade integralizada. ON e PN são
tratadas separadamente; o market cap do emissor é a soma de cada
`ações_da_classe × preço_da_classe`.

## Política temporal

O preço B3 guarda tanto `requested_reference_date` quanto `effective_date`.
Para combinar com a estrutura de capital, a data solicitada deve ser exatamente
a data de referência das ações. Em fim de semana/feriado é aceito o último
pregão anterior por até sete dias; preço futuro, data solicitada diferente ou
lacuna superior bloqueiam o cálculo com `TEMPORAL_INCONSISTENCY`.

Dados sem preço, classe, multiplicador validado ou fonte verificável resultam
em `INSUFFICIENT_MARKET_DATA`. Nenhum preço zero ou ticker de outra classe é
usado como substituto. Uma fonte pode marcar explicitamente
`CORPORATE_ACTION_RISK`, que também impede o cálculo.
