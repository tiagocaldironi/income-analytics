import { icon } from "../shared/icons.js";
let bound = false;
let resizeCharts = () => {};
export function selectAnalysis(index, focus = false) {
  const tabs = [...document.querySelectorAll("[data-analysis-tab]")];
  const panels = [...document.querySelectorAll("[data-analysis-panel]")];
  if (!tabs.length) return;
  index = (index + tabs.length) % tabs.length;
  tabs.forEach((tab, i) => {
    tab.setAttribute("aria-selected", String(i === index));
    tab.tabIndex = i === index ? 0 : -1;
    panels[i].hidden = i !== index;
  });
  if (focus) tabs[index].focus();
  // Panels remain mounted: filters and loaded data survive every switch.
  requestAnimationFrame(() => resizeCharts());
}
export function setupPortfolioView(resize) {
  resizeCharts = resize;
  if (bound) return;
  bound = true;
  const region = document.querySelector("#portfolio-analysis");
  if (!region) return;
  region.addEventListener("click", event => {
    const tab = event.target.closest("[data-analysis-tab]");
    if (tab) selectAnalysis(Number(tab.dataset.analysisTab));
  });
  region.addEventListener("keydown", event => {
    const tab = event.target.closest("[data-analysis-tab]");
    if (!tab) return;
    const i = Number(tab.dataset.analysisTab);
    const next = {ArrowRight:i+1, ArrowLeft:i-1, Home:0, End:3}[event.key];
    if (next !== undefined) { event.preventDefault(); selectAnalysis(next, true); }
  });
  // Swipe is confined to navigation. Chart gestures/tooltips remain untouched.
  const strip = region.querySelector("[role=tablist]");
  let start = null;
  strip?.addEventListener("touchstart", event => {
    const t = event.changedTouches[0]; start = {x:t.clientX,y:t.clientY};
  }, {passive:true});
  strip?.addEventListener("touchend", event => {
    if (!start) return;
    const t = event.changedTouches[0], dx = t.clientX-start.x, dy = t.clientY-start.y;
    start = null;
    if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy)*1.5) return;
    const current = Number(region.querySelector('[aria-selected="true"]').dataset.analysisTab);
    selectAnalysis(current+(dx<0?1:-1));
  }, {passive:true});
  const icons = ["wallet","chart","income","layers"];
  document.querySelectorAll('[data-page="minha-carteira"] .metric').forEach((card,i) => {
    const node = document.createElement("span"); node.className = "metric-icon";
    node.innerHTML = icon(icons[i]); card.prepend(node);
  });
  document.querySelectorAll(".primary-nav a").forEach((link,i) => {
    link.insertAdjacentHTML("afterbegin",icon(["wallet","book","compass","chart","income","settings"][i]));
  });
  new MutationObserver(() => resizeCharts()).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
}
export function updatePortfolioView(dashboard) {
  const root = document.querySelector('[data-page="minha-carteira"]');
  if (!root) return;
  root.dataset.hasPositions = String(dashboard.holdings.classes.some(group => group.assets.some(asset => !asset.target_only)));
}
