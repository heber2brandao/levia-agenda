import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "./components/ui/button";
import { businessRequest } from "./lib/business";

export default function EmailPreferences() {
  const { token } = useParams();
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function revoke() {
    setBusy(true); setError("");
    try { await businessRequest("/public/email/preferences", undefined, { token }); setDone(true); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="account-page">
    <h1>Preferências de e-mail</h1>
    {done ? <p role="status">Você não receberá novos convites de retorno deste espaço. Seus agendamentos continuam válidos.</p> : <>
      <p>Você pode deixar de receber convites de retorno. Confirmações e lembretes de atendimentos já agendados são separados.</p>
      <Button disabled={busy} onClick={() => void revoke()}>{busy ? "Salvando…" : "Não receber convites de retorno"}</Button>
    </>}
    {error && <p role="alert">{error}</p>}
  </main>;
}
