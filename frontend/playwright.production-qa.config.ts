import { defineConfig, devices } from "@playwright/test";

// Read-only smoke checks. Never submit bookings or credentials to production.
export default defineConfig({
  testDir: "./tests-production-qa",
  workers: 1,
  timeout: 90000,
  expect: { timeout: 60000 },
  use: { baseURL: "https://levia-agenda-app.onrender.com", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" } },
  ],
});
