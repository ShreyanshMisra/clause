"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";
import { AppNav } from "@/components/AppNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  // Client-side guard: no account → send to the gooey login.
  useEffect(() => {
    const guard = () => {
      if (getUser()) setReady(true);
      else router.replace("/login");
    };
    guard();
  }, [router]);

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm" style={{ color: "var(--ink-subtle)" }}>Loading…</p>
      </main>
    );
  }

  return (
    <>
      <AppNav />
      {children}
    </>
  );
}
