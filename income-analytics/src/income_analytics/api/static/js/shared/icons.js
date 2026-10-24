const paths = {
 wallet:'<path d="M4 6h14v4H4a2 2 0 0 1 0-4Zm0 4v10h16V8h-2M16 13h4v4h-4z"/>',
 chart:'<path d="M4 4v16h16M8 15l4-5 4 2 4-7"/>',
 income:'<path d="M4 8h16v12H4zM8 4h8M8 13h8M12 10v6"/>',
 layers:'<path d="m12 3 10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5"/>',
 compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6z"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 book:'<path d="M12 6v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2z"/>',
 settings:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
};
export function icon(name) {
 return `<svg class="income-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.chart}</svg>`;
}
