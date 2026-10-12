import { test, expect } from "@playwright/test";

test("página pública grava reserva e painel recupera agenda, cliente e faturamento", async ({
  page,
  request,
}, info) => {
  const setup = await (
    await request.get("http://127.0.0.1:8011/__test/session")
  ).json();
  const profile = await (await request.get("http://127.0.0.1:8011/api/v1/me", {
    headers: { Authorization: `Bearer ${setup.session.access_token}` },
  })).json();
  const { id, logo, public_slug, ...profileInput } = profile;
  const savedProfile = await (await request.put("http://127.0.0.1:8011/api/v1/me", {
    headers: { Authorization: `Bearer ${setup.session.access_token}` }, data: profileInput,
  })).json();
  expect(savedProfile.public_slug).toBeTruthy();
  const future = new Date();
  future.setUTCDate(
    future.getUTCDate() + (info.project.name === "mobile" ? 2 : 1),
  );
  const day = future.toISOString().slice(0, 10);
  await page.route("https://auth.levia.test/**", (route) => route.abort());
  await page.goto(`/agendar/${savedProfile.public_slug}`);
  await page.getByRole("button", { name: /Manicure E2E/ }).click();
  const calendar = page.getByRole("region", { name: "Escolha a data" });
  while (!(await calendar.getByRole("button", { name: day.split("-").reverse().join("/"), exact: true }).count())) {
    await calendar.getByRole("button", { name: "Próximo mês" }).click();
  }
  const availabilityRequest = page.waitForRequest((request) =>
    request.url().endsWith("/availability") && request.method() === "POST" && request.postDataJSON().day === day,
  );
  await calendar.getByRole("button", { name: day.split("-").reverse().join("/"), exact: true }).click();
  expect((await availabilityRequest).postDataJSON().day).toBe(day);
  await page
    .getByRole("button", { name: "09:00 – 09:45", exact: true })
    .click();
  await page.getByLabel("Nome da cliente").fill(`Cliente ${info.project.name}`);
  const chosenSlot = page.getByRole("button", { name: "09:00 – 09:45", exact: true });
  await expect(chosenSlot).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("status")).toContainText(
    `Horário escolhido: ${day.split("-").reverse().join("/")} às 09:00`,
  );
  // Selection must stay visible after focus leaves the time button on mobile.
  await expect(chosenSlot).toHaveCSS("outline-style", "solid");
  await expect(chosenSlot).toHaveCSS("outline-width", "2px");
  await page.screenshot({ path: `test-results/selected-time-${info.project.name}.png`, fullPage: true });
  await page
    .getByLabel("Telefone com DDD")
    .fill(info.project.name === "mobile" ? "65977777777" : "65966666666");
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await expect(
    page.getByText("Agendamento registrado!", { exact: true }),
  ).toBeVisible();
  await page.addInitScript((session) => {
    sessionStorage.setItem("sb-auth-auth-token", JSON.stringify(session));
  }, setup.session);
  await page.goto("/conta");
  await expect(
    page.getByRole("heading", { name: /Olá, Profissional/ }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Próximos agendamentos" })).toBeVisible();
  await expect(page.getByText(`Cliente ${info.project.name}`, { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Avisos/ })).toBeVisible();
  await expect(page.getByText("Novo agendamento", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Marcar como lido" }).first().click();
  await page.getByText("E-mails e franquia mensal", { exact: true }).click();
  await expect(page.getByText(/Envios desativados/)).toBeVisible();
  await page.getByRole("link", { name: "Agenda", exact: true }).click();
  await page.getByLabel("Data", { exact: true }).fill(day);
  await expect(
    page.getByText(`Cliente ${info.project.name}`, { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByLabel("Data", { exact: true }).fill(day);
  await expect(
    page.getByText(`Cliente ${info.project.name}`, { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByText("Confirmado", { exact: true })).toBeVisible();
  const clientRequests: string[] = [];
  const trackClientRequests = (request: import("@playwright/test").Request) => {
    clientRequests.push(new URL(request.url()).pathname);
  };
  page.on("request", trackClientRequests);
  await page.getByRole("link", { name: "Clientes", exact: true }).click();
  const card = page
    .locator('[data-slot="card"]')
    .filter({
      has: page.getByRole("heading", {
        name: `Cliente ${info.project.name}`,
        exact: true,
      }),
    });
  await card.getByRole("button", { name: "Ver histórico" }).click();
  page.off("request", trackClientRequests);
  expect(clientRequests).not.toContain("/api/v1/me/dashboard");
  expect(clientRequests).not.toContain("/api/v1/me/appointments");
  expect(clientRequests).not.toContain("/api/v1/me/services");
  await expect(
    page.getByRole("heading", {
      name: `Histórico de Cliente ${info.project.name}`,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Faturamento", exact: true }).click();
  await expect(
    page.getByText("Atendimentos concluídos no mês", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("R$ 35,00", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Visão geral", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: /Olá, Profissional/ }),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/dashboard-${info.project.name}.png`,
    fullPage: true,
  });
});
