import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import {
  CalendarDays,
  LayoutDashboard,
  Sparkles,
  Users,
  Settings,
  Leaf,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { profileRequest, type AccountProfile } from "./lib/api";
import { supabase } from "./lib/supabase";
import { StudioLogo } from "./components/AppearanceEditor";

const navigation = [
  { path: "/conta", label: "Visão geral", icon: LayoutDashboard },
  { path: "/conta/agenda", label: "Agenda", icon: CalendarDays },
  { path: "/conta/servicos", label: "Serviços", icon: Sparkles },
  { path: "/conta/clientes", label: "Clientes", icon: Users },
  { path: "/conta/faturamento", label: "Faturamento", icon: Wallet },
  { path: "/conta/perfil", label: "Meu espaço", icon: Settings },
];
export default function ProfessionalShell({
  session,
  children,
}: {
  session: Session;
  children: ReactNode;
}) {
  const [profile, setProfile] = useState<AccountProfile | null>(null),
    [error, setError] = useState("");
  const token = useRef(session.access_token);
  token.current = session.access_token;
  const { pathname } = useLocation();
  useEffect(() => {
    const c = new AbortController();
    profileRequest(token.current, c.signal)
      .then((p) => {
        if (!c.signal.aborted) setProfile(p);
      })
      .catch(() => {});
    return () => c.abort();
  }, [session.user.id, pathname]);
  return (
    <div className="app-shell connected-shell">
      <aside className="sidebar">
        <Link to="/conta" className="brand">
          levia<span>agenda</span>
          <i>●</i>
        </Link>
        <p className="workspace-label">SEU ESPAÇO</p>
        <nav aria-label="Navegação principal">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink end={path === "/conta"} to={path} key={path}>
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
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>{profile?.studio_name || "Seu espaço"}</span>
          <div>
            {profile && (
              <StudioLogo
                logo={profile.logo}
                studioName={profile.studio_name}
              />
            )}
            <Button
              variant="ghost"
              onClick={async () => {
                const result = await supabase!.auth.signOut();
                if (result.error)
                  setError("Não foi possível sair. Tente novamente.");
              }}
            >
              Sair
            </Button>
          </div>
        </header>
        <main id="main-content" className="main">
          {error && <p role="alert">{error}</p>}
          {children}
        </main>
        <footer>
          Levia Agenda <span>Feita para deixar seu dia mais leve.</span>
        </footer>
      </div>
    </div>
  );
}
