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
      </main>
    </>
  );
}
