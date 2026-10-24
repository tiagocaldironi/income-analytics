const paths = {
 check:'<path d="m5 12 4 4L19 6"/>',
 home:'<path d="m3 11 9-8 9 8v10H3V11ZM9 21v-8h6v8"/>',
 wallet:'<path d="M4 6h14v4H4a2 2 0 0 1 0-4Zm0 4v10h16V8h-2M16 13h4v4h-4z"/>',
 chart:'<path d="M4 4v16h16M8 15l4-5 4 2 4-7"/>',
 income:'<path d="M4 8h16v12H4zM8 4h8M8 13h8M12 10v6"/>',
 layers:'<path d="m12 3 10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5"/>',
 compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6z"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 book:'<path d="M12 6v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2z"/>',
 moneybag:'<path d="m8 3 1.5 4h5L16 3l-4 1-4-1ZM9 7c-1 3-5 5-5 10 0 3 3 4 8 4s8-1 8-4c0-5-4-7-5-10M9 8h6M14 12h-3a1.5 1.5 0 0 0 0 3h2a1.5 1.5 0 0 1 0 3h-3M12 11v8"/>',
 tools:'<path d="m14 6 4-4a5 5 0 0 1-6 7L4 17a2.1 2.1 0 0 0 3 3l8-8a5 5 0 0 0 7-6l-4 4-4-4ZM3 3l4 1 2 3-2 2-3-2-1-4ZM8 8l3 3M15 15l5 5a1.4 1.4 0 0 1-2 2l-5-5"/>',
 settings:'<path d="m10 3-.5 2-2 .9-1.8-1-2 3.4 1.5 1.4v2.6l-1.5 1.4 2 3.4 1.8-1 2 .9.5 2h4l.5-2 2-.9 1.8 1 2-3.4-1.5-1.4V9.7l1.5-1.4-2-3.4-1.8 1-2-.9L14 3h-4Z"/><circle cx="12" cy="11" r="3"/>',
 help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4M12 16.5h.01"/>',
};
export function icon(name) {
 return `<svg class="income-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.chart}</svg>`;
}
