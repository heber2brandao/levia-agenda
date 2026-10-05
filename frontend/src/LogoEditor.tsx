import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { logoRequest } from "@/lib/api";
import { StudioLogo } from "./components/AppearanceEditor";

export default function LogoEditor({
  token,
  logo,
  studioName,
  onChange,
  onBusy,
}: {
  token: string;
  logo: string | null;
  studioName: string;
  onChange: (logo: string | null) => void;
  onBusy: (busy: boolean) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  async function save(file?: File) {
    setError("");
    setMessage("");
    if (
      file &&
      (file.size > 2 * 1024 * 1024 ||
        !["image/png", "image/jpeg", "image/webp"].includes(file.type))
    ) {
      setError("Escolha PNG, JPG ou WebP de até 2 MB.");
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    onBusy(true);
    try {
      const result = await logoRequest(token, controller.signal, file);
      if (!controller.signal.aborted) {
        onChange(result.logo);
        setMessage(
          file ? "Logo salva na sua conta." : "Logo removida da sua conta.",
        );
      }
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof Error
            ? reason.message
            : "Não foi possível salvar a logo.",
        );
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
        onBusy(false);
      }
    }
  }
  return (
    <section className="account-logo" aria-label="Logo do espaço">
      <StudioLogo logo={logo} studioName={studioName || "Seu espaço"} />
      <label className="field">
        Logo do espaço
        <Input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void save(file);
          }}
        />
      </label>
      <p className="muted">
        PNG, JPG ou WebP, até 2 MB e 4096 × 4096 pixels. A logo é salva
        automaticamente após selecionar. Salve seu perfil primeiro.
      </p>
      {logo && (
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          onClick={() => void save()}
        >
          Remover logo
        </Button>
      )}
      {(busy || message) && (
        <p role="status">{busy ? "Salvando logo…" : message}</p>
      )}
      {error && (
        <p role="alert" className="upload-error">
          {error}
        </p>
      )}
    </section>
  );
}
