# Promoção técnica por escopo — PR69 incluindo PR62

O job final `CI / Release scoped` ocorre **após** staging e consolida cinco estados:
ENGINEERING, SECURITY, FINANCIAL_SCOPED, HISTORICAL_DEBT e RELEASE. O antigo
`gate-summary.json` permanece como relatório anterior ao staging e diagnóstico
abrangente; seu bloqueio global não representa a decisão restrita posterior.
Nenhum job/teste bruto é removido ou relabelado. O workflow global pode continuar
reprovado por diagnósticos históricos, mesmo com RELEASE=GO restrito.

## Requisitos de GO

- Engineering e Security hospedados aprovados, mesma execução/checkout/head,
  fingerprint de conteúdo e política, build reproduzível e pacote idêntico.
- Revalidação do relatório financeiro restrito pelo avaliador existente, com
  todos os testes, funções e dependências exigidos, sem skips/falhas/erros,
  integridade dos 41 arquivos e ausência de chamadas CERT_48.
- Mesmas causas/IDs históricos comprovados e vinculados a #57/#58; nenhuma mudança
  negativa em caso preexistente, nenhum teste antigo ausente ou caso novo reprovado.
  Os 486 diagnósticos continuam sujeitos à política já aceita e ao seu prazo;
  nenhuma adição pode ser compensada por remoção.
- Staging/health/backup/restore/rollback/negativos/incompatibilidade de schema
  aprovados pelo avaliador de entrega existente. Evidência operacional obrigatória.
- Aprovação do proprietário verificada na API GitHub, não inferida de status PASS.

## Aprovação e SHA sem autorreferência

A [aprovação expressa na Issue76](https://github.com/tiagocaldironi/income-analytics/issues/76#issuecomment-6616676753)
refere-se a `42325f4d8e37ff1491f1bb26eb8e10fad891a979`, permite revalidação e não
autoriza merge/deploy. O registro `ci/scoped-promotion-approval.json` fixa autor,
ID/URL/hash do texto e digest da superfície certificada. A API autenticada GET
confere o registro; exclusão, alteração ou autor diferente bloqueiam. Não se
atribui revisão independente a pessoa inexistente.

O gate compara diretamente árvores Git do SHA aprovado e candidato. A superfície
protegida inclui código produtivo completo (também frontend), migrações,
dependências runtime, testes financeiros/API/domínio/aceitação/infraestrutura,
fixtures, avaliadores de certificação, isolamento, controles de entrega/rollback,
políticas e referências históricas/tipagem. A lista exata está em `PROTECTED` no
avaliador. Novas entradas, remoções, modo e identidade de blob participam do digest.
Mudança nessa superfície **não herda o aceite** e exige decisão própria; não é
permitida normalização de hashes ou CRLF para aprovar. Alterações exclusivamente
de governança/segurança fora dela exigem CI completa e certificação do escopo no
novo SHA. Assim o aceite original não vira autorização irrestrita para SHAs futuros.

O relatório vincula SHA aprovado, SHA de checkout/merge, head do PR, run, pacote,
fingerprints e revalidação atual. Uma aprovação não contém seu próprio SHA futuro:
ela referencia uma superfície já aprovada, cuja equivalência o gate verifica.
Essa regra implementa a instrução atual de reaproveitar o aceite sem reabrir a
certificação nem corrigir dívida histórica.

## NO-GO e limites

Ausência/duplicação de relatório, coleta inválida, SHA/run/head divergentes,
workspace alterado, teste/dependência não exercitado, acesso às funções CERT_48,
mudança de bytes imutáveis, nova falha/skip/diagnóstico, aprovação revogada,
staging/rollback incompleto ou job cancelado/skipped produzem NO_GO. Os casos
positivos e negativos residem em `tests/security/test_scoped_promotion.py`.
Um problema independente novo deve ser registrado em issue específica; não
ampliar esta tarefa para recuperar históricos.

GO significa apenas **elegibilidade técnica do escopo para a decisão de promoção**.
`merge_authorized=false`, `deployment_authorized=false` e
`production_status=PRODUCTION_NOT_AUTHORIZED` permanecem obrigatórios.
O alvo produtivo não é implementado/acionado; proteções de branch e controles de
PR não são alterados. O rollback comprovado é de staging descartável. Nenhuma
afirmação de restauração produtiva é inferida dele. As exigências para executar
uma promoção/deploy real permanecem separadas; esta política não as dispensa.

Artefato da decisão: `scoped-promotion-<checkout_sha>/promotion-report.json`, com
resultados independentes, motivos, aceite, SHA certificado e backlog. Um resumo
GO não deve ser apresentado como certificação global da Magic Formula/CERT_48.
