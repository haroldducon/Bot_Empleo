import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Field, Section, TagInput, inputCls, primaryBtn } from "./ui";

const empty = {
  full_name: "",
  headline: [],
  summary: "",
  city: "",
  modality: "cualquiera",
  desired_titles: [],
  skills: [],
  salary_min: "",
  notification_email: "",
  notify_enabled: true,
  experiences: [],
  education: [],
};

function completeness(f) {
  const checks = [
    f.full_name,
    f.headline,
    f.summary,
    f.city,
    f.desired_titles.length,
    f.skills.length,
    f.experiences.length,
    f.education.length,
    f.notification_email,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function initials(name) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] || "?").toUpperCase() + (parts[1]?.[0] || "").toUpperCase();
}

export default function Profile({ avatarUrl = "", onProfileUpdated }) {
  const [form, setForm] = useState(empty);
  const [status, setStatus] = useState({ text: "", error: false });
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarStatus, setAvatarStatus] = useState({ text: "", error: false });
  const avatarInput = useRef(null);

  useEffect(() => {
    api
      .getProfile()
      .then((p) =>
        setForm({
          ...p,
          headline: (p.headline || "").split("\n").map((title) => title.trim()).filter(Boolean).slice(0, 4),
          salary_min: p.salary_min ?? "",
          experiences: p.experiences.map((e) => ({
            ...e,
            start_date: e.start_date ?? "",
            end_date: e.end_date ?? "",
          })),
          education: p.education.map((e) => ({
            ...e,
            start_year: e.start_year ?? "",
            end_year: e.end_year ?? "",
          })),
        })
      )
      .catch((e) => setStatus({ text: e.message, error: true }));
  }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setItem = (key, i, field, value) =>
    setForm((f) => ({
      ...f,
      [key]: f[key].map((it, idx) => (idx === i ? { ...it, [field]: value } : it)),
    }));
  const addItem = (key, item) => setForm((f) => ({ ...f, [key]: [...f[key], item] }));
  const removeItem = (key, i) =>
    setForm((f) => ({ ...f, [key]: f[key].filter((_, idx) => idx !== i) }));

  async function uploadAvatar(event) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setAvatarStatus({ text: "La foto no puede superar 2 MB.", error: true });
      return;
    }
    if (file.type && !["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setAvatarStatus({ text: "Elige una imagen JPG, PNG o WebP.", error: true });
      return;
    }

    setAvatarBusy(true);
    setAvatarStatus({ text: "Subiendo foto...", error: false });
    try {
      await api.uploadAvatar(file);
      setAvatarStatus({ text: "Foto de perfil actualizada.", error: false });
      onProfileUpdated?.();
    } catch (err) {
      setAvatarStatus({ text: err.message || "No se pudo guardar la foto.", error: true });
    } finally {
      setAvatarBusy(false);
    }
  }

  async function deleteAvatar() {
    setAvatarBusy(true);
    setAvatarStatus({ text: "Quitando foto...", error: false });
    try {
      await api.deleteAvatar();
      setAvatarStatus({ text: "Foto eliminada.", error: false });
      onProfileUpdated?.();
    } catch (err) {
      setAvatarStatus({ text: err.message || "No se pudo eliminar la foto.", error: true });
    } finally {
      setAvatarBusy(false);
    }
  }

  async function save(e) {
    e.preventDefault();
    setStatus({ text: "Guardando...", error: false });
    try {
      await api.saveProfile({
        full_name: form.full_name,
        headline: form.headline.join("\n"),
        summary: form.summary,
        city: form.city,
        modality: form.modality,
        desired_titles: Array.from(
          new Map([...form.headline, ...form.desired_titles].map((title) => [title.toLowerCase(), title])).values()
        ).slice(0, 34),
        skills: form.skills,
        salary_min: form.salary_min === "" ? null : Number(form.salary_min),
        notification_email: form.notification_email || null,
        notify_enabled: form.notify_enabled,
        experiences: form.experiences.map((x) => ({
          company: x.company,
          position: x.position,
          start_date: x.start_date || null,
          end_date: x.end_date || null,
          description: x.description || "",
        })),
        education: form.education.map((x) => ({
          institution: x.institution,
          degree: x.degree,
          field: x.field || "",
          start_year: x.start_year === "" ? null : Number(x.start_year),
          end_year: x.end_year === "" ? null : Number(x.end_year),
        })),
      });
      setStatus({ text: "Cambios guardados", error: false });
      onProfileUpdated?.();
    } catch (err) {
      setStatus({ text: err.message, error: true });
    }
  }

  const pct = completeness(form);

  return (
    <form onSubmit={save}>
      <div className="flex flex-col gap-5 pb-8 sm:flex-row sm:items-center">
        <div className="profile-avatar-large grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-full bg-brand-600 font-display text-xl font-semibold text-white">
          {avatarUrl ? <img className="h-full w-full object-cover" src={avatarUrl} alt="" /> : initials(form.full_name || "Tu perfil")}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-2xl font-semibold">
            {form.full_name || "Completa tu perfil"}
          </h1>
          <p className="truncate text-muted">
            {form.headline.length ? form.headline.join(" · ") : "Agrega tus cargos o especialidades para que el bot te entienda mejor."}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="rounded-lg border border-brand-600 bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-60"
              onClick={() => avatarInput.current?.click()}
              disabled={avatarBusy}
            >
              {avatarBusy ? "Procesando..." : avatarUrl ? "Cambiar foto" : "Agregar foto"}
            </button>
            {avatarUrl && (
              <button
                type="button"
                className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-muted hover:bg-canvas disabled:opacity-60"
                onClick={deleteAvatar}
                disabled={avatarBusy}
              >
                Quitar
              </button>
            )}
            <input
              ref={avatarInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={uploadAvatar}
              aria-label="Elegir foto de perfil"
            />
            <span className={`text-xs ${avatarStatus.error ? "text-red-600" : "text-muted"}`} role="status">
              {avatarStatus.text || "JPG, PNG o WebP · máximo 2 MB"}
            </span>
          </div>
        </div>
        <div className="w-full sm:w-56">
          <div className="flex justify-between text-sm">
            <span className="text-muted">Perfil completo</span>
            <span className="font-semibold">{pct}%</span>
          </div>
          <div className="mt-1.5 h-2 rounded-full bg-line">
            <div
              className="h-2 rounded-full bg-brand-600 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>

      <Section title="Datos básicos" hint="Así te presentas en tu perfil.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nombre completo">
            <input className={inputCls} value={form.full_name} onChange={(e) => set("full_name", e.target.value)} />
          </Field>
          <Field label="Cargos o especialidades principales" hint="Agrega hasta 4; cada uno se incluirá en los cargos que el bot compara.">
            <TagInput
              value={form.headline}
              onChange={(v) => set("headline", v)}
              placeholder="Ej. Analista de datos"
              maxTags={4}
              maxTagLength={45}
            />
          </Field>
        </div>
        <Field label="Resumen profesional" hint="Dos o tres frases sobre tu experiencia y lo que sabes hacer.">
          <textarea rows={4} className={inputCls} value={form.summary} onChange={(e) => set("summary", e.target.value)} />
        </Field>
      </Section>

      <Section title="Qué estás buscando" hint="El bot usa esto para filtrar y ordenar las ofertas.">
        <Field label="Otros cargos que te interesan" hint="Puedes agregar hasta 30 más. Pulsa Enter después de cada cargo; se buscarán junto con tus cargos principales.">
          <TagInput
            value={form.desired_titles}
            onChange={(v) => set("desired_titles", v)}
            placeholder="Ej. Analista de datos"
            maxTags={30}
          />
        </Field>
        <Field label="Habilidades" hint="Herramientas, idiomas o conocimientos. Pulsa Enter después de cada una.">
          <TagInput
            value={form.skills}
            onChange={(v) => set("skills", v)}
            placeholder="Ej. Excel, SQL, inglés"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Ciudad">
            <input className={inputCls} value={form.city} onChange={(e) => set("city", e.target.value)} />
          </Field>
          <Field label="Modalidad">
            <select className={inputCls} value={form.modality} onChange={(e) => set("modality", e.target.value)}>
              <option value="cualquiera">Cualquiera</option>
              <option value="remoto">Remoto</option>
              <option value="presencial">Presencial</option>
              <option value="hibrido">Híbrido</option>
            </select>
          </Field>
          <Field label="Salario mínimo (COP)" hint="Opcional.">
            <input type="number" min="0" className={inputCls} value={form.salary_min} onChange={(e) => set("salary_min", e.target.value)} />
          </Field>
        </div>
      </Section>

      <Section
        title="Experiencia laboral"
        hint="Empieza por el empleo más reciente. Deja la fecha final vacía si es tu trabajo actual."
      >
        {form.experiences.length === 0 && (
          <p className="text-sm text-muted">Aún no has agregado experiencia.</p>
        )}
        {form.experiences.map((x, i) => (
          <div key={i} className="space-y-3 rounded-lg border border-line bg-white p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Empresa">
                <input className={inputCls} value={x.company} onChange={(e) => setItem("experiences", i, "company", e.target.value)} />
              </Field>
              <Field label="Cargo">
                <input className={inputCls} value={x.position} onChange={(e) => setItem("experiences", i, "position", e.target.value)} />
              </Field>
              <Field label="Fecha de inicio">
                <input type="date" className={inputCls} value={x.start_date} onChange={(e) => setItem("experiences", i, "start_date", e.target.value)} />
              </Field>
              <Field label="Fecha de fin">
                <input type="date" className={inputCls} value={x.end_date} onChange={(e) => setItem("experiences", i, "end_date", e.target.value)} />
              </Field>
            </div>
            <Field label="Funciones y logros">
              <textarea rows={3} className={inputCls} value={x.description} onChange={(e) => setItem("experiences", i, "description", e.target.value)} />
            </Field>
            <button type="button" className="text-sm font-medium text-red-600 hover:underline" onClick={() => removeItem("experiences", i)}>
              Quitar experiencia
            </button>
          </div>
        ))}
        <button
          type="button"
          className="rounded-lg border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
          onClick={() =>
            addItem("experiences", { company: "", position: "", start_date: "", end_date: "", description: "" })
          }
        >
          Agregar experiencia
        </button>
      </Section>

      <Section title="Estudios" hint="Títulos, cursos y certificaciones.">
        {form.education.length === 0 && (
          <p className="text-sm text-muted">Aún no has agregado estudios.</p>
        )}
        {form.education.map((x, i) => (
          <div key={i} className="space-y-3 rounded-lg border border-line bg-white p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Institución">
                <input className={inputCls} value={x.institution} onChange={(e) => setItem("education", i, "institution", e.target.value)} />
              </Field>
              <Field label="Título">
                <input className={inputCls} value={x.degree} onChange={(e) => setItem("education", i, "degree", e.target.value)} />
              </Field>
              <Field label="Área de estudio">
                <input className={inputCls} value={x.field} onChange={(e) => setItem("education", i, "field", e.target.value)} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Año de inicio">
                  <input type="number" className={inputCls} value={x.start_year} onChange={(e) => setItem("education", i, "start_year", e.target.value)} />
                </Field>
                <Field label="Año de fin">
                  <input type="number" className={inputCls} value={x.end_year} onChange={(e) => setItem("education", i, "end_year", e.target.value)} />
                </Field>
              </div>
            </div>
            <button type="button" className="text-sm font-medium text-red-600 hover:underline" onClick={() => removeItem("education", i)}>
              Quitar estudio
            </button>
          </div>
        ))}
        <button
          type="button"
          className="rounded-lg border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
          onClick={() =>
            addItem("education", { institution: "", degree: "", field: "", start_year: "", end_year: "" })
          }
        >
          Agregar estudio
        </button>
      </Section>

      <Section title="Avisos por correo" hint="Aquí te llegará el resumen con las mejores ofertas.">
        <Field label="Correo de avisos">
          <input type="email" className={inputCls} value={form.notification_email} onChange={(e) => set("notification_email", e.target.value)} />
        </Field>
        <label className="flex items-center gap-2.5 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4 accent-brand-600"
            checked={form.notify_enabled}
            onChange={(e) => set("notify_enabled", e.target.checked)}
          />
          Quiero recibir las ofertas por correo
        </label>
      </Section>

      <div className="sticky bottom-0 -mx-4 flex items-center gap-4 border-t border-line bg-canvas/90 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
        <button className={primaryBtn}>Guardar cambios</button>
        <span
          role="status"
          className={`text-sm ${status.error ? "text-red-600" : "text-muted"}`}
        >
          {status.text}
        </span>
      </div>
    </form>
  );
}
