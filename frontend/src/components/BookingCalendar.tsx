import { useState } from "react";
import { addDays } from "../lib/business";

export default function BookingCalendar({ value, min, max, onChange, disabled }: {
  value: string; min: string; max: string; onChange: (day: string) => void; disabled?: boolean;
}) {
  const [month, setMonth] = useState(value.slice(0, 7) + "-01");
  const first = new Date(month + "T12:00:00Z");
  const start = addDays(month, -first.getUTCDay());
  function shift(amount: number) {
    const date = new Date(first);
    date.setUTCMonth(date.getUTCMonth() + amount);
    setMonth(date.toISOString().slice(0, 10));
  }
  function choose(day: string) {
    setMonth(day.slice(0, 7) + "-01");
    onChange(day);
  }
  return <section className="booking-calendar" aria-label="Escolha a data">
    <div className="actions">
      <button type="button" disabled={disabled} onClick={() => choose(min)}>Hoje</button>
      <button type="button" disabled={disabled} onClick={() => choose(addDays(min, 1))}>Amanhã</button>
    </div>
    <div className="calendar-heading">
      <button type="button" aria-label="Mês anterior" disabled={disabled || month.slice(0, 7) <= min.slice(0, 7)} onClick={() => shift(-1)}>‹</button>
      <strong aria-live="polite">{first.toLocaleDateString("pt-BR", {month: "long", year: "numeric", timeZone: "UTC"})}</strong>
      <button type="button" aria-label="Próximo mês" disabled={disabled || month.slice(0, 7) >= max.slice(0, 7)} onClick={() => shift(1)}>›</button>
    </div>
    <div className="calendar-days">
      {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map(d => <small key={d}>{d}</small>)}
      {Array.from({length: 42}, (_, i) => addDays(start, i)).map(day => day.slice(0, 7) !== month.slice(0, 7)
        ? <span key={day} />
        : <button key={day} type="button" aria-label={day.split("-").reverse().join("/")} aria-pressed={day === value}
          disabled={disabled || day < min || day > max} onClick={() => choose(day)}>{Number(day.slice(-2))}</button>)}
    </div>
  </section>;
}
