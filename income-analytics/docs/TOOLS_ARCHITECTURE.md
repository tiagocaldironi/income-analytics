# Ferramentas

Ferramentas é um hub independente da carteira para descoberta de oportunidades. O registry em `application/investment_tools.py` centraliza rota, versão, categoria e estado dos dados. O backend é a única camada responsável por rankings; o frontend apenas exibe contratos.

Estados: `AVAILABLE`, `PARTIAL`, `STALE`, `INSUFFICIENT_DATA`, `DATA_GAP` e `ERROR`.

Novas ferramentas são adicionadas ao registry, sem alterar a navegação estrutural.
