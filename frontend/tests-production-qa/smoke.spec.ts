import { test, expect } from "@playwright/test";

test("produção: login, reserva pública, logo e layout sem enviar dados", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/conta");
  await expect(page.getByRole("heading", { name: "Entre no seu espaço" })).toBeVisible();
  await expect(page.getByLabel("E-mail", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("login.png"), fullPage: true });
  await page.goto("/agendar/barber-heber");
  await expect(page.getByRole("heading", { name: "Barber Heber", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Escolha um ou mais serviços" })).toBeVisible();
  const logo = page.getByRole("img", { name: /Logo de/ });
  if (await logo.count()) {
    await expect(logo).toHaveCSS("border-radius", "50%");
    await expect(logo).toHaveCSS("object-fit", "cover");
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("public-booking.png"), fullPage: true });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Barber Heber", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("produção: API protege dados e valida CORS", async ({ request }) => {
  const api = "https://levia-api.onrender.com";
  expect((await request.get(`${api}/api/v1/ready`)).status()).toBe(200);
  for (const path of ["me", "me/clients", "me/appointments", "me/dashboard"]) {
    expect((await request.get(`${api}/api/v1/${path}`)).status()).toBe(401);
  }
  expect((await request.get(`${api}/openapi.json`)).status()).toBe(404);
  for (const origin of ["https://levia-agenda-app.onrender.com", "https://levia-agenda-heber.onrender.com"]) {
    const response = await request.fetch(`${api}/api/v1/me`, { method: "OPTIONS", headers: {
      Origin: origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization",
    } });
    expect(response.status()).toBe(200);
    expect(response.headers()["access-control-allow-origin"]).toBe(origin);
  }
  const blocked = await request.fetch(`${api}/api/v1/me`, { method: "OPTIONS", headers: {
    Origin: "https://untrusted.example", "Access-Control-Request-Method": "GET",
  } });
  expect(blocked.headers()["access-control-allow-origin"]).toBeUndefined();
});
