# PR 5 — Simulação V2: Aportes Executáveis

## Resultado
A tela Simular mantém o formulário, atalhos e comparação Hoje → Cenário → Objetivo. O resultado acrescenta plano por ativo: quantidade, incremento, preço/moeda/fonte/data, câmbio utilizado, custo estimado, participação antes/depois e motivo. As comparações usam os valores das compras negociáveis, e não o aporte teórico integral.

A implementação é somente de leitura: não registra compras, não envia ordens, não publica modelos e não altera a política. Entender permanece intacta. Diagnóstico anterior à implementação: `SIMULATION_EXECUTABLE_V2_DIAGNOSIS.md`.

## Algoritmo anterior e proposto
Anterior: o alocador oficial distribui dinheiro nos déficits de classe após o aporte e, havendo política intraclasse completa, entre ativos. Arredonda dinheiro em centavos, sem comprovar unidades.

Novo: mantém esse alocador como semente, reserva o valor destinado a instrumentos sem dados e arredonda compras para incrementos negociáveis. Em seguida reavalia o saldo. A escolha adicional exige déficits positivos de classe e ativo no patrimônio pretendido após o aporte e benefício superior aos custos conhecidos. O desempate usa benefício/custo e ticker lexical. Incrementos decimais são agrupados até a fronteira do déficit ou orçamento; a quantidade de iterações tem limite proporcional ao número de ativos.

O objetivo usa o patrimônio pretendido com o aporte total e considera o saldo ainda não investido como caixa sem alvo; não equivale a garantir redução estrita da distância da carteira já investida em todos os casos discretos. A comparação oficial mostra o resultado efetivo. Trata-se de heurística determinística, sem promessa de ótimo combinatório global. Nenhum ativo fora da estratégia é incluído para consumir saldo.

## Precisão e condições
| Classe | Regra inicial |
|---|---|
| Ações, FIIs e ETFs brasileiros | Quantidades e incrementos inteiros, mínimo inicial de uma unidade; lote maior configurável. Não envia ordens nem escolhe rota de negociação. |
| Exterior, ETFs internacionais e REITs | Inteiros por padrão; frações somente com confirmação do usuário, precisão padrão de 6 casas e configurável até 12. |
| Cripto | 8 casas por padrão, configurável até 12; mínimo e incremento informados são respeitados. |
| Renda fixa | Exige mínimo e incremento de aplicação, além de preço observado. Usa a interseção do incremento monetário e da quantidade; valores derivados de curva não são cotações de compra. |
| Outros mercados | Não simuláveis nesta versão. |

Os parâmetros estão na seção expansível Regras de negociação e custos. Permanecem na tela, sem modificar cadastro ou estratégia. A mudança para frações ajusta o incremento e o mínimo padrão; mínimos personalizados são preservados.

Preços são lidos da sessão existente, sem novo provedor: até 7 dias corridos para ativos listados e 1 para cripto; timestamp antigo também invalida a observação. Câmbio usa o histórico e a política oficial de 5 dias. Referências futuras são rejeitadas. Não são cotações em tempo real.

Custos fixos por compra são expressos na moeda-base, custos proporcionais incidem sobre o principal convertido. Custos e arredondamento são cobrados uma vez por ativo, reunindo a quantidade final em uma compra. O total é arredondado para cima ao centavo para preservar o teto do orçamento. Decimais são processados com precisão 50 e transmitidos como strings.

## Contratos e arquivos
- Novo `application/executable_contribution.py`: adaptação de dados da sessão autorizada e planejamento puro de quantidades.
- `api/routers/dashboard.py`: POST `/api/portfolio/simulation/executable-contribution`; amount e regras por ticker, sem aceitar preços do cliente ou carteira no corpo. As rotas monetárias anteriores permanecem válidas.
- `static/js/api.js`: cliente da nova rota com ownership e CSRF existentes.
- `static/js/features/simulation-executable.js`: apresentação do plano e edição das condições.
- `static/js/features/simulation.js`: integração e proteção contra respostas antigas; preserva renderização legada.
- `static/css/feature-theme-v2.css`: cartões responsivos e campos de negociação.
- Novos testes de aplicação e frontend; matriz Firebase ampliada. Sem mudanças em motores, projetores financeiros, bancos pessoais, migrações ou hashes certificados.

## Testes e evidências
91 testes Python aprovados: planejamento, alocador original, projetor hipotético original, módulos frontend e autorização Firebase. As 28 suítes Node em `tests/frontend` passaram. Ruff passou nos novos arquivos Python. Validações de propriedade, CSRF, não persistência e recusa de regras/preços inválidos foram aprovadas com dois usuários e SQLite descartável.

Casos obrigatórios cobertos: R$ 50 a R$ 34,50; preço maior que orçamento; dois preços; redistribuição; residual; recusa de frações brasileiras; ações e ETFs internacionais fracionários; alta precisão cripto; mínimo de renda fixa; preço ausente/antigo/futuro; câmbio; custos; orçamento zero; ativo acima do peso; empate lexical; não regressão da política. Casos adicionais: timestamp antigo, ativo inativo, ausência de composição por ativo e recusa de valor de curva como preço.

A árvore de acessibilidade do navegador confirmou o formulário, comparação e plano de 10 unidades de VALID11 a R$ 94,76, com orçamento R$ 1.000 e saldo R$ 52,40, em carteira sintética. A captura final de screenshots ficou indisponível no navegador integrado. Não há novas imagens desktop/mobile anexadas; não se usam capturas de versões anteriores como evidência desta implementação.

## Saldos e limitações
- R$ 50 / unidade R$ 34,50: uma unidade e R$ 15,50 residuais.
- R$ 50 / unidade R$ 60: nenhuma compra, R$ 50 residuais.
- Dois ativos com alvos iguais a R$ 34,50 e R$ 15,50: reavaliação compra uma unidade de cada, sem saldo.
- Ativo sem cotação com R$ 25 destinados: R$ 25 aguardam dados; esse orçamento não é desviado para outro alvo.
- Renda fixa com preço observado de R$ 1, mínimo R$ 100 e incremento R$ 25, orçamento R$ 130: R$ 125 aplicáveis e R$ 5 residuais.

Uma avaliação incompleta das posições bloqueia todo o objetivo, pois o patrimônio e seus desvios são desconhecidos. Uma cotação ausente de ativo-alvo sem posição reserva sua parcela e permite os outros ativos elegíveis. Classes sem composição por ativo exigem configuração, sem presumir pesos iguais.

Condições de corretora e custos são declarados pelo usuário, não verificados por integração. Mínimos desconhecidos, spread, execução e custos omitidos podem mudar a viabilidade. Produtos sem preço observado ou condições de aplicação conhecidas permanecem bloqueados. A simulação continua educacional e não executa ordens.
