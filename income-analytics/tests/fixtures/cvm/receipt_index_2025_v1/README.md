# CVM — índice de recebimento DFP 2025

Extrato exato de `dfp_cia_aberta_2025.csv` do ZIP histórico cujo SHA-256 já estava
fixado em `tests/fixtures/cvm/phase2_v1/manifest.json` na baseline. Nenhuma linha
ou coluna foi selecionada, criada ou recalculada. O gzip usa mtime zero.

Fonte: Comissão de Valores Mobiliários, SEP / Suporte a Sistemas CVM.
Dataset e licença declarada: [CVM DFP — ODbL](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp).
Licença: [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
Preservar a atribuição à CVM e esta indicação de licença ao redistribuir.
Consulta dos metadados de licença: 28/10/2026. O ZIP corrente não foi baixado:
a CVM atualiza arquivos, portanto a URL atual não substitui o digest histórico.

O índice contém documentos de companhias abertas e seus CNPJs, não carteiras,
credenciais ou dados de investidores. Não inclui os anexos FCA com contatos.
Serve somente ao contrato de datas de protocolo, não a cálculos de EY/ROC.

Digests, origem e limites constam em
`docs/engineering/cicd-assessment/magic_formula_reference_provenance.json`.
O provisionador gera ZIP de teste contendo apenas este índice; ele não é
o arquivo oficial completo e possui outro hash. Não substituir o arquivo DFP
financeiro por esse ZIP nem atribuir-lhe o SHA-256 oficial.
