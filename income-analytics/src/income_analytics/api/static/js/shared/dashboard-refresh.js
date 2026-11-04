// Confirmation of a committed write is separate from the derived dashboard.
export async function waitForDashboard({ status, portfolioId, isCurrent, pause = ms => new Promise(resolve => setTimeout(resolve, ms)), attempts = 90 }) {
  for (let i = 0; i < attempts; i++) {
    if (!isCurrent()) return "CANCELLED";
    const result = await status();
    if (!isCurrent()) return "CANCELLED";
    if (portfolioId && result.portfolio_id !== portfolioId) throw new Error("A carteira mudou durante a atualização.");
    if (result.status === "VALID") return "VALID";
    if (result.status !== "UPDATING") throw new Error("O lançamento foi excluído, mas o recálculo não foi concluído. Atualize a carteira para tentar novamente.");
    await pause(1000);
  }
  throw new Error("O lançamento foi excluído. O recálculo continua em andamento; atualize a carteira para acompanhar.");
}
