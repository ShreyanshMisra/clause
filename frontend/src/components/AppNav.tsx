"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getUser, clearUser } from "@/lib/auth";

const TABS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analyze", label: "Upload & Analyze" },
];

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setEmail(getUser());
    sync();
    window.addEventListener("clause:auth", sync);
    return () => window.removeEventListener("clause:auth", sync);
  }, []);

  const logout = () => {
    clearUser();
    router.replace("/login");
  };

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: "rgba(250,249,245,0.72)",
        backdropFilter: "blur(20px) saturate(1.4)",
        WebkitBackdropFilter: "blur(20px) saturate(1.4)",
        borderBottom: "1px solid rgba(107,107,99,0.12)",
      }}
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
        {/* Wordmark */}
        <Link href="/dashboard" className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M7 1L2 3.5v4c0 2.5 2.2 4.7 5 5 2.8-.3 5-2.5 5-5v-4L7 1z"
              fill="var(--accent)" opacity="0.9" />
          </svg>
          <span className="text-sm font-bold uppercase"
            style={{ color: "var(--accent-deep)", letterSpacing: "0.12em" }}>
            Clause
          </span>
        </Link>

        {/* Tabs */}
        <nav
          className="flex items-center gap-1 rounded-full p-1"
          style={{
            background: "rgba(240,238,230,0.7)",
            border: "1px solid rgba(107,107,99,0.10)",
          }}
        >
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className="rounded-full px-4 py-1.5 text-[13px] font-medium transition-all"
                style={{
                  color: active ? "#fff" : "var(--ink-muted)",
                  background: active ? "var(--accent)" : "transparent",
                  boxShadow: active ? "0 2px 10px rgba(217,119,87,0.28)" : "none",
                  letterSpacing: "-0.01em",
                }}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        {/* Account */}
        <div className="flex items-center gap-3">
          <span
            className="hidden text-xs sm:inline"
            style={{ color: "var(--ink-subtle)", letterSpacing: "0.01em" }}
            title={email ?? undefined}
          >
            {email}
          </span>
          <button
            type="button"
            onClick={logout}
            className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              color: "var(--ink-muted)",
              border: "1px solid rgba(107,107,99,0.16)",
              background: "transparent",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(107,107,99,0.06)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
