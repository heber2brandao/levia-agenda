import { test, expect } from "@playwright/test";

test("profile cache expires, isolates sessions and invalidates edits", async ({ page }) => {
  let reads = 0;
  await page.route("**/api/v1/me", async route => {
    if (route.request().method() === "GET") reads++;
    await route.fulfill({ json: { name: "Perfil de teste", logo: null } });
  });
  await page.route("**/api/v1/me/logo", route => route.fulfill({ json: { logo: null } }));
  await page.goto("/conta");
  const result = await page.evaluate(async () => {
    const modulePath = "/src/lib/api.ts";
    const api = await import(/* @vite-ignore */ modulePath);
    const signal = new AbortController().signal;
    const first = await api.profileRequest("session-a", signal);
    first.name = "Mutated locally";
    const cached = await api.profileRequest("session-a", signal);
    await api.profileRequest("session-b", signal);
    await api.profileRequest("session-a", signal);
    const now = Date.now;
    Date.now = () => now() + 31_000;
    await api.profileRequest("session-a", signal);
    Date.now = now;
    await api.profileRequest("session-a", signal, { ...api.emptyProfile, name: "Edited" });
    await api.profileRequest("session-a", signal);
    await api.logoRequest("session-a", signal);
    await api.profileRequest("session-a", signal);
    const aborted = new AbortController();
    aborted.abort();
    let rejected = false;
    try { await api.profileRequest("session-a", aborted.signal); } catch { rejected = true; }
    return { name: cached.name, rejected };
  });
  expect(result).toEqual({ name: "Perfil de teste", rejected: true });
  expect(reads).toBe(5);
});
