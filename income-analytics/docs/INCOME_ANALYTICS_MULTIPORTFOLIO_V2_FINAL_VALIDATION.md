# Multiportfólio V2 — validação final e correções

**Decisão atual: INCOMPLETE.** As validações de backend, finanças, isolamento, importação B3, Magic Formula e performance foram executadas. A única classe de gates ainda não certificada é a interação real em navegador desktop/mobile, bloqueada por limitações comprovadas do ambiente. A suíte completa final passou: **883 testes aprovados, 6 avisos de depreciação e zero falhas** (882 existentes + 1 regressão nova).

## Resultado principal

Foi confirmado e corrigido um defeito V2 no read model: uma carteira recém-criada podia exibir o snapshot da carteira MAIN. O contexto de worker podia fazer as rotas de leitura do snapshot caírem na carteira MAIN, mesmo com `X-Portfolio-Id` explícito. Agora o snapshot é preparado durante a criação e as rotas de dashboard/holdings selecionam o read model pelo header validado; chamadas legadas sem header continuam usando MAIN. O teste de regressão verifica que carteira vazia recebe HTTP 200, não mostra posições/classes e mantém o snapshot igual à leitura direta, mesmo quando MAIN tem posições.

Também foram corrigidos dois problemas de infraestrutura de teste: um monkeypatch que vazava método vinculado após teardown e o nome do banco de testes baseado apenas no PID, que podia reutilizar dados antigos quando o Windows reciclava o processo. Agora o teste substitui o método na factory e cada execução usa arquivo SQLite com UUID. Nenhuma expectativa financeira foi relaxada.

Não houve mudança em fórmula TWR, patrimônio, renda, fluxos de capital, benchmarks, B3 ou metodologia da Fórmula Mágica. Nenhuma migration foi necessária. Não houve implementação de V3.

## Banco e integridade

O banco real foi usado somente em leitura. O backup foi verificado, a revisão é `0020_shared_pension_quota_identity`, `integrity_check=ok`, `foreign_key_check=0`, e o checksum SHA-256 da origem permaneceu igual antes/depois (`3122a50bc7dff518dce54719c6fcd70be1529243e9153f00d283613255e33c8f`). Testes e mutações B3 ocorreram em cópias isoladas. Evidência privada detalhada ficou em armazenamento local fora do repositório.

## Evidência financeira e isolamento

Os hashes históricos existentes para resumo da carteira, dashboard e holdings foram preservados. Para as demais rotas, foram comparados contexto legado MAIN sem header e MAIN explícita, usando a mesma cópia, parâmetros e período. Foram semanticamente equivalentes em 17 pares de endpoints. A chamada de Wealth Explanation selecionada retorna o mesmo HTTP 422 nos dois caminhos; foi classificada `PREEXISTING_EQUIVALENT`, sem alteração.

Os testes de isolamento cobrem carteira A/B, mesmo ativo com posição e custo independentes, read models, cache, operações, renda, alvos, ativos privados e identidade de cota de previdência compartilhada. A Fórmula Mágica continuou em `MF_BR_2027_V1`, com os mesmos hashes, snapshot e 165 empresas ranqueadas nos contextos MAIN/A/B.

O token de preview B3 de A foi rejeitado ao tentar aplicar em B por HTTP 404, sem gravações. O token foi aceito pelo proprietário e reaplicado idempotentemente em uma cópia isolada.

## Performance

Foram medidos 30 pares aquecidos para dashboard, holdings e TWR; e comparações pareadas para evolução patrimonial, comparação de performance e findings. Não apareceu overhead V2 consistente ou material. Nas medianas, TWR foi 1,341 s no caminho legado e 1,365 s no explícito; os dois caminhos têm caudas variáveis. Isso aponta custo compartilhado no cálculo atual, não regressão de contexto V2.

## Limite de navegador

Desktop e mobile permanecem `NOT_RUN_ENVIRONMENT_LIMITATION`: o navegador disponível falhou com `ERR_CONNECTION_REFUSED` em `127.0.0.1:8000`, e a execução de servidor local isolado foi recusada pela política do ambiente. Não foi instalado framework pesado nem contornado o controle. A validação ASGI com `TestClient` e o teste Node do frontend são evidências separadas, não substituem E2E visual.

Consulte a matriz e os apêndices em [multiportfolio_v2_final_validation](appendices/multiportfolio_v2_final_validation/). O estado final só será marcado `PASS` se todos os gates executáveis terminarem aprovados; com os gates de navegador indisponíveis, o resultado permanece `INCOMPLETE`.
