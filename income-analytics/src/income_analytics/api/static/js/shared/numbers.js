export function decimalForApi(value) {
  const input = String(value ?? "").trim().replace(/\s/g, "");
  if (!input) return null;
  const sign = input.startsWith("-") ? "-" : "";
  const unsigned = input.replace(/^[+-]/, "");
  if (!/^[\d.,]+$/.test(unsigned)) return null;
  const comma = unsigned.lastIndexOf(",");
  const dot = unsigned.lastIndexOf(".");
  const decimalIndex = Math.max(comma, dot);
  const integerPart = decimalIndex === -1 ? unsigned : unsigned.slice(0, decimalIndex);
  const fractionalPart = decimalIndex === -1 ? "" : unsigned.slice(decimalIndex + 1);
  const normalized = sign + integerPart.replace(/[.,]/g, "") + (fractionalPart ? "." + fractionalPart : "");
  return Number.isFinite(Number(normalized)) ? normalized : null;
}

export function formatDecimal(value, { minimumFractionDigits = 0, maximumFractionDigits = 8 } = {}) {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? numeric.toLocaleString("pt-BR", { minimumFractionDigits, maximumFractionDigits })
    : "";
}

export function isPositiveDecimal(value) {
  const normalized = decimalForApi(value);
  return normalized !== null && Number(normalized) > 0;
}
