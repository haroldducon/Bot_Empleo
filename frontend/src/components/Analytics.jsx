import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const CHART = { width: 780, height: 280, left: 48, right: 18, top: 24, bottom: 48 };
const PLOT_WIDTH = CHART.width - CHART.left - CHART.right;
const PLOT_HEIGHT = CHART.height - CHART.top - CHART.bottom;
const MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

function formatWeek(date) {
  if (!date) return "";
  const [, month, day] = date.split("-");
  return `${Number(day)} de ${MONTHS_ES[Number(month) - 1]}`;
}

export function WeeklyBars({ days, peakDay }) {
  const highest = Math.max(0, ...days.map((day) => day.count));
  const step = Math.max(1, Math.ceil(highest / 4));
  const axisMax = step * 4;
  const slotWidth = PLOT_WIDTH / Math.max(days.length, 1);
  const barWidth = Math.min(48, slotWidth * 0.48);
  const baseY = CHART.top + PLOT_HEIGHT;

  return (
    <div className="analytics-chart-scroll">
      <svg
        className="analytics-chart"
        viewBox={`0 0 ${CHART.width} ${CHART.height}`}
        role="img"
        aria-label="Gráfico de barras con el número de ofertas encontradas por día de esta semana"
      >
        <defs>
          <linearGradient id="barNormal" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#48b8a5" />
            <stop offset="100%" stopColor="#15847c" />
          </linearGradient>
          <linearGradient id="barPeak" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#f5bf66" />
            <stop offset="100%" stopColor="#e69b37" />
          </linearGradient>
        </defs>

        {[0, 1, 2, 3, 4].map((tick) => {
          const y = CHART.top + PLOT_HEIGHT - (tick / 4) * PLOT_HEIGHT;
          return (
            <g key={tick}>
              <line x1={CHART.left} x2={CHART.width - CHART.right} y1={y} y2={y} className="analytics-gridline" />
              <text x={CHART.left - 12} y={y + 4} textAnchor="end" className="analytics-axis-label">
                {tick * step}
              </text>
            </g>
          );
        })}

        {days.map((day, index) => {
          const x = CHART.left + index * slotWidth + (slotWidth - barWidth) / 2;
          const barHeight = day.count ? Math.max(4, (day.count / axisMax) * PLOT_HEIGHT) : 0;
          const y = baseY - barHeight;
          const isPeak = peakDay === day.full_label && day.count > 0;
          return (
            <g key={day.date}>
              <title>{`${day.full_label}: ${day.count} ${day.count === 1 ? "oferta" : "ofertas"}`}</title>
              {day.count > 0 && (
                <text x={x + barWidth / 2} y={y - 9} textAnchor="middle" className="analytics-bar-value">
                  {day.count}
                </text>
              )}
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx="7"
                fill={isPeak ? "url(#barPeak)" : "url(#barNormal)"}
                className="analytics-bar"
              />
              <text x={x + barWidth / 2} y={baseY + 27} textAnchor="middle" className="analytics-day-label">
                {day.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function Analytics({ onGoSearch }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await api.weeklyAnalytics());
    } catch (err) {
      setError(err.message || "No se pudo cargar el resumen.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.weeklyAnalytics()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(err.message || "No se pudo cargar el resumen.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  return (
    <div className="analytics-page">
      <div className="analytics-heading">
        <div>
          <span className="section-kicker">DATOS DE TU BÚSQUEDA</span>
          <h1>Resumen analítico</h1>
          <p>Visualiza cómo avanzó tu búsqueda de empleo durante esta semana.</p>
        </div>
        <button type="button" className="analytics-refresh" onClick={load} disabled={loading}>
          <span aria-hidden="true">↻</span> {loading ? "Actualizando…" : "Actualizar"}
        </button>
      </div>

      {error && <div className="analytics-error" role="alert">{error}</div>}

      {loading && !data ? (
        <div className="analytics-loading" role="status">Cargando tus datos semanales…</div>
      ) : data ? (
        <>
          <div className="analytics-stat-grid">
            <article className="analytics-stat analytics-stat-primary">
              <span className="analytics-stat-icon" aria-hidden="true">▥</span>
              <span className="analytics-stat-label">Ofertas encontradas</span>
              <strong>{data.total}</strong>
              <small>En la semana actual</small>
            </article>
            <article className="analytics-stat">
              <span className="analytics-stat-icon" aria-hidden="true">↗</span>
              <span className="analytics-stat-label">Día más activo</span>
              <strong className="analytics-stat-day">{data.peak_day || "—"}</strong>
              <small>{data.peak_count} {data.peak_count === 1 ? "oferta" : "ofertas"} encontradas</small>
            </article>
            <article className="analytics-stat">
              <span className="analytics-stat-icon" aria-hidden="true">◷</span>
              <span className="analytics-stat-label">Semana iniciada</span>
              <strong className="analytics-stat-day">{formatWeek(data.start_date)}</strong>
              <small>Se renueva cada lunes</small>
            </article>
          </div>

          <section className="analytics-panel">
            <div className="analytics-panel-heading">
              <div>
                <h2>Ofertas por día</h2>
                <p>Conteo de ofertas únicas agregadas a tu bandeja esta semana.</p>
              </div>
              <span className="analytics-legend"><i /> Ofertas encontradas</span>
            </div>
            {data.total === 0 ? (
              <div className="analytics-empty">
                <span aria-hidden="true">▥</span>
                <strong>Aún no hay datos esta semana</strong>
                <p>Inicia una búsqueda y aquí verás el resumen diario de tus ofertas.</p>
                <button type="button" onClick={onGoSearch}>Buscar ofertas</button>
              </div>
            ) : (
              <WeeklyBars days={data.days} peakDay={data.peak_day} />
            )}
            <div className="analytics-note">
              <span aria-hidden="true">i</span>
              La cuenta incluye ofertas únicas encontradas por ti; se reinicia cada lunes a las 00:00, hora de Colombia.
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
