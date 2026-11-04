# Confirmação rápida de exclusões

Base: `develop` integrado pelo PR #69, commit `47535d1`.
Implementação em `codex/fast-operation-delete`, sem alteração na instalação publicada.

## Causa e comportamento

O DELETE aguardava o carregamento completo da sessão financeira e o rebuild de
patrimônio, rentabilidade, posições, histórico e alocação antes de responder.
O modal mantinha “Excluindo…” durante todo esse trabalho.

Agora a resposta confirma somente uma exclusão já commitada. Remoção, tombstones
de importação, auditoria e invalidação do snapshot pertencem à mesma transação.
Falha na gravação não retorna sucesso e desfaz também a remoção e a auditoria.
O recibo HTTP 200 inclui `deleted`, `event_id`, `portfolio_id` e
`dashboard_refresh: UPDATING`. Não há sucesso otimista antes do commit.

Dois workers no máximo consolidam as revisões pendentes. Cada carteira tem um
único trabalho ativo; exclusões consecutivas são agrupadas. A publicação usa
UPDATE condicional pela versão persistida: um cálculo antigo não pode substituir
uma revisão mais recente. Escritas síncronas capturam a revisão antes de carregar
o ledger e também respeitam esse controle. Não foram alteradas fórmulas ou regras
de projeção. O mesmo builder alimenta a consolidação síncrona e a assíncrona.

O estado `UPDATING` é persistido no snapshot existente, sem migração. GET do
dashboard/status retoma pendências após reinício. Falhas de cálculo deixam
`ERROR`, sem desfazer uma exclusão confirmada e sem repetição automática infinita.
POST autenticado e protegido por CSRF no mesmo endpoint de status permite uma
tentativa explícita. Os mesmos controles de propriedade e carteira arquivada
continuam anteriores aos caminhos rápidos.

Na Minha Carteira os valores antigos não são exibidos como atuais enquanto há
recálculo: aparecem o estado de atualização e acompanhamento limitado a 90
consultas de metadados, a intervalos de um segundo. Troca de carteira/nova carga
descarta o acompanhamento anterior. O modal confirma a remoção antes das leituras
de histórico e totais, e a tela Operações não mantém o botão bloqueado pelo rebuild.

## Medição controlada local

Teste de DELETE via HTTP/TestClient, em dois bancos privados descartáveis,
criados do mesmo backup SQLite, com o mesmo lançamento e as mesmas cotações.
O processo de aplicação já inicializado foi o alvo: cold start não compõe a métrica.
Nenhum lançamento do banco em uso foi excluído durante a medição.

| Medida | Antes | Depois |
| --- | ---: | ---: |
| Confirmação HTTP após commit | 28,192 s | 0,339 s |
| Conclusão da consolidação | 28,192 s | 26,667 s |
| Payload financeiro final completo | referência | idêntico à referência |

Redução observada de aproximadamente 98,8% no tempo de confirmação. O recálculo
continua custando dezenas de segundos: ele foi retirado do caminho da confirmação,
não eliminado. Esta amostra local não demonstra p95/p99 nem garante latência total
inferior a um segundo no navegador/Tailscale sob qualquer carga. RTT, CSRF,
contenção de escrita SQLite e carga do host continuam relevantes.

Os bancos, perfis e payloads usados na comparação permanecem em evidência privada,
fora do Git. Este documento não inclui ativos, saldos, identificadores de usuário,
credenciais ou cópias dos dados pessoais.

## Validação

Rodada final: **116 testes Python aprovados**, seis suítes frontend aprovadas,
zero falha ou skip nos testes selecionados. Warnings de depreciação existentes
de FastAPI/Starlette permanecem visíveis.

- Testes HTTP: confirmação anterior à conclusão de worker bloqueado; ausência de
  carregamento/projeção no DELETE; commit, auditoria e invalidation atômicos;
  rollback diante de erro SQLite; exclusão inexistente/duplicada/entre carteiras;
  comparação de revisão; falha de agendamento; retry explícito após falha.
- Fila: agrupamento de pedidos, descarte de revisão antiga, recuperação de
  pendência, falha observável, dois contextos de proprietário/carteira separados.
- Regressões: histórico, Tesouro, revisões, projeção, múltiplas carteiras,
  autorização Firebase e módulos de interface.
- Frontend: modal existente e prevenção de duplicidade; polling limitado,
  mudança de carteira, erro, conclusão, operações, deadlines e controles Tesouro.
- Ruff e `git diff --check` aprovados nos arquivos alterados.
- Mypy direcionado: 93 ocorrências na base e 92 no candidato, comparando mensagem,
  regra, módulo e multiplicidade, sem novos diagnósticos semânticos. Não é aprovação
  do gate oficial: suas identidades incluem linhas, deslocadas por esta mudança.
  Nenhum baseline de qualidade foi atualizado ou dispensado.
- Os 41 arquivos da referência financeira permanecem com a mesma identidade Git
  e conteúdo lógico; manifests, hashes, fixtures e motor congelado não foram editados.

## Limites de entrega

Não houve merge, deploy, migration ou alteração do launcher produtivo nesta tarefa.
A aprovação financeira e o GO do PR #69 não são transferidos a este código novo.
CI hospedada, revisão do escopo afetado e liberação continuam pendentes. Eventuais
relocações de diagnósticos históricos precisam de revisão pelos controles existentes;
não são ocultadas por alteração da baseline nesta implementação.

A fila é do processo existente, não uma nova infraestrutura. Após parada abrupta,
a retomada depende de uma leitura autorizada do dashboard/status. A versão
persistida impede sobrescrita obsoleta mesmo quando há trabalho concorrente.
