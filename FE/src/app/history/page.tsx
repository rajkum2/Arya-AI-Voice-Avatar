"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<
    Array<{
      id: string;
      avatar_name?: string;
      duration_sec: number;
      created_at: string;
    }>
  >([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    api.conversations().then(setItems).catch((e) => setError(e.message));
  }, [router]);

  return (
    <>
      <Nav />
      <main className="container" style={{ padding: "2rem 0" }}>
        <h1>Conversation history</h1>
        {error && <div className="error">{error}</div>}
        <div className="stack">
          {items.length === 0 && <p className="muted">No conversations yet.</p>}
          {items.map((c) => (
            <div key={c.id} className="card row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{c.avatar_name || "Avatar"}</strong>
                <div className="muted" style={{ fontSize: "0.9rem" }}>
                  {new Date(c.created_at).toLocaleString()}
                </div>
              </div>
              <span className="badge">{c.duration_sec}s</span>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
