import { test, expect } from '@playwright/test';

test('personalização local, logo, contraste e restauração', async ({ page }) => {
  await page.goto('/perfil');
  await page.getByLabel('Nome do espaço', { exact: true }).fill('  Studio Bela Flor  ');
  await page.getByRole('button', { name: 'Salvar nome do espaço' }).click();
  await expect(page.locator('.topbar')).toContainText('Studio Bela Flor');
  await expect(page.getByRole('heading', { name: 'Studio Bela Flor' })).toBeVisible();
  await page.getByLabel('Cor principal', { exact: true }).fill('#ffff00');
  await page.getByLabel('Cor de fundo', { exact: true }).fill('#111111');
  const preview = page.getByLabel('Prévia da página pública');
  await expect(preview).toHaveCSS('background-color', 'rgb(17, 17, 17)');
  await expect(preview).toHaveCSS('color', 'rgb(255, 255, 255)');
  await page.getByLabel('Logo do espaço', { exact: true }).setInputFiles({
    name: 'logo.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>'),
  });
  await expect(page.getByRole('alert')).toContainText('PNG, JPG ou WebP');
  const png = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 80; canvas.height = 40;
    const context = canvas.getContext('2d')!; context.fillStyle = '#660099'; context.fillRect(0,0,80,40);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  await page.getByLabel('Logo do espaço', { exact: true }).setInputFiles({ name: 'logo.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
  await expect(page.getByRole('img', { name: /^Logo de / })).toBeVisible();
  await page.getByRole('link', { name: 'Ver página personalizada' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Studio Bela Flor' })).toBeVisible();
  await expect(page.getByRole('img', { name: /^Logo de / })).toBeVisible();
  await expect(page.locator('.public-page')).toHaveCSS('background-color', 'rgb(17, 17, 17)');
  await page.getByRole('button', { name: /^Manicure/ }).click();
  await expect(page.getByRole('button', { name: /^Manicure/ })).toHaveCSS('color', 'rgb(0, 0, 0)');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('link', { name: /Voltar ao painel/ }).click();
  await expect(page.locator('.sidebar')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await page.getByRole('link', { name: 'Meu espaço' }).click();
  await expect(page.getByLabel('Nome do espaço', { exact: true })).toHaveValue('Studio Bela Flor');
  await page.getByLabel('Nome do espaço', { exact: true }).fill('   ');
  await page.getByRole('button', { name: 'Salvar nome do espaço' }).click();
  await expect(page.getByRole('alert')).toContainText('Informe o nome');
  await expect(page.locator('.topbar')).toContainText('Studio Bela Flor');
  await page.getByRole('button', { name: 'Remover logo' }).click();
  await expect(page.getByRole('img', { name: /^Logo de / })).toHaveCount(0);
  await page.getByRole('button', { name: 'Restaurar padrão' }).click();
  await expect(page.getByLabel('Cor principal', { exact: true })).toHaveValue('#9a746d');
  await expect(page.getByLabel('Cor de fundo', { exact: true })).toHaveValue('#f7f3ef');
  await page.getByLabel('Cor principal', { exact: true }).fill('#123456');
  await page.reload();
  await expect(page.getByLabel('Nome do espaço', { exact: true })).toHaveValue('Ateliê Ana Oliveira');
  await expect(page.getByLabel('Cor principal', { exact: true })).toHaveValue('#9a746d');
});

