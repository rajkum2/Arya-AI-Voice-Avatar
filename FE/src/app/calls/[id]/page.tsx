"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn, PhoneCall } from "@/lib/api";

const TERMINAL = new Set(["completed", "failed", "cancelled", "error"]);

export default function CallStatusPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [call, setCall] = useState<PhoneCall | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const c = await api.getCall(id);
        if (stopped) return;
        setCall(c);
        if (!TERMINAL.has(c.status)) {
          timer = setTimeout(poll, 5000);
        }
      } catch (e) {
        if (!stopped) setError(e instanceof Error ? e.message : "Could not load call");
      }
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id, router]);

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 720, padding: "2rem 0" }}>
        {error && <div className="error" style={{ marginBottom: "1rem" }}>{error}</div>}
        {!call && !error && <p className="muted">Loading…</p>}
        {call && (
          <div className="card stack">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h1 style={{ margin: 0, fontSize: "1.3rem" }}>
                Call to {call.callee_name}
              </h1>
              <span className="badge">{call.status}</span>
            </div>
            <p className="muted" style={{ margin: 0 }}>
              {call.to_number} · {call.provider}
              {call.mock_mode ? " (mock)" : ""} · {call.duration_sec}s ·{" "}
              {new Date(call.created_at).toLocaleString()}
            </p>
            {!TERMINAL.has(call.status) && (
              <p className="muted">Ringing / in progress — this page updates automatically.</p>
            )}
            {call.summary && (
              <div>
                <h2 style={{ fontSize: "1rem" }}>Summary</h2>
                <p>{call.summary}</p>
              </div>
            )}
            {call.transcript && (
              <div>
                <h2 style={{ fontSize: "1rem" }}>Transcript</h2>
                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{call.transcript}</pre>
              </div>
            )}
            {call.recording_url && (
              <a href={call.recording_url} target="_blank" rel="noreferrer">
                Listen to recording
              </a>
            )}
          </div>
        )}
      </main>
    </>
  );
}
