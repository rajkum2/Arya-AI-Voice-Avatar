"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn, Session } from "@/lib/api";

type TurnState = "listening" | "thinking" | "speaking";
type Caption = { speaker: string; text: string; is_final: boolean };

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [state, setState] = useState<TurnState>("listening");
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [input, setInput] = useState("");
  const [captionsOn, setCaptionsOn] = useState(true);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  const endCall = useCallback(async () => {
    try {
      wsRef.current?.send(JSON.stringify({ type: "end" }));
      wsRef.current?.close();
      await api.endSession(id);
    } catch {
      /* ignore */
    }
    router.push(`/summary/${id}`);
  }, [id, router]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    const raw = sessionStorage.getItem(`session:${id}`);
    let s: Session | null = raw ? (JSON.parse(raw) as Session) : null;
    const boot = async () => {
      try {
        s = await api.getSession(id);
      } catch {
        /* keep sessionStorage cache if API fails */
      }
      if (!s) {
        setError("Session not found");
        return;
      }
      setSession(s);
      setCaptionsOn(s.captions_enabled);

      const token = localStorage.getItem("access_token");
      const ws = new WebSocket(`${api.wsUrl}/ws/session/${id}?token=${token}`);
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "state") setState(msg.state);
        if (msg.type === "transcript") {
          setCaptions((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.speaker === msg.speaker && !last.is_final) {
              next[next.length - 1] = {
                speaker: msg.speaker,
                text: msg.text,
                is_final: msg.is_final,
              };
            } else {
              next.push({
                speaker: msg.speaker,
                text: msg.text,
                is_final: msg.is_final,
              });
            }
            return next.slice(-40);
          });
        }
        if (msg.type === "error") setError(msg.message);
      };
      ws.onerror = () => setError("WebSocket error");
    };
    void boot();

    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);

    return () => {
      clearInterval(timer);
      window.removeEventListener("beforeunload", onBeforeUnload);
      wsRef.current?.close();
    };
  }, [id, router]);

  function sendText() {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "user_text", text }));
    setInput("");
  }

  function interrupt() {
    wsRef.current?.send(JSON.stringify({ type: "interrupt" }));
  }

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 900, padding: "1rem 0 3rem" }}>
        <div
          className="card"
          style={{
            minHeight: 480,
            display: "flex",
            flexDirection: "column",
            position: "relative",
            overflow: "hidden",
            background:
              "radial-gradient(circle at 50% 30%, #2a1f55 0%, #0b1220 60%)",
          }}
        >
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="badge">AI · not a human</span>
            <span className="muted">
              {mm}:{ss}
              {session?.mock_mode ? " · mock" : ""}
            </span>
          </div>

          <div
            style={{
              flex: 1,
              display: "grid",
              placeItems: "center",
              padding: "2rem 1rem",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  margin: "0 auto 1rem",
                  background:
                    state === "speaking"
                      ? "linear-gradient(135deg,#22d3ee,#7c5cff)"
                      : state === "thinking"
                        ? "linear-gradient(135deg,#fbbf24,#f97316)"
                        : "linear-gradient(135deg,#34d399,#0ea5e9)",
                  boxShadow: "0 0 60px rgba(124,92,255,0.35)",
                  animation: state !== "listening" ? "pulse 1.2s ease infinite" : undefined,
                }}
              />
              <div className={`state-${state}`} style={{ fontWeight: 700, textTransform: "capitalize" }}>
                {state}
              </div>
              <p className="muted" style={{ maxWidth: 360, margin: "0.5rem auto 0" }}>
                {session?.mock_mode
                  ? "Mock mode: type a message below. Wire HeyGen/LiveKit for real video."
                  : "Live WebRTC avatar track will render here."}
              </p>
            </div>
          </div>

          {captionsOn && (
            <div
              style={{
                background: "rgba(0,0,0,0.55)",
                borderRadius: 12,
                padding: "0.75rem 1rem",
                maxHeight: 140,
                overflowY: "auto",
                marginBottom: "1rem",
              }}
            >
              {captions.length === 0 && (
                <span className="muted">Captions will appear here…</span>
              )}
              {captions.map((c, i) => (
                <div key={i} style={{ marginBottom: 4, opacity: c.is_final ? 1 : 0.7 }}>
                  <strong style={{ color: c.speaker === "user" ? "#93c5fd" : "#c4b5fd" }}>
                    {c.speaker === "user" ? "You" : "Avatar"}:
                  </strong>{" "}
                  {c.text}
                </div>
              ))}
            </div>
          )}

          {error && <div className="error" style={{ marginBottom: "0.75rem" }}>{error}</div>}

          <div className="row" style={{ justifyContent: "center" }}>
            <button className="btn btn-secondary" onClick={() => setCaptionsOn((v) => !v)}>
              {captionsOn ? "CC on" : "CC off"}
            </button>
            {session?.barge_in_enabled && (
              <button className="btn btn-secondary" onClick={interrupt}>
                Interrupt
              </button>
            )}
            <button className="btn btn-danger" onClick={endCall}>
              End call
            </button>
          </div>

          <div className="row" style={{ marginTop: "1rem" }}>
            <input
              className="input"
              placeholder="Type what you would say (accessibility + mock STT)…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendText()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={sendText}>
              Send
            </button>
          </div>
        </div>
      </main>
      <style jsx global>{`
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.04); }
          100% { transform: scale(1); }
        }
      `}</style>
    </>
  );
}
