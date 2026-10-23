import { authRequest, exchangeSession, firebaseClient, refreshCsrf, signOutDevice, clearPrivateBrowserState } from "./auth-client.js";

const $ = selector => document.querySelector(selector);
let config, memoryUser, linkedUser, busy = false;
const path = location.pathname;
function message(text, error = false) {
  $("#account-message").textContent = text;
  $("#account-message").dataset.error = String(error);
}
function pane(id, title, description) {
  for (const name of ["login-controls", "verify-controls", "first-wallet", "account-controls"])
    $(`#${name}`).hidden = name !== id;
  $("#account-title").textContent = title;
  $("#account-description").textContent = description;
}
function readableError(error) {
  if (error.code === "auth/account-exists-with-different-credential" || error.code === "auth/credential-already-in-use")
    return "Entre pelo método que você já usa. Você pode adicionar outro em sua conta, sem unir contas diferentes.";
  if (error.code === "auth/too-many-requests") return "Muitas tentativas. Aguarde antes de tentar novamente.";
  if (error.code === "auth/weak-password") return "Use uma senha mais forte, com pelo menos 8 caracteres.";
  if (error.code === "auth/popup-closed-by-user") return "A janela de acesso foi fechada. Você pode tentar novamente.";
  if (error.code?.startsWith("auth/")) return "Não foi possível concluir o acesso. Confira os dados ou recupere sua senha.";
  return error.message || "Não foi possível continuar. Tente novamente.";
}
async function action(callback) {
  if (busy) return;
  busy = true;
  const buttons = [...document.querySelectorAll("button")].filter(button => button.id !== "theme");
  buttons.forEach(button => { button.disabled = true; });
  $(".account-card").setAttribute("aria-busy", "true");
  message("");
  try { await callback(); }
  catch (error) { message(readableError(error), true); }
  finally {
    busy = false;
    buttons.forEach(button => { button.disabled = false; });
    $(".account-card").setAttribute("aria-busy", "false");
  }
}
async function finish(user) {
  memoryUser = user;
  if (!user.emailVerified) {
    pane("verify-controls", "Confirme seu e-mail", "Um passo para proteger sua conta.");
    return;
  }
  const { auth, sdk } = await firebaseClient(config);
  await exchangeSession(user);
  await sdk.signOut(auth);
  memoryUser = null;
  location.replace("/primeiro-acesso");
}
function provider(sdk) {
  const google = new sdk.GoogleAuthProvider();
  google.setCustomParameters({ prompt: "select_account" });
  return google;
}
async function initialize() {
  const preferred = localStorage.getItem("income.accountTheme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  document.documentElement.dataset.theme = preferred;
  $("#theme").addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("income.accountTheme", theme);
  });
  config = await authRequest("/config");
  if (config.mode !== "firebase") { location.replace("/"); return; }
  await refreshCsrf();
  if (path === "/primeiro-acesso" || path === "/conta") {
    await authRequest("/me");
    if (path === "/primeiro-acesso") {
      const response = await fetch("/api/portfolios", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("Entre novamente para abrir suas carteiras.");
      const { portfolios } = await response.json();
      if (portfolios.some(wallet => wallet.status === "ACTIVE")) { location.replace("/"); return; }
      pane("first-wallet", "Seu primeiro passo", "Comece a organizar seus investimentos no Income Free.");
      $("#first-wallet").addEventListener("submit", event => {
        event.preventDefault();
        action(async () => {
          const csrf = await refreshCsrf();
          const response = await fetch("/api/portfolios", {
            method: "POST", credentials: "same-origin", cache: "no-store",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
            body: JSON.stringify({ name: $("#wallet-name").value, base_currency: "BRL" }),
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.detail || "Não foi possível criar a carteira.");
          localStorage.setItem("income.activePortfolioId", result.id);
          location.replace("/#operacoes");
        });
      });
    } else {
      pane("account-controls", "Sua conta", "Seu espaço no Income.");
      $("#logout").addEventListener("click", () => action(signOutDevice));
      $("#revoke").addEventListener("click", () => action(async () => {
        await authRequest("/revoke", { method: "POST" });
        clearPrivateBrowserState(); location.replace("/entrar");
      }));
      const confirmCurrent = async user => {
        await authRequest("/confirm-method", { method: "POST", body: JSON.stringify({ id_token: await user.getIdToken(true) }) });
        linkedUser = user; $("#link-actions").hidden = false;
        message("Acesso confirmado. Escolha o método que deseja adicionar.");
      };
      $("#link-credentials").addEventListener("submit", event => {
        event.preventDefault(); action(async () => {
          const { auth, sdk } = await firebaseClient(config);
          const { user } = await sdk.signInWithEmailAndPassword(auth, $("#link-email").value, $("#link-password").value);
          $("#link-password").value = "";
          await confirmCurrent(user);
        });
      });
      $("#confirm-google").addEventListener("click", () => action(async () => {
        const { auth, sdk } = await firebaseClient(config);
        await confirmCurrent((await sdk.signInWithPopup(auth, provider(sdk))).user);
      }));
      const linked = async () => {
        await authRequest("/authorize-method", { method: "POST", body: JSON.stringify({ id_token: await linkedUser.getIdToken(true) }) });
        await exchangeSession(linkedUser);
        const { auth, sdk } = await firebaseClient(config);
        await sdk.signOut(auth); linkedUser = null; $("#link-actions").hidden = true;
        message("Método adicionado à sua conta.");
      };
      $("#link-google").addEventListener("click", () => action(async () => {
        const { sdk } = await firebaseClient(config);
        await sdk.linkWithPopup(linkedUser, provider(sdk)); await linked();
      }));
      $("#link-password-form").addEventListener("submit", event => {
        event.preventDefault(); action(async () => {
          const { sdk } = await firebaseClient(config);
          if (!linkedUser?.emailVerified) throw new Error("Confirme seu e-mail antes de adicionar uma senha.");
          const credential = sdk.EmailAuthProvider.credential(linkedUser.email, $("#new-password").value);
          await sdk.linkWithCredential(linkedUser, credential);
          $("#new-password").value = ""; await linked();
        });
      });
    }
    return;
  }
  pane("login-controls", path === "/criar-conta" ? "Crie sua conta Free" : "Entrar", "Seu patrimônio começa com um primeiro passo.");
  $("#signup-link").hidden = !config.signup_enabled || path === "/criar-conta";
  $("#login-link").hidden = path !== "/criar-conta";
  if (path === "/criar-conta") {
    if (!config.signup_enabled) throw new Error("O cadastro ainda não está disponível.");
    $("#submit").textContent = "Criar conta Free";
    $("#password").autocomplete = "new-password";
  }
  if (path === "/recuperar-senha") {
    $("#account-title").textContent = "Recuperar acesso";
    $("#account-description").textContent = "Enviaremos as instruções para o seu e-mail.";
    $("#password").hidden = true; $("#password").required = false;
    $("label[for=password]").hidden = true; $("#google").hidden = true;
    $(".separator").hidden = true; $("#submit").textContent = "Enviar instruções";
  }
  if (path === "/confirmar-email") {
    message("E-mail confirmado? Entre com sua senha para continuar.");
  }
  $("#credentials").addEventListener("submit", event => {
    event.preventDefault(); action(async () => {
      const { auth, sdk } = await firebaseClient(config);
      const email = $("#email").value.trim(), password = $("#password").value;
      $("#password").value = "";
      if (path === "/recuperar-senha") {
        // Do not reveal account existence, including provider errors.
        await sdk.sendPasswordResetEmail(auth, email, { url: `${location.origin}/entrar` }).catch(() => {});
        message("Se houver uma conta para este e-mail, você receberá as instruções."); return;
      }
      const result = path === "/criar-conta"
        ? await sdk.createUserWithEmailAndPassword(auth, email, password)
        : await sdk.signInWithEmailAndPassword(auth, email, password);
      if (!result.user.emailVerified) await sdk.sendEmailVerification(result.user, { url: `${location.origin}/confirmar-email` });
      await finish(result.user);
    });
  });
  $("#google").addEventListener("click", () => action(async () => {
    const { auth, sdk } = await firebaseClient(config);
    await finish((await sdk.signInWithPopup(auth, provider(sdk))).user);
  }));
  $("#verified").addEventListener("click", () => action(async () => {
    if (!memoryUser) { location.replace("/entrar"); return; }
    const { sdk } = await firebaseClient(config); await sdk.reload(memoryUser);
    if (!memoryUser.emailVerified) throw new Error("A confirmação ainda não foi concluída. Verifique sua caixa de entrada.");
    await finish(memoryUser);
  }));
  $("#resend").addEventListener("click", () => action(async () => {
    if (!memoryUser) { location.replace("/entrar"); return; }
    const { sdk } = await firebaseClient(config);
    await sdk.sendEmailVerification(memoryUser, { url: `${location.origin}/confirmar-email` });
    message("Mensagem enviada. Confira também a pasta de spam.");
  }));
}
action(initialize);
