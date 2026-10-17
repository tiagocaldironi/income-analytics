# Segurança dos dados da carteira

## Base em uso

O backend local usa a base indicada por INCOME_ANALYTICS_DATABASE. Em uso
normal ela é income_analytics.db; testes automatizados não podem utilizá-la.

## Ambiente de testes

O arquivo tests/conftest.py força toda execução do pytest para uma SQLite
temporária do sistema operacional, com INCOME_ANALYTICS_TESTING=1. Nenhuma
suíte deve apontar para a base da carteira.

## Migrations

Antes de aplicar uma migration pendente na base em uso, o backend cria uma
cópia em backups/, com data UTC no nome. A migration é aditiva por padrão:
adicionar campos/tabelas e preservar registros; remoção ou transformação
irreversível exige uma task explícita e restauração validada.

## Regra operacional

1. Validar código e migrations no banco temporário de testes.
2. Executar a suíte de regressão.
3. Fazer backup automático.
4. Aplicar migration na base da carteira.
5. Validar reconstrução e contagem de ativos/eventos sem alterar os dados.

O botão “Excluir todos os dados” continua sendo a única operação da aplicação
autorizada a apagar registros, com confirmação explícita.
