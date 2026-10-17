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
