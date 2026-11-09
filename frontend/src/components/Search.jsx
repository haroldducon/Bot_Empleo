import { useEffect, useState } from "react";
import { api } from "../api";
import { primaryBtn } from "./ui";
import dashboardInsights from "../assets/dashboard-panorama.jpg";

function sourceStatus(st) {
  if (st.state === "pending") return { text: "En espera", cls: "text-muted" };
  if (st.state === "running")
    return { text: `Buscando... (${st.found} ofertas)`, cls: "text-brand-700" };
  if (st.state === "error") return { text: st.error || "Error", cls: "text-red-600" };
  return { text: `${st.found} ofertas`, cls: "text-brand-700" };
}

const GMAIL_CALLBACK_MESSAGES = {
  connected: "Gmail conectado. Selecciona la etiqueta que contiene las alertas de empleo.",
  denied: "No se concedió acceso a Gmail.",
  error: "No se pudo completar la conexión de Gmail. Intenta nuevamente.",
  state_error: "El intento de conexión venció o no es válido. Intenta nuevamente.",
};

export default function Search({ onViewJobs }) {
  const [sources, setSources] = useState([]);
  const [selected, setSelected] = useState([]);
  const [run, setRun] = useState({ state: "idle" });
  const [error, setError] = useState("");
  const [gmail, setGmail] = useState(null);
  const [gmailLabels, setGmailLabels] = useState([]);
  const [gmailLabel, setGmailLabel] = useState("");
  const [gmailBusy, setGmailBusy] = useState(false);
  const [gmailMessage, setGmailMessage] = useState(() => {
    const status = new URLSearchParams(window.location.search).get("gmail");
    return GMAIL_CALLBACK_MESSAGES[status] || "";
  });
  const running = run.state === "running";

  useEffect(() => {
    let active = true;
    const callbackStatus = new URLSearchParams(window.location.search).get("gmail");
    if (callbackStatus) {
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
    }

    async function load() {
      try {
        const status = await api.gmailStatus();
        if (!active) return;
        setGmail(status);
        setGmailLabel(status.label_id || "");
        if (status.connected) {
          try {
            const labels = await api.gmailLabels();
            if (active) setGmailLabels(labels);
          } catch (e) {
            if (active) setGmailMessage(e.message);
          }
        }
      } catch (e) {
        if (active) setGmailMessage(e.message);
      }
      try {
        const availableSources = await api.sources();
        if (active) {
          setSources(availableSources);
          setSelected(availableSources.filter((source) => source.available).map((source) => source.key));
        }
      } catch (e) {
        if (active) setError(e.message);
      }
      try {
        const status = await api.searchStatus();
        if (active) setRun(status);
      } catch {
        /* Se conserva el estado inicial si aún no hay una ejecución. */
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(async () => {
      try {
        setRun(await api.searchStatus());
      } catch {
        /* se reintenta en el siguiente ciclo */
      }
    }, 2000);
    return () => clearInterval(id);
  }, [running]);

  async function start() {
    setError("");
    try {
      setRun(await api.runSearch(selected));
    } catch (e) {
      setError(e.message);
    }
  }

  async function connectGmail() {
    setGmailBusy(true);
    setGmailMessage("");
    try {
      const result = await api.gmailConnect();
      window.location.assign(result.authorization_url);
    } catch (e) {
      setGmailMessage(e.message);
      setGmailBusy(false);
    }
  }

  async function saveGmailLabel() {
    if (!gmailLabel) return;
    setGmailBusy(true);
    setGmailMessage("");
    try {
      const status = await api.gmailSelectLabel(gmailLabel);
      setGmail((current) => ({ ...current, ...status, configured: true }));
      const availableSources = await api.sources();
      setSources(availableSources);
      setSelected((current) =>
        availableSources.some((source) => source.key === "alertas" && source.available)
          ? [...new Set([...current, "alertas"])]
          : current.filter((key) => key !== "alertas"),
      );
      setGmailMessage(`La app consultará la etiqueta “${status.label_name}” y validará que los mensajes provengan de LinkedIn.`);
    } catch (e) {
      setGmailMessage(e.message);
    } finally {
      setGmailBusy(false);
    }
  }

  async function disconnectGmail() {
    if (!window.confirm("¿Desconectar Gmail y revocar el acceso de Nexo Laboral?")) return;
    setGmailBusy(true);
    try {
      await api.gmailDisconnect();
      setGmail({ ...gmail, connected: false, email: null, label_id: null, label_name: null, label_configured: false });
      setGmailLabels([]);
      setGmailLabel("");
      const availableSources = await api.sources();
      setSources(availableSources);
      setSelected((current) => current.filter((key) => key !== "alertas"));
      setGmailMessage("Gmail quedó desconectado.");
    } catch (e) {
      setGmailMessage(e.message);
    } finally {
      setGmailBusy(false);
    }
  }

  const toggle = (key) =>
    setSelected((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));

  return (
    <div className="search-page">
      <section className="search-hero">
        <div className="search-hero-copy">
          <span className="search-eyebrow"><span /> EMPLEO, CON MEJORES DATOS</span>
          <h1>Tu siguiente oportunidad empieza aquí.</h1>
          <p>Busca en varias fuentes y descubre las ofertas que mejor encajan con tu experiencia y lo que quieres.</p>
          <div className="search-hero-proof"><span>✦</span> Coincidencias inteligentes <i /> Perfil personalizado <i /> Análisis con IA</div>
        </div>
        <div className="search-hero-art" aria-hidden="true"><img src={dashboardInsights} alt="" /></div>
        <div className="search-hero-glow" />
      </section>

      <div className="search-section-heading">
        <div><span className="section-kicker">CONFIGURA TU BÚSQUEDA</span><h2>Elige tus fuentes</h2></div>
        <p>Usaremos los cargos, la ciudad y las habilidades de tu perfil.</p>
      </div>

      <ul className="mt-5 divide-y divide-line rounded-xl border border-line bg-white">
        {sources.map((source) => {
          const st = run.sources?.[source.key];
          const info = st ? sourceStatus(st) : null;
          const isLinkedIn = source.key === "alertas";
          return (
            <li key={source.key} className="flex flex-col items-start justify-between gap-1 px-4 py-3 sm:flex-row sm:items-center sm:gap-3">
              <div className="min-w-0 w-full">
                <label className={`flex items-center gap-3 ${source.available ? "" : "opacity-70"}`}>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-brand-600"
                    disabled={!source.available || running}
                    checked={selected.includes(source.key)}
                    onChange={() => toggle(source.key)}
                  />
                  <span className="font-medium">{source.label}</span>
                  {!source.available && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-muted">
                      {isLinkedIn && gmail?.configured ? "Conecta Gmail" : source.key === "jooble" ? "Requiere API" : isLinkedIn ? "Configurar Google" : "Pronto"}
                    </span>
                  )}
                </label>
                {!source.available && source.setup_hint && (
                  <p className="ml-7 mt-1 max-w-2xl text-xs leading-relaxed text-muted">{source.setup_hint}</p>
                )}
                {source.available && source.notice && (
                  <p className="ml-7 mt-1 max-w-2xl text-xs leading-relaxed text-muted">{source.notice}</p>
                )}

                {isLinkedIn && gmail?.configured && !gmail.connected && (
                  <div className="ml-7 mt-3 flex flex-wrap items-center gap-3">
                    <button type="button" className={primaryBtn} onClick={connectGmail} disabled={gmailBusy}>
                      {gmailBusy ? "Conectando…" : "Conectar Gmail"}
                    </button>
                    <span className="max-w-2xl text-xs leading-relaxed text-muted">
                      Google concede lectura del buzón completo, no solo de una etiqueta. Nexo Laboral está programado para consultar únicamente la etiqueta seleccionada y validar remitentes y enlaces de LinkedIn; conecta solo un Gmail dedicado a estas alertas.
                    </span>
                  </div>
                )}

                {isLinkedIn && gmail?.connected && (
                  <div className="ml-7 mt-3 space-y-3 rounded-xl border border-line bg-slate-50 p-3 sm:max-w-2xl">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm text-slate-700">Conectado como <strong>{gmail.email}</strong></p>
                      <button type="button" onClick={disconnectGmail} disabled={gmailBusy} className="text-xs font-medium text-red-700 underline underline-offset-2">
                        Desconectar
                      </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <label htmlFor="gmail-label" className="text-sm font-medium text-slate-700">Etiqueta de alertas</label>
                      <select
                        id="gmail-label"
                        value={gmailLabel}
                        onChange={(event) => setGmailLabel(event.target.value)}
                        className="min-w-48 rounded-lg border border-line bg-white px-3 py-2 text-sm"
                        disabled={gmailBusy || gmailLabels.length === 0}
                      >
                        <option value="">Selecciona una etiqueta</option>
                        {gmailLabels.map((label) => <option key={label.id} value={label.id}>{label.name}</option>)}
                      </select>
                      <button type="button" onClick={saveGmailLabel} disabled={gmailBusy || !gmailLabel} className="rounded-lg border border-brand-600 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50">
                        {gmailBusy ? "Guardando…" : "Usar etiqueta"}
                      </button>
                    </div>
                    <p className="text-xs leading-relaxed text-muted">
                      En Gmail, crea un filtro desde un correo de alerta de empleo de LinkedIn y asígnale una etiqueta; luego selecciónala aquí. Nexo Laboral solo consulta mensajes de esa etiqueta y verifica remitente y enlaces de empleo.
                    </p>
                  </div>
                )}
              </div>
              {info && <span className={`text-sm ${info.cls}`}>{info.text}</span>}
            </li>
          );
        })}
      </ul>

      <div className="mt-5 flex flex-wrap items-center gap-4">
        <button onClick={start} disabled={running || selected.length === 0} className={primaryBtn}>
          {running ? "Buscando…" : "Buscar ofertas ahora"}
        </button>
        {run.state === "done" && (
          <button onClick={onViewJobs} className="rounded-lg border border-brand-600 px-4 py-2.5 text-sm font-medium text-brand-700 hover:bg-brand-50">
            Ver mis ofertas
          </button>
        )}
      </div>

      <p role="status" className={`mt-3 text-sm ${run.state === "error" ? "text-red-600" : "text-muted"}`}>
        {run.message}
      </p>
      {gmailMessage && (
        <p role="status" className="mt-3 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">
          {gmailMessage}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
