# PR82: atualização de cotações e concorrência SQLite

O controle de frequência fazia commits SQLite diretamente no event loop HTTP.
Um leitor concorrente que precisava do mesmo loop para terminar podia impedir o
commit até o timeout. O teste em banco descartável reproduziu `database is locked`
antes da correção e passou depois de mover as sete chamadas para workers aguardados.
Os limites, chaves, janelas, contadores atômicos e respostas de segurança são mantidos.
Isso corrige o mecanismo reproduzido, sem prometer eliminar toda contenção SQLite.

Tesouro Direto continua sem provedor automático de cotação. Este PR não altera
lançamentos, preços, fórmulas, schema ou a configuração do banco produtivo.

## Evidência do primeiro candidato

- Head `b62b5ab359fe58f5d0b8e9e821351bcb9dd6b82d`; execução hospedada
  [44275644151](https://github.com/tiagocaldironi/income-analytics/actions/runs/44275644151).
- 24 testes locais de concorrência, autorização e headers aprovados; Ruff aprovado.
- Frontend, instalação, build, prontidão operacional e Python engineering aprovados.
- SAST sem achados pendentes; 150 testes de segurança aprovados.
- Mypy completo: 481 achados, nenhum no arquivo alterado. Comparação pelo mapeamento
  auditado existente: zero ocorrências novas contra as 486 originalmente aceitas.
- O registro dos oito diagnósticos já resolvidos em `saas_security.py` foi revisto
  contra esse relatório; continuam resolvidos, sem aceitar dívida nova. Seu hash
  foi atualizado para os bytes Git do arquivo efetivamente analisado.

## Correção de dependência necessária

A auditoria identificou `opentelemetry-api==1.45.1` afetado por
[GHSA-mf5v-w3w3-f6cg](https://github.com/advisories/GHSA-mf5v-w3w3-f6cg).
O patch 1.45.2 substitui exclusivamente esse pacote nos locks runtime e desenvolvimento.
SHA256 do wheel PyPI: `2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34`.
O resolver com hashes aceita a alteração sem outras mudanças de dependências.
A referência de compatibilidade do lock foi atualizada; versões das ferramentas
de qualidade, configuração de escopo e baseline de diagnósticos permanecem iguais.
O smoke do pacote corrigido aceita traceparent válido e rejeita o tamanho excessivo.
Esta atualização exige nova CI; a evidência do primeiro candidato não a certifica.

## Decisão pendente, sem ativação

O aceite em `ci/typing-baseline-acceptance.json` venceu em 17/11/2026 (UTC).
Proposta para o proprietário: renovar até **02/12/2026**, mantendo o inventário
exato de 486 ocorrências, responsáveis, riscos e referências já documentados em
`docs/engineering/release-policy-65/occurrence_risk_proposals.json`. Os 481 achados
atuais são um subconjunto desse inventário; os cinco ausentes não compensam erros novos.
Digest do conteúdo originalmente aceito:
`bfb56031699c3b79908657442703c086cc6f18fceea8f9c7d30abee1c177b74e`.

Esta é uma proposta, não uma renovação. Nenhum prazo ou aceite foi alterado.
Também é necessária aprovação específica da superfície final do PR82 para a
promoção por escopo: o aceite do PR81 não se transfere ao middleware e aos locks
alterados. Uma eventual autorização permanece condicionada à CI do candidato,
segurança, certificação pertinente, staging e rollback aprovados. Não dispensa
CERT_48, não aceita falhas financeiras novas e não autoriza publicar com gate vermelho.
