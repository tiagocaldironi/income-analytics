export const assetClassLabels = {
  BRAZILIAN_STOCK: "Ações Brasil", BRAZILIAN_ETF: "ETF Brasil", FII: "FIIs", FIXED_INCOME: "Renda fixa", PENSION: "Previdência", REAL_ESTATE: "Imóveis", INTERNATIONAL: "Exterior", INTERNATIONAL_ETF: "ETF internacional", US_REIT: "REITs EUA", CRYPTO: "Cripto", OTHER: "Outros",
};
export const assetClassLabel = value => assetClassLabels[value] || value;
