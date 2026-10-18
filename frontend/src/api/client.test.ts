import { api, ApiError, setCsrfToken } from "./client";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(new Response(body === null ? null : JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("api client", () => {
  it("sends the CSRF token only on state-changing requests, with same-origin credentials", async () => {
    setCsrfToken("token-123");
    const fetch = mockFetch(200, { ok: true });
    await api("GET", "/api/v1/projects", { query: { q: "a&b", empty: "" } });
    await api("POST", "/api/v1/projects", { body: { name: "x" } });
    const [getUrl, getInit] = fetch.mock.calls[0] as [string, RequestInit];
    const [, postInit] = fetch.mock.calls[1] as [string, RequestInit];
    expect(getUrl).toBe("/api/v1/projects?q=a%26b");
    expect((getInit.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
    expect((postInit.headers as Record<string, string>)["X-CSRF-Token"]).toBe("token-123");
    expect(postInit.credentials).toBe("same-origin");
  });

  it("raises ApiError with the server's code, message and trace id", async () => {
    mockFetch(403, { code: "forbidden", message: "この操作を行う権限がありません。", trace_id: "a".repeat(32) });
    const err = await api("POST", "/api/v1/projects", { body: {} }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 403, code: "forbidden", traceId: "a".repeat(32) });
  });

  it("falls back to a generic Japanese message when the body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>bad gateway</html>", { status: 502 })));
    const err = (await api("GET", "/api/v1/projects").catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe("処理できませんでした。");
    expect(err.message).not.toContain("html");
  });
});
