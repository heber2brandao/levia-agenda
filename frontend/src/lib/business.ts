export type Appointment = {
  id: string;
  starts_at: string;
  ends_at: string;
  kind: string;
  status: string;
  price_cents: number;
  services: { id: string; name: string; duration_minutes: number }[];
  client_id: string | null;
  client_name: string;
  phone: string | null;
  return_date: string | null;
};
export type Customer = {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  invites_allowed: boolean;
};
export type Summary = {
  day: string;
  timezone: string;
  appointments_today: number;
  expected_cents: number;
  completed_month_cents: number;
  returns_due: number;
  clients: number;
};
export type Offer = {
  id: string;
  name: string;
  price_cents: number;
  duration_minutes: number;
};

export async function businessRequest<T>(
  path: string,
  token?: string,
  body?: unknown,
  method = "POST",
  signal?: AbortSignal,
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
    throw new Error("A API precisa usar HTTPS.");
  const response = await fetch(base + path, {
    method: body === undefined ? "GET" : method,
    signal,
    cache: "no-store",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let message = "Não foi possível concluir. Tente novamente.";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      /* generic error */
    }
    throw new Error(message);
  }
  return response.json();
}
export function localDay(zone: string, instant = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(instant);
}

export async function loadAppointments(
  start: string,
  end: string,
  token: string,
  signal: AbortSignal,
) {
  const items: Appointment[] = [];
  let more = true;
  while (more) {
    const page = await businessRequest<{
      items: Appointment[];
      has_more: boolean;
    }>(
      `/me/appointments?start=${start}&end=${end}&offset=${items.length}`,
      token,
      undefined,
      "GET",
      signal,
    );
    items.push(...page.items);
    more = page.has_more && page.items.length > 0;
  }
  return { items };
}
export function addDays(day: string, amount: number) {
  const d = new Date(day + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + amount);
  return d.toISOString().slice(0, 10);
}
export function clock(instant: string, zone: string) {
  return new Date(instant).toLocaleTimeString("pt-BR", {
    timeZone: zone,
    hour: "2-digit",
    minute: "2-digit",
  });
}
export function dateLabel(day: string) {
  return new Date(day + "T12:00:00Z").toLocaleDateString("pt-BR", {
    timeZone: "UTC",
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}
export function zonedInstant(value: string, zone: string) {
  const target = Date.parse(value + ":00Z");
  let candidate = target;
  for (let i = 0; i < 3; i++) {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: zone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(new Date(candidate));
    const get = (type: string) => parts.find((p) => p.type === type)?.value;
    const displayed = Date.parse(
      `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}:00Z`,
    );
    if (displayed === target) return new Date(candidate).toISOString();
    candidate += target - displayed;
  }
  throw new Error("Horário inválido no fuso do espaço.");
}
