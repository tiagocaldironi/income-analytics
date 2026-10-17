import { portfolioApi } from "../api.js";
import { emptyState, errorState, percentage, table } from "../shared/ui.js";

export async function renderDiversification() {
  const target = document.querySelector("#diversification");
  if (!target) return;
  try {
    const data = await portfolioApi.diversification();
    const dimensions = ["asset_class", "sector", "country", "currency"];
    target.innerHTML = table(["Dimensão", "Maior exposição", "HHI"], dimensions.map(name => { const dimension = data[name]; const largest = dimension.exposures[0]; return `<tr><td>${name}</td><td>${largest ? `${largest.key} (${percentage(largest.weight * 100)})` : dimension.unavailable_reason || "—"}</td><td>${dimension.hhi ?? "—"}</td></tr>`; }));
  } catch (error) { target.innerHTML = errorState(error.message); }
}
