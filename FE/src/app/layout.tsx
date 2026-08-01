import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arya — AI Voice Avatar",
  description: "Real-time interactive photorealistic AI avatar conversations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
