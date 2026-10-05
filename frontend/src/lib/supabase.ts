import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL?.trim() ?? "";
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
// Never initialize a client with a privileged key, even by configuration mistake.
export const supabase =
  /^https:\/\/[^/]+$/.test(url) && key.startsWith("sb_publishable_")
    ? createClient(url, key, {
        auth: {
          storage: window.sessionStorage,
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          flowType: "pkce",
        },
      })
    : null;
