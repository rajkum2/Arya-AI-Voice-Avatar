"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, isLoggedIn } from "@/lib/api";

export default function ConsentPage() {
  const router = useRouter();
  const [disclosure, setDisclosure] = useState("");
  const [understand, setUnderstand] = useState(false);
  const [voice, setVoice] = useState(false);
  const [store, setStore] = useState(false);
  const [improve, setImprove] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
    api.bootstrap().then((b) => setDisclosure(b.ai_disclosure)).catch(() => {});
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.submitConsent({
        understand_ai: understand,
        voice_processing: voice,
        store_transcripts: store,
        improve_service: improve,
      });
      router.push("/gallery");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const canContinue = understand && voice;

  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 640, padding: "2rem 0" }}>
        <div className="card stack">
          <span className="badge">Required · EU AI Act Art. 50</span>
          <h1 style={{ margin: 0 }}>You&apos;ll be talking to an AI, not a human</h1>
          <p className="muted">{disclosure}</p>
          <ul className="muted">
            <li>Voice audio is processed to text, then an AI response, then speech + avatar video.</li>
            <li>Provider API keys stay on the server; you only receive short-lived session tokens.</li>
            <li>You can export or delete your data later in Settings.</li>
          </ul>
          {error && <div className="error">{error}</div>}
          <form className="stack" onSubmit={onSubmit}>
            <label className="checkbox">
              <input type="checkbox" checked={understand} onChange={(e) => setUnderstand(e.target.checked)} />
              <span>I understand this is an AI (required)</span>
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={voice} onChange={(e) => setVoice(e.target.checked)} />
              <span>I consent to voice processing for conversations (required)</span>
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={store} onChange={(e) => setStore(e.target.checked)} />
              <span>Store transcripts for history (optional)</span>
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={improve} onChange={(e) => setImprove(e.target.checked)} />
              <span>Use anonymized data to improve the service (optional)</span>
            </label>
            <button className="btn btn-primary" type="submit" disabled={!canContinue || loading}>
              {loading ? "Saving…" : "Agree & Continue"}
            </button>
          </form>
        </div>
      </main>
    </>
  );
}
