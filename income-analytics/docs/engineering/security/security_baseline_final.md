# Baseline de segurança de engenharia

O recibo final do [PR53](https://github.com/tiagocaldironi/income-analytics/pull/53) registra o SHA integrado da develop, os runs pós-merge e o estado definitivo. Este documento e [security_hosted_validation.json](security_hosted_validation.json) versionam a implementação e a evidência hospedada anterior à integração. `SECURITY_BASELINE_IMPLEMENTED` só se aplica após merge protegido e aprovação dos gates pós-merge; uma validação de PR isolada não encerra a missão.

## Baseline e escopo

A develop consultada antes das alterações era `0cf5921c88f358938fd6c5df6aa3d1a7fb3a1195`; PR52 estava MERGED. CI40869935442 tinha Engineering/build aprovados e dívida diagnóstica conhecida; CD40871039283 e repetição40871613070 estavam aprovados. Ruleset26078982 ativo, strict, sem bypass, com `CI / Engineering` obrigatório pelo aplicativo15368. [security_before.json](security_before.json) conserva a baseline de locks e workflows; não foram presumidos SHAs históricos.

Trabalho em branch/worktree isolados. Não foram abertos bancos reais, configurações privadas, credenciais produtivas ou arquivos de carteira. Alterações locais originais foram preservadas. O inventário cobre 408 ativos lógicos/arquivos e 106 pares handler/método estáticos; a matriz HTTP usa as rotas efetivas, incluindo aliases e includes. Um ativo inventariado não significa que o host/provedor correspondente foi certificado.

- [Inventário estruturado](security_inventory.json): backend, frontend, persistência, integrações, configuração, ferramentas e fronteiras de confiança.
- [Threat model STRIDE](threat_model.md): ameaças, controles existentes, lacunas e testes.
- [Achados curados](security_findings.json): condição de exploração, impacto, severidade, confiança, correção e estado residual.
- [Triagem de scanners](security_scanner_triage.json): cada identidade de código/segredo, justificativa e reavaliação em caso de mudança.
- [Matriz de 20 controles negativos](security_controls_matrix.csv), [privacidade](privacy_data_inventory.md) e [procedimentos operacionais](security_remediation_plan.md).

## Controles implementados

| Área | Controle efetivo | Evidência |
|---|---|---|
| Autenticação | Firebase Admin verifica ID tokens e cookies, incluindo revogação nas rotas financeiras. Sem fallback local após falha. Aliases prod/production em INCOME_ENV e ENVIRONMENT exigem Firebase/HTTPS; emulator proibido em conflito produtivo | infrastructure/auth_config.py; firebase_identity.py; testes SDK/HTTP |
| Modo local | Somente peer loopback e Host permitido; escrita de Origin externo recusada. Forwarded headers não autorizam um peer remoto | api/saas_security.py; baseline_hardening |
| Autorização | Fronteira default-deny, ownership, contexto por carteira/usuário, funções globais restritas e logs globais não expostos | matriz de rotas, quatro carteiras/dois usuários, IDs de eventos alheios, imports e simulações |
| API/upload | Limites de corpo/stream, CSRF/origin/cookies, rate limits existentes, validação de ZIP/XML e dados tipados preservados | testes de payload, archive bombs, entidades, CSRF, replay e SQL payload parametrizado |
| SQLite | INCOME_DATA_ROOT explícito e absoluto em produção; destino resolvido dentro da raiz antes da conexão. Sem schema novo | infrastructure/database.py; testes de traversal e configuração |
| Logs | Credenciais em campos identificados, bearer, userinfo de URL e e-mail redigidos antes dos handlers, inclusive texto de exceção; argumentos e exc_info brutos não são mantidos no registro | infrastructure/security_logging.py; teste de mensagem/traceback sintético |
| SAST | Bandit1.9.4 em src/ci e regras próprias JS para APIs críticas/fontes DOM diretas. Alertas novos ou sem triagem falham | ci/security.py; 293 ocorrências triadas, sem confundir alertas com vulnerabilidades confirmadas |
| Segredos | Gitleaks8.30.1 com ZIP e executável fixados por SHA-256; regras upstream e autoteste negativo obrigatório. Sem gitleaks:allow nem ignore do repositório. Scanner complementar cobre fonte, histórico e conteúdo textual das wheels do artefato | Gitleaks REJECTED no fixture sintético; triagem por identidade/bytes exatos; relatórios sem Match/Secret/autor/e-mail |
| Dependências/SBOM | Locks Python com hashes, OSV, dependências JS declaradas, versão embutida do ECharts e bytes CDN conferidos; CycloneDX1.6 ligado ao commit e digest do pacote | 87 consultas/componentes; SBOM e relatórios do mesmo run |
| CI/entrega | Security é dependência real do agregado obrigatório Engineering; falha, skip ou ausência não vira PASS. Candidato B exige job Security real e agregado Security PASS | gate_policy.py, governance.py, delivery.py/pipeline.py, testes negativos e CD hospedado |
| Registro manual | HIGH/CRITICAL confirmado, não triado, aceito ou não verificado reprova mesmo com scanner limpo. Correção/mitigação/falso positivo exige evidência e regressão | enforce_confirmed_findings; registro curado integra a identidade da política |

O A histórico exato do PR6 permanece apenas como fixture de rollback sintético, verificado pelos pins originais de run/SHA/digest. Não pode se tornar um candidato novo sem Security. Instalação, backup consistente, restauração semântica, falha de health/startup, seleção do A, bloqueio de schema incompatível, imutabilidade e limpeza continuam sendo exercitados pelo PR7. Nenhum caminho produtivo foi habilitado.

## Achados e dependências

O registro curado tem 10 achados: três HIGH corrigidos, três MEDIUM corrigidos, um MEDIUM mitigado, um MEDIUM com risco aceito explícito, um MEDIUM não verificado e um INFO falso positivo. Não há CRITICAL confirmado ou HIGH confirmado explorável sem correção/mitigação na implementação. Isso não afirma ausência universal de vulnerabilidades.

| Componente anterior → corrigido | Intervalo/advisory | Exposição avaliada |
|---|---|---|
| setuptools80.9.0 →84.1.0 | [GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c): versões anteriores a83.0.0; exclusão de sdist/normalização Unicode | condição de empacotamento, especialmente macOS; não demonstrada como exploração HTTP deste Windows |
| setuptools80.9.0 →84.1.0 | [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w): >=38.2.2 e <84.1.0; namespace_packages/instalação legada Windows | caminho de instalação malicioso; correção aplicada sem alterar bibliotecas de cálculo |
| wheel0.45.1 →0.46.2 | [GHSA-8rrh-rw8j-w5fx / CVE-2026-24049](https://github.com/advisories/GHSA-8rrh-rw8j-w5fx): >=0.40.0 e <0.46.2 | traversal/chmod no unpack; severidade HIGH preservada, ainda que exposição HTTP ordinária não tenha sido demonstrada |

Aliases PYSEC não são contados como novas vulnerabilidades. Os hashes das wheels corrigidas vieram de PyPI. packaging26.3 foi acrescentado ao runtime porque wheel0.46.2 exige packaging>=24, usando o mesmo pin/hash já presente no lock de desenvolvimento. As demais versões dos locks existentes foram preservadas. A primeira execução [40897473051](https://github.com/tiagocaldironi/income-analytics/actions/runs/40897473051) reprovou build/runtime por essa dependência ausente; Security SKIPPED ali não foi aceito como validação.

ci/javascript-components.json registra oito componentes transitivos declarados do Firebase app/auth/ECharts e integridades publicadas de tarballs npm. Para o helper tslib embutido no Firebase, a declaração ^2.1.0 não permite comprovar versão exata: o SBOM omite versão inventada e OSV consulta o pacote inteiro. Os dois módulos gstatic têm hashes observados e conferidos na CI. O navegador ainda não usa SRI para esses imports; o controle de CI não certifica sozinho seu runtime. Go transitivo do Gitleaks e sistemas operacionais não receberam certificação independente.

O identificador Firebase Web sinalizado pelo Gitleaks foi classificado por ocorrência exata conforme [documentação oficial](https://firebase.google.com/docs/projects/api-keys), sem republicar seu valor. Não é um token de sessão nem chave Admin. Restrições reais de APIs/quota do Google Cloud permanecem NOT_VERIFIED; não houve sondagem de validade ou rotação.

## Evidência hospedada verificada

Run [40936317910](https://github.com/tiagocaldironi/income-analytics/actions/runs/40936317910); head do PR `ab47675a0d2303a669dad34273e0d20cf7b03d61`; checkout sintético `3392ae95bd7026cf9f91fc2db8b1036c8b986dda`. Esses SHAs têm papéis distintos. Todos os envelopes de artifacts foram comparados com o digest publicado pela API; identidades de fonte/política foram recalculadas a partir dos blobs Git do checkout efetivo.

| Gate | Resultado |
|---|---|
| CI / Engineering | PASS; 1231 testes Python, zero falhas/erros/skips no escopo de engenharia |
| CI / Security baseline | PASS; 137 testes de segurança, zero falhas/erros/skips; SAST, Gitleaks, fonte/artefato, OSV e registro manual aprovados |
| Frontend | PASS; 31 suítes offline |
| CI / Reproducible build | PASS; dois builds independentes, instalação limpa/offline, smoke e integridade |
| CD / Staging validation | PASS; promoção pré-merge bloqueada, ambiente descartável/sintético |
| Qualidade | PASS na não regressão: 803 diagnósticos históricos, 802 atuais, zero novos |
| Financeiro | BLOCKED; 73 PASS, 15 FAIL, 9 ERROR, zero skips; identidades/estados originais preservados |

O teste test_shares_unit_020_frozen_engine continuou executado e FAILED. CERT_48, integridade congelada e 22 referências históricas seguem bloqueando certificação financeira e produção. Os casos existentes do diagnóstico Python completo mantiveram os estados anteriores; os novos casos passaram. A conclusão global do workflow continua failure por dívida/diagnósticos conhecidos; não se declara CI integralmente limpa.

Pacote: [artifact 12925571425](https://github.com/tiagocaldironi/income-analytics/actions/runs/40936317910/artifacts/12925571425). SHA-256 `6ac872f28d5718680c0b220dd3fabf51363042d8b971537e6a024fb39402ea38`. Manifest SHA-256 `b72a94c7be0b03180d648d4ec1d8b4f11ad2d91e354ac5337f58c0b950c357f8`. [SBOM/relatórios de segurança 12925786574](https://github.com/tiagocaldironi/income-analytics/actions/runs/40936317910/artifacts/12925786574); SBOM SHA-256 `3cb2df3a947317e1903acdcfd55766e658686b27555520a7358c81ab9909b09c`. IDs, digests de transporte, políticas e inventário de arquivos estão no snapshot JSON. Essa é uma evidência pré-merge; o recibo final do PR53 registra o pacote do SHA integrado e seus runs pós-merge.

A baseline histórica de qualidade permanece byte-idêntica, SHA-256 4bff522ba5cf8f203dbb7851a88f3745df4a6f75f4478c88fdd933740bed152a. quality_compatibility.json atesta apenas o novo lock/configuração e a realocação das mesmas mensagens após duas linhas de guarda em main.py. Nenhum alerta foi dispensado; tipar o callback SQLite corrigiu uma dívida real. Não houve exceção global de lint/mypy, redução de testes ou edição de fixtures/manifests/hashes financeiros.

## Reprodução e limites

Usar checkout limpo com blobs LF, Windows x64, Python3.14.7 e Node24.19.0. Instalar ci/requirements-windows-py314.lock e ci/security-tools-windows-py314.lock com pip --isolated --require-hashes --only-binary=:all:; executar pip check. Rodar ci/governance.py engineering, quality e node; ci/build_pipeline.py; depois ci/security.py --history --artifact <ZIP do mesmo commit> --build-report <result.json correspondente>. O build recusa checkout sujo e não executa resolver durante instalação.

Testes usam SQLite/arquivos/portas descartáveis e ambiente sanitizado com rede externa negada. O scanner online envia somente nomes/versões públicos a OSV e busca ferramentas/SDKs públicos em origens verificadas. Relatórios brutos ficam privados/temporários; artifacts contêm evidências sanitizadas, nunca bancos, backups reais, tokens ou dados de carteira. Histórico acessível é examinado; refs inacessíveis, dangling objects e LFS não são presumidos cobertos. Falha/indisponibilidade/resultado parcial de scanner é FAIL ou NOT_VERIFIED, nunca aprovação silenciosa.

O escopo automatizado SAST de Python é src/ci, acrescido das regras JS próprias e da inspeção das configurações versionadas. Não é uma prova formal de todo fluxo DOM nem substitui análise independente de ferramentas operacionais. As suítes Firebase Emulator/cloud continuam separadas; doubles comprovam decisões locais e delegação ao Admin SDK, sem certificar o serviço real.

## Privacidade, riscos residuais e produção

Persistem riscos médios explícitos de parsing offline/fornecedores, redirects/DNS externos, CSP/estilos inline e confiança CDN, além de verificações do host, Firebase real, conta mantenedora e políticas de dados. Redaction cobre os padrões identificados, não todo possível campo extra ou valor financeiro em logs. NTFS, criptografia de disco, proxies/Tailscale, credenciais e backups reais estão NOT_VERIFIED. Retenção/base legal/portabilidade integral/termos/incidentes exigem decisões do controlador; POLICY_NOT_DEFINED não equivale a LGPD conforme.

O [procedimento operacional](security_remediation_plan.md) separa verificações futuras do responsável. Não houve deploy, reinício, abertura/alteração do SQLite produtivo, migration produtiva, mudança de launcher/Tailscale, rotação de credenciais, acesso a terceiros ou varredura contra endpoints produtivos. Nenhuma regra financeira foi alterada. A baseline de engenharia não autoriza release financeiro ou deploy e não representa pentest, conformidade LGPD integral ou segurança comprovada do host.
