let library;

export function loadECharts() {
  if (window.echarts) return Promise.resolve(window.echarts);
  if (library) return library;
  library = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/static/vendor/echarts-6.1.0.min.js";
    script.onload = () => resolve(window.echarts);
    script.onerror = () => reject(new Error("Não foi possível carregar os gráficos."));
    document.head.append(script);
  });
  return library;
}

export function chartTheme() {
  const styles = getComputedStyle(document.documentElement);
  return {
    accent: styles.getPropertyValue("--income-action").trim() || "#27c7a8",
    muted: styles.getPropertyValue("--income-secondary").trim() || "#93a4b8",
    text: styles.getPropertyValue("--income-text").trim() || "#edf3fb",
    surface: styles.getPropertyValue("--income-surface").trim() || "#111f32",
    border: styles.getPropertyValue("--income-line").trim() || "#344963",
  };
}
