# Income Starter V3 — implementação e pendências

**Dependência:** PR #13 (`codex/income-starter-v2-research-governance`).
**Estado dos modelos de alocação:** Conservadora, Moderada e Arrojada continuam `DRAFT`, sem percentuais Income e sem adoção.
**Identidade:** a aplicação local usa carteira selecionada e ainda não oferece autenticação de usuário. O progresso é isolado por carteira local; não é atribuído a um usuário autenticado.

## Primeiros Passos

O catálogo diferencia `GUIDED_JOURNEY` de `ALLOCATION_MODEL`. Primeiros Passos é uma jornada para entender a reserva, definir despesas essenciais e meses de cobertura, declarar quanto está reservado e acompanhar meta, restante, cobertura e progresso. A referência CVM de 6–12 meses é apresentada como orientação educacional ajustável, não regra universal.

O valor reservado é autodeclarado. Não se infere reserva a partir de renda fixa, patrimônio, caixa ou liquidez. Nenhuma dessas informações gera operação, posição, aporte, valuation, capital aplicado ou TWR. Um objetivo zero é tratado sem divisão por zero. Alterações fazem upsert de um registro por carteira.

Conclusão da jornada não concede perfil de risco, não executa suitability e não escolhe uma estratégia automaticamente.

## Exposição econômica

A classificação complementar suporta ações Brasil/internacionais, renda fixa, imobiliário listado/direto, commodities, cripto, caixa/equivalentes e não classificado. Um ativo pode ter várias parcelas, mas percentuais conhecidos devem fechar 100%, incluindo parcela explicitamente desconhecida. Classificação confirmada exige fonte HTTPS e data de referência. Nenhum provedor foi inventado ou integrado; sem evidência, estado é `UNKNOWN`.

Esta taxonomia é separada da classe operacional Income e não participa dos cálculos financeiros ou da alocação.

## Propostas editoriais de alocação

- [Conservadora](INCOME_STARTER_CONSERVADORA_PROPOSAL.md)
- [Moderada](INCOME_STARTER_MODERADA_PROPOSAL.md)
- [Arrojada](INCOME_STARTER_ARROJADA_PROPOSAL.md)

Cada proposta registra percentuais originais publicados por terceiros e pendências de correspondência econômica. Não foram convertidos em percentuais Income, inseridos em `allocations`, enviados para revisão ou publicação. A divergência entre fontes e as categorias atualmente não suportadas impedem uma proposta de alocação Income defensável nesta entrega.

## Pendências de homologação

1. Uma pessoa responsável deve definir orçamento, regras de alteração e privacidade quando houver futura identidade de usuário.
2. Homologar conteúdo educacional e comportamento da jornada.
3. Integrar fontes confiáveis para exposições econômicas e determinar atualização/revisão de classificações.
4. Definir taxonomia e pesos Income a partir de fontes pertinentes ao Brasil; resolver caixa, ETF, previdência, geografia, concentração e rebalanceamento.
5. Obter revisão financeira e regulatória independentes, identificadas e datadas, antes de mover qualquer estratégia para `IN_REVIEW`/`PUBLISHED`.
6. Planejar sincronização dos dados por usuário quando login/compartilhamento multiusuário for implementado.

## Limites da certificação

Os testes verificam cálculo e isolamento da jornada, separação da persistência financeira, persistência da taxonomia e as proteções de adoção existentes. A interface usa os contratos reais; validação em navegador real depende do ambiente desktop/mobile disponível durante revisão. Nenhum manifesto de hash do motor financeiro foi alterado.
