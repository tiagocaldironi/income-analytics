# Fórmula Mágica — correção de carregamento em runtime

**Resultado: PASS no runtime HTTP; smoke visual do navegador: NOT_RUN.** O snapshot V12.2 não foi recalculado e a política não mudou.

## Causa encontrada

Antes do reinício, o Uvicorn já em execução devolvia HTTP 200, mas com a resposta antiga do preview (`MAGIC_FORMULA_STOCKS_V1`, `ranking_gate=BLOCKED`, referência 31/12/2025 e 179 empresas no resumo de preview). A interface atual espera o contrato do ranking publicado (`MF_BR_2027_V1`, `snapshot`, `summary` e paginação). Portanto, a tela e o backend carregado no processo estavam em versões diferentes. O processo servia arquivos estáticos atuais, mas mantinha módulos Python antigos em memória.

O build e o processo estavam configurados para o mesmo diretório e banco: `C:\Projetos\income-analytics` e `C:\Projetos\income-analytics\data\magic_formula\canonical_rankings.db`. `INCOME_ANALYTICS_DATABASE` não estava definido; essa variável configura o banco da carteira, enquanto o ranking canônico usa `RANKING_DB` relativo ao diretório de trabalho. O snapshot publicado estava presente nesse banco: `mf-f1ee50809c83979ba221d84e`, política `MF_BR_2027_V1`, 165 linhas.

Ao reiniciar, apareceu um segundo bloqueio de inicialização: a reconstrução do read model da carteira lança `ValueError` quando encontra uma venda acima da posição existente. A inicialização agora registra o stack trace e continua servindo rotas independentes, incluindo a Fórmula Mágica. Os lançamentos da carteira não foram alterados. O erro continua visível no log em `tmp/magic_formula_runtime/uvicorn.stderr.log`.

## Correções

- O endpoint retorna `status=AVAILABLE` com o contrato point-in-time, ou `status=NO_PUBLISHED_RANKING` quando não existe snapshot publicado. Erro ao ler o repositório resulta em HTTP 503 e log, em vez de uma resposta vazia que parecia ausência de dados.
- O cliente HTTP aborta requests após 15 segundos. A tela apresenta mensagem de falha com ação de nova tentativa; ausência de snapshot tem mensagem própria. A Fórmula Mágica não depende mais do sucesso simultâneo do endpoint de FIIs.
- O startup registra a falha de reconstrução da carteira sem derrubar o servidor inteiro.
- Testes de regressão verificam endpoint real via ASGI, contrato persistido, estado sem snapshot e tolerância de startup à inconsistência reportada.

## Evidência de runtime

Depois do reinício no mesmo diretório, com o mesmo comando Uvicorn e ambiente do processo anterior, a chamada HTTP real respondeu 200 com `MF_BR_2027_V1`, snapshot `mf-f1ee50809c83979ba221d84e`, total 165 e 25 itens na primeira página. O log registra startup completo e as chamadas de página, busca, filtros e detalhe retornando 200. A busca por WEGE3 retornou uma empresa; o detalhe trouxe proveniência point-in-time. Varejo filtrado retornou 140 resultados; a paginação da página 2, aviação e filtro combinado também foram consultados e mantiveram ranks globais.

O navegador embutido já havia recusado navegação para localhost por política de URL. Por isso, a execução manual no browser e a observação do DOM/console ficam como `NOT_RUN`, sem alegar que a tabela foi observada visualmente. O endpoint e o JavaScript servido agora usam o mesmo contrato, e a renderização da tabela está coberta estruturalmente pelos testes automatizados.

## Verificações

- Testes focados Fórmula Mágica/runtime/UI: 43/43 PASS.
- Baseline V9.2: os 273 IDs foram encontrados e passaram na suíte final.
- Suíte completa: 840/840 PASS.
- Ruff nos arquivos Python alterados: PASS; `node --check` nos dois módulos JavaScript: PASS.
- Política, snapshot, 165 empresas e ranking: preservados; não houve recálculo.

O artefato detalhado de evidência de runtime está em [runtime_loading_fix.json](appendices/magic_formula_v12_2/runtime_loading_fix.json).
