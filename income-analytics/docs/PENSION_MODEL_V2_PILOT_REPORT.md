# PENSION_MODEL_V2_PILOT_REPORT

## Summary

Previdência v2 foi consolidada como uma implementação full stack compatível
com os planos já persistidos. A identidade do plano permanece interna e cada
novo plano recebe um identificador técnico próprio, permitindo planos distintos
na mesma administradora ou patrocinadora.

## Current Model Analysis

O modelo anterior tratava previdência como PGBL/VGBL obrigatório, misturava
nome do plano com produto e exigia um identificador visível. Não havia origem
de posse, estrutura aberta/fechada, patrocinador, match, vesting ou composição
opcional do saldo.

## Final Domain Model

- O ID do ativo continua sendo o identificador interno. Novos planos recebem
  ticker técnico PENSION-UUID automaticamente; o formulário não o exibe.
- PensionPlanDetails passou a suportar origem, estrutura, produto/modalidade,
  patrocinador, identificadores regulatórios, composição, match, vesting e
  status, mantendo os campos legados para reconstrução compatível.
- Valores monetários e percentuais continuam em Decimal.
- A validação diferencia OPEN/PGBL-VGBL/OTHER/UNKNOWN de CLOSED/CD-CV-BD,
  rejeita OPEN + CD e CLOSED + PGBL, valida CNPJ, saldo não negativo,
  composição consistente e vesting entre zero e cem.
- Administradora e patrocinador/instituidor são entidades distintas. Match e
  vesting são declarativos e somente se aplicam à origem empresarial.

## Database Migration

0011_pension_v2 adiciona campos sem remover os antigos e preenche product_type
a partir de pension_type em registros existentes.

## Frontend Changes and Conditional UI Rules

- Removido o identificador visível.
- Nome do plano, administrador, origem e estrutura são os dados iniciais.
- Produto aparece somente para plano aberto; modalidade somente para fechado.
- Patrocinador aparece para origem empresarial ou associação; contrapartida e
  vesting aparecem somente para origem empresarial.
- A composição participante/patrocinador é opcional.
- A data do saldo substitui a data genérica da operação durante o cadastro.
- Campos ocultos são desabilitados, portanto valores incompatíveis não são
  enviados após trocar entre aberta, fechada ou não informada.

## Existing Data Migration

Registros v1 são preservados como planos particulares, abertos e ativos. O
campo PGBL/VGBL existente é copiado para product_type; dados ambíguos não são
inventados.

## Tests Added and Executed

- PENSION-001/002/003: PGBL, VGBL e regime UNDEFINED.
- PENSION-004/005/006: origem empresarial e match, inclusive acima de 100%.
- PENSION-008: composição explícita consistente.
- PENSION-011/012/013: CD, CV e BD.
- PENSION-014/015/016: CNPJ e limites de vesting.
- PENSION-018/019: combinações OPEN/CLOSED incompatíveis.
- Regressão completa executada em domínio, persistência, renda fixa, carteira,
  infraestrutura e módulos de frontend: 268 testes aprovados.

## Future Portability Readiness

O plano preserva identidade interna e status ACTIVE, INACTIVE, PORTED ou
CLOSED. Uma futura entidade PENSION_PORTABILITY poderá apontar para planos de
origem e destino sem renomear ou sobrescrever o plano original.

## SELF_QA Findings and Fixes

- O snapshot e a persistência já preservavam todos os campos v2; nenhum dado
  existente foi apagado ou deduplicado.
- Corrigida a aceitação silenciosa de produto aberto em plano fechado.
- Corrigido o fluxo de associação para reutilizar patrocinador como entidade
  instituidora, sem mostrar controles de match/vesting.
- Corrigido o bloqueio de controles ocultos para impedir envio de estado
  incompatível.

## Known Limitations and Future Readiness

- A edição completa de plano, portabilidade e histórico de saldos continuam
  fora desta entrega; o status e a identidade interna permitem implementá-los
  sem sobrescrever o plano original.
- Match e vesting são persistidos como dados declarativos; não há motor de
  cálculo automático nesta entrega.

## Data Preservation

A migration 0011 adiciona campos e apenas copia PGBL/VGBL legado para
product_type. Não remove planos, saldos ou identificadores existentes.

## Final Status

DONE
