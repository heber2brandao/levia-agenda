import type { CSSProperties } from "react";

export type Appearance = { primary: string; background: string; logo: string | null };
export const defaultAppearance: Appearance = {
  primary: "#9a746d", background: "#f7f3ef", logo: null,
};

// Relative sRGB luminance. Choose the better of black/white for readable text.
function luminance(hex: string) {
  const channels = hex.slice(1).match(/../g)!.map(value => {
    const n = parseInt(value, 16) / 255;
    return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}
function readableText(hex: string) {
  return luminance(hex) > 0.179 ? "#000000" : "#ffffff";
}
export function appearanceStyle(appearance: Appearance): CSSProperties {
  const primary = /^#[0-9a-f]{6}$/i.test(appearance.primary) ? appearance.primary : defaultAppearance.primary;
  const background = /^#[0-9a-f]{6}$/i.test(appearance.background) ? appearance.background : defaultAppearance.background;
  return {
    "--brand-primary": primary,
    "--brand-on-primary": readableText(primary),
    "--brand-background": background,
    "--brand-text": readableText(background),
  } as CSSProperties;
}

export async function readLogo(file: File): Promise<string> {
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
    throw new Error("Escolha uma imagem PNG, JPG ou WebP.");
  }
  if (file.size > 2 * 1024 * 1024) throw new Error("A logo deve ter no máximo 2 MB.");
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    if (!img.naturalWidth || !img.naturalHeight || img.naturalWidth > 4096 || img.naturalHeight > 4096) {
      throw new Error("Use uma imagem com até 4096 × 4096 pixels.");
    }
    const ratio = Math.min(1, 512 / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(img.naturalWidth * ratio));
    canvas.height = Math.max(1, Math.round(img.naturalHeight * ratio));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Não foi possível preparar a logo neste navegador.");
    context.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } catch (error) {
    if (error instanceof DOMException) throw new Error("Não foi possível ler a imagem. Escolha outro arquivo.");
    throw error;
  } finally {
    URL.revokeObjectURL(url);
  }
}
