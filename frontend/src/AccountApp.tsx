import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import ProfessionalBusiness from "./ProfessionalBusiness";
import ProfessionalShell from "./ProfessionalShell";
import LogoEditor from "./LogoEditor";
import ConnectedCatalog from "./ConnectedCatalog";
import type { Session } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { supabase, finishRecovery, hadAuthCallback, isRecoveringUser } from "@/lib/supabase";
import {
  ApiError,
  emptyProfile,
  profileRequest,
  type AccountProfile,
} from "@/lib/api";

function ProfileForm({ session }: { session: Session }) {
  const [profile, setProfile] = useState<AccountProfile>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const saveController = useRef<AbortController | null>(null);
  const currentToken = useRef(session.access_token);
  currentToken.current = session.access_token;
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setLoadFailed(false);
    profileRequest(currentToken.current, controller.signal)
      .then(setProfile)
      .catch((reason) => {
        if (controller.signal.aborted) return;
        if (reason instanceof ApiError && reason.status === 404)
          setProfile({ ...emptyProfile });
        else {
          setLoadFailed(true);
          setError(
            reason instanceof ApiError
              ? reason.message
              : "Não foi possível carregar seu perfil.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [session.user.id, retry]);
  useEffect(() => () => saveController.current?.abort(), []);
  function update<K extends keyof AccountProfile>(
    key: K,
    value: AccountProfile[K],
  ) {
    setProfile((previous) => ({ ...previous, [key]: value }));
    setMessage("");
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    const controller = new AbortController();
    saveController.current = controller;
    try {
      const saved = await profileRequest(
        session.access_token,
        controller.signal,
        profile,
      );
      if (!controller.signal.aborted) {
        setProfile(saved);
        setMessage("Perfil salvo no banco de dados.");
      }
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Não foi possível salvar. Verifique sua conexão.",
        );
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  }
  if (loading) return <p role="status">Carregando seu perfil…</p>;
  if (loadFailed)
    return (
      <>
        <p role="alert">{error}</p>
        <Button onClick={() => setRetry((n) => n + 1)}>Tentar novamente</Button>
      </>
    );
  const days = [
    "Segunda",
    "Terça",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sábado",
    "Domingo",
  ];
  return (
    <form onSubmit={save}>
      {profile.id && (
        <section className="notice" aria-label="Link de agendamento">
          <label className="field">
            Seu link de agendamento
            <Input readOnly value={`${window.location.origin}/agendar/${profile.public_slug || profile.id}`}
              onFocus={(event) => event.currentTarget.select()} />
          </label>
          <p>Compartilhe este link com suas clientes. Ele permanece igual ao editar o nome do espaço.</p>
          <Button type="button" variant="outline" onClick={async () => {
            try {
              await navigator.clipboard.writeText(`${window.location.origin}/agendar/${profile.public_slug || profile.id}`);
              setMessage("Link copiado.");
            } catch {
              setMessage("Selecione o endereço acima e copie o link.");
            }
          }}>Copiar link</Button>
        </section>
      )}
      <fieldset disabled={saving || logoBusy} className="account-fields">
        <div className="form-grid">
          <label className="field">
            Seu nome
            <Input
              required
              maxLength={100}
              value={profile.name}
              onChange={(e) => update("name", e.target.value)}
            />
          </label>
          <label className="field">
            Nome do espaço
            <Input
              required
              maxLength={100}
              value={profile.studio_name}
              onChange={(e) => update("studio_name", e.target.value)}
            />
          </label>
          <label className="field">
            Telefone com DDD
            <Input
              required
              type="tel"
              inputMode="tel"
              placeholder="65999999999"
              pattern="\+?[0-9]{10,15}"
              value={profile.phone}
              onChange={(e) =>
                update("phone", e.target.value.replace(/[^0-9+]/g, ""))
              }
            />
          </label>
          <label className="field">
            E-mail de contato (opcional)
            <Input
              type="email"
              value={profile.email ?? ""}
              onChange={(e) => update("email", e.target.value || null)}
            />
          </label>
          <label className="field">
            Fuso horário
            <select
              value={profile.timezone}
              onChange={(e) => update("timezone", e.target.value)}
            >
              {[
                "America/Cuiaba",
                "America/Sao_Paulo",
                "America/Manaus",
                "America/Rio_Branco",
                "America/Noronha",
              ].map((zone) => (
                <option key={zone}>{zone}</option>
              ))}
            </select>
          </label>
        </div>
        <fieldset className="specialties">
          <legend>Especialidades — selecione uma ou mais</legend>
          {[
            "Unhas",
            "Cílios",
            "Sobrancelhas",
            "Cabelos",
            "Depilação",
            "Estética",
            "Outros",
          ].map((value) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={profile.specialties.includes(value)}
                onChange={(e) =>
                  update(
                    "specialties",
                    e.target.checked
                      ? [...profile.specialties, value]
                      : profile.specialties.filter((s) => s !== value),
                  )
                }
              />
              {value}
            </label>
          ))}
        </fieldset>
        <h2>Horários de funcionamento</h2>
        <p className="muted">
          Adicione períodos separados para o intervalo de almoço. Dias sem
          períodos ficam fechados.
        </p>
        {profile.working_periods.map((period, index) => (
          <div className="working-period" key={index}>
            <label className="field">
              Dia
              <select
                value={period.weekday}
                onChange={(e) =>
                  update(
                    "working_periods",
                    profile.working_periods.map((p, i) =>
                      i === index
                        ? { ...p, weekday: Number(e.target.value) }
                        : p,
                    ),
                  )
                }
              >
                {days.map((day, i) => (
                  <option key={day} value={i}>
                    {day}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Início
              <Input
                type="time"
                required
                value={period.starts_at.slice(0, 5)}
                onChange={(e) =>
                  update(
                    "working_periods",
                    profile.working_periods.map((p, i) =>
                      i === index ? { ...p, starts_at: e.target.value } : p,
                    ),
                  )
                }
              />
            </label>
            <label className="field">
              Fim
              <Input
                type="time"
                required
                value={period.ends_at.slice(0, 5)}
                onChange={(e) =>
                  update(
                    "working_periods",
                    profile.working_periods.map((p, i) =>
                      i === index ? { ...p, ends_at: e.target.value } : p,
                    ),
                  )
                }
              />
            </label>
            <Button
              type="button"
              variant="outline"
              aria-label={`Remover período ${index + 1}`}
              onClick={() =>
                update(
                  "working_periods",
                  profile.working_periods.filter((_, i) => i !== index),
                )
              }
            >
              Remover
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          disabled={profile.working_periods.length >= 28}
          onClick={() =>
            update("working_periods", [
              ...profile.working_periods,
              { weekday: 0, starts_at: "09:00", ends_at: "12:00" },
            ])
          }
        >
          Adicionar período
        </Button>
        <h2>Aparência</h2>
        <LogoEditor
          token={session.access_token}
          logo={profile.logo}
          studioName={profile.studio_name}
          onBusy={setLogoBusy}
          onChange={(logo) => setProfile((previous) => ({ ...previous, logo }))}
        />
        <div className="palette-fields">
          <label className="field">
            Cor principal
            <Input
              type="color"
              value={profile.primary_color}
              onChange={(e) => update("primary_color", e.target.value)}
            />
          </label>
          <label className="field">
            Cor de fundo
            <Input
              type="color"
              value={profile.background_color}
              onChange={(e) => update("background_color", e.target.value)}
            />
          </label>
        </div>
        <p className="muted">
          As cores ficam salvas no perfil. Upload permanente da logo e página
          pública real serão conectados nas próximas etapas.
        </p>
        <Button
          type="submit"
          disabled={profile.specialties.length === 0 || saving}
        >
          {saving ? "Salvando…" : "Salvar perfil"}
        </Button>
        {profile.specialties.length === 0 && (
          <p className="muted">Selecione pelo menos uma especialidade.</p>
        )}
      </fieldset>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="upload-error">
          {error}
        </p>
      )}
    </form>
  );
}

function Login({
  recovering,
  onRecovered,
}: {
  recovering: boolean;
  onRecovered: () => void;
}) {
  const [mode, setMode] = useState<"login" | "signup" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (recovering) {
        const { error } = await supabase.auth.updateUser({ password });
        if (error) throw error;
        setPassword("");
        onRecovered();
        return;
      }
      if (mode === "reset") {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: location.origin + "/conta",
        });
        if (error) throw error;
        setMessage(
          "Se houver uma conta elegível, você receberá instruções por e-mail.",
        );
      } else if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: location.origin + "/conta" },
        });
        if (error) throw error;
        setMessage(
          "Confira seu e-mail para confirmar o cadastro, se necessário.",
        );
        setPassword("");
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        setPassword("");
      }
    } catch (reason) {
      const code = reason && typeof reason === "object" && "code" in reason ? reason.code : undefined;
      setError(
        recovering && code === "same_password"
          ? "A nova senha deve ser diferente da senha atual. Escolha outra senha com pelo menos 12 caracteres."
          : "Não foi possível concluir. Confira os dados, a confirmação de e-mail ou tente novamente mais tarde.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h1>
        {recovering
          ? "Nova senha"
          : mode === "signup"
            ? "Crie sua conta"
            : mode === "reset"
              ? "Recuperar acesso"
              : "Entre no seu espaço"}
      </h1>
      <form onSubmit={submit} className="auth-form">
        <fieldset disabled={busy}>
          {!recovering && (
            <label className="field">
              E-mail
              <Input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}
          {(recovering || mode !== "reset") && (
            <label className="field">
              Senha
              <Input
                type="password"
                required
                minLength={mode === "signup" || recovering ? 12 : 1}
                maxLength={128}
                autoComplete={
                  recovering || mode === "signup"
                    ? "new-password"
                    : "current-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          )}
          {(recovering || mode === "signup") && (
            <p className="muted">
              Use pelo menos 12 caracteres para sua senha.
            </p>
          )}
          <Button type="submit">
            {busy
              ? "Aguarde…"
              : recovering
                ? "Salvar nova senha"
                : mode === "signup"
                  ? "Criar conta"
                  : mode === "reset"
                    ? "Solicitar recuperação"
                    : "Entrar"}
          </Button>
        </fieldset>
      </form>
      {!recovering && (
        <div className="actions">
          {(["login", "signup", "reset"] as const)
            .filter((m) => m !== mode)
            .map((m) => (
              <Button
                key={m}
                variant="ghost"
                disabled={busy}
                onClick={() => {
                  setMode(m);
                  setError("");
                  setMessage("");
                  setPassword("");
                }}
              >
                {m === "login"
                  ? "Já tenho conta"
                  : m === "signup"
                    ? "Criar conta"
                    : "Esqueci minha senha"}
              </Button>
            ))}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="upload-error">
          {error}
        </p>
      )}
    </>
  );
}

export default function AccountApp() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(!supabase);
  const [recovering, setRecovering] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => {
    if (!supabase) return;
    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next);
      setReady(true);
      setRecovering(!!next && (event === "PASSWORD_RECOVERY" || isRecoveringUser(next.user.id)));
    });
    return () => data.subscription.unsubscribe();
  }, []);
  if (ready && session && !recovering) {
    const section =
      pathname === "/conta/agenda"
        ? "agenda"
        : pathname === "/conta/clientes"
          ? "clients"
          : pathname === "/conta/faturamento"
            ? "finance"
            : "dashboard";
    return (
      <ProfessionalShell key={session.user.id} session={session}>
        {pathname === "/conta/perfil" ? (
          <>
            <div className="page-heading">
              <h1>Meu espaço</h1>
            </div>
            <Card>
              <CardContent>
                <ProfileForm session={session} />
              </CardContent>
            </Card>
          </>
        ) : pathname === "/conta/servicos" ? (
          <ConnectedCatalog session={session} />
        ) : (
          <ProfessionalBusiness
            key={section}
            session={session}
            section={section}
          />
        )}
      </ProfessionalShell>
    );
  }
  return (
    <main className="account-page">
      <header>
        <Link to="/conta" className="account-brand">
          levia<span>agenda</span>
        </Link>
        <span>Conta da profissional</span>
      </header>
      {import.meta.env.VITE_DEMO_MODE === "true" && (
        <Link to="/">← Voltar à demonstração</Link>
      )}
      <Card>
        <CardContent>
          {!supabase ? (
            <>
              <h1>Vamos conectar seu espaço</h1>
              <p>
                A área de conta está preparada, mas o Supabase ainda não foi
                configurado.
              </p>
              <p className="muted">
                O cadastro real ficará disponível após a configuração.
                Nenhuma conta foi criada e nenhum dado foi enviado.
              </p>
            </>
          ) : !ready ? (
            <p role="status">Verificando sessão…</p>
          ) : (
            <>
            {hadAuthCallback && !session && (
              <p role="alert">Não foi possível validar o link. Solicite uma nova recuperação e abra o e-mail no mesmo navegador usado para solicitar.</p>
            )}
            <Login
              recovering={recovering}
              onRecovered={() => { finishRecovery(); setRecovering(false); }}
            />
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
