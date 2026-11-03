# Solicitação de aprovação financeira independente

Estado: **PENDING — não assinada; nenhuma autoridade presumida**.

Destino público de revisão: PR #69 e Issue #57. A identidade do revisor financeiro
independente foi solicitada ao proprietário na conversa, que informou ainda não
ter revisor definido. O implementador não pode
assinar a própria conclusão, e o aceite anterior de tipagem não serve como aceite
financeiro. Nenhuma mensagem externa a terceiros foi enviada.

## Decisão solicitada

Revisar `scope_and_applicability.md`, a política de escopo, os 24 IDs históricos,
o inventário imutável, o relatório `scoped-financial.json` do job Financial e os
resultados completos/hospedados no mesmo SHA. Aprovar ou rejeitar:

1. A independência entre cálculos de Tesouro/carteira/aportes e as funções da
   Magic Formula cobertas pelo CERT_48, reconhecendo os imports compartilhados.
2. A não aplicabilidade restrita do CERT_48 e da fixture de identidade histórica
   a este release, sem certificar nem substituir o certificado original.
3. A retirada dos 22 casos de referências históricas do gate decisório deste
   escopo, mantendo execução e backlog #58, e mantendo #57 aberto.
4. A suficiência dos casos financeiros e dependências exercitadas, dos exemplos
   independentes e das limitações registradas.

O registro da decisão deverá identificar nome e papel da autoridade, sua
independência da implementação, SHA candidato e merge testado, hashes do parecer,
política e relatório, critérios aceitos/rejeitados, riscos e prazo/condições de
revogação. Uma assinatura ou declaração escrita deverá possuir origem verificável;
inserir um nome num JSON não cria aprovação independente.

## Condições de revogação

Mudança nos caminhos financeiros ou nas dependências, nova falha financeira,
alteração dos arquivos imutáveis, uso de ranking/QA congelado no escopo ou expansão
para RendA+/Educa+/contratos legados exige nova revisão. Cotação ausente ou inválida
continua indisponível/bloqueada. Vulnerabilidade relevante e regressão nova
continuam bloqueantes, independentemente de dívida aceita.

## Decisão atual

**NO-GO financeiro, por aprovação independente pendente.** A instrumentação e o
pacote permitem uma decisão concreta; não removem unilateralmente o bloqueio.
Nenhum merge, deploy, migração produtiva ou alteração dos 41 arquivos foi feito.
Uma eventual aprovação financeira não equivale a autorização de deploy nem a
validação de restauração produtiva.
