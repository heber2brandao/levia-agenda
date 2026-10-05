import { ApiError } from "./api";

export type CatalogService = {
  id: string;
  name: string;
  price_cents: number;
  duration_minutes: number;
  return_days: number | null;
  active: boolean;
};
export type Suggestion = Pick<
  CatalogService,
  "name" | "duration_minutes" | "return_days"
> & { specialty: string };
export type Availability = {
  day: string;
  timezone: string;
  duration_minutes: number;
  price_cents: number;
  slots: { starts_at: string; ends_at: string }[];
};

export async function catalogRequest<T>(
  token: string,
  path: string,
  signal: AbortSignal,
  body?: unknown,
  method = "POST",
): Promise<T> {
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
    throw new Error("A conexão da API precisa usar HTTPS.");
  const response = await fetch(base + "/me" + path, {
    method: body === undefined ? "GET" : method,
    signal,
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Sua sessão expirou. Saia e entre novamente.",
      404: "Perfil ou serviço não encontrado. Salve seu perfil e atualize o catálogo.",
      409: "Limite de 500 serviços no catálogo atingido.",
      422: "Confira os dados: selecione até 10 serviços, no máximo 480 minutos, e uma data nos próximos 90 dias.",
      429: "Muitas consultas. Aguarde um minuto.",
    };
    throw new ApiError(
      response.status,
      messages[response.status] ?? "Serviço indisponível. Tente novamente.",
    );
  }
  return response.json();
}

export async function loadCatalog(token: string, signal: AbortSignal) {
  const first = await catalogRequest<{
    items: CatalogService[];
    total: number;
  }>(token, "/services", signal);
  const rest = await Promise.all(
    Array.from({ length: Math.ceil(first.total / 100) - 1 }, (_, i) =>
      catalogRequest<{ items: CatalogService[] }>(
        token,
        `/services?offset=${(i + 1) * 100}`,
        signal,
      ),
    ),
  );
  return [...first.items, ...rest.flatMap((page) => page.items)];
}
