export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadResponse {
  file_id: string; filename: string; size: number;
  pii_redacted: Record<string, number>; message: string;
}
export interface StatusResponse {
  file_id: string; status: string; progress: number; message: string; filename?: string;
}
export interface BoundingRect {
  x1: number; y1: number; x2: number; y2: number; width: number; height: number; pageNumber: number;
}
export interface HighlightPosition {
  boundingRect: BoundingRect; rects: BoundingRect[]; pageWidth: number; pageHeight: number;
}
export interface Finding {
  id: string; page: number; quoted_text: string; category: string;
  severity: string; color: string; statute_citation: string | null;
  explanation: string; damages_estimate: number | null; position: HighlightPosition | null;
}
export interface AnalysisResult {
  documentId: string;
  documentMetadata: { parties: { landlord: string; tenant: string; property: string };
    monthlyRent: string; leaseTerm: string; securityDeposit: string };
  deidentificationSummary: { redactedEntities: Record<string, number>; encryptionStatus: string };
  analysisSummary: { overallRisk: string; issuesFound: number; estimatedRecovery: string;
    topIssues: { title: string; severity: string; amount?: string }[] };
  highlights: Finding[];
}

export interface CaseSummary {
  id: string; filename: string; created_at: number; status: string;
  overall_risk: string | null; issues_found: number | null;
  estimated_recovery: string | null;
}

// The signed-in email travels as a header on every request (see lib/auth).
function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const email = window.localStorage.getItem("clause.email");
  return email ? { "X-User-Email": email } : {};
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
  return res.json();
}

export const api = {
  login: (email: string) =>
    req<{ email: string }>("/login", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }),
  listCases: () => req<{ cases: CaseSummary[] }>("/cases").then((r) => r.cases),
  upload: (file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return req<UploadResponse>("/upload", { method: "POST", body: fd });
  },
  analyze: (file_id: string) =>
    req<{ status: string }>("/analyze", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_id }) }),
  status: (file_id: string) => req<StatusResponse>(`/status/${file_id}`),
  document: (file_id: string) => req<AnalysisResult>(`/document/${file_id}`),
  pdfUrl: (file_id: string) => `${BASE_URL}/pdf/${file_id}`,
  warmup: () => fetch(`${BASE_URL}/health`).catch(() => {}),
  demandLetter: (file_id: string, sender: object, recipient: object) =>
    fetch(`${BASE_URL}/demand-letter`, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id, sender, recipient }) }),
};
