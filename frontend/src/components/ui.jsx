import { useState } from "react";

export const inputCls =
  "w-full rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20";

export const primaryBtn =
  "rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50";

export function Logo({ light = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`grid h-9 w-9 place-items-center rounded-lg ${
          light ? "bg-white/15" : "bg-brand-600"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5 text-white"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="3" y="7" width="18" height="13" rx="2" />
          <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
          <path d="M3 13h18" />
        </svg>
      </span>
      <span className="font-display text-lg font-semibold">Nexo Laboral</span>
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Section({ title, hint, action, children }) {
  return (
    <section className="grid gap-x-10 gap-y-4 border-t border-line py-8 lg:grid-cols-[240px_1fr]">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
        {action}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

export function TagInput({ value, onChange, placeholder, maxTags = Infinity, maxTagLength = 100 }) {
  const [text, setText] = useState("");

  function add(raw) {
    const t = raw.trim();
    if (value.length >= maxTags) {
      setText("");
      return;
    }
    if (t && !value.some((v) => v.toLowerCase() === t.toLowerCase())) {
      onChange([...value, t]);
    }
    setText("");
  }

  function onKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(text);
    } else if (e.key === "Backspace" && !text && value.length) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-white px-2.5 py-2 focus-within:border-brand-600 focus-within:ring-2 focus-within:ring-brand-600/20">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 py-1 pl-3 pr-1.5 text-sm text-brand-700"
          >
            {tag}
            <button
              type="button"
              aria-label={`Quitar ${tag}`}
              onClick={() => onChange(value.filter((v) => v !== tag))}
              className="grid h-5 w-5 place-items-center rounded-full text-brand-700 hover:bg-brand-100"
            >
              ×
            </button>
          </span>
        ))}
        <input
          value={text}
          maxLength={maxTagLength}
          disabled={value.length >= maxTags}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => add(text)}
          placeholder={value.length >= maxTags ? "Límite alcanzado" : value.length ? "" : placeholder}
          className="min-w-[8rem] flex-1 bg-transparent py-1 text-[15px] outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>
      {Number.isFinite(maxTags) && (
        <div className="mt-1.5 text-right text-xs text-muted" aria-live="polite">
          {value.length} de {maxTags}
        </div>
      )}
    </div>
  );
}
