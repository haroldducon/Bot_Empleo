import { useState } from "react";
import { api, setToken } from "../api";
import { Logo, inputCls, primaryBtn } from "./ui";
import { CURRENT_YEAR } from "../constants";
import loginAnalytics from "../assets/login-analytics.jpg";
import "./Login.css";

const INSIGHTS = [
  { icon: "↗", title: "Coincidencia inteligente", detail: "Ofertas alineadas con tu experiencia" },
  { icon: "◷", title: "Ahorra tiempo", detail: "Tu búsqueda, organizada en un solo lugar" },
  { icon: "✦", title: "Análisis con IA", detail: "Entiende tus fortalezas y oportunidades" },
];

export default function Login({ onLogin, onRegister }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") await api.register(email, password);
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const isLogin = mode === "login";

  return (
    <div className="auth-shell">
      <aside className="auth-showcase">
        <div className="auth-brand"><Logo light /></div>
        <div className="auth-showcase-copy">
          <span className="auth-eyebrow"><span className="auth-live-dot" /> BÚSQUEDA DE EMPLEO CON IA</span>
          <h1>Tu próximo paso profesional, <em>con claridad.</em></h1>
          <p className="auth-lead">
            Encuentra oportunidades que hacen sentido para ti. Compara cada oferta con tu experiencia y enfoca tu energía en las mejores.
          </p>
          <div className="auth-visual" aria-hidden="true">
            <img src={loginAnalytics} alt="" />
            <div className="auth-visual-shade" />
            <div className="auth-visual-caption"><span className="auth-caption-mark">✦</span><span><b>Inteligencia para tu búsqueda</b><small>Datos, oportunidades y decisiones en contexto</small></span></div>
          </div>
          <div className="auth-benefits">
            {INSIGHTS.map((item) => (
              <div className="auth-benefit" key={item.title}>
                <span className="auth-benefit-icon" aria-hidden="true">{item.icon}</span>
                <span><b>{item.title}</b><small>{item.detail}</small></span>
              </div>
            ))}
          </div>
        </div>
        <div className="auth-footnote"><span className="auth-shield">✓</span> Tus datos personales están protegidos.</div>
      </aside>

      <main className="auth-main">
        <div className="auth-mobile-brand"><Logo /></div>
        <section className="auth-form-wrap">
          <div className="auth-form-heading">
            <span className="auth-form-kicker">BIENVENIDO A BORDO</span>
            <h2>{isLogin ? "Qué bueno tenerte de vuelta" : "Crea tu cuenta"}</h2>
            <p>{isLogin ? "Inicia sesión para continuar con tu búsqueda." : "Configura tu espacio profesional en un minuto."}</p>
          </div>

          <form onSubmit={submit} className="auth-form">
            <label className="auth-field">
              <span>Correo electrónico</span>
              <input type="email" required autoComplete="email" placeholder="nombre@correo.com" value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
            </label>
            <label className="auth-field">
              <span>Contraseña</span>
              <input type="password" required minLength={8} autoComplete={isLogin ? "current-password" : "new-password"} placeholder={isLogin ? "Escribe tu contraseña" : "Mínimo 8 caracteres"} value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} />
            </label>
            {error && <p role="alert" className="auth-error">{error}</p>}
            <button disabled={loading} className={`${primaryBtn} auth-submit`}>
              {loading ? "Un momento…" : isLogin ? "Iniciar sesión" : "Crear mi cuenta"}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="auth-switch">
            {isLogin ? "¿Todavía no tienes cuenta?" : "¿Ya tienes una cuenta?"}{" "}
            <button type="button" onClick={() => {
              setError("");
              if (isLogin && onRegister) onRegister();
              else setMode(isLogin ? "register" : "login");
            }}>
              {isLogin ? "Regístrate gratis" : "Inicia sesión"}
            </button>
          </p>
          <div className="auth-form-trust"><span>●</span> Acceso seguro · Sin costo para empezar</div>
        </section>
        <div className="auth-copyright">© {CURRENT_YEAR} NEXO LABORAL <span>·</span> DESARROLLADO POR <strong>HAROLD DUCON</strong></div>
      </main>
    </div>
  );
}
