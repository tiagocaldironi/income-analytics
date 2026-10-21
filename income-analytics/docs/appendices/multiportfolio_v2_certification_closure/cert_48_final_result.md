# CERT_48 — resultado final

**CERT_48 = PASS_WITH_HISTORICAL_LIMITATION_ACCEPTED.** O gate histórico não foi reescrito nem tratado como equivalente: a investigação de origem é `UNRESOLVABLE`, a lacuna foi aceita e a busca adicional foi encerrada. O manifesto legado e seus hashes esperados permanecem preservados como `UNRESOLVED_LEGACY_BASELINE`.

O novo gate é prospectivo. `MF_BR_2027_V1_FROZEN_ENGINE_BASELINE_V2` liga o código atual, o contrato comportamental e os testes ao commit `63e742b`; seu payload determinístico tem SHA-256 `a19381cb17819222116d5ede4b89f00e48de0765fead6c556b3055584148e8cb`. Duas gerações do manifesto produziram o mesmo payload/hash. Foram protegidos 23 arquivos de implementação, 25 arquivos de teste e 8 casos semânticos.

Os 8/8 goldens passaram. A auditoria A–O confirmou mercado 010 sem fallback para 020, tratamento de UNIT e classes sem duplicação, seleção S4 independente de EY/ROC/rank, L3 e S4 consistentes com a política ativada, subtração de tesouraria, ausência de filtros mínimos de market cap/volume, screening posterior para varejo/aviação, utilities incluídas e exclusões financeiras estruturais mantidas.

A política e o snapshot canônico não mudaram: `MF_BR_2027_V1`, policy hash `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`, snapshot `mf-f1ee50809c83979ba221d84e`, ranking hash `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3`, 165 empresas e canonical result SHA-256 `162c1b2f8856ae7d88cf5809d9418395464d0b2042bf6177fb48141e5b4fcf6a`. Os testes também verificaram o hash bruto do artefato publicado, que cobre EY, ROC e os ranks salvos.

| Verificação | Resultado |
|---|---:|
| Goldens semânticos | 8/8 PASS |
| Regressões Magic Formula | 370 PASS, 0 FAIL |
| Suíte completa | 893 PASS, 0 FAIL, 0 SKIP, 6 warnings |
| Isolamento V2 | 20/20 PASS |
| Ruff nos arquivos Python alterados | PASS |

O gate V2 foi atualizado para `PASS`; a limitação de validação automatizada de navegador continua registrada como `NOT_RUN_ENVIRONMENT_LIMITATION`, com as verificações manuais desktop e mobile preservadas. Nenhuma metodologia, política, fórmula, ranking ou implementação V3 foi alterada. A fundação de membership pode avançar como próxima fase, mas não foi iniciada nesta execução.
