import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError, profileRequest, type AccountProfile } from "@/lib/api";
import { loadCatalog, type CatalogService } from "@/lib/catalog-api";
import { StudioLogo } from "./components/AppearanceEditor";

export default function AccountDashboard({ session }: { session: Session }) {
  const token = useRef(session.access_token);
  token.current = session.access_token;
  const [data, setData] = useState<{
    profile: AccountProfile;
    services: CatalogService[];
  } | null>(null);
  const [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [incomplete, setIncomplete] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setIncomplete(false);
    Promise.all([
      profileRequest(token.current, controller.signal),
      loadCatalog(token.current, controller.signal),
    ])
      .then(([profile, services]) => {
        if (!controller.signal.aborted) setData({ profile, services });
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          if (reason instanceof ApiError && reason.status === 404)
            setIncomplete(true);
          else
            setError("Não foi possível carregar seu painel. Tente novamente.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [session.user.id, retry]);
  if (loading) return <p role="status">Carregando seu painel…</p>;
  if (error)
    return (
      <div role="alert">
        <p>{error}</p>
        <Button onClick={() => setRetry((n) => n + 1)}>Tentar novamente</Button>
      </div>
    );
  if (incomplete || !data)
    return (
      <section>
        <h2>Bem-vinda ao Levia</h2>
        <p>Complete seu perfil para começar a organizar seu espaço.</p>
        <Button asChild>
          <Link to="/conta/perfil">Completar meu perfil</Link>
        </Button>
      </section>
    );
  const { profile, services } = data;
  return (
    <section className="account-dashboard">
      <div className="dashboard-welcome">
        <StudioLogo logo={profile.logo} studioName={profile.studio_name} />
        <div>
          <p className="eyebrow">SEU PAINEL</p>
          <h2>{profile.studio_name}</h2>
          <p>Olá, {profile.name}. O que vamos organizar hoje?</p>
        </div>
      </div>
      <div className="service-grid">
        <Card>
          <CardContent>
            <h3>Meu perfil e minha marca</h3>
            <p>Nome do espaço, logo, cores e horários de funcionamento.</p>
            <Button asChild variant="outline">
              <Link to="/conta/perfil">Editar meu perfil</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <h3>Meus serviços</h3>
            <p>
              {services.filter((s) => s.active).length} ativos ·{" "}
              {services.length} cadastrados
            </p>
            <Button asChild>
              <Link to="/conta/servicos">Serviços e horários</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
      <p className="muted">
        Agenda de atendimentos e gestão de clientes estarão disponíveis na
        próxima etapa.
      </p>
    </section>
  );
}
