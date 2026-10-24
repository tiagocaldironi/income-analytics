import { signOutDevice } from "./auth-client.js";

export function mountAccountMenu(header) {
  if (!header) return;
  const menu = document.createElement("details");
  menu.className = "user-account";
  // Static markup only; no identity data or provider content is interpolated.
  menu.innerHTML = `<summary aria-label="Abrir menu da conta"><span class="user-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/></svg></span><span class="user-account-label">Minha conta</span><span aria-hidden="true">⌄</span></summary><div class="user-account-panel"><p class="user-account-heading">Sua conta <span>Income Free</span></p><a href="/conta">Configurações da conta <span aria-hidden="true">↗</span></a><div class="user-account-divider"></div><button type="button" class="user-signout"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 4H4v16h5M13 7l5 5-5 5M8 12h11"/></svg><span>Sair da conta</span></button><p class="user-account-status" role="status" aria-live="polite"></p></div>`;
  header.append(menu);
  const trigger = menu.querySelector("summary");
  const button = menu.querySelector("button");
  const status = menu.querySelector("[role=status]");
  menu.addEventListener("keydown", event => {
    if (event.key === "Escape") { menu.open = false; trigger.focus(); }
  });
  document.addEventListener("pointerdown", event => {
    if (!menu.contains(event.target)) menu.open = false;
  });
  document.addEventListener("focusin", event => {
    if (!menu.contains(event.target)) menu.open = false;
  });
  button.addEventListener("click", async () => {
    if (button.disabled) return;
    button.disabled = true;
    button.querySelector("span").textContent = "Saindo…";
    status.textContent = "";
    try { await signOutDevice(); }
    catch {
      status.textContent = "Não foi possível sair. Verifique a conexão e tente novamente.";
      button.disabled = false;
      button.querySelector("span").textContent = "Sair da conta";
    }
  });
}
