# PR5.2 — Plano de proteção de develop

**PROPOSTA, NÃO APLICADA.** Estado de ativação: bloqueado por ausência de aprovador independente. Repositório público pessoal tiagocaldironi/income-analytics; único admin/write verificado: tiagocaldironi. Nenhum convite, revisão ou mudança de permissão foi realizado.

## Viabilidade verificada

GET repo confirma admin=true no token e public=true. GET rulesets/rules/branches/develop é permitido e retorna []; GET protection retorna Branch not protected. O plano de cobrança não foi exposto (plan=null), mas a documentação oficial confirma branch protection e CODEOWNERS para repositórios públicos no Free. Não é necessário presumir recurso pago.

CI / Engineering foi efetivamente publicado por GitHub Actions app 15368 no head a2f6d64 e está success. Propor exatamente esse contexto, sem usar a conclusão geral do workflow como substituto. A aceitação do payload e a efetividade das regras só poderão ser comprovadas após autorização para escrita; não foi feita chamada PUT/PATCH de proteção como teste.

## Política concreta para aceite

Payload revisável em ci_branch_protection_proposal.json, marcado PROPOSAL_ONLY_DO_NOT_APPLY. É um envelope documental; apenas proposed_branch_protection_payload descreve uma futura chamada de proteção de develop.

| Controle | Proposta | Estado hoje |
| --- | --- | --- |
| PR obrigatório | required_pull_request_reviews, pelo menos uma aprovação | Inativo |
| Independência | Aprovador com write distinto do autor e do último push revisável | Sem segundo elegível; BLOQUEADO |
| Reviews obsoletas | dismiss_stale_reviews=true; require_last_push_approval=true | Inativo |
| CODEOWNERS | require_code_owner_reviews=true, depois de dois owners elegíveis e bootstrap autorizado | Apenas arquivo local proposto |
| Conversas | required_conversation_resolution=true | Inativo |
| Check obrigatório | CI / Engineering de app 15368; strict=true | Check publicado, exigência inativa |
| Force-push/exclusão | allow_force_pushes=false; allow_deletions=false | Inativo |
| Administradores | enforce_admins=true; sem bypass permanente ou exceção informal | Inativo |
| Atualização com base | Exigir branch atualizada; disparar e concluir CI para a nova árvore | Proposto |
| Merge queue | Não ativar; workflow não escuta merge_group | Desabilitada nesta proposta |

Não exigir globalmente Financial certification, Full Python diagnostic ou sucesso dos jobs Ruff/mypy enquanto bloqueados. Isso não dispensa certificação para mudanças financeiras certificadas ou release. Não remover esses jobs nem seus relatórios. Não usar um status de outro app ou de outra árvore como equivalente.

Repositório pessoal não oferece o mesmo modelo de equipes/bypass granular de uma organização. restrictions=null não concede bypass: a proposta aplica reviews/checks também ao administrador. A autoridade do proprietário para editar configurações persiste; nenhuma política pode ser apresentada como proteção contra o próprio proprietário com administração irrestrita. A governança exige registro explícito de exceções e revisão.

## Etapa 1 — Aceite do mantenedor

1. Rever ci_governance_review.md, baseline 130 Ruff/673 mypy, evidências preservadas e os quatro estados independentes. Registrar aceite da dívida e da política; inventário não equivale a aceite.
2. Nomear um segundo usuário real; autorizar separadamente acesso write e verificar elegibilidade. Não usar conta fictícia, bot ou conta secundária do mesmo aprovador como independência.
3. Incluir ambos os owners verificados em cada padrão, na mesma linha. Caso outro colaborador também abra PR, deve haver owner distinto disponível para revisar. Confirmar disponibilidade operacional antes de exigir reviews.
4. Aprovar o bootstrap: CODEOWNERS precisa chegar à base por mudança revisada e autorizada. A primeira alteração não pode se autoproteger apenas por existir na head. Enquanto não houver regra, manter controle operacional explícito do mantenedor sem alegar bloqueio técnico.
5. Revisar os novos arquivos locais do PR5.2. Autorizar commits/push em etapa separada e exigir novo run para o SHA publicado; o run E não valida os novos testes/CODEOWNERS.
6. Apresentar impacto: cada PR exige revisor distinto, novo push relevante invalida aprovação e exige CI da árvore atualizada. Mudanças em CI/baseline exigem owner review; a indisponibilidade de owners interrompe integração deliberadamente.
7. Só após isso autorizar a aplicação das regras. Não alterar o draft nem integrar #48 automaticamente.

O mantenedor tiagocaldironi pode aprovar este plano administrativo, mas não pode satisfazer a review independente do PR #48 de sua autoria. Até a inclusão de outro colaborador elegível, manter GOVERNANCE_BLOCKED para integração sob essa política.

## Etapa 2 — Ativação futura autorizada

1. Reconsultar permissões, owners, base/head, checks e proteções para detectar mudanças desde esta proposta.
2. Exportar configuração atual e registrar aprovador, escopo, horário e payload aprovado antes de qualquer alteração. Se já houver regra nova, reconciliar proposta por nova revisão; não sobrescrever.
3. Aplicar exclusivamente regras autorizadas de develop. Confirmar via GET cada campo e contexto/app; guardar evidências de resposta sanitizadas.
4. Em branch/PR descartável, com autorização de publicação, verificar negativa de merge sem review, sem Engineering e com conversas abertas; verificar invalidação após novo push e revisão obrigatória de CI/CODEOWNERS/baseline. Não tentar force-push/excluir develop para testar. Usar simulação/regra de teste e sinais de bloqueio sem alteração destrutiva.
5. Verificar um caminho legítimo: PR sem mudança financeira, Engineering success, owner independente aprovado e conversas resolvidas. Verificar elegibilidade para merge sem executar merge se não autorizado.
6. Confirmar que usuários e administrador sem requisitos satisfeitos não têm bypass operacional inadvertido. Registrar limitações de interface/API e decisões, não apenas exemplos positivos.
7. Registrar estado realmente ativo. Reconciliar a política se houver falha; nunca aprovar sucesso artificial ou ajustar baseline para passar.

## Recuperação controlada

Não há bypass permanente proposto. Se regras futuras bloquearem operações legítimas, abrir registro com PR/SHA, motivo, controle afetado e evidência; procurar o owner independente antes de alterar regras. O admin pode tecnicamente mudar configurações, mas qualquer exceção temporária exige autorização explícita, escopo mínimo, prazo e plano de restauração. Preservar a configuração anterior; restaurar e verificar por GET, repetindo os testes de efetividade. Não remover CERT_48 ou editar finanças como recuperação de CI. Não automatizar esse procedimento nesta fase.

## Referências

[Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) e [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners), consultados em 28/10/2026. Condições reais e comandos de consulta estão em ci_governance_review.md. Nada neste plano autoriza merge, produção, convite de colaborador, commit/push ou ativação de regra.
