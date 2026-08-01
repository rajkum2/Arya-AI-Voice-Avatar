"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, saveTokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await api.login(email, password);
      saveTokens(tokens);
      const boot = await api.bootstrapMe();
      router.push(boot.consent_required ? "/consent" : "/gallery");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 440, padding: "2rem 0" }}>
        <div className="card stack">
          <h1 style={{ margin: 0 }}>Welcome back</h1>
          <p className="muted">Demo: demo@example.com / demo12345 · Admin: admin@example.com / admin12345</p>
          {error && <div className="error">{error}</div>}
          <form className="stack" onSubmit={onSubmit}>
            <div>
              <label className="label">Email</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" disabled={loading} type="submit">
              {loading ? "Signing in…" : "Log in"}
            </button>
          </form>
          <p className="muted">
            No account? <Link href="/signup">Sign up</Link>
          </p>
        </div>
      </main>
    </>
  );
}
