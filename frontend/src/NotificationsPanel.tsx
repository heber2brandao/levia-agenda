import { useEffect, useState } from "react";
import { Button } from "./components/ui/button";
import { Card, CardContent } from "./components/ui/card";
import { businessRequest } from "./lib/business";

type Notifications = {
  unread: number;
  items: { id: string; title: string; message: string; read: boolean }[];
  email: { enabled: boolean; limit: number; reserved: number; month: string; statuses: Record<string, number> };
};

export default function NotificationsPanel({ token }: { token: string }) {
  const [data, setData] = useState<Notifications | null>(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    businessRequest<Notifications>("/me/notifications", token, undefined, "GET", controller.signal)
      .then(value => { if (!controller.signal.aborted) setData(value); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [token, reload]);
  async function mark(id: string) {
    setBusy(true); setError("");
    try {
      await businessRequest(`/me/notifications/${id}/read`, token, {}, "PUT");
      setReload(n => n + 1);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <Card className="notifications-panel"><CardContent>
    <h2>Avisos {data ? `(${data.unread} não lidos)` : ""}</h2>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p role="status">Carregando avisos…</p>}
    {data && <>
      {data.items.length === 0 && <p>Nenhum aviso por enquanto. Novos agendamentos aparecerão aqui.</p>}
      {data.items.slice(0, 5).map(notice => <div className="notice-row" key={notice.id}>
        <div><strong>{notice.title}</strong><p>{notice.message}</p></div>
        {!notice.read && <Button variant="outline" disabled={busy} onClick={() => void mark(notice.id)}>Marcar como lido</Button>}
      </div>)}
      {data.items.length > 5 && <details><summary>Mais avisos recentes</summary>
        {data.items.slice(5).map(notice => <div className="notice-row" key={notice.id}>
          <div><strong>{notice.title}</strong><p>{notice.message}</p></div>
          {!notice.read && <Button variant="outline" disabled={busy} onClick={() => void mark(notice.id)}>Marcar como lido</Button>}
        </div>)}
      </details>}
      <details className="email-status"><summary>E-mails e franquia mensal</summary>
        <p>{data.email.enabled ? "Envios habilitados. O processamento depende do worker em execução." : "Envios desativados — aguardando configuração do serviço de e-mail."}</p>
        <p>{data.email.reserved} de {data.email.limit} e-mails reservados no mês {data.email.month.slice(0, 7).split("-").reverse().join("/")}.</p>
        <p className="muted">A reserva inclui envios aceitos e tentativas com resultado incerto. Não comprova entrega na caixa de entrada.</p>
        <p>Pendentes: {data.email.statuses.pending || 0} · Aceitos pelo provedor: {data.email.statuses.accepted || 0} · Limite atingido: {data.email.statuses.quota || 0} · Precisam de revisão: {(data.email.statuses.review || 0) + (data.email.statuses.failed || 0)}</p>
      </details>
    </>}
  </CardContent></Card>;
}
