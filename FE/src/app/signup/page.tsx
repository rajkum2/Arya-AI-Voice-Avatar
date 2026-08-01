"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, saveTokens } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await api.register(email, password, name);
      saveTokens(tokens);
      router.push("/consent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 440, padding: "2rem 0" }}>
        <div className="card stack">
          <h1 style={{ margin: 0 }}>Create account</h1>
          {error && <div className="error">{error}</div>}
          <form className="stack" onSubmit={onSubmit}>
            <div>
              <label className="label">Display name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Password (min 8)</label>
              <input
                className="input"
                type="password"
                minLength={8}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" disabled={loading} type="submit">
              {loading ? "Creating…" : "Sign up"}
            </button>
          </form>
          <p className="muted">
            Have an account? <Link href="/login">Log in</Link>
          </p>
        </div>
      </main>
    </>
  );
}
