import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import BookingCalendar from "./components/BookingCalendar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { money } from "./demo";
import { addDays, businessRequest, clock, localDay, type Offer } from "./lib/business";

export default function BookingForm({
  offers,
  zone,
  base,
  token,
  onSaved,
}: {
  offers: Offer[];
  zone: string;
  base: string;
  token?: string;
  onSaved?: (day: string) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]),
    [day, setDay] = useState(localDay(zone));
  const [slots, setSlots] = useState<
      { starts_at: string; ends_at: string }[] | null
    >(null),
    [start, setStart] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [receipt, setReceipt] = useState<{
      id: string;
      starts_at: string;
      price_cents: number;
    } | null>(null);
  const requestKey = useRef(crypto.randomUUID());
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const chosen = offers.filter((o) => selected.includes(o.id));
  const today = localDay(zone);
  const duration = chosen.reduce((n, s) => n + s.duration_minutes, 0);
  function invalidate() {
    controller.current?.abort();
    setBusy(false);
    setSlots(null);
    setStart("");
    setError("");
    requestKey.current = crypto.randomUUID();
  }
  const loadSlots = useCallback(async () => {
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setStart("");
    setSlots(null);
    try {
      const data = await businessRequest<{
        slots: { starts_at: string; ends_at: string }[];
      }>(
        base + "/availability",
        token,
        { day, service_ids: selected },
        "POST",
        abort.signal,
      );
      if (!abort.signal.aborted) setSlots(data.slots);
    } catch (e) {
      if (!abort.signal.aborted) setError((e as Error).message);
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }, [base, token, day, selected]);
  useEffect(() => {
    if (selected.length && selected.length <= 10 && duration <= 480 && !receipt) {
      void loadSlots();
    }
    return () => controller.current?.abort();
  }, [loadSlots, selected.length, duration, receipt]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    try {
      const result = await businessRequest<{
        id: string;
        starts_at: string;
        price_cents: number;
      }>(
        base + "/appointments",
        token,
        {
          day,
          starts_at: start,
          service_ids: selected,
          name: form.get("name"),
          phone: String(form.get("phone")).replace(/\D/g, ""),
          email: form.get("email") || null,
          invites_allowed: form.get("consent") === "on",
          request_key: requestKey.current,
        },
        "POST",
        abort.signal,
      );
      if (!abort.signal.aborted) {
        setReceipt(result);
        onSaved?.(day);
      }
    } catch (e) {
      if (!abort.signal.aborted) setError((e as Error).message);
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  if (receipt)
    return (
      <div role="status" className="notice">
        <h2>Agendamento registrado!</h2>
        <p>
          {day.split("-").reverse().join("/")} às{" "}
          {clock(receipt.starts_at, zone)} · {money(receipt.price_cents / 100)}
        </p>
        <p>
          Seu pedido já aparece na agenda da profissional. Se você informou e-mail,
          os avisos dependem do serviço de envio estar ativo. O WhatsApp é manual.
        </p>
        <Button
          type="button"
          onClick={() => {
            setReceipt(null);
            invalidate();
          }}
        >
          Novo agendamento
        </Button>
      </div>
    );
  return (
    <section className="booking-form">
      <h2>Escolha um ou mais serviços</h2>
      <div className="service-grid">
        {offers.map((o) => (
          <button
            type="button"
            disabled={busy}
            className={`service-choice ${selected.includes(o.id) ? "selected" : ""}`}
            aria-pressed={selected.includes(o.id)}
            key={o.id}
            onClick={() => {
              invalidate();
              setSelected((ids) =>
                ids.includes(o.id)
                  ? ids.filter((id) => id !== o.id)
                  : [...ids, o.id],
              );
            }}
          >
            <span>
              <strong>{o.name}</strong>
              <small>{o.duration_minutes} min</small>
            </span>
            <b>{money(o.price_cents / 100)}</b>
          </button>
        ))}
      </div>
      {!offers.length && <p>Nenhum serviço ativo no momento.</p>}
      <p>
        {chosen.reduce((n, s) => n + s.duration_minutes, 0)} minutos ·{" "}
        {money(chosen.reduce((n, s) => n + s.price_cents, 0) / 100)}
      </p>
      <h2>Escolha o dia</h2>
      <BookingCalendar value={day} min={today} max={addDays(today, 90)} disabled={busy}
        onChange={(value) => { if (value !== day) { invalidate(); setDay(value); } }} />
      <h2>Escolha o horário</h2>
      <p className="muted">{day.split("-").reverse().join("/")} · Horário local do espaço</p>
      {!selected.length && <p>Selecione um serviço para ver os horários.</p>}
      {(selected.length > 10 || duration > 480) && <p role="alert">Escolha até 10 serviços e 480 minutos por atendimento.</p>}
      {busy && !start && <p role="status">Buscando horários…</p>}
      {slots && (
        <div className="actions">
          {slots.length ? (
            slots.map((s) => (
              <Button
                type="button"
                disabled={busy}
                key={s.starts_at}
                aria-pressed={start === s.starts_at}
                aria-label={`${clock(s.starts_at, zone)} – ${clock(s.ends_at, zone)}`}
                variant={start === s.starts_at ? "default" : "outline"}
                onClick={() => {
                  setStart(s.starts_at);
                  requestKey.current = crypto.randomUUID();
                }}
              >
                {clock(s.starts_at, zone)}
              </Button>
            ))
          ) : (
            <p>Não há horários disponíveis neste dia. Escolha outra data.</p>
          )}
        </div>
      )}
      {start && (
        <form onSubmit={save}>
          <fieldset disabled={busy}>
            <div className="form-grid">
              <label className="field">
                Nome da cliente
                <Input name="name" required maxLength={100} />
              </label>
              <label className="field">
                Telefone com DDD
                <Input
                  name="phone"
                  type="tel"
                  required
                  pattern="[0-9 ()+\-]{10,22}"
                />
              </label>
              <label className="field">
                E-mail (opcional)
                <Input name="email" type="email" />
              </label>
            </div>
            <label className="consent">
              <input name="consent" type="checkbox" />{" "}
              {token
                ? "A cliente autorizou convites futuros para retorno."
                : "Autorizo convites futuros para retorno (opcional)."}
            </label>
            <p className="muted">
              Nome e telefone serão usados para organizar este atendimento. A
              autorização para convites pode ser revogada com a profissional.
            </p>
            <Button type="submit">
              {busy ? "Salvando…" : "Confirmar agendamento"}
            </Button>
          </fieldset>
        </form>
      )}
      {error && (
        <div><p role="alert" className="upload-error">
          {error}
        </p>{!start && selected.length > 0 && selected.length <= 10 && duration <= 480 && <Button type="button" disabled={busy} onClick={() => void loadSlots()}>Tentar novamente</Button>}</div>
      )}
    </section>
  );
}
