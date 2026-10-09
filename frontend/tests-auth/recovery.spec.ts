import { test, expect } from "@playwright/test";

test("email opened in another tab reaches new password and survives reload", async ({ page, context }) => {
  let callback = "";
  let challenge = "";
  const user = { id: "00000000-0000-4000-8000-000000000001", aud: "authenticated", email: "test@example.test", app_metadata: {}, user_metadata: {}, created_at: new Date().toISOString() };
  await context.route("https://auth.levia.test/**", async route => {
    const req = route.request();
    if (req.url().includes("/recover")) {
      callback = new URL(req.url()).searchParams.get("redirect_to")!;
      challenge = req.postDataJSON().code_challenge;
      await route.fulfill({ json: {} });
    } else if (req.url().includes("/token")) {
      const verifier = req.postDataJSON().code_verifier;
      const { createHash } = await import("node:crypto");
      expect(createHash("sha256").update(verifier).digest("base64url")).toBe(challenge);
      await route.fulfill({ json: { access_token: "test-token", refresh_token: "test-refresh", token_type: "bearer", expires_in: 3600, user } });
    } else if (req.url().includes("/user")) {
      await route.fulfill({ json: user });
    } else await route.abort();
  });
  await page.goto("/conta");
  await page.getByRole("button", { name: "Esqueci minha senha" }).click();
  await page.getByLabel("E-mail", { exact: true }).fill(user.email);
  await page.getByRole("button", { name: "Solicitar recuperação" }).click();
  await expect(page.getByRole("status")).toBeVisible();
  const other = await context.newPage();
  const target = new URL(callback);
  target.searchParams.set("code", "test-code");
  await other.goto(target.href);
  await expect(other.getByRole("heading", { name: "Nova senha" })).toBeVisible();
  await other.reload();
  await expect(other.getByRole("heading", { name: "Nova senha" })).toBeVisible();
  expect(await other.evaluate(() => Object.values(localStorage).some(v => v.includes("test-refresh")))).toBe(false);
  // Supabase broadcasts recovery to other open tabs in the same browser.
  await expect(page.getByRole("heading", { name: "Nova senha" })).toBeVisible();
});

test("callback without verifier gives actionable feedback, never a new password form", async ({ page, context }) => {
  await context.route("https://auth.levia.test/**", route => route.abort());
  await page.goto("/conta?code=expired-or-other-browser");
  await expect(page.getByRole("alert")).toContainText("Solicite uma nova recuperação");
  await expect(page.getByRole("heading", { name: "Nova senha" })).toHaveCount(0);
});
