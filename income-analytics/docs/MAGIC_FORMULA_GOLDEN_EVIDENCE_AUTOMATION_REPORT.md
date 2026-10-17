# Magic Formula Stocks — Automação de Evidência Golden

## Arquitetura

O fluxo de evidência é separado em três agentes independentes: DFP contábil,
FCA/composição de capital e B3 COTAHIST. O builder apenas consolida seus
contratos; ele não lê snapshots nem busca provedores.

## Referências reproduzíveis

- DFP: arquivo, código CVM, data, escopo, demonstração, conta e período.
- FCA: arquivo, registro de formulário, CNPJ, ticker e data de validade.
- Capital: registro de composição de capital mais classe explícita.
- COTAHIST: ZIP, membro TXT, número da linha, data, ticker e fechamento.

## Gate

Uma fixture só fica `READY_FOR_VALIDATION` quando todos os componentes,
unidades e referências de origem existem. A validação compara cada métrica e
cada componente contra um read-back de snapshot em nova sessão. Falta de
lineage é `REVIEW_REQUIRED`; divergência é `FAIL`.

## Correção de lineage

Foi identificado que snapshots V1 registravam o total de OCA em cada uma de
suas contas. Isso impede auditoria por componente. A correção preserva a
metodologia e cria evidência sob `CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE`;
snapshots V1 permanecem imutáveis e não devem ser sobrescritos.

## Estado de publicação

O ranking permanece inativo. A promoção para `RESOLVED` exige a materialização
dos snapshots V2 e o PASS completo do QA para cada emissor.
