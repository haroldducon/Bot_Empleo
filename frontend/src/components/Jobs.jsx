import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";

const STATUS = {
  ok: { label: "Cumple", cls: "bg-brand-50 text-brand-700", bar: "bg-brand-600" },
  partial: { label: "Parcial", cls: "bg-amber-50 text-amber-800", bar: "bg-accent" },
  missing: { label: "No cumple", cls: "bg-red-50 text-red-700", bar: "bg-red-400" },
  unknown: { label: "No informado", cls: "bg-slate-100 text-slate-600", bar: "bg-slate-300" },
};
const WHERE = { profile: "En tu perfil", offer: "Depende de la oferta" };
const MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

function formatWeekStart(date) {
  if (!date) return "";
  const [, month, day] = date.split("-");
  return `${Number(day)} de ${MONTHS_ES[Number(month) - 1]}`;
}
const REC = {
  aplicar: { label: "Te conviene aplicar", cls: "bg-brand-50 text-brand-700" },
  revisar: { label: "Vale la pena revisarla", cls: "bg-amber-50 text-amber-800" },
  descartar: { label: "Mejor descartarla", cls: "bg-red-50 text-red-700" },
};

const AI_PROVIDERS = [
  { id: "gemini", label: "Gemini" },
  { id: "groq", label: "Groq · GPT-OSS 20B (gratis)" },
  { id: "openrouter", label: "OpenRouter · modelo gratis automático" },
];
const AI_DETAIL_SOURCES = new Set(["computrabajo", "elempleo"]);

const WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const BOGOTA_DATE_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  timeZone: "America/Bogota",
});

function dateKeyInBogota(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = Object.fromEntries(
    BOGOTA_DATE_FORMATTER.formatToParts(date).map(({ type, value: part }) => [type, part]),
  );
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function formatFoundDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `Encontrada el ${new Intl.DateTimeFormat("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "America/Bogota",
  }).format(date)}`;
}

function formatPublishedDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `Publicada el ${new Intl.DateTimeFormat("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "America/Bogota",
  }).format(date)}`;
}

function getPageItems(current, total) {
  const pages = [...new Set([1, current - 1, current, current + 1, total])]
    .filter((page) => page >= 1 && page <= total)
    .sort((a, b) => a - b);
  return pages.flatMap((page, index) => [
    ...(index > 0 && page - pages[index - 1] > 1 ? [{ type: "gap", key: `gap-${page}` }] : []),
    { type: "page", value: page },
  ]);
}

function scoreColor(score) {
  if (score >= 70) return "bg-brand-600";
  if (score >= 40) return "bg-accent";
  return "bg-slate-400";
}

