"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getUser, setUser, isValidEmail } from "@/lib/auth";
import { GooeyEmailInput } from "@/components/GooeyEmailInput";

export default function LoginPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already signed in → skip straight to the dashboard.
  useEffect(() => {
    if (getUser()) router.replace("/dashboard");
  }, [router]);

  const handleSubmit = async (email: string) => {
    setError(null);
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setBusy(true);
    try {
      const { email: normalized } = await api.login(email);
      setUser(normalized);
      router.replace("/dashboard");
    } catch (e) {
      setError((e as Error).message || "Could not sign in. Is the backend running?");
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6">
      <div
        className="w-full"
        style={{
          borderRadius: "28px",
          padding: "48px 40px 40px",
          background: "rgba(250,249,245,0.74)",
          backdropFilter: "blur(24px) saturate(1.5)",
          WebkitBackdropFilter: "blur(24px) saturate(1.5)",
          border: "1.5px solid rgba(255,255,255,0.55)",
          outline: "1px solid rgba(107,107,99,0.14)",
          outlineOffset: "-2px",
          boxShadow: [
            "0 4px 6px rgba(20,20,19,0.04)",
            "0 10px 40px rgba(20,20,19,0.09)",
            "0 32px 72px rgba(20,20,19,0.06)",
            "0 1px 0 rgba(255,255,255,0.9) inset",
          ].join(", "),
          animation: "slideUp 0.6s cubic-bezier(.16,1,.3,1) both",
        }}
      >
        {/* Wordmark */}
        <div
          className="mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5"
          style={{
            background: "rgba(217,119,87,0.09)",
            border: "1px solid rgba(217,119,87,0.22)",
          }}
        >
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M7 1L2 3.5v4c0 2.5 2.2 4.7 5 5 2.8-.3 5-2.5 5-5v-4L7 1z"
              fill="var(--accent)" opacity="0.9" />
          </svg>
          <span className="text-xs font-semibold uppercase"
            style={{ color: "var(--accent-deep)", letterSpacing: "0.12em" }}>
            Clause
          </span>
        </div>

        <h1
          className="mb-2"
          style={{
            fontSize: "clamp(1.8rem, 5vw, 2.2rem)",
            fontWeight: 650,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
            color: "var(--ink)",
          }}
        >
          Know what you&rsquo;re signing.
        </h1>
        <p
          className="mb-8 text-sm font-medium leading-relaxed"
          style={{ color: "var(--ink-muted)" }}
        >
          Enter your email to continue — no password needed. Your email is your
          account, and your analysed leases live under it.
        </p>

        <GooeyEmailInput onSubmit={handleSubmit} busy={busy} error={error} />

        <p className="mt-6 text-xs" style={{ color: "var(--ink-subtle)" }}>
          Personal information in your lease is redacted before analysis.
        </p>
      </div>
    </main>
  );
}
