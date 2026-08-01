"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, Avatar, isLoggedIn, User } from "@/lib/api";

export default function GalleryPage() {
  const router = useRouter();
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.listAvatars(), api.me(), api.bootstrapMe()])
      .then(([list, me, boot]) => {
        if (boot.consent_required) router.replace("/consent");
        setAvatars(list);
        setUser(me);
      })
      .catch((e) => setError(e.message));
  }, [router]);

  async function search(value: string) {
    setQ(value);
    try {
      setAvatars(await api.listAvatars(value || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <>
      <Nav />
      <main className="container" style={{ padding: "1.5rem 0 3rem" }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: "1.25rem" }}>
          <div>
            <h1 style={{ margin: 0 }}>Choose an avatar</h1>
            <p className="muted">Talk naturally — captions and AI disclosure stay on during calls.</p>
          </div>
          {user && (
            <span className="badge">
              {user.remaining_minutes} min remaining
            </span>
          )}
        </div>
        <input
          className="input"
          placeholder="Search personas…"
          value={q}
          onChange={(e) => search(e.target.value)}
          style={{ marginBottom: "1.25rem", maxWidth: 420 }}
        />
        {error && <div className="error">{error}</div>}
        <div className="grid grid-3">
          {avatars.map((a) => (
            <Link key={a.id} href={`/avatars/${a.id}`} className="card" style={{ display: "block" }}>
              <div className="row" style={{ marginBottom: "0.75rem" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={a.thumbnail_url}
                  alt={a.name}
                  width={56}
                  height={56}
                  style={{ borderRadius: 14, background: "#000" }}
                />
                <div>
                  <strong>{a.name}</strong>
                  <div className="muted" style={{ fontSize: "0.85rem" }}>
                    {a.category}
                    {a.is_featured ? " · Featured" : ""}
                  </div>
                </div>
              </div>
              <p className="muted" style={{ margin: 0, fontSize: "0.92rem" }}>
                {a.description}
              </p>
            </Link>
          ))}
        </div>
      </main>
    </>
  );
}
