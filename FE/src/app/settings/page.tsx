"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn, User } from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    api.me().then(setUser).catch(() => router.replace("/login"));
  }, [router]);

  async function exportData() {
    const data = await api.exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "arya-export.json";
    a.click();
    setMsg("Export downloaded.");
  }

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 640, padding: "2rem 0" }}>
        <h1>Settings</h1>
        {user && (
          <div className="card stack">
            <div>
              <div className="label">Account</div>
              <strong>{user.display_name}</strong>
              <div className="muted">{user.email}</div>
              <div className="muted">
                Quota: {user.used_minutes}/{user.quota_minutes} min used · role {user.role}
              </div>
            </div>
            <div>
              <div className="label">Privacy & data (GDPR)</div>
              <div className="row">
                <button className="btn btn-secondary" onClick={exportData}>
                  Export my data
                </button>
              </div>
              {msg && <p className="muted">{msg}</p>}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
