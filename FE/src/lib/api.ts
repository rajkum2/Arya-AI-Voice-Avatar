const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  remaining_minutes: number;
  quota_minutes: number;
  used_minutes: number;
};

export type Avatar = {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail_url: string;
  provider: string;
  is_featured: boolean;
  greeting?: string;
};

export type Bootstrap = {
  maintenance_mode: boolean;
  captions_default: boolean;
  barge_in_enabled: boolean;
  consent_version: string;
  consent_required: boolean;
  ai_disclosure: string;
  features: Record<string, boolean>;
};

export type Session = {
  id: string;
  avatar_id: string;
  provider: string;
  status: string;
  room_url: string;
  room_token: string;
  captions_enabled: boolean;
  barge_in_enabled: boolean;
  mock_mode: boolean;
  greeting: string;
  max_duration_sec: number;
  transport?: string;
  sandbox?: boolean;
  failover_reason?: string;
};

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  url: API_URL,
  wsUrl: WS_URL,

  register(email: string, password: string, display_name: string) {
    return request<TokenPair>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    });
  },

  login(email: string, password: string) {
    return request<TokenPair>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  me() {
    return request<User>("/api/v1/auth/me");
  },

  bootstrap() {
    return request<Bootstrap>("/api/v1/bootstrap");
  },

  bootstrapMe() {
    return request<Bootstrap>("/api/v1/bootstrap/me");
  },

  submitConsent(body: {
    understand_ai: boolean;
    voice_processing: boolean;
    store_transcripts: boolean;
    improve_service: boolean;
  }) {
    return request("/api/v1/auth/consent", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  listAvatars(q?: string) {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<Avatar[]>(`/api/v1/avatars${qs}`);
  },

  getAvatar(id: string) {
    return request<Avatar>(`/api/v1/avatars/${id}`);
  },

  startSession(avatar_id: string, captions_enabled?: boolean) {
    return request<Session>("/api/v1/sessions", {
      method: "POST",
      body: JSON.stringify({ avatar_id, captions_enabled }),
    });
  },

  getSession(id: string) {
    return request<Session>(`/api/v1/sessions/${id}`);
  },

  endSession(id: string) {
    return request<Session>(`/api/v1/sessions/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ reason: "user_ended" }),
    });
  },

  conversations() {
    return request<
      Array<{
        id: string;
        session_id: string;
        avatar_id: string;
        avatar_name?: string;
        duration_sec: number;
        created_at: string;
      }>
    >("/api/v1/conversations");
  },

  exportData() {
    return request<Record<string, unknown>>("/api/v1/me/export");
  },

  adminDashboard() {
    return request<{
      active_sessions: number;
      total_minutes_today: number;
      total_users: number;
      latency_p50_ms: number;
      latency_p95_ms: number;
      cost_today_usd: number;
    }>("/api/v1/admin/dashboard");
  },

  adminFlags() {
    return request<Array<{ key: string; value: string; description: string }>>(
      "/api/v1/admin/feature-flags"
    );
  },

  adminLiveSessions() {
    return request<Array<Record<string, string>>>("/api/v1/admin/sessions/live");
  },

  adminUsers() {
    return request<Array<Record<string, unknown>>>("/api/v1/admin/users");
  },

  adminAvatars() {
    return request<Avatar[]>("/api/v1/admin/avatars");
  },
};

export function saveTokens(tokens: TokenPair) {
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export function isLoggedIn() {
  return typeof window !== "undefined" && !!localStorage.getItem("access_token");
}
