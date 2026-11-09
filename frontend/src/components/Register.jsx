import { useState } from "react";
import { api, setToken } from "../api";
import { inputCls, primaryBtn } from "./ui";
import { CURRENT_YEAR } from "../constants";
import AuthShowcase from "./AuthShowcase";
import AuthMascot from "./AuthMascot";
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
      <AuthShowcase isRegister />
      <main className="auth-main">
        <section className="auth-form-wrap">
          <AuthMascot />
          <div className="auth-form-heading">
            <span className="auth-form-kicker">EMPIEZA GRATIS</span>
            <h1>Crea tu cuenta</h1>
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
