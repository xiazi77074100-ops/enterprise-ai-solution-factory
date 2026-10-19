// P3-01d: documents (list / upload / download), the document input of a run, and the export links, against a
// mocked API (contract-shaped fixtures). The backend side of the same flow is
// backend/tests/integration/test_invoice_workflow.py (production capabilities end to end).
import { expect, test, type Page, type Route } from "@playwright/test";

const SHOTS = process.env.E2E_SCREENSHOT_DIR ?? "test-results/screens";
const ME = "11111111-1111-4111-8111-111111111111";
const PROJECT = "22222222-2222-4222-8222-222222222222";
const RUN = "33333333-3333-4333-8333-333333333333";
const SOLUTION = "55555555-5555-4555-8555-555555555555";
const DOC = "77777777-7777-4777-8777-777777777777";
const HASH = "a".repeat(64);
const NOW = "2026-10-19T03:00:00Z";

const doc = (id: string, name: string, media_type: string, pages: number) => ({
  id, project_id: PROJECT, display_name: name, media_type, size_bytes: 123456, page_count: pages, sha256: HASH,
  data_origin: "synthetic", created_at: NOW,
});  // prettier-ignore
const workflow = {
  schema_version: "1",
  workflow_id: "invoice-poc",
  version: 2,
  name: "請求書処理",
  inputs: [{ name: "document", type: "document_ref", to: [{ node_id: "parse", field: "document_ref" }] }],
  nodes: [{}, {}, {}, {}, {}, {}],
};
const run = { id: RUN, solution_id: SOLUTION, project_id: PROJECT, workflow_hash: HASH, status: "succeeded", execution_mode: "real",
  trace_id: "b".repeat(32), input_sha256: HASH, failure_code: null, started_at: NOW, finished_at: NOW,
  usage: { llm_input_tokens: 0, llm_output_tokens: 0, cost_jpy: 0, cost_known: true } };  // prettier-ignore
const node = (node_id: string, capability_id: string) => ({
  id: crypto.randomUUID(), node_id, capability_id, capability_version: "1.0.0", capability_version_id: SOLUTION, status: "succeeded",
  execution_mode: "real", attempt: 1, duration_ms: 1200, input_sha256: HASH, output_sha256: HASH, output_summary: null, llm: null,
  error_code: null,
});  // prettier-ignore

type Captured = { method: string; path: string; body: string | null; json: unknown; headers: Record<string, string> };

async function mockApi(page: Page, captured: Captured[]) {
  const docs = [
    doc(DOC, "請求書_2025年6月分_とても長いファイル名で表の幅が崩れないことを確かめるための文字列.pdf", "application/pdf", 2),
    doc(SOLUTION, "scan-0008.png", "image/png", 1),
  ];
  await page.route("**/api/v1/**", async (route: Route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (req.method() !== "GET") {
      const raw = req.postData();
      let parsed: unknown = null;
      try {
        parsed = req.postDataJSON();
      } catch {
        parsed = null; // multipart
      }
      captured.push({ method: req.method(), path, body: raw, json: parsed, headers: req.headers() });
    }
    if (path === "/api/v1/session") {
      return json({ user: { id: ME, display_name: "試験 太郎", roles: [] }, csrf_token: "c".repeat(64), expires_at: "2099-01-01T00:00:00Z" });
    }
    if (path === `/api/v1/projects/${PROJECT}`) {
      return json({ id: PROJECT, name: "請求書の POC", business_domain: "経理", description: null, owner_id: ME, created_at: NOW, updated_at: NOW });
    }
    if (path === `/api/v1/projects/${PROJECT}/members`) return json([{ user_id: ME, display_name: "試験 太郎", roles: ["solution_lead"] }]);
    if (path === `/api/v1/projects/${PROJECT}/requirements`) return json([]);
    if (path === `/api/v1/projects/${PROJECT}/documents` && req.method() === "POST") {
      const created = doc(crypto.randomUUID(), "inv-0001.pdf", "application/pdf", 1);
      docs.unshift(created);
      return json(created, 201);
    }
    if (path === `/api/v1/projects/${PROJECT}/documents`) return json({ items: docs, page: { total: docs.length, next_cursor: null } });
    if (path === `/api/v1/projects/${PROJECT}/solutions`) {
      return json({
        items: [{ id: SOLUTION, project_id: PROJECT, requirement_revision_id: SOLUTION, state: "approved", workflow, workflow_hash: HASH,
          created_by: SOLUTION, approved_by: ME, created_at: NOW }],
        page: { total: 1, next_cursor: null },
      });  // prettier-ignore
    }
    if (path === "/api/v1/runs") return json({ items: [run], page: { total: 1, next_cursor: null } });
    if (path === `/api/v1/solutions/${SOLUTION}/runs`) return json({ ...run, status: "pending" }, 202);
    if (path === `/api/v1/runs/${RUN}`) return json(run);
    if (path === `/api/v1/runs/${RUN}/nodes`) {
      return json([
        node("parse", "document.parser"), node("extract", "document.rule_extractor"), node("validate", "document.rule_validator"),
        node("locate", "document.evidence_locator"), node("review", "review.human"), node("export", "result.exporter"),
      ]);  // prettier-ignore
    }
    if (path === `/api/v1/runs/${RUN}/trace`) return json({ items: [], page: { total: 0, next_cursor: null } });
    return json({ code: "not_found", message: "対象が見つかりません。", trace_id: "0".repeat(32) }, 404);
  });
}

