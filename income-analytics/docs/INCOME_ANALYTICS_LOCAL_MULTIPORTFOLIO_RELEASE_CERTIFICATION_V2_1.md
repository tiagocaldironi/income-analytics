# Income Analytics — certificação de release Multiportfólio V2.1

**Resultado: INCOMPLETE.** A revisão do banco local, as três comparações financeiras históricas disponíveis, os contratos de escopo e a suíte completa não revelaram regressão V2. Porém, a certificação completa exige equivalência dourada para mais endpoints, comparação explícita do Magic Formula e gates de browser desktop/mobile. Eles não puderam ser executados neste ambiente e permanecem `NOT_RUN`; portanto, não declaro V2 como `PASS` nem avanço para User/Membership/Authentication.

## Evidência executada

- Banco pessoal identificado em `income_analytics.db`, revisão Alembic `0020_shared_pension_quota_identity`. Uma cópia SQLite consistente foi criada fora do repositório e verificada por checksum, `integrity_check`, chaves estrangeiras, esquema e contagens de linhas. O banco fonte permaneceu com o mesmo SHA-256 durante e após as leituras HTTP; `REAL_DB_TEST_WRITES=0`.
- MAIN `7a54eeb7-542a-5832-8544-8be7dcb0237e` existe exatamente uma vez; `foreign_key_check=0`, órfãos referenciando carteira `0` e grupos duplicados nas chaves verificadas de referências globais `0`.
- Os hashes brutos históricos guardados para `/api/portfolio`, `/api/portfolio/dashboard` e `/api/portfolio/holdings` coincidem com as respostas atuais, todas HTTP 200. Esta evidência cobre somente esses três endpoints; os outros outputs financeiros não têm baseline anterior equivalente nos artefatos V2.
- GET sem cabeçalho equivaleu byte a byte a MAIN. IDs explícitos inválido e inexistente foram rejeitados com HTTP 400 e 404, sem fallback silencioso para MAIN.
- A suíte completa passou: `882 passed`. Testes multiportfólio cobrem isolamento A-B-A/B-A-B, IDs inválidos, arquivamento, ativo privado, previdência compartilhada e seleção/escopo do frontend. O teste Node de troca de carteira passou.
- Ruff passou em todos os 109 arquivos Python modificados na branch V2. A varredura completa do repositório retorna 35 diagnósticos em oito arquivos não modificados por V2; são preexistentes e não foram corrigidos nesta certificação.
- O sanity de performance mediu endpoints aquecidos. A comparação não é conclusiva contra V1: o intervalo/cache não é uma baseline pareada; a rota de performance teve 2,87 s aquecida e a referência aproximada anterior era 1,31 s. Isso precisa de baseline comparável antes de concluir regressão.

## Gates pendentes

1. Comparação dourada para alocação, renda, operações, evolução patrimonial, explicação patrimonial, TWR/performance, comparação de índices, findings, targets/configuração e Magic Formula.
2. Browser real em desktop e mobile, incluindo ciclo B, persistência, arquivamento/restauração, preservação de rota, stale UI, race tardia e overflow mobile.
3. Aplicar token B3 de outra carteira e validar rejeição cross-portfolio por HTTP.
4. Medir performance contra uma baseline pareada e registrar o resultado da não regressão.

O browser embutido recusou a navegação automatizada por política de segurança; a inicialização de um servidor dedicado isolado também foi bloqueada pela política da ferramenta. Não usei o browser conectado ao banco pessoal para executar mutações, nem tentei contornar essas restrições. Esses limites estão documentados como `ENVIRONMENT_LIMITATION`, não como falha de arquitetura.

## Artefatos

O resumo comittable está em `docs/appendices/local_multiportfolio_v2_1/`. Evidências locais com caminhos, checksums e hashes financeiros ficam em `%USERPROFILE%\.codex\local-evidence\income-analytics-v2-1\` e não são comittadas. Nenhum payload financeiro foi incluído no repositório.

**Decisão:** `INCOME_ANALYTICS_LOCAL_MULTIPORTFOLIO_RELEASE_CERTIFICATION_V2_1 = INCOMPLETE`. Não iniciar V3 com base nesta certificação; não houve implementação nesta fase.
