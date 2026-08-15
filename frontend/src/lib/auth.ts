"use client";

// Accounts are email + password. On login the backend returns a signed session
// token; we keep it (plus the email, for display) in localStorage and send the
// token as `Authorization: Bearer <token>` on every request.

const EMAIL_KEY = "clause.email";
const TOKEN_KEY = "clause.token";

export function getUser(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(EMAIL_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setSession(email: string, token: string): void {
  window.localStorage.setItem(EMAIL_KEY, email);
  window.localStorage.setItem(TOKEN_KEY, token);
  // Let other tabs / the shell react to sign-in/out.
  window.dispatchEvent(new Event("clause:auth"));
}

export function clearUser(): void {
  window.localStorage.removeItem(EMAIL_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("clause:auth"));
}

export function isValidEmail(email: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim());
}
