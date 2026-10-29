# PR9 — Financial Certification Closure

**FINANCIAL_CERTIFICATION_BLOCKED**. A investigação não equivale à aprovação. CERT_48, identidade e 22 casos históricos continuam bloqueadores; nenhum resultado esperado, fórmula, fixture ou hash congelado foi alterado.

## Baseline e preflight

Develop c76132b4398434fb8a196f895b78b7f46ed3845e, PR53 integrado. CI40941528433: Engineering/Security/Build aprovados; homologação automática40943880889 aprovada. Ruleset26078982 ativo, sem bypass, Engineering obrigatório incluindo Security. Novo worktree/branch codex/pr9-financial-certification; HEADs e alterações dos originais preservados. As medidas GitHub foram consultadas novamente, não presumidas dos relatórios anteriores.

Reprodução sem alterações: **73 PASS /15 FAIL /9 ERROR /0 SKIP**, 97 casos, Python3.14.7 e locks PR8. O checkout convertido Windows inicialmente apresentou74P/14F/9E; a diferença de transporte foi registrada separadamente. Execução canônica usa exatamente os blobs Git, não normaliza originais nem redefine hashes.

## Causas e recuperação

24 ocorrências: dois testes de identidade congelada e22 casos de replay histórico (13 falhas +9 erros), dependentes de referências compartilhadas. Não são22 arquivos ausentes independentes. Inventário individual inclui entrada, operação/asserções, dependências, tipo, stack sanitizado, causa e material necessário. Não foi comprovado defeito em fórmulas nem correção financeira autorizada.

Oito arquivos sob dois guards: três fontes de engine e cinco fixtures de identidade. Cinco divergências nos bytes Git: uma fonte e quatro textos. Outros manifests CVM foram inventariados sem recertificação. Hash igual, equivalência semântica, proveniência e certificação são decisões distintas. A ausência de prova original impede correção automática CRLF/LF.

19 grupos de referência; três candidatos públicos locais e oito snapshots de universo público revalidados por leitura SQLite somente leitura, tabela permitida, hash antes/depois idêntico. Nenhum banco de carteira pessoal foi aberto. Autodigests válidos e contagens agregadas não aprovam proveniência completa nem redistribuição. Não foram copiados/committados DBs ou payloads B3. Um índice CVM reduzido já aprovado continua utilizável apenas no seu escopo original; não representa o ZIP contábil completo.

Recuperação parcial comprovada: o candidato V12.2 tem ranking hash `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3` e content hash `18a8631490f3a340575df3234acc26065a467b701c9a999cd3eaed859bb82db7`, ambos recalculados por stdlib sobre os bytes existentes e coincidentes com a documentação Git anterior. Isso verifica a integridade do candidato, sem recalcular EY/ROC, mas não aprova a cadeia inteira nem redistribuição. Os contratos V11 (174 empresas, cutoff contábil2026-10-13) e V12.2 (165, cutoff2025-12-30) são distintos; não se atualizou expectativa para confundi-los.

Refs/tags/objetos Git alcançáveis, histórico direcionado e229 artefatos GitHub foram pesquisados; nenhum pacote original de referências aprovado foi identificado. Seis URLs oficiais CVM responderam HEAD200; os metadados atuais não provam identidade com aquisições históricas. O portal oficial declara atualizações semanais por reapresentações: [DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp), [ITR](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr). Os [termos institucionais B3](https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/) não foram tratados como autorização específica de redistribuição deste pacote misto. Downloads atuais não foram usados como substitutos.

## Controles implementados

`ci/financial_certification.py` acrescenta FINANCIAL_PASS/FAIL/BLOCKED/NOT_VERIFIED, cobertura obrigatória dos97 casos originais, identidade dos manifests originais e classificação causal. Uma falha nova ou causa diferente no mesmo ID é FAIL, não é absorvida pela dívida histórica. Falta de execução, skip, duplicata ou contagem inconsistente é NOT_VERIFIED. Falha/erro continuam no JUnit; bloqueios independentes impedem aprovação mesmo se asserções passarem.

O verificador de evidência compara bytes e relações snapshot/engine/política/período/fonte/ordem/resultado com pins independentes; seus testes usam contratos sintéticos explicitamente identificados. Esses contratos não aprovam as referências reais: nenhuma autoridade independente foi inventada. A política real conserva aprovações pendentes. Arquivos de controles e testes entram no fingerprint/política CI. Engineering e Security continuam independentes da certificação e obrigatórios; release financeiro e produção permanecem bloqueados.

