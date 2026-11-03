# Issue77 — Security Baseline do PR69

## Causa comprovada

Run reprovado: `41720296662`, head `42325f4d8e37ff1491f1bb26eb8e10fad891a979`,
merge testado `035f43d6a9c80cc782b5f56cd6c46b6d54924d24`.
Artifact `13272900909`: `result.json`, `security-junit.xml`, `sbom.cdx.json`.
Comparação aprovada: run `41715005775`, merge `5d715b74d1e4e0344dce3ade7b27001681251fbf`.

| Controle | Anterior | Reprovado |
|---|---|---|
| Testes de segurança | 144 PASS, zero falha/erro/skip | Igual |
| SAST e achados high/critical | PASS, sem pendência | Igual |
| Fonte, scanner interno de secrets e artifact | PASS | Igual |
| Dependências OSV | PASS, zero alerta | Igual |
| SBOM | CycloneDX, 87 componentes | Mesmos 87 nomes/versões |
| Gitleaks 8.30.1 | PASS, zero não triado | FAIL, duas ocorrências não triadas |

Regra: `generic-api-key`. Local: linha 12 de
`docs/engineering/scoped-financial-certification/immutable_reference_inventory.json`.
O conteúdo é o SHA-256 público da migração `alembic/versions/0008_paid_income_brapi.py`.
O nome BRAPI faz a heurística interpretar o checksum como chave. O valor foi
recalculado dos bytes atuais e do blob de develop `b642709`; ambos coincidem com
o inventário. O checksum não é um token, não foi consultado em provedor e não foi
alterado. A migração e os 41 arquivos financeiros permanecem intactos.

IDs exatos reprovados:

- Arquivo atual: `197358740fcb22d9780a8e416b7586a1cbb820784e86a44d540dcfd7bec243b4`,
  vinculado ao digest integral do inventário
  `d6f99bca05a7d3f6ad4d3e67ce46db5c6876da71dfc7c15d15c5b1b0f7c83853`.
- Histórico: `6d77fca7bafcb08e50acb7ae323d0842e1eb6734905cfa269e7ceb0ccf731519`,
  vinculado ao commit `42325f4d8e37ff1491f1bb26eb8e10fad891a979`, arquivo, linha e regra.

Classificação: **falso positivo novo na documentação; divergência da triagem
versionada**, não vulnerabilidade real, regressão de autorização ou dependência
vulnerável. A nova cópia do inventário introduziu as duas ocorrências na varredura.
`failures=[]` lista exceções operacionais do runner; não representa todos os
controles reprovados. O `result.json` já identifica `gitleaks.status=FAIL` e as duas
ocorrências. Não é necessário mudar o runner para resolver a causa.

## Correção mínima e validação

Acrescentadas somente duas decisões FALSE_POSITIVE por identidade exata na
triagem existente, após a verificação dos bytes. Nenhuma exclusão de arquivo,
regex genérica, regra ignorada, baseline de mypy ou controle de segurança alterado.
Conteúdo diferente, commit diferente, linha/regra/local diferente continuam sem
aprovação. A credencial sintética de controle do Gitleaks continua obrigatoriamente
detectada e rejeitada. Testes adicionais comprovam a proveniência do checksum e
que mutações da identidade não herdam a decisão.

O escopo financeiro aprovado pelo proprietário permanece intacto; esta correção
não reabre CERT_48, não altera cálculos, fixtures ou política financeira. Os 394
testes do escopo continuam executados pela CI existente. Resultados hospedados do
novo commit, links de evidência e encerramento são registrados na Issue77 e PR69,
sem commit circular do próprio SHA. Não houve merge ou deploy.

## Renovação da identidade do arquivo de testes

O primeiro replay `41730400112` comprovou Gitleaks PASS, 150 testes de segurança
PASS, SAST/dependências PASS e escopo financeiro inalterado (394 PASS). O scanner
interno rejeitou o novo hash integral de `test_baseline_hardening.py`, que já
continha uma URL de teste deliberadamente inválida em domínio reservado. A adição
dos seis testes mudou o digest; a triagem existente corretamente não se estendeu
a esses bytes. O prefixo original do arquivo foi comparado byte a byte com
`42325f4` e permaneceu idêntico. Somente casos novos foram acrescentados.

Renovada uma decisão por digest integral
`512e68f41b243777389c252b9661e23f213089b515e89be27c143a36d73868f1`,
cobrindo as duas referências aos mesmos bytes (atual e blob histórico). Não é
vulnerabilidade independente nem autorização por prefixo/tipo de credencial.
O comportamento de rejeitar qualquer conteúdo não revisado foi preservado.
