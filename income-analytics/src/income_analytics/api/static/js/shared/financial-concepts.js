export const financialConcepts = {
  returnLabel: "Rentabilidade TWR",
  returnTooltip: "Mostra o desempenho dos seus investimentos no período, considerando a valorização dos ativos e os rendimentos recebidos, como dividendos e JCP. Movimentações externas de capital são neutralizadas.",
  returnPeriod12Months: "Últimos 12 meses",
  returnPeriodTotal: "Desde o início do histórico disponível",
  returnMethodologyHref: "#ajuda-metodologia/rentabilidade",
};

export const methodologySections = [
  { id: "patrimonio", title: "Patrimônio", questions: [{ question: "O que é o patrimônio da minha carteira?", answer: "O patrimônio investido representa o valor de mercado dos ativos que você mantém na carteira, com base nas posições e cotações disponíveis. Rendimentos já recebidos e que não permanecem investidos não são somados ao valor atual dos ativos." }] },
  { id: "evolucao-patrimonial", title: "Evolução patrimonial", questions: [{ question: "O que significa evolução patrimonial?", answer: "A evolução mostra como o valor dos ativos mudou entre duas datas. Ela pode refletir aquisições, vendas, valorização ou desvalorização, câmbio e outros efeitos de avaliação. Por isso, crescimento do patrimônio não significa necessariamente a mesma coisa que rentabilidade." }] },
  { id: "rentabilidade", title: "Rentabilidade", questions: [
    { question: "Como a rentabilidade da carteira é calculada?", answer: "O Income utiliza a Rentabilidade Ponderada pelo Tempo (TWR). Ela mede o desempenho da carteira ao longo do período e neutraliza o efeito de aportes e retiradas. A valorização ou desvalorização dos ativos e os rendimentos recebidos, como dividendos e JCP, participam do resultado econômico." },
    { question: "Pode dar um exemplo?", answer: "Você compra um ativo por R$ 100. Ao final do período ele vale R$ 105 e pagou R$ 5 em dividendos. A valorização do ativo foi de R$ 5; considerando também os dividendos, o investimento gerou R$ 10 de resultado econômico. Este exemplo simples não demonstra todos os detalhes matemáticos do TWR em carteiras com múltiplos fluxos." },
    { question: "Um aporte aumenta minha rentabilidade?", answer: "Não. Um aporte pode aumentar o patrimônio porque você adicionou capital, mas isso não significa que os investimentos renderam mais. O TWR neutraliza o efeito das movimentações externas de capital." },
    { question: "Meu patrimônio aumentou. Isso significa que tive a mesma rentabilidade?", answer: "Não necessariamente. O patrimônio pode aumentar por novas aquisições, valorização dos ativos ou uma combinação desses fatores. A rentabilidade mede o desempenho dos investimentos separando-o das movimentações de capital." },
  ] },
  { id: "rendimentos", title: "Rendimentos", questions: [{ question: "Rendimentos aumentam meu patrimônio?", answer: "Dividendos, JCP, rendimentos de FIIs e distribuições equivalentes fazem parte do retorno dos investimentos. Quando são distribuídos, ficam registrados como rendimentos recebidos. Se não permanecerem aplicados, não aumentam o valor atual dos ativos; ainda assim participam da rentabilidade do período." }] },
  { id: "preco-medio", title: "Preço médio", questions: [{ question: "O que significa a valorização mostrada em cada ativo?", answer: "A valorização desde a compra compara o valor atual da posição com o custo registrado. Ela não é o TWR da carteira e pode não incluir todos os rendimentos recebidos ao longo do tempo." }] },
  { id: "cobertura-dados", title: "Cobertura dos dados", questions: [{ question: "Por que alguns períodos podem não mostrar rentabilidade?", answer: "O cálculo depende de informações suficientes para valorar a carteira ao longo do período. Quando faltam preços históricos, câmbio ou outros dados necessários, o Income pode indicar cobertura parcial ou deixar a rentabilidade indisponível em vez de apresentar um número potencialmente incorreto." }] },
];

export function escapeConceptHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}
