import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests-business",
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:5175", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command:
        '"..\\.venv\\Scripts\\python.exe" "..\\scripts\\business_e2e_server.py"',
      url: "http://127.0.0.1:8011/api/v1/health",
      reuseExistingServer: false,
    },
    {
      command: "npm.cmd run dev -- --port 5175 --strictPort",
      url: "http://127.0.0.1:5175",
      reuseExistingServer: false,
      env: {
        VITE_DEMO_MODE: "false",
        VITE_API_URL: "http://127.0.0.1:8011/api/v1",
        VITE_SUPABASE_URL: "https://auth.levia.test",
        VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_local_browser_test",
      },
    },
  ],
});
