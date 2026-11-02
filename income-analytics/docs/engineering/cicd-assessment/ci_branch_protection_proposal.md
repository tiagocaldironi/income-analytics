# Proposta de proteção de develop — PR5.1E

Proposta somente: nenhuma proteção foi ativada. Em 28/10/2026, GitHub informa develop em ca627ac72f110d0f4d62faaa9c51a08eaed54965, protected=false.

- Exigir Pull Request e pelo menos uma aprovação independente; invalidar aprovações após alterações relevantes e exigir resolução das conversas.
- Candidato principal: `CI / Engineering`, associado ao GitHub Actions. Ativar somente após validação hospedada e aceite da política. Runtime, Python engineering, Frontend e Quality non-regression são componentes agregados; torná-los obrigatórios separadamente é opcional.
- Exigir revisão específica de `.github/workflows/`, `income-analytics/ci/` e baseline de qualidade. Propor CODEOWNERS nesses caminhos, com responsáveis nomeados pelo mantenedor; não criar proprietários fictícios nem ativar regras nesta etapa.
- Proibir force-push e exclusão de develop. Impedir bypass não autorizado, incluindo administradores; qualquer exceção operacional deve ter autorização e trilha de auditoria.
- Preferir branch atualizada antes de integrar. Merge queue depende de suporte e inclusão futura de `merge_group` no workflow; o workflow atual não cobre esse evento, portanto não ativar fila agora.
- Manter Full Python diagnostic, Ruff e mypy visíveis, sem exigir sucesso global enquanto houver dívida explicitamente aceita. Quality non-regression deve reprovar novas identidades ou multiplicidades, mesmo que outras sejam removidas.
- Financial certification permanece obrigatória para certificação e release, mas não deve ser check global obrigatório para todo PR enquanto CERT_48 e referências históricas estiverem bloqueadas. Engineering aprovado não autoriza mudanças financeiras nem promoção de produção.

Próxima etapa: revisar evidências hospedadas, obter aceite dos responsáveis e só então propor a ativação em mudança separada. Sem CD nesta entrega.