## Determinismo e limites

Contratos existentes já cobrem Decimal, empate/ordem, datas futuras, identidade e readback/imutabilidade; novos controles rejeitam ordem ambígua e evidência do período errado. Repetições descartáveis, sementes e resultados serão registrados em financial_gate_validation.json. Não foi provada equivalência financeira histórica completa: faltam entradas originais. Outras versões Python, locales/timezones reais do SO e paralelismo não são certificados por uma execução Windows3.14.7; não foram alteradas configurações globais para alegar essa cobertura.

## Execução e evidências

Comando base, a partir de income-analytics em checkout limpo: `.venv/Scripts/python.exe ci/governance.py financial`. Locks e setup estão no workflow da raiz Git. Novo teste `ci/test_financial_certification.py` executa tanto em Engineering quanto na seleção financeira; JUnit e enum de causa não publicam raw logs. Relatórios pós-alteração e hospedados serão registrados nos JSONs desta pasta e no recibo final do PR. Não declarar workflow global verde enquanto houver diagnósticos/falhas.

Entregáveis: financial_failure_inventory.json; cert48_provenance_analysis.md; frozen_identity_matrix.json; magic_formula_historical_cases.csv; external_evidence_requirements.json; financial_provenance_matrix.csv; financial_gate_validation.json; financial_hosted_validation.json. O recibo final do PR completa o snapshot versionado com SHA e runs definitivos pós-merge.

## Material necessário para desbloqueio

1. Originais dos três arquivos congelados e aprovação independente ligando os hashes existentes aos bytes; cadeia dos quatro textos de identidade, PDF/linha COTAHIST e mapeamento temporal.
2. Universo original completo com IDs históricos, rowids/ordem de timestamps empatados e âncoras independentes; V8/V9.2 CSVs por emissor, ranking V12.2 e lineage V6/V7/V9.
3. Versões exatas dos ZIPs DFP/ITR/FCA, COTAHIST2022–2025, documentos de ações/ISIN/trocas de ticker e regras de transformação versionadas, respeitando cutoffs e reapresentações.
4. Autorização de uso/redistribuição aplicável ao material B3/derivado. Sem prova, não distribuir candidatos em CI pública.
5. Replay determinístico integral e parecer de certificação após recuperação legítima. Não usar novas cotações, autocálculo de goldens ou alteração de hashes para eliminar bloqueios.

Não houve deploy, migration produtiva, reinício, alteração de regras fiscais/Magic Formula/rentabilidade/alocação, acesso a carteiras pessoais ou concessão de acesso. Bancos produtivos pessoais não foram acessados. A inspeção do repositório separado de universos públicos foi somente leitura, sem cópia ou alteração.

## Arquivos-fonte públicos recuperados

Os seis ZIPs CVM DFP2023/2024/2025, ITR2025 e FCA2024/2025 e o COTAHIST_A2025.ZIP foram localizados e seus SHA-256 coincidem com os registros anteriores. Nenhum foi copiado, regenerado ou publicado. Não é necessário solicitar novamente esses sete arquivos: faltam vínculos/transformações históricas e aprovações aplicáveis, e a autorização de redistribuição B3 continua pendente. Fonte disponível não significa certificação financeira completa.

## Validação local concluída

Seleção financeira:103 PASS/15 FAIL/9 ERROR/0 SKIP; os97 casos originais mantêm exatamente seus estados e30 controles novos passam. Duas execuções descartáveis com seeds0/97 preservam casos e causas. Foco governança/integridade:106 PASS. Qualidade802 diagnósticos atuais/803 históricos, zero novos. Nenhum diff em src/tests/alembic/scripts ou baseline original. Gates hospedados ainda pendentes nesta revisão.

O harness de teste negativo de tamanho foi corrigido com IDs explícitos curtos, preservando o payload grande e as asserções; erros intermediários de limite de variável de ambiente foram rejeitados e não tratados como aprovação. O parser JUnit é limitado a16MiB, UTF-8 sem NUL/DOCTYPE/ENTITY. As novas ocorrências SAST e relocações de contexto foram revisadas individualmente; não houve ignore global.
