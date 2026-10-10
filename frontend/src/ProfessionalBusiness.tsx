import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { Leaf, ArrowUpRight, ChevronRight, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import BookingForm from "./BookingForm";
import NotificationsPanel from "./NotificationsPanel";
import { money } from "./demo";
import { profileRequest, type AccountProfile } from "./lib/api";
import { loadCatalog, type CatalogService } from "./lib/catalog-api";
import {
  businessRequest,
  loadAppointments,
  localDay,
  clock,
  addDays,
  dateLabel,
  zonedInstant,
  type Appointment,
  type Customer,
  type Summary,
} from "./lib/business";

const labels: Record<string, string> = {
  pending: "A confirmar",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled: "Cancelado",
};
function AppointmentRow({
  item,
  zone,
  act,
  move,
}: {
  item: Appointment;
  zone: string;
  act?: (item: Appointment, status: string) => void;
  move?: (item: Appointment) => void;
}) {
  return (
    <div className="real-appointment">
      <div className="appointment">
        <span className="time">{clock(item.starts_at, zone)}</span>
        <div className="appointment-person">
          <strong>{item.client_name}</strong>
          <span>
            {item.services.map((s) => s.name).join(" + ") ||
              "Horário bloqueado"}
          </span>
          <small>
            {clock(item.starts_at, zone)} – {clock(item.ends_at, zone)}{" "}
            {item.kind === "appointment"
              ? `· ${money(item.price_cents / 100)}`
              : ""}
          </small>
        </div>
        <span
          className={`status ${item.status === "confirmed" ? "confirmed" : ""}`}
        >
          {labels[item.status]}
        </span>
      </div>
      {act && !["completed", "cancelled"].includes(item.status) && (
        <div className="actions">
          {item.kind === "appointment" && (
            <>
              {item.status === "pending" && (
                <Button
                  variant="outline"
                  onClick={() => act(item, "confirmed")}
                >
                  Confirmar
                </Button>
              )}
              <Button
                variant="outline"
                disabled={new Date(item.starts_at) > new Date()}
                onClick={() => act(item, "completed")}
              >
                Concluir
              </Button>
              <Button variant="outline" onClick={() => move?.(item)}>
                Reagendar
              </Button>
            </>
          )}
          <Button variant="ghost" onClick={() => act(item, "cancelled")}>
            {item.kind === "block" ? "Liberar horário" : "Cancelar"}
          </Button>
          {item.phone && (
            <a
              href={`https://wa.me/${item.phone.length <= 11 ? "55" : ""}${item.phone}?text=${encodeURIComponent(`Olá! Seu atendimento está marcado para ${dateLabel(localDay(zone, new Date(item.starts_at)))} às ${clock(item.starts_at, zone)}.`)}`}
              target="_blank"
              rel="noreferrer"
            >
              Compartilhar pelo WhatsApp
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProfessionalBusiness({
  session,
  section,
}: {
  session: Session;
  section: "dashboard" | "agenda" | "clients" | "finance";
}) {
  const token = useRef(session.access_token);
  token.current = session.access_token;
  const [profile, setProfile] = useState<AccountProfile | null>(null),
    [services, setServices] = useState<CatalogService[]>([]),
    [summary, setSummary] = useState<Summary | null>(null);
  const [requestedDay, setDay] = useState(""),
    [weekly, setWeekly] = useState(false),
    [items, setItems] = useState<Appointment[]>([]);
  const day = requestedDay || (profile ? localDay(profile.timezone) : "");
  const [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [reload, setReload] = useState(0);
  const [creating, setCreating] = useState(false),
    [blocking, setBlocking] = useState(false),
    [moving, setMoving] = useState<Appointment | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]),
    [total, setTotal] = useState(0),
    [offset, setOffset] = useState(0),
    [search, setSearch] = useState(""),
    [history, setHistory] = useState<{
      client: Customer;
      items: Appointment[];
      offset: number;
    } | null>(null);
  useEffect(() => {
    const refresh = () => setReload(n => n + 1);
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, []);
  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setError("");
    setHistory(null);
    setMoving(null);
    Promise.all([
      profileRequest(token.current, c.signal),
      section === "agenda" ? loadCatalog(token.current, c.signal) : Promise.resolve([]),
    ])
      .then(async ([p, s]) => {
        const chosen = requestedDay || localDay(p.timezone);
        const end =
          section === "finance"
            ? addDays(chosen.slice(0, 7) + "-01", 31)
            : section === "dashboard"
              ? addDays(chosen, 30)
            : weekly && section === "agenda"
              ? addDays(chosen, 6)
              : chosen;
        const start =
          section === "finance" ? chosen.slice(0, 7) + "-01" : chosen;
        const [stats, agenda] = await Promise.all([
          section === "dashboard" || section === "finance" ? businessRequest<Summary>(
            `/me/dashboard?day=${chosen}`,
            token.current,
            undefined,
            "GET",
            c.signal,
          ) : Promise.resolve(null),
          section === "clients" ? Promise.resolve({ items: [] }) : loadAppointments(start, end, token.current, c.signal),
        ]);
        if (!c.signal.aborted) {
          setProfile(p);
          setServices(s);
          setSummary(stats);
          setItems(agenda.items);
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [session.user.id, section, requestedDay, weekly, reload]);
  useEffect(() => {
    if (section !== "clients") return;
    const c = new AbortController();
    businessRequest<{ items: Customer[]; total: number }>(
      `/me/clients?q=${encodeURIComponent(search)}&offset=${offset}`,
      token.current,
      undefined,
      "GET",
      c.signal,
    )
      .then((r) => {
        if (!c.signal.aborted) {
          setCustomers(r.items);
          setTotal(r.total);
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [section, session.user.id, reload, search, offset]);
  async function mutate(path: string, body: unknown, method = "PUT") {
    setBusy(true);
    setError("");
    try {
      await businessRequest(path, token.current, body, method);
      setReload((n) => n + 1);
      setMoving(null);
      setBlocking(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function showHistory(client: Customer, page = 0) {
    setBusy(true);
    setError("");
    try {
      const r = await businessRequest<{ items: Appointment[] }>(
        `/me/clients/${client.id}/history?offset=${page}`,
        token.current,
      );
      setHistory({ client, items: r.items, offset: page });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function block(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      void mutate(
        "/me/blocks",
        {
          starts_at: zonedInstant(String(f.get("start")), profile!.timezone),
          ends_at: zonedInstant(String(f.get("end")), profile!.timezone),
          request_key: crypto.randomUUID(),
        },
        "POST",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading) return <p role="status">Carregando seu espaço…</p>;
  if (!profile || ((section === "dashboard" || section === "finance") && !summary))
    return (
      <section>
        <h1>Seu espaço</h1>
        <p role="alert">{error || "Complete seu perfil para começar."}</p>
        <Button asChild>
          <Link to="/conta/perfil">Abrir meu perfil</Link>
        </Button>
      </section>
    );
  const zone = profile.timezone;
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">SEU NEGÓCIO, COM MAIS LEVEZA</p>
          <h1>
            {section === "dashboard"
              ? `Olá, ${profile.name.split(" ")[0]}.`
              : section === "agenda"
                ? "Minha agenda"
                : section === "clients"
                  ? "Minhas clientes"
                  : "Faturamento"}
          </h1>
        </div>
        <Button asChild variant="outline">
          <Link to={`/agendar/${profile.id}`}>
            Ver página pública <ArrowUpRight size={16} />
          </Link>
        </Button>
      </div>
      {error && (
        <p role="alert" className="upload-error">
          {error}
        </p>
      )}
      <fieldset disabled={busy} className="business-fields">
        {section === "dashboard" && (
          <>
            <section className="welcome">
              <div>
                <span className="eyebrow">TEMPO PARA O QUE IMPORTA</span>
                <h2>
                  Você cuida da beleza.
                  <br />A gente cuida da agenda.
                </h2>
                <p>
                  Seu dia organizado, do primeiro atendimento ao último detalhe.
                </p>
                <Button asChild>
                  <Link to="/conta/agenda">
                    Abrir minha agenda <ChevronRight size={16} />
                  </Link>
                </Button>
              </div>
              <div className="welcome-art" aria-hidden="true">
                <Leaf />
                <span>leve. simples. sua.</span>
              </div>
            </section>
            <div className="stats">
              {[
                [summary!.appointments_today, "Atendimentos no dia"],
                [money(summary!.expected_cents / 100), "Valor previsto no dia"],
                [
                  money(summary!.completed_month_cents / 100),
                  "Concluídos neste mês",
                ],
                [summary!.returns_due, "Retornos autorizados em aberto"],
              ].map(([v, l]) => (
                <Card key={l}>
                  <CardContent className="stat">
                    <span>{l}</span>
                    <strong>{v}</strong>
                    <small>{dateLabel(day)}</small>
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="dashboard-grid">
              <Card>
                <CardContent>
                  <div className="section-heading">
                    <h2>Próximos agendamentos</h2>
                    <Link to="/conta/agenda">Ver agenda</Link>
                  </div>
                  <p className="muted">Hoje e os próximos 30 dias</p>
                  <Button variant="outline" onClick={() => setReload(n => n + 1)}>Atualizar agendamentos</Button>
                  {items
                    .filter((i) => i.kind === "appointment" && ["pending", "confirmed"].includes(i.status))
                    .map((i) => (
                      <div key={i.id}>
                        <p><strong>{localDay(zone, new Date(i.starts_at)) === addDays(day, 1) ? "Amanhã · " : ""}{dateLabel(localDay(zone, new Date(i.starts_at)))}</strong></p>
                        <AppointmentRow item={i} zone={zone} />
                      </div>
                    ))}
                  {!items.some((i) => i.kind === "appointment" && ["pending", "confirmed"].includes(i.status)) && (
                    <p className="empty-state">
                      Nenhum atendimento pendente ou confirmado nos próximos 30 dias.
                    </p>
                  )}
                </CardContent>
              </Card>
              <Card className="tip">
                <CardContent>
                  <Bell />
                  <h2>Um convite para voltar</h2>
                  <p>
                    {summary!.returns_due} cliente(s) com retorno sugerido e
                    autorização para convites.
                  </p>
                  <p className="muted">
                    Convites por e-mail dependem da autorização e do serviço de
                    envio ativo. O compartilhamento pelo WhatsApp é manual.
                  </p>
                  <Button asChild variant="outline">
                    <Link to="/conta/clientes">Ver clientes</Link>
                  </Button>
                </CardContent>
              </Card>
            </div>
            <NotificationsPanel token={token.current} />
          </>
        )}
        {(section === "agenda" || section === "finance") && (
          <div className="toolbar">
            <label className="field">
              {section === "finance"
                ? "Mês de referência (escolha uma data)"
                : "Data"}
              <Input
                type="date"
                value={day}
                onChange={(e) => {
                  if (e.target.value) setDay(e.target.value);
                }}
              />
            </label>
            {section === "agenda" && (
              <>
                <div className="segmented">
                  <Button
                    variant={!weekly ? "default" : "ghost"}
                    onClick={() => setWeekly(false)}
                  >
                    Dia
                  </Button>
                  <Button
                    variant={weekly ? "default" : "ghost"}
                    onClick={() => setWeekly(true)}
                  >
                    Semana
                  </Button>
                </div>
                <Button onClick={() => setCreating((v) => !v)}>
                  Novo agendamento
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setBlocking((v) => !v)}
                >
                  Bloquear horário
                </Button>
              </>
            )}
          </div>
        )}
        {section === "agenda" && (
          <>
            <p className="muted">Horários no fuso {zone}.</p>
            {creating && (
              <Card>
                <CardContent>
                  <BookingForm
                    offers={services.filter((s) => s.active)}
                    zone={zone}
                    base="/me"
                    token={token.current}
                    onSaved={(savedDay) => {
                      setDay(savedDay);
                      setCreating(false);
                      setReload((n) => n + 1);
                    }}
                  />
                </CardContent>
              </Card>
            )}
            {blocking && (
              <Card>
                <CardContent>
                  <h2>Bloquear horário</h2>
                  <form onSubmit={block}>
                    <div className="form-grid">
                      <label className="field">
                        Início
                        <Input
                          name="start"
                          type="datetime-local"
                          required
                          defaultValue={day + "T09:00"}
                        />
                      </label>
                      <label className="field">
                        Fim
                        <Input
                          name="end"
                          type="datetime-local"
                          required
                          defaultValue={day + "T10:00"}
                        />
                      </label>
                    </div>
                    <Button type="submit">Salvar bloqueio</Button>
                  </form>
                </CardContent>
              </Card>
            )}
            {moving && (
              <Card>
                <CardContent>
                  <h2>Reagendar {moving.client_name}</h2>
                  <p>
                    Mesmo preço e duração do agendamento original. O horário
                    será validado ao salvar.
                  </p>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      try {
                        void mutate(
                          `/me/appointments/${moving.id}/reschedule`,
                          {
                            starts_at: zonedInstant(
                              String(
                                new FormData(e.currentTarget).get("start"),
                              ),
                              zone,
                            ),
                          },
                        );
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  >
                    <label className="field">
                      Novo início ({zone})
                      <Input name="start" type="datetime-local" required />
                    </label>
                    <Button type="submit">Salvar novo horário</Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setMoving(null)}
                    >
                      Fechar
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}
            <div className={weekly ? "week real-week" : ""}>
              {Array.from({ length: weekly ? 7 : 1 }, (_, i) =>
                addDays(day, i),
              ).map((d) => (
                <Card key={d}>
                  <CardContent>
                    <h2>{dateLabel(d)}</h2>
                    {items
                      .filter(
                        (i) =>
                          localDay(zone, new Date(i.starts_at)) === d ||
                          (i.kind === "block" &&
                            localDay(zone, new Date(i.starts_at)) < d &&
                            localDay(zone, new Date(i.ends_at)) >= d),
                      )
                      .map((i) => (
                        <AppointmentRow
                          key={i.id}
                          item={i}
                          zone={zone}
                          act={(item, status) => {
                            if (
                              status !== "cancelled" ||
                              window.confirm(
                                "Cancelar este atendimento ou liberar este bloqueio?",
                              )
                            )
                              void mutate(
                                `/me/appointments/${item.id}/status`,
                                { status },
                              );
                          }}
                          move={setMoving}
                        />
                      ))}
                    {!items.some(
                      (i) => localDay(zone, new Date(i.starts_at)) === d,
                    ) && (
                      <p className="muted">
                        Sem atendimentos iniciando neste dia.
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
        {section === "finance" && (
          <>
            <div className="stats">
              <Card>
                <CardContent className="stat">
                  <span>Atendimentos concluídos no mês</span>
                  <strong>{money(summary!.completed_month_cents / 100)}</strong>
                  <small>Valores dos serviços na data da reserva</small>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="stat">
                  <span>Previsto para o mês</span>
                  <strong>
                    {money(
                      items
                        .filter(
                          (i) =>
                            i.kind === "appointment" &&
                            i.status !== "cancelled" &&
                            localDay(zone, new Date(i.starts_at)).slice(
                              0,
                              7,
                            ) === day.slice(0, 7),
                        )
                        .reduce((n, i) => n + i.price_cents, 0) / 100,
                    )}
                  </strong>
                  <small>Inclui agendados e concluídos</small>
                </CardContent>
              </Card>
            </div>
            <p className="notice">
              Faturamento por atendimentos concluídos; não é conciliação de
              pagamentos nem lucro. Cancelados não entram nos totais.
            </p>
            {items
              .filter(
                (i) =>
                  i.kind === "appointment" &&
                  i.status === "completed" &&
                  localDay(zone, new Date(i.starts_at)).slice(0, 7) ===
                    day.slice(0, 7),
              )
              .map((i) => (
                <Card key={i.id}>
                  <CardContent>
                    <p>{dateLabel(localDay(zone, new Date(i.starts_at)))}</p>
                    <AppointmentRow item={i} zone={zone} />
                  </CardContent>
                </Card>
              ))}
          </>
        )}
        {section === "clients" && (
          <>
            <label className="field">
              Buscar cliente pelo nome
              <Input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setOffset(0);
                  setHistory(null);
                }}
              />
            </label>
            <p>{total} cliente(s) cadastrada(s)</p>
            <div className="service-grid">
              {customers.map((c) => (
                <Card key={c.id}>
                  <CardContent>
                    <h2>{c.name}</h2>
                    <p>{c.phone}</p>
                    <p>{c.email}</p>
                    <p className="muted">
                      {c.invites_allowed
                        ? "Autoriza convites de retorno"
                        : "Sem autorização para convites"}
                    </p>
                    <div className="actions">
                      <Button
                        variant="outline"
                        onClick={() => void showHistory(c)}
                      >
                        Ver histórico
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          if (
                            window.confirm(
                              c.invites_allowed
                                ? "Revogar a autorização para convites?"
                                : "A cliente autorizou expressamente convites futuros?",
                            )
                          )
                            void mutate(`/me/clients/${c.id}/consent`, {
                              allowed: !c.invites_allowed,
                            });
                        }}
                      >
                        {c.invites_allowed
                          ? "Revogar autorização"
                          : "Registrar autorização"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="actions">
              <Button
                disabled={offset === 0}
                variant="outline"
                onClick={() => setOffset((n) => n - 50)}
              >
                Anterior
              </Button>
              <Button
                disabled={offset + 50 >= total}
                variant="outline"
                onClick={() => setOffset((n) => n + 50)}
              >
                Próximas clientes
              </Button>
            </div>
            {history && (
              <Card>
                <CardContent>
                  <h2>Histórico de {history.client.name}</h2>
                  {history.items.map((i) => (
                    <div key={i.id}>
                      <p>{dateLabel(localDay(zone, new Date(i.starts_at)))}</p>
                      <AppointmentRow item={i} zone={zone} />
                      {i.return_date && (
                        <p>Retorno sugerido: {dateLabel(i.return_date)}</p>
                      )}
                    </div>
                  ))}
                  {!history.items.length && (
                    <p>Nenhum atendimento neste período do histórico.</p>
                  )}
                  <div className="actions">
                    <Button
                      disabled={history.offset === 0}
                      onClick={() =>
                        void showHistory(history.client, history.offset - 50)
                      }
                    >
                      Mais recentes
                    </Button>
                    <Button
                      disabled={history.items.length < 50}
                      onClick={() =>
                        void showHistory(history.client, history.offset + 50)
                      }
                    >
                      Mais antigos
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </fieldset>
    </>
  );
}
