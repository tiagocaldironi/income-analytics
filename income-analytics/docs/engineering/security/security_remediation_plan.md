# Remediação e verificação operacional

Nenhum procedimento abaixo foi executado no host produtivo. Não reutilizar automaticamente configurações locais como prova do estado real.

1. Antes de qualquer release, fechar CERT_48, integridade congelada e referências históricas com reconciliação independente. Segurança de engenharia não libera cálculo financeiro.
2. Responsável pelo host deve inventariar o processo real, binding, portas, proxy headers/trusted peers, origem HTTPS, Tailscale Serve e ACLs. Não habilitar modo local para tráfego remoto; configurar INCOME_AUTH_MODE=firebase em produção e declarar INCOME_ENV=production. ENVIRONMENT=production/prod também é reconhecido como produção.
3. Configurar INCOME_DATA_ROOT absoluto, privado e dedicado; INCOME_ANALYTICS_DATABASE deve resolver dentro dessa raiz. Não ativar este controle sem confirmar o caminho real e backup validado. Nenhum banco foi movido ou aberto por esta avaliação.
4. Validar Firebase projeto/audience/issuer/revogação no ambiente autorizado, com usuário sintético, sem reutilizar dados reais. Credenciais Admin ficam fora do checkout; nunca no navegador. Remover emulator em produção. Manter signup fechado até validação funcional e autorização.
5. Verificar permissões NTFS, conta de serviço sem privilégios excessivos, proteção de logs/backups/temporários, atualização Windows/Python, proteção de disco e antimalware conforme benchmark aplicável. Estado atual NOT_VERIFIED.
6. Testar restauração e rollback no ambiente homologado autorizado com plano de compatibilidade de schema. PR7 prova apenas staging descartável e sintético; nunca aplicar downgrade automático.
7. Caso o proprietário descubra segredo real, restringir acesso ao material, determinar alcance sem republicação, revogar/rotacionar pelo fornecedor com autorização específica, testar a credencial substituta e documentar evidência redigida. Não reescrever Git automaticamente. O marcador PEM histórico revisado não contém chave.
8. Definir retenção, exclusão de backups, portabilidade completa, aviso/termos, responsáveis por incidentes e compartilhamento externo. POLICY_NOT_DEFINED não pode ser convertido em LGPD PASS.
9. Avaliar egress allowlist/DNS/redirects dos provedores, CSP com remoção gradual de estilo inline e dependência CDN Firebase, parsing offline/arquivos externos e logging estruturado de dados financeiros. Riscos médios explícitos, sem cobertura presumida por scanner.
10. Scanner indisponível, feed parcial/paginado, referência/digest divergente ou fixture de segredo alterada devem reprovar o gate. Revisões de baseline exigem identidade específica e justificativa; não aceitar HIGH/CRITICAL como ACCEPTED_RISK.

Prioridades: P0/P1 confirmados no código devem ter correção e testes antes do merge; ações produtivas são separadas e dependem do responsável. Não realizar deploy, reinício, migrations, rotação real, Tailscale ou varredura contra produção neste PR.
