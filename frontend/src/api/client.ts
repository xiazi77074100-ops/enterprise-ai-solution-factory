// Single fetch wrapper (jp-secure-coding frontend-react.md): same-origin cookies, CSRF header on
// state-changing requests, server errors surfaced as {code, message, trace_id} only.
import type { components } from "./schema";

export type Schemas = components["schemas"];

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly traceId: string | null;
  readonly details: { field: string; reason: string }[];

  constructor(status: number, code: string, message: string, traceId: string | null, details: ApiError["details"]) {
    super(message);
    this.status = status;
    this.code = code;
    this.traceId = traceId;
    this.details = details;
  }
}

let csrfToken: string | null = null; // kept in memory only, never in storage

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

type Query = Record<string, string | number | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  return url.pathname + url.search;
}

export async function api<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  options: { query?: Query; body?: unknown; headers?: Record<string, string> } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...options.headers, Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const res = await fetch(buildUrl(path, options.query), {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (data ?? {}) as Partial<Schemas["Error"]>;
    throw new ApiError(
      res.status,
      err.code ?? "error",
      err.message ?? "処理できませんでした。",
      err.trace_id ?? null,
      err.details ?? [],
    );
  }
  return data as T;
}

/** A fresh Idempotency-Key for one user intent (keep it while the same dialog is open, so a retry is not a new run). */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
