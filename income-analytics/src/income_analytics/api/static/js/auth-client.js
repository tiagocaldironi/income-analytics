// Only the HttpOnly backend cookie persists. Firebase credentials stay in memory.
let csrf = null;
let clientPromise = null;
export async function authRequest(path, options = {}) {
  const method = options.method || "GET";
  const headers = new Headers(options.headers || {});
  if (method !== "GET") {
    if (!csrf) await refreshCsrf();
    headers.set("X-CSRF-Token", csrf);
    if (options.body) headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/api/auth${path}`, {
    ...options, method, headers, credentials: "same-origin", cache: "no-store",
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof body.detail === "string" ? body.detail : "Não foi possível concluir. Tente novamente.");
    error.status = response.status;
    throw error;
  }
  return body;
}
export async function refreshCsrf() {
  const result = await authRequest("/csrf");
  csrf = result.csrf_token;
  return csrf;
}
export async function firebaseClient(config) {
  if (!clientPromise) clientPromise = (async () => {
    const [{ initializeApp }, sdk] = await Promise.all([
      import("https://www.gstatic.com/firebasejs/13.1.0/firebase-app.js"),
      import("https://www.gstatic.com/firebasejs/13.1.0/firebase-auth.js"),
    ]);
    const auth = sdk.initializeAuth(initializeApp(config.firebase), {
      persistence: sdk.inMemoryPersistence,
      popupRedirectResolver: sdk.browserPopupRedirectResolver,
    });
    if (config.emulator) sdk.connectAuthEmulator(auth, `http://${config.emulator}`);
    return { auth, sdk };
  })();
  return clientPromise;
}
export function clearPrivateBrowserState() {
  localStorage.removeItem("income.activePortfolioId");
  sessionStorage.removeItem("income.userId");
  localStorage.removeItem("income.authUser");
  if (typeof BroadcastChannel !== "undefined") {
    const channel = new BroadcastChannel("income-auth");
    channel.postMessage("signed-out");
    channel.close();
  }
}
export async function exchangeSession(user) {
  const token = await user.getIdToken(true);
  const result = await authRequest("/session", {
    method: "POST", body: JSON.stringify({ id_token: token }),
  });
  await refreshCsrf();
  localStorage.removeItem("income.activePortfolioId");
  sessionStorage.setItem("income.userId", result.user_id);
  localStorage.setItem("income.authUser", result.user_id);
  return result;
}
export async function signOutDevice() {
  await authRequest("/logout", { method: "POST" });
  clearPrivateBrowserState();
  location.replace("/entrar");
}
