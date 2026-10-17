# Magic Formula Stocks — correção do Accounting Registry

## Status final

- `DEV_STATUS`: `HUMAN_REVIEW_REQUIRED`
- `TOOL_STATUS`: `VALIDATION_REQUIRED`
- Ranking: **não ativado**.

## Defeito e evidência

Os DFPs consolidados de 2025 de Votorantim, Vale, Localiza, MRV e Ambev
possuem `1.01.02` como Aplicações Financeiras. O registry inicial somava essa
conta a ativos correntes operacionais, inflando NWC. Também não havia regra de
EBIT, embora `3.05` esteja disponível como resultado antes do resultado
financeiro e dos tributos.

## Correção

O V1 não tinha snapshots de produção persistidos (a verificação da base
retornou zero), portanto a correção não altera histórico publicado. O registry
passou a usar `EBIT_RULE_002` para DRE `3.05` e `NWC_ASSET_RULE_002` apenas
para BPA `1.01.03` e `1.01.04`. `1.01.02` é excluída tanto de OCA quanto de
caixa. A dívida de longo prazo usa apenas BPP `2.02.01`, não o passivo não
circular inteiro.

## Testes adicionados

O teste de regressão insere aplicações financeiras materiais (`999`) e prova
que OCA permanece `50` e NWC `35`; logo a conta financeira não participa do
cálculo. O fixture também verifica EBIT, caixa, dívida CP/LP, imobilizado,
escopo consolidado e `Decimal`.

## Riscos residuais

O registry é deliberadamente estreito. A validação multissetorial ainda deve
confrontar cada companhia e período com fontes independentes, preservar a
referência financeira/mercado e decidir exceções por setor. Não há fallback
automático, ranking, score ou mudança para `AVAILABLE` nesta correção.
