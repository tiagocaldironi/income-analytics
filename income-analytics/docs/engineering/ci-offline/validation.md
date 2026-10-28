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

## Commit e execução em clone limpo

Commit inicial: `e023ade90345e2393806932558cb2bfbbb9f9f2a`. Clone novo, checkout detached com `core.autocrlf=false`, venv nova, instalação por hashes e `pip check` aprovados. Árvore limpa nos relatórios (`worktree_dirty:false`). Nenhum diretório pessoal de dados ou credencial copiado.

Resultados: Ruff 130; mypy 674; Node 29/30 suítes existentes aprovadas mais autoteste da guarda; CERT_48 uma falha; Python **994 passed, 15 failed, 9 errors, 5 skipped**, cobertura de linhas 80,69%. Diferença contra CRLF: uma fixture congelada de identidade/preço também diverge em LF. Os diagnósticos de Ruff/mypy e resultados Node foram reproduzidos no GitHub.

Primeiro workflow remoto: [run 40689578278](https://github.com/tiagocaldironi/income-analytics/actions/runs/40689578278), merge sintético `38a68ff7880b35651d094ed097e3ff71679a015b`, head `e023ade`. Todos os seis checks foram executados e geraram artifacts; runtime mínimo passou. Python remoto teve 993 passed/16 failed/9 errors/5 skipped, incluindo uma falha extra no teste de segurança do caminho temporário. O runner foi ajustado para resolver aliases de TEMP no Windows antes de configurar o ambiente; cinco testes próprios da CI mais o teste de segurança passaram na validação dirigida. A execução remota posterior é necessária para confirmar a correção na plataforma hospedada.

## Critério de recomendação

O PR pode ser revisado como implantação de uma esteira diagnóstica que reporta corretamente dívida existente. Não há recomendação automática de merge com checks vermelhos: os responsáveis devem revisar os resultados, a disponibilidade das evidências e a política de integração. Não ativar checks obrigatórios prematuramente. Não há autorização de deploy, e CERT_48 permanece bloqueador de certificação e promoção de produção.
