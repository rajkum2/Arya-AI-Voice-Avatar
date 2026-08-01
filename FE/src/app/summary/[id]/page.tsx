"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Nav } from "@/components/Nav";

export default function SummaryPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <Nav />
      <main className="container" style={{ maxWidth: 520, padding: "2rem 0" }}>
        <div className="card stack">
          <h1 style={{ margin: 0 }}>Conversation ended</h1>
          <p className="muted">Session {id.slice(0, 8)}… — thanks for talking with Arya.</p>
          <div className="row">
            <Link href="/gallery" className="btn btn-primary">
              Back to gallery
            </Link>
            <Link href="/history" className="btn btn-secondary">
              View history
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
