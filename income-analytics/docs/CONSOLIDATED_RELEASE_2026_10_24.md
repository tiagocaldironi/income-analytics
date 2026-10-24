# Versão consolidada — 24/10/2026

A versão reúne PRs #24 (visão patrimonial), #25 (Meus Ativos), #26 (identidade e ranking), #27 (pizza) e #28 (onboarding). O usuário autorizou resolver os conflitos e publicar o conjunto.

O PR #26 foi atualizado com develop e integrado sem perda das interações de onboarding. No PR #27, o conflito estava no final de portfolio-v2.css: os estilos da pizza e os estilos de Meus Ativos/onboarding foram preservados juntos. O JS foi integrado mantendo invalidação de consultas, filtros e instrumentação das análises.

Validação conjunta: 79 testes Python de migração, isolamento/autorização, sessões, interface, lançamentos e regressão financeira; dez testes da API de Ferramentas usando a fixture de referência local; 14 scripts Node passaram. Na prévia isolada: pizza, filtros, novos ícones e guia presentes, sem overflow no desktop/390px, pizza de 240px no mobile.

Ensaio de 0027 em cópia consistente do banco: 42 tabelas anteriores idênticas, integridade ok e nenhuma violação de FK. O procedimento de publicação inclui novo backup imediatamente antes do corte, aplicação somente da migração de metadados, comparação dos registros anteriores e verificação HTTP do serviço. Cadastro público permanece desabilitado e o acesso continua por HTTPS privado no Tailscale.

Os registros operacionais de backup, hashes e resultado final ficam fora do Git em AppData/Local/IncomeAnalytics/consolidated-release; não contêm cópias de credenciais no repositório. O motor e o manifesto certificado permanecem intocados; a falha preexistente de hash CRLF/LF segue documentada nos relatórios anteriores.
