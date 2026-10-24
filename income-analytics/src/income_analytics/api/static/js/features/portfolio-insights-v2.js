import { percentage } from "../shared/ui.js";

// Compare only weights supplied by the authorized dashboard read model.
// Incomplete valuation cannot establish the largest share of the whole portfolio.
export function largestClassInsight(dashboard) {
  const total = dashboard?.portfolio?.total_market_value;
  if (total === null || total === undefined || !Number.isFinite(Number(total)) || Number(total) <= 0) return null;
  const groups = (dashboard?.holdings?.classes || []).filter(group => group.assets?.some(asset => !asset.target_only));
  if (!groups.length || groups.some(group => group.market_value === null || group.market_value === undefined || !Number.isFinite(Number(group.market_value)) || group.weight === null || group.weight === undefined || !Number.isFinite(Number(group.weight)) || Number(group.weight) < 0 || Number(group.weight) > 1)) return null;
  const max = Math.max(...groups.map(group => Number(group.weight)));
  if (max <= 0) return null;
  return { labels: groups.filter(group => Number(group.weight) === max).map(group => group.label), weight: max };
}
export function renderPortfolioInsight(dashboard) {
  const target = document.querySelector("#portfolio-insight");
  if (!target) return;
  const insight = largestClassInsight(dashboard);
  target.hidden = !insight;
  if (!insight) { target.textContent = ""; return; }
  const title = document.createElement("strong");
  title.textContent = "Sua carteira em perspectiva";
  const copy = document.createElement("p");
  copy.textContent = `${insight.labels.length === 1 ? "Maior participação na carteira" : "Classes com a mesma maior participação"}: ${insight.labels.join(" e ")} (${percentage(insight.weight * 100)}${insight.labels.length > 1 ? " cada" : ""}).`;
  const context = document.createElement("small");
  context.textContent = "Composição pelo valor atual na moeda-base. Não representa desempenho nem recomendação de investimento.";
  target.replaceChildren(title, copy, context);
}
