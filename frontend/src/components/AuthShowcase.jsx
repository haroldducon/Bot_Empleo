import { Logo } from "./ui";
import loginPerson from "../assets/login-person.webp";

const FEATURES = [
  { icon: "✦", title: "Coincidencias con IA", detail: "Ofertas alineadas contigo", className: "auth-float-one" },
  { icon: "↗", title: "Analiza cada oferta", detail: "Compara requisitos y perfil", className: "auth-float-two" },
  { icon: "◷", title: "Alertas organizadas", detail: "Tu búsqueda, en un solo lugar", className: "auth-float-three" },
];

export default function AuthShowcase({ isRegister = false }) {
  return (
    <aside className="auth-showcase">
      <div className="auth-brand"><Logo light /></div>
      <div className="auth-showcase-copy">
        <span className="auth-eyebrow"><span className="auth-live-dot" /> {isRegister ? "TU ESPACIO PROFESIONAL" : "BÚSQUEDA DE EMPLEO CON IA"}</span>
        <h1>{isRegister ? <>Una búsqueda más inteligente <em>empieza aquí.</em></> : <>Tu próximo paso profesional, <em>con claridad.</em></>}</h1>
        <p className="auth-lead">{isRegister ? "Crea tu cuenta y encuentra oportunidades que sí encajan contigo." : "Encuentra oportunidades que hacen sentido para ti y enfoca tu energía en las mejores."}</p>
        <div className="auth-person-stage" aria-label="Profesional usando su laptop">
          <div className="auth-person-halo" aria-hidden="true" />
          <img className="auth-person-image" src={loginPerson} alt="Mujer profesional trabajando con una laptop" />
          {FEATURES.map((item) => (
            <div className={`auth-float-card ${item.className}`} key={item.title}>
              <span className="auth-float-icon" aria-hidden="true">{item.icon}</span>
              <span><b>{item.title}</b><small>{item.detail}</small></span>
            </div>
          ))}
        </div>
      </div>
      <div className="auth-footnote"><span className="auth-shield">✓</span> Tus datos personales están protegidos.</div>
    </aside>
  );
}
