import { useState, type FormEvent, type ReactNode, type Dispatch, type SetStateAction } from "react";
import AppearanceEditor, { StudioLogo } from "@/components/AppearanceEditor";
import { appearanceStyle, defaultAppearance, type Appearance } from "@/lib/appearance";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import {
  CalendarDays,
  LayoutDashboard,
  Sparkles,
  Users,
  Settings,
  ArrowUpRight,
  Plus,
  Clock,
  ChevronRight,
  Leaf,
  Bell,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { appointments, initialServices, money, type Service } from "./demo";

const navigation = [
  { path: "/", label: "Visão geral", icon: LayoutDashboard },
  { path: "/agenda", label: "Agenda", icon: CalendarDays },
  { path: "/servicos", label: "Serviços", icon: Sparkles },
  { path: "/clientes", label: "Clientes", icon: Users },
  { path: "/perfil", label: "Meu espaço", icon: Settings },
];
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function Heading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </div>
  );
}
function AppointmentList() {
  return (
    <div>
      {appointments.map((a) => (
        <div className="appointment" key={a.time}>
          <span className="time">{a.time}</span>
          <div className="appointment-person">
            <strong>{a.name}</strong>
            <span>{a.service}</span>
          </div>
          <span
            className={`status ${a.status === "Confirmado" ? "confirmed" : ""}`}
          >
            {a.status}
          </span>
        </div>
      ))}
    </div>
  );
}
function Dashboard({ professionalName }: { professionalName: string }) {
  return (
    <>
      <Heading eyebrow="SEU NEGÓCIO, COM MAIS LEVEZA" title={`Bom dia, ${professionalName.split(/\s+/)[0]}.`}>
        <Button asChild variant="outline">
          <Link to="/agendar/ana">
            Ver página pública <ArrowUpRight size={16} />
          </Link>
        </Button>
      </Heading>
      <section className="welcome">
        <div>
          <span className="eyebrow">TEMPO PARA O QUE IMPORTA</span>
          <h2>
            Você cuida da beleza.
            <br />A gente cuida da agenda.
          </h2>
          <p>Seu dia organizado, do primeiro atendimento ao último detalhe.</p>
          <Button asChild>
            <Link to="/agenda">
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
          ["03", "Atendimentos no dia"],
          ["R$ 165", "Valor previsto · exemplo"],
          ["02", "Retornos sugeridos"],
        ].map(([value, label]) => (
          <Card key={label}>
            <CardContent className="stat">
              <span>{label}</span>
              <strong>{value}</strong>
              <small>Dados ilustrativos</small>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="dashboard-grid">
        <Card>
          <CardContent>
            <div className="section-heading">
              <h2>Seu próximo cuidado</h2>
              <Link to="/agenda">
                Ver agenda <ArrowUpRight size={14} />
              </Link>
            </div>
            <p className="muted">Sexta-feira, 2 de outubro · dia ilustrativo</p>
            <AppointmentList />
          </CardContent>
        </Card>
        <Card className="tip">
          <CardContent>
            <Bell size={23} />
            <h2>Um convite para voltar</h2>
            <p>
              Marina e Clara estão no período sugerido para um novo atendimento.
            </p>
            <p className="muted">
              Exemplo de aviso. Nenhuma mensagem foi enviada.
            </p>
            <Button asChild variant="outline">
              <Link to="/clientes">
                Ver clientes <ChevronRight size={16} />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
function Agenda() {
  const [view, setView] = useState("Dia");
  return (
    <>
      <Heading eyebrow="CADA HORÁRIO, UM CUIDADO" title="Minha agenda" />
      <div className="toolbar">
        <h2>2 de outubro de 2026</h2>
        <div className="segmented">
          {["Dia", "Semana"].map((v) => (
            <Button
              key={v}
              variant={v === view ? "default" : "ghost"}
              onClick={() => setView(v)}
              aria-pressed={v === view}
            >
              {v}
            </Button>
          ))}
        </div>
      </div>
      <p className="notice">
        Agenda ilustrativa. Criação manual, bloqueios e alterações reais chegam
        na Etapa 4.
      </p>
      {view === "Dia" ? (
        <Card>
          <CardContent>
            <AppointmentList />
            <div className="free-slot">
              <Clock size={18} /> 15:00 – 18:00 · exemplo de período livre
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="week">
          {["Seg 28", "Ter 29", "Qua 30", "Qui 1", "Sex 2"].map((day, i) => (
            <Card key={day}>
              <CardContent>
                <h3>{day}</h3>
                {i === 4 ? (
                  appointments.map((a) => (
                    <div className="week-event" key={a.time}>
                      <strong>{a.time}</strong>
                      <p>{a.name}</p>
                      <small>{a.service}</small>
                    </div>
                  ))
                ) : (
                  <p className="muted">Sem exemplos</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
function Services({
  services,
  setServices,
}: {
  services: Service[];
  setServices: (s: Service[]) => void;
}) {
  const [editing, setEditing] = useState<Service | null>(null);
  const [open, setOpen] = useState(false);
  function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const service = {
      id: editing?.id ?? crypto.randomUUID(),
      name: String(f.get("name")).trim(),
      price: Number(f.get("price")),
      duration: Number(f.get("duration")),
      returnDays: Number(f.get("returnDays")),
      active: editing?.active ?? true,
    };
    if (!service.name) return;
    setServices(
      editing
        ? services.map((s) => (s.id === editing.id ? service : s))
        : [...services, service],
    );
    setOpen(false);
  }
  return (
    <>
      <Heading eyebrow="O SEU TALENTO EM CADA DETALHE" title="Meus serviços">
        <Button
          onClick={() => {
            setEditing(null);
            setOpen(true);
          }}
        >
          <Plus size={17} /> Novo serviço
        </Button>
      </Heading>
      <p className="muted intro">
        Os serviços ativos aparecem como cartões na página pública. Alterações
        duram somente nesta sessão.
      </p>
      {open && (
        <Card className="editor">
          <CardContent>
            <h2>{editing ? "Editar serviço" : "Novo serviço"}</h2>
            <form onSubmit={save} key={editing?.id ?? "new"}>
              <div className="form-grid">
                <Field label="Nome do serviço">
                  <Input
                    name="name"
                    required
                    maxLength={80}
                    defaultValue={editing?.name}
                  />
                </Field>
                <Field label="Valor (R$)">
                  <Input
                    name="price"
                    type="number"
                    min="0"
                    max="99999"
                    step="0.01"
                    required
                    defaultValue={editing?.price}
                  />
                </Field>
                <Field label="Duração (minutos)">
                  <Input
                    name="duration"
                    type="number"
                    min="5"
                    max="480"
                    required
                    defaultValue={editing?.duration ?? 45}
                  />
                </Field>
                <Field label="Retorno sugerido (dias)">
                  <Input
                    name="returnDays"
                    type="number"
                    min="1"
                    max="365"
                    required
                    defaultValue={editing?.returnDays ?? 14}
                  />
                </Field>
              </div>
              <div className="actions">
                <Button type="submit">Salvar na demonstração</Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setOpen(false)}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
      <div className="service-grid">
        {services.map((s) => (
          <Card key={s.id}>
            <CardContent>
              <div className="section-heading">
                <Sparkles size={22} />
                <span className="status">{s.active ? "Ativo" : "Inativo"}</span>
              </div>
              <h2>{s.name}</h2>
              <p className="service-price">
                {money(s.price)} <small> / atendimento</small>
              </p>
              <p className="muted">
                <Clock size={15} /> {s.duration} min · retorno em {s.returnDays}{" "}
                dias
              </p>
              <div className="actions">
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditing(s);
                    setOpen(true);
                  }}
                  aria-label={`Editar ${s.name}`}
                >
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  onClick={() =>
                    setServices(
                      services.map((item) =>
                        item.id === s.id
                          ? { ...item, active: !item.active }
                          : item,
                      ),
                    )
                  }
                >
                  {s.active ? "Desativar" : "Ativar"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
function Clients() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [revocations, setRevocations] = useState<string[]>([]);
  const revoked = revocations.includes(selected);
  const filtered = appointments.filter((a) =>
    a.name.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <Heading eyebrow="RELAÇÕES QUE FLORESCEM" title="Minhas clientes" />
      <Field label="Buscar cliente fictícia">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Busque pelo nome"
        />
      </Field>
      <Card className="client-list">
        <CardContent>
          {filtered.length ? (
            filtered.map((a, i) => (
              <div className="appointment" key={a.name}>
                <span className="avatar">{a.name[0]}</span>
                <div className="appointment-person">
                  <strong>{a.name}</strong>
                  <span>{i + 2} atendimentos · exemplo</span>
                </div>
                <Button variant="outline" onClick={() => setSelected(a.name)}>
                  Ver histórico
                </Button>
              </div>
            ))
          ) : (
            <p>Nenhuma cliente encontrada.</p>
          )}
        </CardContent>
      </Card>
      {selected && (
        <Card className="editor">
          <CardContent>
            <h2>Histórico de {selected}</h2>
            <p>18/09/2026 · Manicure · Concluído (exemplo)</p>
            <p>Retorno sugerido: 02/10/2026</p>
            <p>
              Convites futuros:{" "}
              {revoked
                ? "autorização revogada nesta sessão"
                : "autorização ilustrativa"}
            </p>
            <Button
              variant="outline"
              onClick={() => setRevocations((previous) => [...previous, selected])}
              disabled={revoked}
            >
              Simular revogação de autorização
            </Button>
            <p className="muted">
              Dados fictícios, sem registro de consentimento real.
            </p>
          </CardContent>
        </Card>
      )}
    </>
  );
}
type ProfessionalProfile = { name: string; phone: string; email: string; specialty: string; timezone: string; opens: string; closes: string };
function Profile({ appearance, setAppearance, studioName, setStudioName, profile, saveProfile }: { appearance: Appearance; setAppearance: Dispatch<SetStateAction<Appearance>>; studioName: string; setStudioName: (name: string) => void; profile: ProfessionalProfile; saveProfile: (profile: ProfessionalProfile, name?: string) => string }) {
  const [saved, setSaved] = useState(false);
  const [nameDraft, setNameDraft] = useState(studioName);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState("");
  const [draft, setDraft] = useState(profile);
  const [profileError, setProfileError] = useState("");
  const specialty = draft.specialty;
  function updateDraft(key: keyof ProfessionalProfile, value: string) {
    setDraft(previous => ({ ...previous, [key]: value })); setSaved(false); setProfileError("");
  }
  return (
    <>
      <Heading eyebrow="DO SEU JEITO" title="Meu espaço" />
      <p className="notice">Você está na demonstração. <Link to="/conta" className="underline">Abrir minha conta conectada</Link> para configurar o perfil real.</p>
      <Card className="editor"><CardContent>
        <form onSubmit={e => {
          e.preventDefault();
          const name = nameDraft.trim();
          if (!name) { setNameError("Informe o nome do espaço."); return; }
          setStudioName(name); setNameDraft(name); setNameError(""); setNameSaved(true);
        }}>
          <Field label="Nome do espaço"><Input required maxLength={100} value={nameDraft} onChange={e => { setNameDraft(e.target.value); setNameSaved(false); setNameError(""); }} /></Field>
          <div className="actions"><Button type="submit">Salvar nome do espaço</Button></div>
          {nameError && <p role="alert">{nameError}</p>}
          {nameSaved && <p role="status">Nome salvo nesta sessão e atualizado na página pública.</p>}
          <p className="muted">A alteração dura até recarregar a página, como as cores e a logo.</p>
        </form>
      </CardContent></Card>
      <AppearanceEditor appearance={appearance} setAppearance={setAppearance} studioName={studioName} />
      <Card>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const name = draft.name.trim();
              if (!name || !nameDraft.trim()) { setProfileError("Informe seu nome e o nome do espaço."); return; }
              if (draft.closes <= draft.opens) { setProfileError("O fim do expediente deve ser depois do início."); return; }
              const next = { ...draft, name };
              const displayedName = saveProfile(next, nameDraft.trim() !== studioName ? nameDraft.trim() : undefined);
              setDraft(next); setNameDraft(displayedName); setProfileError(""); setNameSaved(false);
              setSaved(true);
            }}
          >
            <div className="form-grid">
              <Field label="Seu nome">
                <Input required maxLength={100} value={draft.name} onChange={e => updateDraft("name", e.target.value)} />
              </Field>
              <Field label="Telefone">
                <Input type="tel" placeholder="(65) 99999-9999" value={draft.phone} onChange={e => updateDraft("phone", e.target.value)} />
              </Field>
              <Field label="E-mail">
                <Input type="email" placeholder="Use somente dados fictícios" value={draft.email} onChange={e => updateDraft("email", e.target.value)} />
              </Field>
              <Field label="Especialidade">
                <select
                  value={specialty}
                  onChange={(e) => updateDraft("specialty", e.target.value)}
                >
                  {[
                    "Unhas",
                    "Cílios",
                    "Sobrancelhas",
                    "Cabelos",
                    "Depilação",
                    "Estética",
                    "Outros",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </Field>
              <Field label="Fuso horário">
                <select value={draft.timezone} onChange={e => updateDraft("timezone", e.target.value)}>
                  <option>America/Cuiaba</option>
                  <option>America/Sao_Paulo</option>
                </select>
              </Field>
              <Field label="Início do expediente (seg. a sex.)">
                <Input type="time" value={draft.opens} onChange={e => updateDraft("opens", e.target.value)} required />
              </Field>
              <Field label="Fim do expediente (seg. a sex.)">
                <Input type="time" value={draft.closes} onChange={e => updateDraft("closes", e.target.value)} required />
              </Field>
            </div>
            <p className="notice">
              Sugestões para {specialty}:{" "}
              {specialty === "Unhas"
                ? "Manicure, pedicure e esmaltação em gel"
                : "Configure os serviços que você oferece"}
              . Adicione e personalize em Serviços.
            </p>
            <Button type="submit">Salvar perfil nesta sessão</Button>
            {profileError && <p role="alert">{profileError}</p>}
            {saved && (
              <p role="status">
                Perfil atualizado nesta sessão. As alterações serão perdidas ao recarregar a página. Nenhum dado foi enviado.
              </p>
            )}
          </form>
        </CardContent>
      </Card>
      <p className="muted intro">
        Plano planejado: R$ 19,90/mês · 1 profissional · 100 e-mails/mês como
        franquia inicial configurável. Cobrança e envio não disponíveis.
      </p>
    </>
  );
}
function Booking({ services, appearance, studioName }: { services: Service[]; appearance: Appearance; studioName: string }) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [done, setDone] = useState(false);
  const active = services.filter((s) => s.active);
  const selected = active.filter(s => selectedIds.includes(s.id));
  const totalMinutes = selected.reduce((total, s) => total + s.duration, 0);
  const totalPrice = selected.reduce((total, s) => total + Math.round(s.price * 100), 0) / 100;
  return (
    <div className="public-theme public-page" style={appearanceStyle(appearance)}><main className="booking">
      <Link to="/" className="back-link">
        ← Voltar ao painel demonstrativo
      </Link>
      <div className="booking-header">
        <StudioLogo logo={appearance.logo} studioName={studioName} />
        <p className="eyebrow">SEU MOMENTO DE CUIDADO</p>
        <h1>{studioName}</h1>
        <p>Um tempo só seu. Escolha como quer se cuidar.</p>
      </div>
      <div className="notice">
        Demonstração · horários fictícios, sem reserva real. Use dados
        fictícios.
      </div>
      {done ? (
        <Card>
          <CardContent className="booking-success">
            <Sparkles size={36} />
            <h2>Seu fluxo está completo!</h2>
            <p>
              Simulação de {selected.map(s => s.name).join(" + ")} em{" "}
              {date.split("-").reverse().join("/")} às {time}.
            </p>
            <p>{selected.length} serviço(s) · {totalMinutes} minutos · Total: {money(totalPrice)}</p>
            <strong>
              Nenhum horário foi reservado e nenhuma mensagem foi enviada.
            </strong>
            <Button
              onClick={() => {
                setDone(false);
                setSelectedIds([]);
                setTime("");
                setDate("");
              }}
            >
              Simular novamente
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <h2 className="step-title">
            01 <span>Escolha seus serviços</span>
          </h2>
          <p className="muted intro">Selecione um ou mais serviços para o mesmo atendimento. Toque novamente para remover.</p>
          <div className="booking-services">
            {active.map((s) => (
              <button
                className={`service-choice ${selectedIds.includes(s.id) ? "selected" : ""}`}
                key={s.id}
                aria-pressed={selectedIds.includes(s.id)}
                onClick={() => {
                  setSelectedIds(previous => previous.includes(s.id) ? previous.filter(id => id !== s.id) : [...previous, s.id]);
                  setTime("");
                }}
              >
                <Sparkles size={22} />
                <span>
                  <strong>{s.name}</strong>
                  <small>{s.duration} minutos</small>
                  {selectedIds.includes(s.id) && <small>✓ Selecionado</small>}
                </span>
                <b>{money(s.price)}</b>
              </button>
            ))}
          </div>
          {!active.length && (
            <p>Nenhum serviço ativo. Ative um serviço no painel.</p>
          )}
          {selected.length > 0 && <div className="booking-summary" role="status" aria-live="polite"><strong>{selected.length} {selected.length === 1 ? "serviço selecionado" : "serviços selecionados"}</strong><p>{selected.map(s => s.name).join(" + ")}</p><p>{totalMinutes} minutos no total · <strong>{money(totalPrice)}</strong></p></div>}
          {selected.length > 0 && (
            <section>
              <h2 className="step-title">
                02 <span>Escolha uma data e um horário</span>
              </h2>
              <Field label="Data desejada">
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => {
                    setDate(e.target.value);
                    setTime("");
                  }}
                  min={new Date().toLocaleDateString("en-CA")}
                  required
                />
              </Field>
              {date && (
                <>
                  <p className="muted intro">
                    Horários de exemplo; não representam disponibilidade real.
                  </p>
                  <div className="time-slots">
                    {["09:00", "10:00", "13:30", "15:00"].map((t) => (
                      <Button
                        key={t}
                        variant={time === t ? "default" : "outline"}
                        onClick={() => setTime(t)}
                        aria-pressed={time === t}
                      >
                        {t}
                      </Button>
                    ))}
                  </div>
                </>
              )}
            </section>
          )}
          {time && selected.length > 0 && (
            <section>
              <h2 className="step-title">
                03 <span>Seus dados</span>
              </h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setDone(true);
                }}
              >
                <div className="form-grid">
                  <Field label="Nome">
                    <Input
                      name="name"
                      required
                      maxLength={100}
                      autoComplete="off"
                    />
                  </Field>
                  <Field label="Telefone com DDD">
                    <Input
                      name="phone"
                      type="tel"
                      required
                      pattern="[0-9\s\(\)\+\-]{10,20}"
                      title="Informe de 10 a 20 caracteres, incluindo DDD."
                      autoComplete="off"
                    />
                  </Field>
                  <Field label="E-mail (opcional)">
                    <Input type="email" name="email" autoComplete="off" />
                  </Field>
                </div>
                <label className="consent">
                  <input type="checkbox" /> Quero receber convites futuros para
                  retornar (opcional e revogável).
                </label>
                <p className="muted">
                  Nesta demonstração, seus dados não são enviados nem
                  persistidos.
                </p>
                <Button type="submit" className="booking-submit">
                  Concluir simulação · {money(totalPrice)}
                </Button>
              </form>
            </section>
          )}
        </>
      )}
    </main></div>
  );
}
export default function App() {
  const [services, setServices] = useState(initialServices);
  const [appearance, setAppearance] = useState<Appearance>({ ...defaultAppearance });
  const [profile, setProfile] = useState<ProfessionalProfile>({ name: "Ana Oliveira", phone: "", email: "", specialty: "Unhas", timezone: "America/Cuiaba", opens: "09:00", closes: "18:00" });
  const [customStudioName, setStudioName] = useState<string | null>(null);
  const studioName = customStudioName ?? `Ateliê ${profile.name}`;
  function saveProfile(next: ProfessionalProfile, spaceName?: string) {
    setProfile(next);
    if (spaceName !== undefined) setStudioName(spaceName);
    return spaceName ?? customStudioName ?? `Ateliê ${next.name}`;
  }
  return (
    <Routes>
      <Route path="/agendar/ana" element={<Booking services={services} appearance={appearance} studioName={studioName} />} />
      <Route
        path="*"
        element={
          <div className="app-shell">
            <aside className="sidebar">
              <Link to="/" className="brand">
                levia<span>agenda</span>
                <i>●</i>
              </Link>
              <p className="workspace-label">SEU ESPAÇO</p>
              <nav aria-label="Navegação principal">
                {navigation.map(({ path, label, icon: Icon }) => (
                  <NavLink end={path === "/"} key={path} to={path}>
                    <Icon size={19} />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </nav>
              <div className="sidebar-bottom">
                <Leaf size={26} />
                <p>
                  Mais tempo para cuidar.
                  <br />
                  Mais leveza para crescer.
                </p>
                <span className="demo-pill">ETAPA 1 · DEMONSTRAÇÃO</span>
              </div>
            </aside>
            <div className="workspace">
              <header className="topbar">
                <span>{studioName}</span>
                <div>
                  <span className="demo-pill">Modo demonstração</span>
                  <span className="avatar" aria-label={profile.name}>{profile.name.split(/\s+/).slice(0, 2).map(word => Array.from(word)[0]).join("").toLocaleUpperCase("pt-BR")}</span>
                </div>
              </header>
              <div className="demo-banner">
                Dados fictícios · alterações temporárias · nenhuma integração
                ativa
              </div>
              <main id="main-content" className="main">
                <Routes>
                  <Route path="/" element={<Dashboard professionalName={profile.name} />} />
                  <Route path="/agenda" element={<Agenda />} />
                  <Route
                    path="/servicos"
                    element={
                      <Services services={services} setServices={setServices} />
                    }
                  />
                  <Route path="/clientes" element={<Clients />} />
                  <Route path="/perfil" element={<Profile appearance={appearance} setAppearance={setAppearance} studioName={studioName} setStudioName={setStudioName} profile={profile} saveProfile={saveProfile} />} />
                  <Route
                    path="*"
                    element={
                      <>
                        <h1>Página não encontrada</h1>
                        <Link to="/">Voltar ao início</Link>
                      </>
                    }
                  />
                </Routes>
              </main>
              <footer>
                Levia Agenda <span>Feita para deixar seu dia mais leve.</span>
              </footer>
            </div>
          </div>
        }
      />
    </Routes>
  );
}
