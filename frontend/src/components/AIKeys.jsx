import { useEffect, useState } from "react";
import { api } from "../api";
import { inputCls, primaryBtn } from "./ui";

const PROVIDERS = [
  ["gemini", "Gemini", "Google AI Studio", "https://aistudio.google.com/apikey"],
  ["claude", "Claude", "Anthropic", "https://console.anthropic.com/settings/keys"],
  ["openai", "OpenAI", "ChatGPT", "https://platform.openai.com/api-keys"],
  ["groq", "Groq", "GPT-OSS 20B · plan gratuito", "https://console.groq.com/keys"],
  ["openrouter", "OpenRouter", "Router automático de modelos gratuitos", "https://openrouter.ai/settings/keys"],
];

export default function AIKeys() {
  const [saved, setSaved] = useState({});
  const [values, setValues] = useState({});
  const [msg, setMsg] = useState({ text: "", error: false });

  async function load() {
    try {
      const rows = await api.listKeys();
      setSaved(Object.fromEntries(rows.map((r) => [r.provider, r.hint])));
    } catch (e) {
      setMsg({ text: e.message, error: true });
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function save(provider, name) {
    setMsg({ text: "", error: false });
    try {
      await api.saveKey(provider, values[provider] || "");
      setValues((v) => ({ ...v, [provider]: "" }));
      setMsg({ text: `Clave de ${name} guardada`, error: false });
      load();
    } catch (e) {
      setMsg({ text: e.message, error: true });
    }
  }

  async function remove(provider, name) {
    setMsg({ text: "", error: false });
    try {
      await api.deleteKey(provider);
      setMsg({ text: `Clave de ${name} eliminada`, error: false });
      load();
    } catch (e) {
      setMsg({ text: e.message, error: true });
    }
  }

  return (
    <div className="ai-keys-page max-w-3xl">
      <h1 className="text-2xl font-semibold">Claves de IA</h1>
      <p className="mt-2 text-muted">
        La IA lee cada oferta y te explica por qué encaja contigo. Cada persona usa su propia clave,
        que se guarda cifrada y no vuelve a mostrarse completa. Groq ofrece GPT-OSS 20B con límites
        gratuitos publicados de 30 solicitudes/minuto, 1.000 solicitudes/día, 8.000 tokens/minuto
        y 200.000 tokens/día.
        OpenRouter usa <code>openrouter/free</code>, que selecciona un modelo
        gratuito disponible; el límite publicado para cuentas sin créditos comprados es de 50
        solicitudes al día. Los cupos y modelos pueden cambiar, y no configuramos respaldo a modelos pagos.
      </p>

      <ul className="mt-6 divide-y divide-line rounded-xl border border-line bg-white">
        {PROVIDERS.map(([id, name, note, keyUrl]) => (
          <li key={id} className="space-y-3 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">{name}</h2>
                <p className="text-sm text-muted">
                  {note} ·{" "}
                  <a href={keyUrl} target="_blank" rel="noreferrer" className="font-medium text-brand-600 hover:underline">
                    Obtener clave
                  </a>
                </p>
              </div>
              {saved[id] ? (
                <span className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
                  Guardada ({saved[id]})
                </span>
              ) : (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-muted">
                  Sin clave
                </span>
              )}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="password"
                autoComplete="off"
                aria-label={`Clave de ${name}`}
                placeholder="Pega aquí tu clave"
                className={`${inputCls} flex-1`}
                value={values[id] || ""}
                onChange={(e) => setValues((v) => ({ ...v, [id]: e.target.value }))}
              />
              <button
                type="button"
                onClick={() => save(id, name)}
                disabled={!values[id] || values[id].length < 10}
                className={primaryBtn}
              >
                {saved[id] ? "Reemplazar clave" : "Guardar clave"}
              </button>
              {saved[id] && (
                <button
                  type="button"
                  onClick={() => remove(id, name)}
                  className="rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  Eliminar
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <p
        role="status"
        className={`mt-4 text-sm ${msg.error ? "text-red-600" : "text-muted"}`}
      >
        {msg.text}
      </p>
    </div>
  );
}
