"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Room,
  RoomEvent,
  Track,
  type RemoteTrack,
  type RemoteTrackPublication,
  type RemoteParticipant,
} from "livekit-client";
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
  const [livekitStatus, setLivekitStatus] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const roomRef = useRef<Room | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const endCall = useCallback(async () => {
    try {
      wsRef.current?.send(JSON.stringify({ type: "end" }));
      wsRef.current?.close();
      if (roomRef.current) {
        await roomRef.current.disconnect();
        roomRef.current = null;
      }
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
    let cancelled = false;

    const boot = async () => {
      try {
        s = await api.getSession(id);
      } catch {
        /* keep sessionStorage cache if API fails */
      }
      // Prefer richer session from startSession storage when getSession omits tokens
      if (raw) {
        try {
          const cached = JSON.parse(raw) as Session;
          if (s) {
            s = {
              ...s,
              room_url: s.room_url || cached.room_url,
              room_token: s.room_token || cached.room_token,
              mock_mode: s.mock_mode ?? cached.mock_mode,
              transport: s.transport || cached.transport,
              sandbox: s.sandbox ?? cached.sandbox,
              failover_reason: s.failover_reason || cached.failover_reason,
            };
          } else {
            s = cached;
          }
        } catch {
          /* ignore */
        }
      }
      if (cancelled) return;
      if (!s) {
        setError("Session not found");
        return;
      }
      setSession(s);
      setCaptionsOn(s.captions_enabled);

      // LiveKit video when LiveAvatar returned a real room
      const isLiveKit =
        !s.mock_mode &&
        !!s.room_url &&
        !!s.room_token &&
        (s.room_url.startsWith("wss://") || s.room_url.startsWith("ws://"));

      if (isLiveKit) {
        try {
          setLivekitStatus("Connecting to avatar…");
          const room = new Room({ adaptiveStream: true, dynacast: true });
          roomRef.current = room;

          const attachVideo = (
            track: RemoteTrack,
            publication: RemoteTrackPublication,
            participant: RemoteParticipant
          ) => {
            if (track.kind !== Track.Kind.Video) return;
            if (!videoRef.current) return;
            track.attach(videoRef.current);
            setLivekitStatus(`Connected · ${participant.identity || "avatar"}`);
            setState("speaking");
          };

          room.on(
            RoomEvent.TrackSubscribed,
            (track, publication, participant) => {
              attachVideo(track, publication, participant);
            }
          );
          room.on(RoomEvent.Disconnected, () => {
            setLivekitStatus("Disconnected");
          });

          await room.connect(s.room_url, s.room_token);
          await room.localParticipant.setMicrophoneEnabled(true);
          setLivekitStatus("Live · mic on");

          // Attach already-subscribed video tracks
          room.remoteParticipants.forEach((p) => {
            p.trackPublications.forEach((pub) => {
              if (pub.track && pub.kind === Track.Kind.Video) {
                attachVideo(pub.track as RemoteTrack, pub, p);
              }
            });
          });
        } catch (e) {
          setError(
            e instanceof Error
              ? `LiveKit connect failed: ${e.message}`
              : "LiveKit connect failed"
          );
          setLivekitStatus("LiveKit error");
        }
      }

      // Backend transcript WS still useful for mock + captions sidecar
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
      ws.onerror = () => {
        if (!isLiveKit) setError("WebSocket error");
      };
    };
    void boot();

    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);

    return () => {
      cancelled = true;
      clearInterval(timer);
      window.removeEventListener("beforeunload", onBeforeUnload);
      wsRef.current?.close();
      roomRef.current?.disconnect();
      roomRef.current = null;
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
  const isLive =
    session &&
    !session.mock_mode &&
    session.room_url?.startsWith("wss://");

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
              {session?.sandbox ? " · sandbox" : ""}
              {session?.mock_mode ? " · mock" : ` · ${session?.provider || ""}`}
            </span>
          </div>

          <div
            style={{
              flex: 1,
              display: "grid",
              placeItems: "center",
              padding: "1rem",
              minHeight: 280,
            }}
          >
            {isLive ? (
              <div style={{ width: "100%", maxWidth: 560 }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  style={{
                    width: "100%",
                    borderRadius: 16,
                    background: "#000",
                    aspectRatio: "16/9",
                    objectFit: "cover",
                  }}
                />
                <p className="muted" style={{ textAlign: "center", marginTop: 8 }}>
                  {livekitStatus || "Starting LiveAvatar…"}
                </p>
                <div
                  className={`state-${state}`}
                  style={{ textAlign: "center", fontWeight: 700, textTransform: "capitalize" }}
                >
                  {state}
                </div>
              </div>
            ) : (
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
                  }}
                />
                <div
                  className={`state-${state}`}
                  style={{ fontWeight: 700, textTransform: "capitalize" }}
                >
                  {state}
                </div>
                <p className="muted" style={{ maxWidth: 360, margin: "0.5rem auto 0" }}>
                  {session?.failover_reason
                    ? `Fallback mock: ${session.failover_reason.slice(0, 120)}`
                    : session?.mock_mode
                      ? "Mock mode: type a message below. LiveAvatar video appears when provider session succeeds."
                      : "Connecting…"}
                </p>
              </div>
            )}
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
                <span className="muted">
                  {isLive
                    ? "Speak naturally — LiveAvatar handles the conversation in FULL mode."
                    : "Captions will appear here…"}
                </span>
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

          {error && (
            <div className="error" style={{ marginBottom: "0.75rem" }}>
              {error}
            </div>
          )}

          <div className="row" style={{ justifyContent: "center" }}>
            <button className="btn btn-secondary" onClick={() => setCaptionsOn((v) => !v)}>
              {captionsOn ? "CC on" : "CC off"}
            </button>
            {session?.barge_in_enabled && !isLive && (
              <button className="btn btn-secondary" onClick={interrupt}>
                Interrupt
              </button>
            )}
            <button className="btn btn-danger" onClick={endCall}>
              End call
            </button>
          </div>

          {!isLive && (
            <div className="row" style={{ marginTop: "1rem" }}>
              <input
                className="input"
                placeholder="Type what you would say (mock STT)…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendText()}
                style={{ flex: 1 }}
              />
              <button className="btn btn-primary" onClick={sendText}>
                Send
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
