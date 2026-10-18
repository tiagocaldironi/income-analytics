# Contrato legado sem cabeçalho

`GET /api/portfolio` sem `X-Portfolio-Id` retornou HTTP 200 e o corpo bruto foi idêntico ao request com `X-Portfolio-Id: 7a54eeb7-542a-5832-8544-8be7dcb0237e`. IDs explícitos malformado e inexistente retornaram 400 e 404, respectivamente, sem fallback.

`LEGACY_HEADERLESS_MAIN_FALLBACK=PRESENT`
`LEGACY_FALLBACK_CLASSIFICATION=COMPATIBILITY_ONLY`

**THIS CONTRACT MUST NOT BE USED AS AUTHORIZATION FALLBACK.** A V2 ainda não possui autenticação/autorização; este comportamento existe apenas para compatibilidade legada.
