"use client";

import Link from "next/link";
import { clearTokens, isLoggedIn } from "@/lib/api";
import { useEffect, useState } from "react";

export function Nav() {
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => setLoggedIn(isLoggedIn()), []);

  return (
    <nav className="nav container">
      <Link href="/" className="logo">
        Arya <span>AI</span>
      </Link>
      <div className="row">
        {loggedIn ? (
          <>
            <Link href="/gallery">Gallery</Link>
            <Link href="/history">History</Link>
            <Link href="/settings">Settings</Link>
            <Link href="/admin">Admin</Link>
            <button
              className="btn btn-secondary"
              onClick={() => {
                clearTokens();
                window.location.href = "/";
              }}
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link href="/login">Log in</Link>
            <Link href="/signup" className="btn btn-primary">
              Get started
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
