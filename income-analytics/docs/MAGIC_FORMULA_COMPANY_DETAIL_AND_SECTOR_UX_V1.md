# Fórmula Mágica: detalhe da empresa e setor

**Resultado: PASS.** A listagem agora mostra o setor CVM e oferece “Ver empresa”, que abre um drawer com a posição e os dados históricos efetivamente usados pelo snapshot publicado. A metodologia, universo, score, elegibilidade e ranking permaneceram inalterados.

## Implementação

- O read model da lista recebe setor e referência da fonte CVM do mesmo snapshot-fonte congelado; o enrichment é cacheado por `data_snapshot_id` e digest. O setor não entra no hash nem nos cálculos da Fórmula Mágica.
- O detalhe consulta a identidade canônica no mesmo snapshot publicado selecionado pela lista. A API aceita `snapshot_id`, devolve identificação, rank, EY/ROC/score, valores e linhagem, período contábil, filing e cotação. Valores não registrados são `null` na API e aparecem como “Não disponível” na tela.
- O drawer é carregado sob demanda e explica a composição do score sem linguagem de recomendação. Tem estados de carregamento, erro/tentar novamente e indisponibilidade explícita. A experiência móvel usa painel inferior responsivo.
- A busca foi conectada ao parâmetro `query` do ranking; fechar o detalhe mantém a tela no estado atual. Não foi criado filtro por setor.
- A classificação exibida é exclusivamente o metadado descritivo atual da CVM. Sua disponibilidade point-in-time é `UNKNOWN`; não é apresentada como informação conhecida na data histórica do ranking.
- Segmento de listagem não foi incluído: esse campo não está persistido no snapshot canônico usado pelo detalhe. Subsetor e segmento econômico continuam indisponíveis, sem inferência.

## Evidência de dados e metodologia

| Item | Resultado |
| --- | --- |
| Política | `MF_BR_2027_V1`; hash antes/depois `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac` |
| Snapshot | `mf-f1ee50809c83979ba221d84e`; referência `2025-12-30` |
| Ranking | 165 empresas; hash antes/depois `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3` |
| Setor | CVM FCA 2025, campo `Setor_Atividade`: 307/307 universo e 165/165 ranqueadas |
| Subsetor / segmento econômico | Não disponível; não inferido |
| Segmento de listagem | Existe na fonte FCA, mas não está materializado no snapshot canônico; não exibido |
| Segurança point-in-time do setor | `UNKNOWN`; somente descritivo |

Golden case: WEGE3 mantém rank #78, EY 0,0384963 (3,85%), EY rank 130, ROC 0,3278997 (32,79%), ROC rank 37, score 167. O detalhe aponta DFP 2024, protocolo em 26/02/2025 e preço de 30/12/2025, além das referências contábeis e de mercado persistidas. Valor de mercado e ações em circulação não fazem parte dos valores identificados neste contrato; são mostrados como indisponíveis, sem substituição por dados atuais. Outros casos: TAEE11 (utility), RADL3 (varejo tradicional), UNIT e CSNA3 bloqueada sem detail fabricado. Não há empresa ranqueada marcada com a flag de aviação, portanto esse golden case é não aplicável.

## Validação

- Testes de API do detalhe + aceitação frontend: **36/36 PASS**.
- Testes de aplicação da Fórmula Mágica: **283/283 PASS**; IDs congelados da baseline V9.2: **273/273 PASS**.
- Suíte completa: **843/843 PASS** (duas advertências de depreciação `FastAPI on_event`, sem falhas).
- Ruff nos três arquivos Python afetados: **PASS**. Sintaxe JS nos módulos afetados: **PASS**.
- Browser smoke no runtime local: **PASS** — lista carregada, WEGE3 abriu com dados do snapshot e percentuais corretos, drawer fechou, busca/página foram preservadas, e a troca para POSI3 carregou o detalhe correto. A viewport de 390×844 não teve overflow horizontal.
- Performance quente: 30 requisições medidas por endpoint. Lista: p95 **233,44 ms** (meta 250 ms); detalhe: p95 **161,56 ms** (meta 250 ms). A medição inclui ida HTTP local e serialização JSON.

O browser smoke usou um runtime local com o router do dashboard e os arquivos estáticos, evitando executar tarefas automáticas de startup/refresh da aplicação. O carregador global de pontos de atenção registrou uma exceção independente por inconsistência preexistente de venda superior à posição na carteira; as rotas da Fórmula Mágica e a interação da tela continuaram funcionais. Esse estado não foi alterado nesta entrega. Os resultados e gates estão registrados em `docs/appendices/magic_formula_company_detail_v1/`.

## Resultado final

`MAGIC_FORMULA_COMPANY_DETAIL_AND_SECTOR_UX_V1 = PASS`

O detalhe da empresa está disponível no ranking da Fórmula Mágica e o setor CVM está visível na listagem. Integridade point-in-time dos valores do ranking preservada; o setor segue explicitamente fora dessa garantia histórica.
