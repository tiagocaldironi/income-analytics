# Validação do PR5.1

Baseline fixa: `ca627ac72f110d0f4d62faaa9c51a08eaed54965`.

## Preservação de estado

- Criado worktree novo `ci-offline-pr51`, com branch `codex/ci-offline-pr51` a partir da baseline. Não houve reset, stash, limpeza ou mudança de branch em checkout existente.
- Os seis documentos de assessment foram copiados para a branch, mantendo os originais intactos.
- Apenas declarações de dependência, ignore, workflow, ferramentas/testes de CI e documentação foram alterados. `git diff ca627ac -- income-analytics/src income-analytics/tests income-analytics/alembic` deve permanecer vazio.
- Nenhum launcher, processo, configuração ou banco produtivo foi utilizado pelo runner. Migrations de teste e smoke ocorreram exclusivamente em SQLite descartável.

## Execução exploratória antes do primeiro commit

Instalação em venv nova por hashes, seguida de instalação local sem resolução e `pip check`, aprovada. Runtime testado em outra venv sem pytest, aprovado. Validação estática do YAML confirmou trigger PR, localização na raiz Git, permissões mínimas e Actions fixadas por SHA. Ruff dos arquivos novos de CI aprovado.

Resultados encontrados: Ruff 130 diagnósticos, mypy 674 erros, Python 995 aprovados / 14 failures / 9 errors / 5 skips, frontend 29/30 aprovadas e CERT_48 dedicado reprovado. Esses resultados são de árvore de trabalho com a implementação ainda não commitada; não são apresentados como aprovação do SHA da baseline. Detalhes e causas estão em [known_failures.md](known_failures.md).

O runner registra `worktree_dirty` para distinguir exploração local de execução de commit limpo. Relatórios por SHA e execução remota devem ser consultados nos checks/artifacts do PR; nenhum payload de falha ou banco deve ser anexado ao PR.

## Critério de recomendação

O PR pode ser revisado como implantação de uma esteira diagnóstica que reporta corretamente dívida existente. Não há recomendação automática de merge com checks vermelhos: os responsáveis devem revisar os resultados, a disponibilidade das evidências e a política de integração. Não ativar checks obrigatórios prematuramente. Não há autorização de deploy, e CERT_48 permanece bloqueador de certificação e promoção de produção.
