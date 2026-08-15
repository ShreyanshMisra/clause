"use client";

// Password-less accounts: the email is the username. We keep it in
// localStorage and send it to the backend as the X-User-Email header. This is
// deliberately lightweight identification, not real authentication.

const KEY = "clause.email";

export function getUser(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setUser(email: string): void {
  window.localStorage.setItem(KEY, email);
  // Let other tabs / the shell react to sign-in/out.
  window.dispatchEvent(new Event("clause:auth"));
}

export function clearUser(): void {
  window.localStorage.removeItem(KEY);
  window.dispatchEvent(new Event("clause:auth"));
}

export function isValidEmail(email: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim());
}
