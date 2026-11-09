import { useState } from "react";
import { api, setToken } from "../api";
import { Logo, inputCls, primaryBtn } from "./ui";
import { CURRENT_YEAR } from "../constants";
import loginAnalytics from "../assets/login-analytics.jpg";
import "./Login.css";

export default function Register({ onLogin, onBack }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      await api.register(email, password);
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <aside className="auth-showcase">
        <div className="auth-brand"><Logo light /></div>
        <div className="auth-showcase-copy">
          <span className="auth-eyebrow"><span className="auth-live-dot" /> TU ESPACIO PROFESIONAL</span>
          <h1>Una búsqueda más inteligente <em>empieza aquí.</em></h1>
          <p className="auth-lead">Crea tu cuenta y deja que los datos te ayuden a encontrar oportunidades que sí encajan contigo.</p>
          <div className="auth-visual" aria-hidden="true">
            <img src={loginAnalytics} alt="" />
            <div className="auth-visual-shade" />
            <div className="auth-visual-caption"><span className="auth-caption-mark">✦</span><span><b>Tu carrera, con mejores insights</b><small>Un perfil. Oportunidades más relevantes.</small></span></div>
          </div>
          <div className="auth-benefits">
            <div className="auth-benefit"><span className="auth-benefit-icon">✓</span><span><b>Perfil personalizado</b><small>Cuéntanos qué buscas</small></span></div>
            <div className="auth-benefit"><span className="auth-benefit-icon">↗</span><span><b>Mejores coincidencias</b><small>Prioriza lo más relevante</small></span></div>
            <div className="auth-benefit"><span className="auth-benefit-icon">✦</span><span><b>Análisis con IA</b><small>Decide con más contexto</small></span></div>
          </div>
        </div>
        <div className="auth-footnote"><span className="auth-shield">✓</span> Tus datos personales están protegidos.</div>
      </aside>

      <main className="auth-main">
        <div className="auth-mobile-brand"><Logo /></div>
        <section className="auth-form-wrap">
          <div className="auth-form-heading">
            <span className="auth-form-kicker">EMPIEZA GRATIS</span>
            <h2>Crea tu cuenta</h2>
            <p>Solo necesitas tu correo y una contraseña para comenzar.</p>
          </div>
          <form onSubmit={submit} className="auth-form">
            <label className="auth-field">
              <span>Correo electrónico</span>
              <input type="email" required autoComplete="email" placeholder="nombre@correo.com" value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
            </label>
            <label className="auth-field">
              <span>Contraseña</span>
              <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="Al menos 8 caracteres" value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} />
              <small className="auth-field-hint">Usa al menos 8 caracteres.</small>
            </label>
            <label className="auth-field">
              <span>Confirma tu contraseña</span>
              <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" placeholder="Escribe la contraseña de nuevo" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={inputCls} />
            </label>
            {error && <p role="alert" className="auth-error">{error}</p>}
            <button disabled={loading} className={`${primaryBtn} auth-submit`}>
              {loading ? "Creando tu cuenta…" : "Crear mi cuenta"}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>
          <p className="auth-switch">¿Ya tienes una cuenta? <button type="button" onClick={onBack}>Inicia sesión</button></p>
          <div className="auth-form-trust"><span>●</span> Registro seguro · Tus datos son privados</div>
        </section>
        <div className="auth-copyright">© {CURRENT_YEAR} NEXO LABORAL <span>·</span> DESARROLLADO POR <strong>HAROLD DUCON</strong></div>
      </main>
    </div>
  );
}
