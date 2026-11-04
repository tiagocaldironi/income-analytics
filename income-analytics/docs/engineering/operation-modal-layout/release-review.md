# PR81 / Issue78 — publicação controlada

O proprietário autorizou a publicação do modal simplificado. O código interno não é mais um campo de usuário. A criação por nome reutiliza a identidade canônica existente, inclusive após encerramento da posição; rejeita ambiguidade e contratos legados. Edições preservam ativo/tipo e exigem identificador original. Chamadas anteriores com ticker continuam compatíveis. Título novo recebe identificador interno; não se inventam cotações.

Alterações de domínio, fórmulas, unidades, manifests e arquivos financeiros congelados: nenhuma. A dependência executada continua sendo a aplicação Tesouro/PortfolioSession já coberta no escopo restrito; CERT_48 permanece fora dos caminhos executados, a verificar no trace do candidato.

A certificação restrita mantém todos os alvos anteriores e exige também a execução de create_treasury_trade e amend_treasury_trade. O gate de promoção inclui explicitamente o PR81 e exige novo registro de autorização vinculado à superfície certificada e CI hospedada do candidato.

A revisão de deslocamentos atualiza somente o hash auditado do arquivo de rotas no manifesto de localização (não os hashes de certificação). Mantém baseline original, ledger e inventário de tipagem aceito. Somente blocos de sintaxe com texto integralmente idêntico podem reutilizar diagnósticos históricos: nenhum diagnóstico de bloco alterado é dispensado. A comparação oficial precisa demonstrar ausência de regressões novas.

Validação funcional inicial: 62 testes Python e 33 suítes frontend aprovados; Ruff aprovado; cenários novos cobrem criação HTTP sem código, reutilização após venda total, venda sem ativo, ambiguidade e contrato legado. A certificação ampliada, segurança, build, staging/rollback e aprovação de promoção hospedados permanecem obrigatórios antes da publicação.

Operação: reutilizar a instância Windows/Tailscale na porta 8002, com backup consistente e integridade SQLite verificada, preservando WIP e configurações. Não executar migrations nem substituir o banco. Retorno à versão 459639b deve preservar novos fatos do usuário; cache pendente requer recuperação pelo procedimento já ensaiado.
