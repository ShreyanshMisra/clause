"use client";

// Accounts are email + password. On login the backend returns a signed session
// token, which we keep (with the email, for display) in module memory only —
// never in localStorage — so an injected/XSS script can't read a persisted
// token. Requests send it as `Authorization: Bearer <token>`. The tradeoff: a
// full page refresh drops the in-memory session, so the user signs in again.

let _token: string | null = null;
let _email: string | null = null;

export function getUser(): string | null {
  return _email;
}

export function getToken(): string | null {
  return _token;
}

export function setSession(email: string, token: string): void {
  _email = email;
  _token = token;
  // Let other tabs / the shell react to sign-in/out.
  if (typeof window !== "undefined") window.dispatchEvent(new Event("clause:auth"));
}

export function clearUser(): void {
  _email = null;
  _token = null;
  if (typeof window !== "undefined") window.dispatchEvent(new Event("clause:auth"));
}

export function isValidEmail(email: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim());
}
