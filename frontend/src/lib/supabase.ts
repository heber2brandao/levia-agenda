import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL?.trim() ?? "";
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
// Email links open another tab. Share only short-lived PKCE material; keep
// access/refresh tokens in sessionStorage, as before.
const authStorage = {
  getItem(name: string) {
    if (!name.endsWith("-code-verifier")) return sessionStorage.getItem(name);
    const raw = localStorage.getItem(name);
    if (!raw) return sessionStorage.getItem(name);
    try {
      const entry = JSON.parse(raw);
      if (entry.expires > Date.now() && typeof entry.value === "string") return entry.value;
    } catch { /* Discard invalid or obsolete verifier data. */ }
    localStorage.removeItem(name);
    return null;
  },
  setItem(name: string, value: string) {
    if (name.endsWith("-code-verifier")) {
      localStorage.setItem(name, JSON.stringify({ value, expires: Date.now() + 60 * 60 * 1000 }));
    } else sessionStorage.setItem(name, value);
  },
  removeItem(name: string) {
    sessionStorage.removeItem(name);
    if (name.endsWith("-code-verifier")) localStorage.removeItem(name);
  },
};
const callbackParams = new URLSearchParams(location.search);
const callbackHash = new URLSearchParams(location.hash.slice(1));
export const hadAuthCallback = callbackParams.has("code") || callbackHash.has("error") || callbackHash.has("access_token");
const recoveryKey = "levia:password-recovery-user";
export const isRecoveringUser = (id: string) => sessionStorage.getItem(recoveryKey) === id;
export const finishRecovery = () => sessionStorage.removeItem(recoveryKey);
// Never initialize a client with a privileged key, even by configuration mistake.
export const supabase =
  /^https:\/\/[^/]+$/.test(url) && key.startsWith("sb_publishable_")
    ? createClient(url, key, {
        auth: {
          storage: authStorage,
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          flowType: "pkce",
        },
      })
    : null;

// Subscribe before React's lazy account screen loads, so the one-time event
// isn't lost. This marker controls UI only; updateUser still requires auth.
supabase?.auth.onAuthStateChange((event, session) => {
  if (event === "PASSWORD_RECOVERY" && session) {
    sessionStorage.setItem(recoveryKey, session.user.id);
  } else if (event === "SIGNED_OUT") finishRecovery();
});
