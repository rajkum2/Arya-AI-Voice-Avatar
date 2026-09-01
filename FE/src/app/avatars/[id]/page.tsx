"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, Avatar, isLoggedIn } from "@/lib/api";

export default function AvatarDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [avatar, setAvatar] = useState<Avatar | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [calleeName, setCalleeName] = useState("");
  const [toNumber, setToNumber] = useState("");
  const [callProvider, setCallProvider] = useState<"auto" | "ringg" | "bolti">("auto");
  const [callLoading, setCallLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    api.getAvatar(id).then(setAvatar).catch((e) => setError(e.message));
  }, [id, router]);

  async function start() {
    setLoading(true);
    setError("");
    try {
      const session = await api.startSession(id);
      sessionStorage.setItem(`session:${session.id}`, JSON.stringify(session));
      router.push(`/conversation/${session.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start");
    } finally {
      setLoading(false);
    }
  }

  async function startPhoneCall() {
    setCallLoading(true);
    setError("");
    try {
      const call = await api.startCall({
        avatar_id: id,
        callee_name: calleeName.trim(),
        to_number: toNumber.trim(),
        ...(callProvider !== "auto" ? { provider: callProvider } : {}),
      });
      router.push(`/calls/${call.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not place call");
    } finally {
      setCallLoading(false);
    }
  }

  if (!avatar && !error) {
    return (
      <>
        <Nav />
        <main className="container"><p className="muted">Loading…</p></main>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 720, padding: "2rem 0" }}>
        {error && <div className="error" style={{ marginBottom: "1rem" }}>{error}</div>}
        {avatar && (
          <div className="card stack">
            <div className="row">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={avatar.thumbnail_url}
                alt={avatar.name}
                width={96}
                height={96}
                style={{ borderRadius: 20 }}
              />
              <div>
                <h1 style={{ margin: 0 }}>{avatar.name}</h1>
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  AI persona · {avatar.category} · {avatar.provider}
                </p>
              </div>
            </div>
            <p>{avatar.description}</p>
            {avatar.greeting && (
              <div className="muted" style={{ fontStyle: "italic" }}>
                “{avatar.greeting}”
              </div>
            )}
            <button className="btn btn-primary" onClick={start} disabled={loading}>
              {loading ? "Starting…" : "Start conversation"}
            </button>
          </div>
        )}
        {avatar && (
          <div className="card stack" style={{ marginTop: "1rem" }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Get a phone call instead</h2>
              <details style={{ fontSize: "0.85rem" }}>
                <summary className="muted" style={{ cursor: "pointer" }}>
                  ⓘ Setup info
                </summary>
                <div className="muted" style={{ marginTop: "0.5rem", maxWidth: 420 }}>
                  An AI agent calls the number you enter — you&apos;ll be talking to an
                  artificial voice, not a human. Calls run through Ringg AI or Bolti AI
                  (pick one below, or leave on Auto): without configured provider keys
                  this runs in mock mode and auto-completes after a few seconds with a
                  simulated transcript. To place real calls, set the{" "}
                  <code>RINGG_*</code> / <code>BOLTI_*</code> env vars and configure the
                  webhook — see <code>docs/RINGG_SETUP.md</code> and{" "}
                  <code>docs/BOLTI_SETUP.md</code> in the repo.
                </div>
              </details>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "0.9rem" }}>
              {avatar.name} calls your phone (E.164 format, e.g. +919876543210).
            </p>
            <input
              type="text"
              placeholder="Your name"
              value={calleeName}
              onChange={(e) => setCalleeName(e.target.value)}
            />
            <input
              type="tel"
              placeholder="+919876543210"
              value={toNumber}
              onChange={(e) => setToNumber(e.target.value)}
            />
            <label className="muted" style={{ fontSize: "0.9rem" }}>
              Provider{" "}
              <select
                value={callProvider}
                onChange={(e) =>
                  setCallProvider(e.target.value as "auto" | "ringg" | "bolti")
                }
              >
                <option value="auto">Auto (backend default)</option>
                <option value="ringg">Ringg AI</option>
                <option value="bolti">Bolti AI</option>
              </select>
            </label>
            <button
              className="btn"
              onClick={startPhoneCall}
              disabled={callLoading || !calleeName.trim() || !toNumber.trim()}
            >
              {callLoading ? "Calling…" : "Call my phone"}
            </button>
          </div>
        )}
      </main>
    </>
  );
}