function Breakdown({ job, onGoProfile }) {
  const fixes = job.criteria.filter((c) => c.fix);
  const profileFixes = fixes.filter((c) => c.where === "profile");

  return (
    <div className="mt-4 space-y-5 rounded-lg bg-canvas p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Coincidencia estimada: {job.score}%</h3>
        <span className="text-xs text-muted">Evidencia evaluada: {job.evidence_coverage}%</span>
      </div>

      <ul className="space-y-4">
        {job.criteria.map((c) => {
          const s = STATUS[c.status];
          return (
            <li key={c.key}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{c.label}</span>
                <span className="flex items-center gap-2 text-sm">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${s.cls}`}>{s.label}</span>
                  <span className="w-12 text-right tabular-nums">
                    {c.points}/{c.max_points}
                  </span>
                </span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-line">
                <div
                  className={`h-1.5 rounded-full ${s.bar}`}
                  style={{ width: `${(c.points / c.max_points) * 100}%` }}
                />
              </div>
              <p className="mt-1.5 text-sm text-muted">{c.detail}</p>
            </li>
          );
        })}
      </ul>

      <div>
        <h4 className="text-sm font-semibold">Para llegar al 100%</h4>
        {fixes.length === 0 ? (
          <p className="mt-1 text-sm text-brand-700">Esta oferta cumple todos los criterios.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {fixes.map((c) => (
              <li key={c.key} className="text-sm">
                <span className="mr-2 rounded-full bg-white px-2 py-0.5 text-xs text-muted ring-1 ring-line">
                  {WHERE[c.where]}
                </span>
                <span className="font-medium">{c.label}:</span> {c.fix}
              </li>
            ))}
          </ul>
        )}
        {profileFixes.length > 0 && (
          <button
            onClick={onGoProfile}
            className="mt-3 text-sm font-medium text-brand-600 hover:underline"
          >
            Ajustar mi perfil
          </button>
        )}
      </div>

      <p className="text-xs text-muted">
        Este cruce solo lee el título y el resumen que muestra la bolsa de empleo. Para que lea la
        oferta completa, usa “Analizar con IA”.
      </p>
    </div>
  );
}

function AIResult({ ai, id, isOpen }) {
  const rec = REC[ai.recommendation] || REC.revisar;
  const when = ai.analyzed_at ? new Date(ai.analyzed_at).toLocaleString("es-CO") : "";
  return (
    <div id={`ai-analysis-${id}`} hidden={!isOpen} role="region" aria-label="Resultado del análisis de IA" className="mt-4 space-y-4 rounded-lg border border-brand-100 bg-brand-50/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Análisis de IA</h3>
        <div className="flex items-center gap-2">
          {ai.provider && (
            <span className="max-w-[18rem] truncate rounded-full bg-white px-3 py-1 text-xs font-medium text-muted" title={ai.model || ai.provider}>
              {ai.provider === "groq"
                ? "Groq · GPT-OSS 20B"
                : ai.provider === "openrouter"
                  ? `OpenRouter · ${ai.model || "modelo gratuito"}`
                  : "Gemini"}
            </span>
          )}
          <span className={`rounded-full px-3 py-1 text-sm font-medium ${rec.cls}`}>{rec.label}</span>
          <span className="text-sm font-semibold tabular-nums">{ai.fit_score}% de encaje</span>
        </div>
      </div>
      <p className="text-sm">{ai.summary}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold text-brand-700">A tu favor</h4>
          {ai.strengths?.length ? (
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
              {ai.strengths.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-muted">No se destacaron puntos.</p>
          )}
        </div>
        <div>
          <h4 className="text-sm font-semibold text-amber-800">Lo que te falta</h4>
          {ai.gaps?.length ? (
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
              {ai.gaps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-muted">No se encontraron vacíos.</p>
          )}
        </div>
      </div>

      {ai.tips?.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold">Para tu postulación</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {ai.tips.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-muted">
        La IA leyó la oferta completa y tu perfil. Puede equivocarse: revisa la oferta antes de
        postularte.{when && ` Analizado el ${when}.`}
      </p>
    </div>
  );
}

export default function Jobs({ onGoSearch, onGoProfile }) {
  const [jobs, setJobs] = useState([]);
  const [weekInfo, setWeekInfo] = useState(null);
  const [minScore, setMinScore] = useState(30);
  const [bucket, setBucket] = useState("match");
  const [dayFilter, setDayFilter] = useState("all");
  const [source, setSource] = useState("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [open, setOpen] = useState(null);
  const [aiBusy, setAiBusy] = useState(null);
  const [aiOpen, setAiOpen] = useState(null);
  const [aiProvider, setAiProvider] = useState("gemini");
  const [aiError, setAiError] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    return api
      .listJobs(minScore)
      .then(setJobs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [minScore]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.weekInfo().then(setWeekInfo).catch(() => {});
  }, []);

  const bucketJobs = useMemo(
    () => jobs.filter((job) => job.classification === bucket),
    [jobs, bucket],
  );
  const bucketCounts = useMemo(() => ({
    match: jobs.filter((job) => job.classification === "match").length,
    review: jobs.filter((job) => job.classification === "review").length,
  }), [jobs]);

  const dayCounts = useMemo(() => {
    const counts = {};
    for (const job of bucketJobs) {
      const date = dateKeyInBogota(job.created_at);
      if (date) counts[date] = (counts[date] || 0) + 1;
    }
    return counts;
  }, [bucketJobs]);

  const dayOptions = useMemo(() => {
    if (!weekInfo?.start_date) return [];
    const weekStart = new Date(`${weekInfo.start_date}T00:00:00.000Z`);
    if (Number.isNaN(weekStart.getTime())) return [];
    return WEEKDAYS.map((weekday, index) => {
      const day = new Date(weekStart);
      day.setUTCDate(day.getUTCDate() + index);
      const value = day.toISOString().slice(0, 10);
      return {
        value,
        label: `${weekday} · ${formatWeekStart(value)} (${dayCounts[value] || 0})`,
      };
    });
  }, [weekInfo, dayCounts]);

  const dayJobs = useMemo(() => {
    const filtered = dayFilter === "all"
      ? bucketJobs
      : bucketJobs.filter((job) => dateKeyInBogota(job.created_at) === dayFilter);
    return [...filtered].sort(
      (a, b) => b.score - a.score || new Date(b.created_at) - new Date(a.created_at),
    );
  }, [bucketJobs, dayFilter]);

  // Fuentes que tienen ofertas en el día elegido, con su cantidad
  const sources = useMemo(() => {
    const map = {};
    for (const j of dayJobs) {
      map[j.source] ??= { key: j.source, label: j.source_label, count: 0 };
      map[j.source].count += 1;
    }
    return Object.values(map).sort((a, b) => b.count - a.count);
  }, [dayJobs]);

  // Si la fuente elegida ya no tiene ofertas, vuelve a "Todas"
  const active = sources.some((s) => s.key === source) ? source : "all";
  const visible = active === "all" ? dayJobs : dayJobs.filter((j) => j.source === active);
  const totalPages = Math.max(1, Math.ceil(visible.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = visible.length ? (currentPage - 1) * pageSize : 0;
  const pageJobs = visible.slice(startIndex, startIndex + pageSize);
  const pageItems = getPageItems(currentPage, totalPages);

  async function dismiss(id) {
    setJobs((list) => list.filter((j) => j.id !== id));
    try {
      await api.dismissJob(id);
    } catch (e) {
      setError(e.message);
      load();
    }
  }

  async function analyze(id) {
    setAiBusy(id);
    setAiError((m) => ({ ...m, [id]: "" }));
    try {
      const ai = await api.analyzeJob(id, aiProvider);
      setJobs((list) => list.map((j) => (j.id === id ? { ...j, ai } : j)));
      setAiOpen(id);
    } catch (e) {
      setAiError((m) => ({ ...m, [id]: e.message }));
    } finally {
      setAiBusy(null);
    }
  }

  const chipCls = (on) =>
    `rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
      on
        ? "border-brand-600 bg-brand-600 text-white"
        : "border-line bg-white text-ink hover:border-brand-600"
    }`;

  return (
    <div className="jobs-page">
      <div className="jobs-toolbar">
        <div className="jobs-toolbar-intro">
          <span className="section-kicker">OPORTUNIDADES PARA TU PERFIL</span>
          <h1 className="jobs-page-title">Tus ofertas <span className="jobs-count">{visible.length}</span></h1>
          <p className="jobs-toolbar-description">El porcentaje es una comparación explicable con los datos disponibles, no una decisión de IA. El análisis profundo con IA está disponible cuando la fuente permite leer el detalle.</p>
        </div>
        <div className="jobs-toolbar-controls">
        <label className="jobs-filter-label">
          <span>Modelo de IA</span>
          <select
            value={aiProvider}
            onChange={(e) => setAiProvider(e.target.value)}
            className="jobs-filter-select max-w-[17rem]"
          >
            {AI_PROVIDERS.map((provider) => (
              <option key={provider.id} value={provider.id}>{provider.label}</option>
            ))}
          </select>
        </label>
        <label className={`jobs-filter-label ${bucket === "review" ? "hidden" : ""}`}>
          <span>Coincidencia</span>
          <select
            value={minScore}
            onChange={(e) => {
              setMinScore(Number(e.target.value));
              setPage(1);
            }}
            className="jobs-filter-select"
          >
            <option value={30}>Desde 30%</option>
            <option value={50}>Desde 50%</option>
            <option value={70}>Desde 70%</option>
          </select>
        </label>
        <label className="jobs-filter-label">
          <span>Día en que se encontró</span>
          <select
            value={dayFilter}
            onChange={(e) => {
              setDayFilter(e.target.value);
              setPage(1);
            }}
            className="jobs-filter-select"
          >
            <option value="all">Toda la semana ({bucketJobs.length})</option>
            {dayOptions.map((day) => (
              <option key={day.value} value={day.value}>{day.label}</option>
            ))}
          </select>
        </label>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Clasificación de ofertas">
        <button type="button" role="tab" aria-selected={bucket === "match"} className={chipCls(bucket === "match")} onClick={() => { setBucket("match"); setSource("all"); setDayFilter("all"); setPage(1); }}>
          Coincidencias ({bucketCounts.match})
        </button>
        <button type="button" role="tab" aria-selected={bucket === "review"} className={chipCls(bucket === "review")} onClick={() => { setBucket("review"); setSource("all"); setDayFilter("all"); setPage(1); }}>
          Revisar ({bucketCounts.review})
        </button>
      </div>
      <p className="mt-2 text-sm text-muted">
        {bucket === "match"
          ? "Se muestran ofertas desde 30% de coincidencia; puedes subir el filtro. Las que necesitan comprobación están en Revisar."
          : "Aquí aparecen excepciones por experiencia relacionada y datos incompletos o contradictorios; revisa la explicación y el anuncio original antes de postularte."}
      </p>

      <div className="weekly-reset-banner" role="note">
        <span className="weekly-reset-icon" aria-hidden="true">↻</span>
        <div>
          <strong>Tu bandeja empieza de nuevo cada lunes</strong>
          <p>Se muestran ofertas encontradas esta semana. Las anteriores se conservan y pueden volver a aparecer cuando las encuentres en una nueva búsqueda.</p>
        </div>
        {weekInfo?.start_date && (
          <span className="weekly-reset-date">
            Semana desde {formatWeekStart(weekInfo.start_date)}
          </span>
        )}
      </div>

      <p className="mt-3 text-xs leading-relaxed text-muted">
        Cada oferta se agrupa por el primer día de esta semana en que se encontró. Si vuelve a aparecer en otra búsqueda, conserva ese día y no se duplica. Dentro del día se muestran primero las de mayor coincidencia.
      </p>

      {sources.length > 0 && (
        <div className="jobs-source-filters mt-4 flex flex-wrap gap-2" role="group" aria-label="Filtrar por fuente">
          <button
            className={`${chipCls(active === "all")} jobs-source-chip${active === "all" ? " is-active" : ""}`}
            aria-pressed={active === "all"}
            onClick={() => {
              setSource("all");
              setPage(1);
            }}
          >
            Todas ({dayJobs.length})
          </button>
          {sources.map((s) => (
            <button
              key={s.key}
              className={`${chipCls(active === s.key)} jobs-source-chip${active === s.key ? " is-active" : ""}`}
              aria-pressed={active === s.key}
              onClick={() => {
                setSource(s.key);
                setPage(1);
              }}
            >
              {s.label} ({s.count})
            </button>
          ))}
        </div>
      )}

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {!loading && (jobs.length === 0 || visible.length === 0) ? (
        <div className="mt-4 rounded-xl border border-dashed border-line p-8 text-center text-muted">
          <p>
            {dayFilter !== "all"
              ? "No hay ofertas registradas en el día seleccionado."
              : bucket === "review"
              ? "No hay ofertas pendientes de revisión."
              : minScore > 30
              ? "No hay coincidencias que cumplan este filtro mínimo."
              : "Aún no hay coincidencias de 30% o más. Busca ofertas o revisa la pestaña Revisar."}
          </p>
          <button
            onClick={() => {
              if (dayFilter !== "all" || minScore > 30) {
                setDayFilter("all");
                setMinScore(30);
                setPage(1);
              } else {
                onGoSearch();
              }
            }}
            className="mt-2 font-medium text-brand-600 hover:underline"
          >
            {dayFilter !== "all" || minScore > 30 ? "Quitar filtros" : "Ir a buscar ofertas"}
          </button>
        </div>
      ) : (
        <ul className="jobs-list mt-4 divide-y divide-line rounded-xl border border-line bg-white">
          {pageJobs.map((j) => {
            const isOpen = open === j.id;
            const busy = aiBusy === j.id;
            return (
              <li key={j.id} className="jobs-card p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <a
                      href={j.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="jobs-card-title font-semibold text-ink hover:text-brand-600 hover:underline"
                    >
                      {j.title}
                    </a>
                    <p className="mt-0.5 text-sm text-muted">
                      {[j.company, j.location].filter(Boolean).join(", ")}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs text-brand-700">
                        {formatFoundDate(j.created_at)}
                      </span>
                      {j.published_at && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-muted">
                          {formatPublishedDate(j.published_at)}
                        </span>
                      )}
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-muted">
                        {j.source_label}
                      </span>
                      {j.classification === "review" && (
                        <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">Requiere revisión</span>
                      )}
                      {j.criteria.some((criterion) => criterion.key === "salario" && criterion.detail.startsWith("Salario no informado")) && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700">Salario no informado</span>
                      )}
                      {j.matched_terms.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs text-brand-700"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="jobs-card-side flex shrink-0 items-center gap-4 sm:flex-col sm:items-end sm:gap-2">
                    <div className="jobs-card-score w-28">
                      <p className="text-right text-sm font-semibold">{j.score}%</p>
                      <div className="mt-1 h-1.5 rounded-full bg-line">
                        <div
                          className={`h-1.5 rounded-full ${scoreColor(j.score)}`}
                          style={{ width: `${j.score}%` }}
                        />
                      </div>
                    </div>
                    <div className="jobs-card-actions flex flex-wrap justify-end gap-3 text-sm">
                      {AI_DETAIL_SOURCES.has(j.source) ? (
                        <button
                          onClick={() => analyze(j.id)}
                          disabled={aiBusy !== null}
                          className="font-medium text-brand-600 hover:underline disabled:opacity-50"
                        >
                          {busy ? "Analizando..." : j.ai ? "Volver a analizar" : "Analizar con IA"}
                        </button>
                      ) : (
                        <span className="text-xs text-muted" title="Abre el anuncio original para leer todos sus requisitos.">
                          Análisis IA de detalle no disponible para esta fuente
                        </span>
                      )}
                      {j.ai && (
                        <button
                          onClick={() => setAiOpen(aiOpen === j.id ? null : j.id)}
                          aria-expanded={aiOpen === j.id}
                          aria-controls={`ai-analysis-${j.id}`}
                          className="font-medium text-brand-600 hover:underline"
                        >
                          {aiOpen === j.id ? "Contraer análisis" : "Leer análisis IA"}
                        </button>
                      )}
                      <button
                        onClick={() => setOpen(isOpen ? null : j.id)}
                        aria-expanded={isOpen}
                        className="font-medium text-brand-600 hover:underline"
                      >
                        {isOpen ? "Ocultar detalle" : "Ver por qué"}
                      </button>
                      <a
                        href={j.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-brand-600 hover:underline"
                      >
                        Ver oferta
                      </a>
                      <button
                        onClick={() => dismiss(j.id)}
                        className="text-muted hover:text-red-600"
                      >
                        Descartar
                      </button>
                    </div>
                  </div>
                </div>

                {j.review_reasons?.length > 0 && (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                    <strong>Por revisar:</strong>
                    <ul className="mt-1 list-disc space-y-1 pl-5">
                      {j.review_reasons.map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  </div>
                )}
                {aiError[j.id] && (
                  <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                    {aiError[j.id]}
                  </p>
                )}
                {j.ai && <AIResult ai={j.ai} id={j.id} isOpen={aiOpen === j.id} />}
                {isOpen && <Breakdown job={j} onGoProfile={onGoProfile} />}
              </li>
            );
          })}
        </ul>
      )}
      {!loading && visible.length > 0 && (
        <div className="jobs-pagination">
          <div className="jobs-pagination-summary" aria-live="polite">
            Mostrando <strong>{startIndex + 1}–{Math.min(startIndex + pageSize, visible.length)}</strong> de <strong>{visible.length}</strong> ofertas
          </div>
          <label className="jobs-pagination-size">
            Ofertas por página
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
            </select>
          </label>
          <nav className="jobs-pagination-controls" aria-label="Paginación de ofertas">
            <button
              type="button"
              className="jobs-page-direction"
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Página anterior"
            >
              <span aria-hidden="true">‹</span> Anterior
            </button>
            <div className="jobs-page-numbers">
              {pageItems.map((item) => item.type === "gap" ? (
                <span key={item.key} className="jobs-page-gap" aria-hidden="true">…</span>
              ) : (
                <button
                  key={item.value}
                  type="button"
                  className={`jobs-page-number${item.value === currentPage ? " is-current" : ""}`}
                  onClick={() => setPage(item.value)}
                  aria-label={`Página ${item.value}`}
                  aria-current={item.value === currentPage ? "page" : undefined}
                >
                  {item.value}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="jobs-page-direction"
              onClick={() => setPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Página siguiente"
            >
              Siguiente <span aria-hidden="true">›</span>
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}
