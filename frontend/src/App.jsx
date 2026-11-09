import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import Login from "./components/Login";
import Register from "./components/Register";
import Search from "./components/Search";
import Jobs from "./components/Jobs";
import Profile from "./components/Profile";
import AIKeys from "./components/AIKeys";
import Analytics from "./components/Analytics";
import { Logo } from "./components/ui";
import { CURRENT_YEAR } from "./constants";
import "./App.css";

const TABS = [
  ["search", "Buscar"],
  ["jobs", "Ofertas"],
  ["analytics", "Resumen"],
  ["profile", "Mi perfil"],
  ["keys", "Claves de IA"],
];

function TabIcon({ id }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };
  const icons = {
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>,
    jobs: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 12h18" /></>,
    analytics: <><path d="M4 19V5M4 19h17" /><path d="m7 15 4-4 3 2 5-6" /><path d="M16 7h3v3" /></>,
    profile: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.8-3.4 3.2-5 7-5s6.2 1.6 7 5" /></>,
    keys: <><circle cx="8" cy="15" r="4" /><path d="m11 12 8-8 2 2-2 2 2 2-3 3-2-2-2 2" /></>,
  };
  return <svg className="app-nav-icon" {...common}>{icons[id]}</svg>;
}

function initials(value) {
  return (value || "U")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export default function App() {
  const [logged, setLogged] = useState(!!getToken());
  const [authPage, setAuthPage] = useState("login");
  const [tab, setTab] = useState("search");
  const [sidebarUser, setSidebarUser] = useState({ email: "", fullName: "", avatarUrl: "" });
  const [profileRefresh, setProfileRefresh] = useState(0);

  useEffect(() => {
    if (!logged) return undefined;
    let cancelled = false;
    let objectUrl = "";

    Promise.allSettled([api.me(), api.getProfile(), api.getAvatar()]).then((results) => {
      const [userResult, profileResult, avatarResult] = results;
      const email = userResult.status === "fulfilled" ? userResult.value.email || "" : "";
      const fullName = profileResult.status === "fulfilled"
        ? (profileResult.value.full_name || "").trim()
        : "";
      const avatarBlob = avatarResult.status === "fulfilled" ? avatarResult.value : null;
      if (avatarBlob && typeof Blob !== "undefined" && avatarBlob instanceof Blob) {
        objectUrl = URL.createObjectURL(avatarBlob);
      }
      if (cancelled) {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        return;
      }
      setSidebarUser({ email, fullName, avatarUrl: objectUrl });
    });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [logged, profileRefresh]);

  if (!logged) {
    const finishLogin = () => setLogged(true);
    return authPage === "register" ? (
      <Register onLogin={finishLogin} onBack={() => setAuthPage("login")} />
    ) : (
      <Login onLogin={finishLogin} onRegister={() => setAuthPage("register")} />
    );
  }

  function signOut() {
    setToken(null);
    setLogged(false);
    setSidebarUser({ email: "", fullName: "", avatarUrl: "" });
  }

  function refreshSidebarProfile() {
    setSidebarUser((current) => ({ ...current, avatarUrl: "" }));
    setProfileRefresh((version) => version + 1);
  }

  const accountName = sidebarUser.fullName || "Completa tu perfil";
  const accountInitials = initials(sidebarUser.fullName || sidebarUser.email);

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Navegación principal">
        <div className="app-sidebar-brand"><Logo /></div>
        <nav className="app-sidebar-nav" aria-label="Secciones">
          <span className="app-nav-caption">MENÚ PRINCIPAL</span>
          {TABS.map(([id, label]) => (
            <button
              key={id}
              className={`app-nav-item${tab === id ? " is-active" : ""}`}
              aria-current={tab === id ? "page" : undefined}
              onClick={() => setTab(id)}
            >
              <TabIcon id={id} />
              <span>{label}</span>
              {tab === id && <span className="app-nav-current-dot" aria-hidden="true" />}
            </button>
          ))}
        </nav>
        <div className="app-sidebar-account">
          <div className="app-account-avatar" aria-hidden="true">
            {sidebarUser.avatarUrl
              ? <img src={sidebarUser.avatarUrl} alt="" />
              : <span>{accountInitials}</span>}
          </div>
          <div className="app-account-details">
            <span className="app-account-label">MI PERFIL</span>
            <span className="app-account-name" title={accountName}>{accountName}</span>
            <span className="app-account-email" title={sidebarUser.email}>{sidebarUser.email}</span>
          </div>
          <button className="app-signout" onClick={signOut} aria-label="Cerrar sesión" title="Cerrar sesión">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" />
            </svg>
          </button>
        </div>
      </aside>

      <div className="app-main-column">
        <main className="app-content mx-auto max-w-5xl px-4 py-8 sm:px-6">
          {tab === "search" && <Search onViewJobs={() => setTab("jobs")} />}
          {tab === "jobs" && (
            <Jobs onGoSearch={() => setTab("search")} onGoProfile={() => setTab("profile")} />
          )}
          {tab === "analytics" && <Analytics onGoSearch={() => setTab("search")} />}
          {tab === "profile" && (
            <Profile
              avatarUrl={sidebarUser.avatarUrl}
              onProfileUpdated={refreshSidebarProfile}
            />
          )}
          {tab === "keys" && <AIKeys />}
        </main>
        <footer className="app-footer">
          <div className="app-footer-inner">
            <span>© {CURRENT_YEAR} Nexo Laboral</span>
            <span className="app-footer-credit">Desarrollado por <strong>Harold Ducon</strong></span>
          </div>
        </footer>
      </div>
    </div>
  );
}
