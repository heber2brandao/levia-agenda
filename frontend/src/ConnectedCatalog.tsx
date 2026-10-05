import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Session } from "@supabase/supabase-js";
import { StudioLogo } from "./components/AppearanceEditor";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { money } from "./demo";
import { ApiError, profileRequest, type AccountProfile } from "@/lib/api";
import { appearanceStyle } from "@/lib/appearance";
import {
  catalogRequest,
  loadCatalog,
  type Availability,
  type CatalogService,
  type Suggestion,
} from "@/lib/catalog-api";

export default function ConnectedCatalog({ session }: { session: Session }) {
  const token = useRef(session.access_token);
  token.current = session.access_token;
  const [services, setServices] = useState<CatalogService[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [profile, setProfile] = useState<AccountProfile | null>(null);
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false);
  const [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [reload, setReload] = useState(0);
  const [editor, setEditor] = useState<Partial<CatalogService> | null>(null);
  const [editorVersion, setEditorVersion] = useState(0);
  function openEditor(value: Partial<CatalogService>) {
    setEditor(value);
    setEditorVersion((n) => n + 1);
  }
  const [selection, setSelection] = useState<string[]>([]),
    [day, setDay] = useState("");
  const [result, setResult] = useState<Availability | null>(null);
  const [consulting, setConsulting] = useState(false);
  const request = useRef<AbortController | null>(null),
    mutation = useRef<AbortController | null>(null);
  const active = services.filter((s) => s.active);
  const chosen = active.filter((s) => selection.includes(s.id));
  function invalidate() {
    request.current?.abort();
    setConsulting(false);
    setResult(null);
  }
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      loadCatalog(token.current, controller.signal),
      catalogRequest<Suggestion[]>(
        token.current,
        "/service-suggestions",
        controller.signal,
      ),
      profileRequest(token.current, controller.signal),
    ])
      .then(([items, hints, owner]) => {
        if (!controller.signal.aborted) {
          setServices(items);
          setSuggestions(hints);
          setProfile(owner);
          setSelection((ids) =>
            ids.filter((id) => items.some((s) => s.id === id && s.active)),
          );
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted)
          setError(
            reason instanceof ApiError
              ? reason.message
              : "Não foi possível carregar o catálogo.",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [session.user.id, reload]);
  useEffect(
    () => () => {
      request.current?.abort();
      mutation.current?.abort();
    },
    [],
  );
  async function persist(data: Omit<CatalogService, "id">, id?: string) {
    const controller = new AbortController();
    mutation.current = controller;
    setBusy(true);
    setError("");
    setMessage("");
    invalidate();
    try {
      await catalogRequest(
        token.current,
        id ? `/services/${id}` : "/services",
        controller.signal,
        data,
        id ? "PUT" : "POST",
      );
      if (!controller.signal.aborted) {
        setEditor(null);
        setMessage("Serviço salvo no banco de dados.");
        setReload((n) => n + 1);
      }
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Não foi possível salvar o serviço.",
        );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    void persist(
      {
        name: String(form.get("name")).trim(),
        price_cents: Math.round(Number(form.get("price")) * 100),
        duration_minutes: Number(form.get("duration")),
        return_days: form.get("return") ? Number(form.get("return")) : null,
        active: editor?.active ?? true,
      },
      editor?.id,
    );
  }
  async function consult() {
    invalidate();
    const controller = new AbortController();
    request.current = controller;
    setConsulting(true);
    setError("");
    try {
      const response = await catalogRequest<Availability>(
        token.current,
        "/availability",
        controller.signal,
        { day, service_ids: chosen.map((s) => s.id) },
      );
      if (!controller.signal.aborted) setResult(response);
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Não foi possível consultar os horários.",
        );
    } finally {
      if (!controller.signal.aborted) setConsulting(false);
    }
  }
  if (loading) return <p role="status">Carregando serviços…</p>;
  return (
    <section className="connected-catalog">
      <div className="section-heading">
        <h2>Meus serviços</h2>
        <Button disabled={busy || !profile} onClick={() => openEditor({})}>
          Novo serviço
        </Button>
      </div>
      {error && (
        <div role="alert">
          <p className="upload-error">{error}</p>
          <Button
            variant="outline"
            onClick={() => {
              invalidate();
              setReload((n) => n + 1);
            }}
          >
            Atualizar catálogo
          </Button>
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {suggestions.length > 0 && (
        <details className="catalog-suggestions">
          <summary>Sugestões para suas especialidades</summary>
          <p className="muted">
            Escolha uma sugestão, defina seu valor e ajuste duração e retorno
            antes de salvar.
          </p>
          <div className="actions">
            {suggestions.map((s) => (
              <Button
                key={s.specialty + s.name}
                disabled={busy}
                variant="outline"
                onClick={() =>
                  openEditor({
                    name: s.name,
                    duration_minutes: s.duration_minutes,
                    return_days: s.return_days,
                  })
                }
              >
                {s.name}
              </Button>
            ))}
          </div>
        </details>
      )}
      {editor && (
        <Card className="editor">
          <CardContent>
            <h3>{editor.id ? "Editar serviço" : "Novo serviço"}</h3>
            <form key={editorVersion} onSubmit={save}>
              <fieldset disabled={busy}>
                <div className="form-grid">
                  <label className="field">
                    Nome do serviço
                    <Input
                      name="name"
                      required
                      maxLength={100}
                      defaultValue={editor.name}
                    />
                  </label>
                  <label className="field">
                    Valor (R$)
                    <Input
                      name="price"
                      required
                      type="number"
                      min="0"
                      max="99999.99"
                      step="0.01"
                      defaultValue={
                        editor.price_cents === undefined
                          ? ""
                          : editor.price_cents / 100
                      }
                    />
                  </label>
                  <label className="field">
                    Duração (minutos)
                    <Input
                      name="duration"
                      required
                      type="number"
                      min="5"
                      max="480"
                      step="1"
                      defaultValue={editor.duration_minutes ?? 45}
                    />
                  </label>
                  <label className="field">
                    Retorno sugerido (dias, opcional)
                    <Input
                      name="return"
                      type="number"
                      min="1"
                      max="365"
                      step="1"
                      defaultValue={editor.return_days ?? ""}
                    />
                  </label>
                </div>
                <div className="actions">
                  <Button type="submit">
                    {busy ? "Salvando…" : "Salvar serviço"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setEditor(null)}
                  >
                    Cancelar
                  </Button>
                </div>
              </fieldset>
            </form>
          </CardContent>
        </Card>
      )}
      {!services.length && profile && (
        <p className="notice">
          Seu catálogo está vazio. Adicione um serviço ou escolha uma sugestão.
        </p>
      )}
      <div className="service-grid">
        {services.map((s) => (
          <Card key={s.id}>
            <CardContent>
              <span className="status">{s.active ? "Ativo" : "Inativo"}</span>
              <h3>{s.name}</h3>
              <p>
                {money(s.price_cents / 100)} · {s.duration_minutes} min
              </p>
              <p className="muted">
                {s.return_days
                  ? `Retorno em ${s.return_days} dias`
                  : "Sem retorno sugerido"}
              </p>
              <div className="actions">
                <Button
                  disabled={busy}
                  variant="outline"
                  onClick={() => openEditor(s)}
                  aria-label={`Editar ${s.name}`}
                >
                  Editar
                </Button>
                <Button
                  disabled={busy}
                  variant="ghost"
                  onClick={() => {
                    const { id, ...data } = s;
                    void persist({ ...data, active: !s.active }, id);
                  }}
                >
                  {s.active ? "Desativar" : "Ativar"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {profile && (
        <div className="catalog-preview">
          <h2>Prévia dos serviços e horários</h2>
          <p className="muted">
            Consulta privada com dados do banco, no fuso {profile.timezone}.
            Ainda não realiza reservas.
          </p>
          <div
            className="public-theme appearance-preview"
            style={appearanceStyle({
              primary: profile.primary_color,
              background: profile.background_color,
              logo: null,
            })}
          >
            <StudioLogo logo={profile.logo} studioName={profile.studio_name} />
            <h3>{profile.studio_name}</h3>
            <p>Selecione um ou mais serviços.</p>
            {active.map((s) => (
              <button
                key={s.id}
                className={`service-choice ${selection.includes(s.id) ? "selected" : ""}`}
                aria-pressed={selection.includes(s.id)}
                onClick={() => {
                  invalidate();
                  setSelection((ids) =>
                    ids.includes(s.id)
                      ? ids.filter((id) => id !== s.id)
                      : [...ids, s.id],
                  );
                }}
              >
                <span>
                  <strong>{s.name}</strong>
                  <small>
                    {s.duration_minutes} min{" "}
                    {selection.includes(s.id) ? "· Selecionado" : ""}
                  </small>
                </span>
                <b>{money(s.price_cents / 100)}</b>
              </button>
            ))}
            {!active.length && <p>Nenhum serviço ativo.</p>}
            {chosen.length > 0 && (
              <>
                <p>
                  {chosen.reduce((n, s) => n + s.duration_minutes, 0)} minutos ·{" "}
                  {money(chosen.reduce((n, s) => n + s.price_cents, 0) / 100)}
                </p>
                <label className="field">
                  Data desejada
                  <Input
                    type="date"
                    required
                    value={day}
                    onChange={(e) => {
                      invalidate();
                      setDay(e.target.value);
                    }}
                  />
                </label>
                <Button
                  disabled={
                    !day ||
                    consulting ||
                    chosen.length > 10 ||
                    chosen.reduce((n, s) => n + s.duration_minutes, 0) > 480
                  }
                  onClick={() => void consult()}
                >
                  {consulting ? "Consultando…" : "Consultar horários"}
                </Button>
                {(chosen.length > 10 ||
                  chosen.reduce((n, s) => n + s.duration_minutes, 0) > 480) && (
                  <p>Selecione até 10 serviços e no máximo 480 minutos.</p>
                )}
              </>
            )}
            {result && (
              <div role="status">
                <p>
                  {result.duration_minutes} minutos ·{" "}
                  {money(result.price_cents / 100)}
                </p>
                {result.slots.length ? (
                  <ul className="available-slots">
                    {result.slots.map((slot) => (
                      <li key={slot.starts_at}>
                        {new Date(slot.starts_at).toLocaleTimeString("pt-BR", {
                          timeZone: result.timezone,
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        –{" "}
                        {new Date(slot.ends_at).toLocaleTimeString("pt-BR", {
                          timeZone: result.timezone,
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Nenhum horário disponível para esta combinação e data.</p>
                )}
                <p>Esta consulta não garante a reserva do horário.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
