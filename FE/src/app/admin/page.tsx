"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn } from "@/lib/api";

export default function AdminPage() {
  const router = useRouter();
  const [dash, setDash] = useState<{
    active_sessions: number;
    total_minutes_today: number;
    total_users: number;
    latency_p50_ms: number;
    latency_p95_ms: number;
    cost_today_usd: number;
  } | null>(null);
  const [flags, setFlags] = useState<Array<{ key: string; value: string; description: string }>>([]);
  const [live, setLive] = useState<Array<Record<string, string>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.adminDashboard(), api.adminFlags(), api.adminLiveSessions()])
      .then(([d, f, l]) => {
        setDash(d);
        setFlags(f);
        setLive(l);
      })
      .catch((e) => setError(e.message || "Admin access required (use admin@example.com)"));
  }, [router]);

  return (
    <>
      <Nav />
      <main className="container" style={{ padding: "2rem 0" }}>
        <h1>Admin control plane</h1>
        <p className="muted">KPIs, feature flags, live sessions — server RBAC enforced.</p>
        {error && <div className="error">{error}</div>}
        {dash && (
          <div className="grid grid-3" style={{ margin: "1.5rem 0" }}>
            {[
              ["Active sessions", dash.active_sessions],
              ["Minutes (all)", dash.total_minutes_today],
              ["Users", dash.total_users],
              ["Latency p50", `${dash.latency_p50_ms} ms`],
              ["Latency p95", `${dash.latency_p95_ms} ms`],
              ["Cost", `$${dash.cost_today_usd}`],
            ].map(([label, value]) => (
              <div key={String(label)} className="card">
                <div className="muted">{label}</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>{value}</div>
              </div>
            ))}
          </div>
        )}
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div className="card">
            <h3>Feature flags</h3>
            {flags.map((f) => (
              <div key={f.key} style={{ marginBottom: "0.75rem" }}>
                <strong>{f.key}</strong> = <code>{f.value}</code>
                <div className="muted" style={{ fontSize: "0.85rem" }}>{f.description}</div>
              </div>
            ))}
          </div>
          <div className="card">
            <h3>Live sessions</h3>
            {live.length === 0 && <p className="muted">None active</p>}
            {live.map((s) => (
              <div key={s.id} className="muted" style={{ fontSize: "0.9rem", marginBottom: 6 }}>
                {s.id?.slice(0, 8)} · {s.provider} · user {s.user_id?.slice(0, 8)}
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
