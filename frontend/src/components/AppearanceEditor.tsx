import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { appearanceStyle, defaultAppearance, readLogo, type Appearance } from "@/lib/appearance";

export function StudioLogo({ logo, studioName }: { logo: string | null; studioName: string }) {
  const initials = studioName.trim().split(/\s+/).slice(0, 2).map(word => Array.from(word)[0]).join("").toLocaleUpperCase("pt-BR");
  return logo ? <img className="studio-logo" src={logo} alt={`Logo de ${studioName}`} /> : <span className="studio-mark" aria-label={studioName}>{initials}</span>;
}

export default function AppearanceEditor({ appearance, setAppearance, studioName }: {
  appearance: Appearance; setAppearance: Dispatch<SetStateAction<Appearance>>; studioName: string;
}) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const uploadVersion = useRef(0);
  useEffect(() => () => { uploadVersion.current += 1; }, []);

  function clearLogo(reset = false) {
    uploadVersion.current += 1;
    setLoading(false); setError("");
    setAppearance(previous => reset ? { ...defaultAppearance } : { ...previous, logo: null });
    setMessage(reset ? "Aparência padrão restaurada." : "Logo removida.");
  }
  async function selectLogo(file?: File) {
    if (!file) return;
    const version = ++uploadVersion.current;
    setError(""); setMessage(""); setLoading(true);
    try {
      const logo = await readLogo(file);
      if (version !== uploadVersion.current) return;
      setAppearance(previous => ({ ...previous, logo }));
      setMessage("Logo aplicada nesta sessão. Nenhum arquivo foi enviado.");
    } catch (reason) {
      if (version === uploadVersion.current) setError(reason instanceof Error ? reason.message : "Não foi possível ler a logo.");
    } finally {
      if (version === uploadVersion.current) setLoading(false);
    }
  }

  return <section className="appearance-editor" aria-labelledby="appearance-title">
    <div className="section-heading"><div><p className="eyebrow">A IDENTIDADE DO SEU ESPAÇO</p><h2 id="appearance-title">Aparência</h2></div></div>
    <p className="muted intro">Personalize sua página de agendamento. As mudanças aparecem na hora e duram até atualizar a página.</p>
    <div className="appearance-grid">
      <Card><CardContent className="appearance-controls">
        <label className="field"><span>Logo do espaço</span><Input type="file" accept="image/png,image/jpeg,image/webp" aria-describedby="logo-help" onChange={e => { void selectLogo(e.target.files?.[0]); e.target.value = ""; }} /></label>
        <p id="logo-help" className="muted">PNG, JPG ou WebP, até 2 MB e 4096 × 4096 pixels. A imagem fica somente neste navegador.</p>
        {(appearance.logo || loading) && <Button variant="outline" onClick={() => clearLogo()}>Remover logo</Button>}
        <div className="palette-fields">{([{ key: "primary", label: "Cor principal" }, { key: "background", label: "Cor de fundo" }] as const).map(({key,label}) => <label className="field" key={key}><span>{label}</span><div className="color-control"><input type="color" value={appearance[key]} aria-label={label} onChange={e => setAppearance(previous => ({ ...previous, [key]: e.target.value }))}/><code>{appearance[key].toUpperCase()}</code></div></label>)}</div>
        <p className="muted">A cor dos textos se ajusta automaticamente para manter a leitura.</p>
        <div className="actions"><Button variant="outline" onClick={() => clearLogo(true)}>Restaurar padrão</Button><Button asChild><Link to="/agendar/ana">Ver página personalizada</Link></Button></div>
        {(loading || message) && <p role="status" className="muted">{loading ? "Preparando logo…" : message}</p>}
        {error && <p role="alert" className="upload-error">{error}</p>}
      </CardContent></Card>
      <div><p className="preview-label">PRÉVIA DA SUA PÁGINA</p><div className="public-theme appearance-preview" style={appearanceStyle(appearance)} aria-label="Prévia da página pública"><StudioLogo logo={appearance.logo} studioName={studioName}/><h3>{studioName}</h3><p>Um tempo só seu.</p><div className="preview-service"><strong>Manicure</strong><span>45 min · R$ 35,00</span></div><span className="preview-button">Escolher horário</span><small>Exemplo visual · sem reserva</small></div></div>
    </div>
  </section>;
}
