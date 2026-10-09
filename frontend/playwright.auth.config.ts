import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests-auth",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5176" },
  webServer: {
    command: "npm.cmd run dev -- --port 5176 --strictPort",
    url: "http://127.0.0.1:5176",
    reuseExistingServer: false,
    env: {
      VITE_DEMO_MODE: "false",
      VITE_SUPABASE_URL: "https://auth.levia.test",
      VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_local_browser_test",
    },
  },
});
