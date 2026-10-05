export type WorkingPeriod = {
  weekday: number;
  starts_at: string;
  ends_at: string;
};
export type AccountProfile = {
  id?: string;
  logo: string | null;
  name: string;
  studio_name: string;
  phone: string;
  email: string | null;
  specialties: string[];
  timezone: string;
  primary_color: string;
  background_color: string;
  working_periods: WorkingPeriod[];
};
export const emptyProfile: AccountProfile = {
  logo: null,
  name: "",
  studio_name: "",
  phone: "",
  email: null,
  specialties: [],
  timezone: "America/Cuiaba",
  primary_color: "#9a746d",
  background_color: "#f7f3ef",
  working_periods: [],
};
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function profileRequest(
  token: string,
  signal: AbortSignal,
  profile?: AccountProfile,
): Promise<AccountProfile> {
  const base = (
    import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const url = new URL(base);
  if (
    url.protocol !== "https:" &&
    !(
      url.protocol === "http:" &&
      ["localhost", "127.0.0.1"].includes(url.hostname)
    )
  ) {
    throw new Error("A conexão da API precisa usar HTTPS.");
  }
  const response = await fetch(base + "/me", {
    method: profile ? "PUT" : "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(profile ? { "Content-Type": "application/json" } : {}),
    },
    body: profile
      ? JSON.stringify(profile, (key, value) =>
          key === "logo" || key === "id" ? undefined : value,
        )
      : undefined,
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Sua sessão expirou. Saia e entre novamente.",
      404: "Complete seu cadastro.",
      422: "Confira telefone, especialidades e horários. Os períodos não podem se sobrepor.",
      429: "Muitas tentativas. Aguarde um minuto.",
      503: "O serviço está indisponível. Tente novamente mais tarde.",
    };
    throw new ApiError(
      response.status,
      messages[response.status] ?? "Não foi possível salvar seus dados.",
    );
  }
  return response.json();
}

export async function logoRequest(
  token: string,
  signal: AbortSignal,
  file?: File,
): Promise<{ logo: string | null }> {
  const base = (
    import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"
  ).replace(/\/$/, "");
  const url = new URL(base);
  if (
    url.protocol !== "https:" &&
    !(
      url.protocol === "http:" &&
      ["localhost", "127.0.0.1"].includes(url.hostname)
    )
  )
    throw new Error("A API precisa usar HTTPS.");
  const response = await fetch(base + "/me/logo", {
    method: file ? "PUT" : "DELETE",
    signal,
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(file ? { "Content-Type": "application/octet-stream" } : {}),
    },
    body: file,
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Entre novamente na sua conta.",
      404: "Salve seu perfil antes de adicionar a logo.",
      413: "Escolha uma imagem de até 2 MB.",
      422: "Use uma imagem estática PNG, JPG ou WebP, de até 4096 × 4096 pixels.",
      429: "Aguarde um minuto antes de tentar novamente.",
    };
    throw new Error(
      messages[response.status] ??
        "Não foi possível salvar a logo. Tente novamente.",
    );
  }
  return response.json();
}
