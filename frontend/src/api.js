const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const getToken = () => sessionStorage.getItem("token");
export const setToken = (t) =>
  t ? sessionStorage.setItem("token", t) : sessionStorage.removeItem("token");

async function request(path, { method = "GET", body, form, responseType = "json" } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (typeof FormData !== "undefined" && body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API}${path}`, { method, headers, body: payload });

  if (res.status === 401 && token) {
    setToken(null);
    window.location.reload();
  }
  if (!res.ok) {
    let msg = "Error inesperado";
    try {
      const d = await res.json();
      msg = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
    } catch {
      /* sin cuerpo JSON */
    }
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return responseType === "blob" ? res.blob() : res.json();
}

export const api = {
  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password } }),
  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      form: { username: email, password },
    }),
  requestPasswordReset: (email) =>
    request("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token, new_password) =>
    request("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
    }),
  me: () => request("/auth/me"),
  getProfile: () => request("/profile"),
  saveProfile: (data) => request("/profile", { method: "PUT", body: data }),
  getAvatar: () => request("/profile/avatar", { responseType: "blob" }),
  uploadAvatar: (file) => {
    const data = new FormData();
    data.append("file", file);
    return request("/profile/avatar", { method: "POST", body: data });
  },
  deleteAvatar: () => request("/profile/avatar", { method: "DELETE" }),
  listKeys: () => request("/ai-keys"),
  saveKey: (provider, api_key) =>
    request(`/ai-keys/${provider}`, { method: "PUT", body: { api_key } }),
  deleteKey: (provider) => request(`/ai-keys/${provider}`, { method: "DELETE" }),
  sources: () => request("/search/sources"),
  runSearch: (sources) =>
    request("/search/run", { method: "POST", body: { sources } }),
  searchStatus: () => request("/search/status"),
  weekInfo: () => request("/search/week"),
  weeklyAnalytics: () => request("/analytics/weekly"),
  gmailStatus: () => request("/gmail/status"),
  gmailConnect: () => request("/gmail/connect", { method: "POST" }),
  gmailLabels: () => request("/gmail/labels"),
  gmailSelectLabel: (label_id) =>
    request("/gmail/label", { method: "PUT", body: { label_id } }),
  gmailDisconnect: () => request("/gmail/connection", { method: "DELETE" }),
  listJobs: (minScore = 0) => request(`/jobs?min_score=${minScore}&limit=300`),
  dismissJob: (id) => request(`/jobs/${id}/dismiss`, { method: "POST" }),
  analyzeJob: (id, provider = "gemini") =>
    request(`/jobs/${id}/analyze`, { method: "POST", body: { provider } }),
};
