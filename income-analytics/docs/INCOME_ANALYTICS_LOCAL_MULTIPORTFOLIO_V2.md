# Income Analytics — carteiras locais múltiplas V2

## Resultado

A aplicação local agora permite manter várias carteiras independentes no mesmo banco SQLite. `MAIN_PORTFOLIO_ID` mantém o UUID V1 `7a54eeb7-542a-5832-8544-8be7dcb0237e`; a migração 0020 adiciona uma identidade compartilhada para séries públicas de cotas de previdência e impede nomes ativos duplicados sem diferenciar maiúsculas/minúsculas.

O seletor da barra superior persiste a carteira ativa em `income.activePortfolioId`. O cliente envia `X-Portfolio-Id` em cada chamada. O middleware valida o UUID e o status antes de construir `PortfolioSession`; ID explícito inválido retorna 400/404 e carteira arquivada não aceita escrita. Chamadas legadas sem cabeçalho continuam usando MAIN.

## Contrato de gestão

- `GET /api/portfolios`: lista carteiras ativas e arquivadas.
- `POST /api/portfolios`: cria uma carteira vazia; recebe `name` e `base_currency` opcional (BRL por padrão).
- `PATCH /api/portfolios/{id}`: renomeia uma carteira ativa.
- `POST /api/portfolios/{id}/archive`: arquiva sem excluir registros; MAIN e a última carteira ativa são protegidas.
- `POST /api/portfolios/{id}/restore`: restaura uma carteira arquivada.

Os nomes são aparados e limitados a 100 caracteres. Nome ativo duplicado retorna 409. Criar uma carteira não copia ativos nem dados financeiros. Ao iniciar, o cliente preserva a seleção válida; sem seleção válida, usa MAIN ativo e depois a primeira carteira ativa.

## Dados compartilhados e próprios

Operações, rendimentos importados, configuração, alvos, detalhes de renda fixa/previdência/imóveis, importações B3, snapshots, execuções de atualização e regras recorrentes permanecem ligados à carteira. Ativos de mercado e séries de preço, câmbio e índices seguem globais. Séries de cotas de previdência são globais por CNPJ CVM; os vínculos entre plano e veículo continuam por carteira.

Ativos com detalhes de renda fixa, previdência ou imóveis não podem ser reutilizados por outra carteira via busca de ticker; o sistema devolve erro explícito. Outros ativos canônicos e dados de mercado continuam compartilháveis. Não há autenticação, usuário, sincronização, soma global de carteiras ou exclusão física.

## Troca de carteira

O cliente centraliza a seleção, mantém a rota corrente e inicia a carga daquela carteira. Respostas recebidas depois que a seleção mudou são descartadas como `AbortError`, para não substituir a tela atual com dados antigos. A migração do banco existente cria backup antes de atualizar o esquema fora de ambiente de testes.

## Validação

O baseline anterior à implementação passou com 876 testes; após as alterações, a suíte completa passou com 882. Um servidor HTTP isolado passou pelo fluxo de criar B, operar, alternar MAIN/B, renomear, arquivar, rejeitar escrita e restaurar. No runtime local, as respostas brutas de MAIN, dashboard e holdings mantiveram os mesmos hashes antes e depois da migração 0020; a migração criou backup automático e o servidor voltou saudável. Consulte `docs/appendices/local_multiportfolio_v2/release_gate.json` para os gates finais e `test_manifest.txt` para os comandos executados.

## Limites verificados

As verificações de browser desktop/mobile e comparação financeira dourada do banco pessoal são registradas como `NOT_RUN` quando não foram executadas. Isso não é uma declaração de aprovação. Os dados reais do usuário não são copiados para os apêndices nem alterados por testes; a validação de escrita usa banco de testes isolado.
