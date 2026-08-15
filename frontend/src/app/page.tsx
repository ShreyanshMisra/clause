"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";

// Entry point: route to the dashboard when signed in, otherwise to login.
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getUser() ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-sm" style={{ color: "var(--ink-subtle)" }}>Loading…</p>
    </main>
  );
}
