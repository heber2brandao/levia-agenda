import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import BookingForm from "./BookingForm";
import { StudioLogo } from "./components/AppearanceEditor";
import { appearanceStyle } from "./lib/appearance";
import { businessRequest, type Offer } from "./lib/business";

type Space = {
  studio_name: string;
  timezone: string;
  logo: string | null;
  primary_color: string;
  background_color: string;
  services: Offer[];
};
export default function PublicBooking() {
  const { tenant } = useParams();
  const [space, setSpace] = useState<Space | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setSpace(null);
    setError("");
    businessRequest<Space>(
      `/public/${tenant}`,
      undefined,
      undefined,
      "GET",
      controller.signal,
    )
      .then(setSpace)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [tenant]);
  if (error)
    return (
      <main className="account-page">
        <h1>Não foi possível abrir este espaço</h1>
        <p role="alert">{error}</p>
      </main>
    );
  if (!space)
    return (
      <main className="account-page" role="status">
        Carregando serviços…
      </main>
    );
  return (
    <main
      className="public-theme public-real"
      style={appearanceStyle({
        primary: space.primary_color,
        background: space.background_color,
        logo: space.logo,
      })}
    >
      <header>
        <StudioLogo logo={space.logo} studioName={space.studio_name} />
        <h1>{space.studio_name}</h1>
        <p>Um tempo só seu. Escolha seu próximo cuidado.</p>
      </header>
      <BookingForm
        offers={space.services}
        zone={space.timezone}
        base={`/public/${tenant}`}
      />
      <footer>Agendamento pelo Levia Agenda</footer>
    </main>
  );
}
