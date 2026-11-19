import { test, expect } from "@playwright/test";

const space = {
  studio_name: "Espaço QA", timezone: "America/Cuiaba", logo: null,
  primary_color: "#9a746d", background_color: "#f7f3ef",
  services: [{ id: "qa-service", name: "Serviço QA", price_cents: 3500, duration_minutes: 45 }],
};

test("espaço inexistente exibe erro sem formulário de reserva", async ({ page }) => {
  await page.route("**/api/v1/public/**", route => route.fulfill({ status: 404, json: { detail: "Espaço não encontrado" } }));
  await page.goto("/agendar/inexistente-qa");
  await expect(page.getByRole("alert")).toContainText("Espaço não encontrado");
  await expect(page.getByRole("button", { name: "Confirmar agendamento" })).toHaveCount(0);
});

test("sem serviços ativos não permite enviar reserva", async ({ page }) => {
  await page.route("**/api/v1/public/**", route => route.fulfill({ json: { ...space, services: [] } }));
  await page.goto("/agendar/qa");
  await expect(page.getByText("Nenhum serviço ativo no momento.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar agendamento" })).toHaveCount(0);
});

test("falha de disponibilidade permite tentar novamente e mostra dia sem horários", async ({ page }) => {
  let failed = false;
  await page.route("**/api/v1/public/**", route => {
    if (route.request().url().endsWith("/availability")) {
      if (!failed) { failed = true; return route.fulfill({ status: 503, json: { detail: "Serviço indisponível" } }); }
      return route.fulfill({ json: { slots: [] } });
    }
    return route.fulfill({ json: space });
  });
  await page.goto("/agendar/qa");
  await page.getByRole("button", { name: /Serviço QA/ }).click();
  await expect(page.getByRole("alert")).toContainText("Serviço indisponível");
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(page.getByText("Não há horários disponíveis neste dia. Escolha outra data.")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("conflito não confirma reserva; reenvio preserva chave e consentimento é opcional", async ({ page }) => {
  const submissions: Record<string, unknown>[] = [];
  await page.route("**/api/v1/public/**", route => {
    if (route.request().url().endsWith("/availability")) {
      const day = route.request().postDataJSON().day;
      return route.fulfill({ json: { slots: [{ starts_at: `${day}T13:00:00Z`, ends_at: `${day}T13:45:00Z` }] } });
    }
    if (route.request().url().endsWith("/appointments")) {
      submissions.push(route.request().postDataJSON());
      return route.fulfill({ status: 409, json: { detail: "Horário ocupado" } });
    }
    return route.fulfill({ json: space });
  });
  await page.goto("/agendar/qa");
  await page.getByRole("button", { name: /Serviço QA/ }).click();
  await page.getByRole("button", { name: "09:00 – 09:45", exact: true }).click();
  await page.getByLabel("Nome da cliente").fill("Cliente QA");
  await page.getByLabel("Telefone com DDD").fill("123");
  expect(await page.getByLabel("Telefone com DDD").evaluate((input: HTMLInputElement) => input.validity.patternMismatch)).toBe(true);
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  expect(submissions).toHaveLength(0);
  await page.getByLabel("Telefone com DDD").fill("(65) 99999-9999");
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await expect(page.getByRole("alert")).toHaveText("Horário ocupado");
  await expect(page.getByText("Agendamento registrado!", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await expect.poll(() => submissions.length).toBe(2);
  expect(submissions[0].request_key).toBe(submissions[1].request_key);
  expect(submissions[0].phone).toBe("65999999999");
  expect(submissions[0].invites_allowed).toBe(false);
  await page.getByRole("button", { name: /Serviço QA/ }).click();
  await expect(page.getByLabel("Nome da cliente")).toHaveCount(0);
});
