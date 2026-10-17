# MF-FII v3 — Data Spike

## Decisão

`RECOMMEND_PARTIAL_WITH_DISCLOSURE`; não ativar o ranking MF-FII v3 ainda.

## Disponibilidade

| Métrica | Classificação | Observação |
|---|---|---|
| P/VP | DERIVABLE | preço B3 + valor patrimonial/cotas do informe CVM |
| distribuição | AVAILABLE_STRUCTURED | informe mensal CVM |
| resultado recorrente | NOT_RELIABLE | exige separar eventos recorrentes de extraordinários |
| vacância financeira / WAULT | AVAILABLE_UNSTRUCTURED | relatórios gerenciais, sem estrutura uniforme |
| alavancagem | AVAILABLE_UNSTRUCTURED | definição e apresentação variam |
| concentração (locatário, imóvel, vencimento) | AVAILABLE_UNSTRUCTURED | geralmente em relatórios gerenciais e com granularidade desigual |

A CVM disponibiliza Informes Mensais FII estruturados e atualizados semanalmente, mas isso não torna os quatro pilares qualitativos uniformes. Ver [dataset CVM](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal) e a orientação do [novo informe mensal](https://www.gov.br/cvm/pt-br/assuntos/noticias/2024/cvm-orienta-sobre-novo-informe-mensal-para-fundos-de-investimento-imobiliarios/).

Conclusão: a automação integral exigiria parsing e normalização auditável por administrador, além de política explícita para campos ausentes. Até essa etapa, `DATA_GAP` é o único estado metodologicamente correto.