async function shoot(page: Page, name: string, project: string) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "page must not scroll horizontally (ui-design §9)").toBeLessThanOrEqual(0);
  await page.screenshot({ path: `${SHOTS}/${project}-${name}.png`, fullPage: true });
}

test("documents: list, upload, run with a document, export (mocked API)", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  page.on("pageerror", (err) => errors.push(err.message));
  const captured: Captured[] = [];
  await mockApi(page, captured);
  const p = info.project.name;

  await page.goto(`/projects/${PROJECT}`);
  const panel = page.getByRole("region", { name: "文書" });
  await expect(panel.getByText("合成データ").first()).toBeVisible();
  const download = panel.getByRole("link", { name: "ダウンロード" }).first();
  await expect(download).toHaveAttribute("href", `/api/v1/documents/${DOC}/content`);
  await expect(download).toHaveAttribute("download", "");
  await shoot(page, "20-documents", p);

  // Upload: the main button stays disabled until an allowed file is chosen (ui-design §5.1).
  await panel.getByRole("button", { name: "登録" }).click();
  const dialog = page.getByRole("dialog", { name: "文書の登録" });
  const submit = dialog.getByRole("button", { name: "登録", exact: true });
  await expect(submit).toBeDisabled();
  const input = dialog.getByLabel(/ファイル/);
  await input.setInputFiles({ name: "image.svg", mimeType: "image/svg+xml", buffer: Buffer.from("<svg/>") });
  await expect(dialog.getByText("PDF・PNG・JPEG のファイルを選択してください。").first()).toBeVisible();
  await expect(submit).toBeDisabled();
  await input.setInputFiles({ name: "inv-0001.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });
  await expect(submit).toBeEnabled();
  await shoot(page, "21-upload", p);
  await submit.click();
  await expect(page.getByText("文書を登録しました。")).toBeVisible();
  const upload = captured.find((c) => c.path.endsWith("/documents") && c.method === "POST");
  expect(upload?.headers["content-type"]).toMatch(/^multipart\/form-data; boundary=/);
  expect(upload?.headers["x-csrf-token"]).toBe("c".repeat(64));
  expect(upload?.body).toContain('name="data_origin"');
  expect(upload?.body).toContain("synthetic");

  // Run: the document input is chosen from the project's documents.
  await page.getByRole("region", { name: "解決策" }).getByRole("button", { name: "実行" }).click();
  const start = page.getByRole("dialog", { name: "解決策の実行" });
  const runButton = start.getByRole("button", { name: "実行", exact: true });
  await expect(runButton).toBeDisabled();
  await start.getByLabel(/document/).selectOption(DOC);
  await expect(runButton).toBeEnabled();
  await runButton.click();
  await page.getByRole("dialog", { name: "実行の開始" }).getByRole("button", { name: "実行する" }).click();
  const started = captured.find((c) => c.path === `/api/v1/solutions/${SOLUTION}/runs`);
  expect(started?.json).toEqual({ inputs: { document: DOC } });

  // Run monitor: a succeeded run with an exporter offers CSV / JSON downloads.
  await expect(page).toHaveURL(new RegExp(`/runs/${RUN}$`));
  await expect(page.getByRole("link", { name: "CSV で出力" })).toHaveAttribute("href", `/api/v1/runs/${RUN}/export?format=csv`);
  await expect(page.getByRole("link", { name: "JSON で出力" })).toHaveAttribute("href", `/api/v1/runs/${RUN}/export?format=json`);
  await shoot(page, "22-run-export", p);

  expect(errors, "no console errors").toEqual([]);
});
