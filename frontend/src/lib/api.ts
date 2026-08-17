import { getToken } from "./auth";

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
  legal_reasoning?: string; severity_rationale?: string; recommended_action?: string;
  confidence?: number; statute_quote?: string; damages_basis?: string;
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

// The signed session token (held in memory, see lib/auth) travels as a Bearer
// header on every request.
function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
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
  login: (email: string, password: string) =>
    req<{ email: string; token: string }>("/login", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) }),
  listCases: () => req<{ cases: CaseSummary[] }>("/cases").then((r) => r.cases),
  upload: (file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return req<UploadResponse>("/upload", { method: "POST", body: fd });
  },
  analyze: (file_id: string) =>
    req<{ status: string }>("/analyze", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_id }) }),
  extractMetadata: (file_id: string) =>
    req<{ status: string; metadata: AnalysisResult["documentMetadata"] }>("/extract-metadata", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id }) }),
  status: (file_id: string) => req<StatusResponse>(`/status/${file_id}`),
  document: (file_id: string) => req<AnalysisResult>(`/document/${file_id}`),
  // The PDF is owner-scoped, so it can't be a plain <embed> URL (pdf.js can't
  // send the auth header). Fetch it with auth and hand the viewer a blob URL.
  pdfObjectUrl: async (file_id: string): Promise<string> => {
    const res = await fetch(`${BASE_URL}/pdf/${file_id}`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return URL.createObjectURL(await res.blob());
  },
  warmup: () => fetch(`${BASE_URL}/health`).catch(() => {}),
  demandLetter: (file_id: string, sender: object, recipient: object) =>
    fetch(`${BASE_URL}/demand-letter`, { method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ file_id, sender, recipient }) }),
};
