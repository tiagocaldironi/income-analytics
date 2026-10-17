# Recuperação de identidade histórica — CSN / V2

Data: 12/10/2026. Escopo: um bloqueador de preço da prévia do universo, sem ativar o ranking.

## Resultado

A declaração CVM 2025 para CSN (CVM 004030, CNPJ 33.042.730/0001-04) trouxe `4030` como ticker. A resposta arquivada do cadastro de Empresas Listadas da B3, consultada em 23/09/2026 pelo mesmo CVM, associa a companhia a `CSNA3`, ISIN `BRCSNAACNOR6`, classe comum e início de cotação em 02/08/1993. O COTAHIST oficial de 2025 contém negociações à vista do mesmo ticker e ISIN na janela de referência; a última cotação elegível é de 30/12/2025, R$ 8,94. O BDI da B3 também lista CSNA3, esse ISIN e a companhia em setembro de 2025 ([edição de 09/09/2025](https://arquivos.b3.com.br/bdi/download/bdi/2025-09-09/BDI_05_20250909.pdf)).

A regra não usa similaridade do nome para resolver identidade. Ela exige correspondência CVM/CNPJ, um único código/ISIN no diretório, classe ON, security ativa listada antes da referência e registros históricos no mercado à vista com o mesmo ISIN. Caso haja mais de um ticker, classe divergente, ISIN conflitante, segurança não listada ou preço fora da janela, a recuperação é rejeitada. Eventos societários e múltiplas securities continuam exigindo evidência específica.

## Snapshot e cobertura

- Snapshot pai: `b3aa341e-7074-4d53-93f3-b3b88d247c19`.
- Snapshot filho persistido: `9dd05e5a-d4a0-402c-809e-fd7f4cbc4f64`.
- Cobertura completa: 179/307 (58,31%) → 180/307 (58,63%).
- Emissores ranqueáveis na prévia: 175 → 176; 4 continuam sem capital investido positivo.
- Gate: `BLOCKED`; ranking: `INACTIVE`; ferramenta: `VALIDATION_REQUIRED`.
- Backup e recibo: `tmp/price-recovery-csn-identity-v2/universe-before-publication.db` e `publication.json`.
- Read-back independente: `readback-report.json`, status PASS, SHA-256 do candidato validado `fec5f0b9b2765239b2f062615f9e9e7d559177c666e550c9daa4ae1f16911d9e`.

Foram preservados os cinco casos golden e todo o conteúdo dos demais emissores. Nenhum cálculo de fundamentos, fórmula, preço aproximado ou decisão QA canônica foi criado para CSN.

## Alterações e verificação

O resolvedor reutilizável `B3_LISTED_SECURITY_IDENTITY_V1` foi adicionado ao caminho de preparação/read-back. A prova liga o diretório oficial atual a linhas datadas do COTAHIST por ISIN e recusa ambiguidades. A captura bruta e hashes permanecem em `data/magic_formula/price_recovery_identity/20260923T102111856750Z/`; o pacote de preparação carrega a referência pai nova sem alterar a captura original.

A suíte de regressão focada passou: 74 testes em identidade histórica, preview, universo e engine. O read-back independente passou para CSNA3, reabriu o snapshot pai, conferiu novamente a linha bruta e o provedor B3, preservou os golden-five e confirmou determinismo. `RANKING_STATUS` continua inativo.

## Próximo bloqueio

Restam 36 price-only blockers. JBS e Marfrig continuam dependentes de análise de evento societário. Os demais casos não devem ser mapeados por semelhança de nomes; seguir apenas com provas de segurança e vigência temporal que satisfaçam o contrato.
