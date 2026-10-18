# Mobile navigation map

| Destination | Label | Route / action |
|---|---|---|
| Home | Início | `#minha-carteira` |
| Holdings | Carteira | `#minha-carteira/ativos` (scrolls to existing positions section; same page/API lifecycle) |
| Understand | Entender | `#entender` (evolution, explanation, performance and comparisons already live here) |
| Act | Agir | `#tools-magic-formula-stocks` |
| More | Mais | Native dialog sheet with Operations, Strategy, Simulation, Risk & Exposure, Tools, Magic Formula FIIs, Settings and Methodology |

The existing desktop primary navigation is hidden only in the mobile shell. “Mais” links use the existing application hash routes. Changing between the root and holdings anchor updates scroll and active navigation without dispatching a second route load for `minha-carteira`. Returning to the root restores top scroll. Native dialog Escape behavior and an explicit close control are retained.
