import Link from "next/link";
import { Nav } from "@/components/Nav";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main className="container" style={{ padding: "3rem 0 5rem" }}>
        <section className="stack" style={{ maxWidth: 720, gap: "1.25rem" }}>
          <span className="badge">EU AI Act Art. 50 ready · Speech-to-speech</span>
          <h1 style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)", lineHeight: 1.1, margin: 0 }}>
            Talk face-to-face with a{" "}
            <span style={{ color: "var(--accent-2)" }}>real-time AI avatar</span>
          </h1>
          <p className="muted" style={{ fontSize: "1.15rem", lineHeight: 1.6 }}>
            Arya delivers low-latency conversations with photorealistic avatars — captions,
            barge-in, and a provider-agnostic backend so you can start on HeyGen and migrate
            in-house later.
          </p>
          <div className="row">
            <Link href="/signup" className="btn btn-primary">
              Start free
            </Link>
            <Link href="/login" className="btn btn-secondary">
              Log in (demo@example.com)
            </Link>
          </div>
        </section>

        <section className="grid grid-3" style={{ marginTop: "3.5rem" }}>
          {[
            {
              title: "Conversation-first",
              body: "Listening / thinking / speaking states modeled on GPT-Live and Meet.",
            },
            {
              title: "Compliance built-in",
              body: "Consent gate, persistent AI badge, export & erasure for GDPR.",
            },
            {
              title: "Provider seam",
              body: "Mock → HeyGen → Anam/Tavus → MuseTalk without rewriting clients.",
            },
          ].map((f) => (
            <div key={f.title} className="card">
              <h3 style={{ marginTop: 0 }}>{f.title}</h3>
              <p className="muted">{f.body}</p>
            </div>
          ))}
        </section>
      </main>
    </>
  );
}
