// P2-03: solutions → run monitor → review, against a mocked API (contract-shaped fixtures).
// Production has no runnable business capability until Phase 3, so these screens are checked with mocks; the
// backend side of the same flow is covered by backend/tests/integration/test_runs.py.
import { expect, test, type Page, type Route } from "@playwright/test";

const SHOTS = process.env.E2E_SCREENSHOT_DIR ?? "test-results/screens";
const ME = "11111111-1111-4111-8111-111111111111";
const PROJECT = "22222222-2222-4222-8222-222222222222";
const RUN = "33333333-3333-4333-8333-333333333333";
const REVIEW = "44444444-4444-4444-8444-444444444444";
const SOLUTION = "55555555-5555-4555-8555-555555555555";
const CAP = "66666666-6666-4666-8666-666666666666";
const HASH = "a".repeat(64);
const NOW = "2026-10-18T03:00:00Z";
const page1 = (total: number) => ({ total, next_cursor: null });

const workflow = {
  schema_version: "1",
  workflow_id: "sample-review",
  version: 1,
  name: "書類の確認フロー（とても長い名前の解決策で表の幅が崩れないことを確かめるための文字列）",
  inputs: [{ name: "text", type: "string", to: [{ node_id: "draft", field: "text" }] }],
  nodes: [{}, {}, {}],
};
const solution = (id: string, state: string) => ({
  id,
  project_id: PROJECT,
  requirement_revision_id: CAP,
  state,
  workflow,
  workflow_hash: HASH,
  created_by: CAP,
  approved_by: state === "approved" ? ME : null,
  created_at: NOW,
});
const run = (id: string, status: string, mode: string, failure: string | null = null) => ({
  id,
  solution_id: SOLUTION,
  project_id: PROJECT,
  workflow_hash: HASH,
  status,
  execution_mode: mode,
  trace_id: "b".repeat(32),
  input_sha256: HASH,
  failure_code: failure,
  started_at: NOW,
  finished_at: status === "waiting_review" ? null : NOW,
  usage: { llm_input_tokens: 120, llm_output_tokens: 40, cost_jpy: 0, cost_known: true },
});
const node = (node_id: string, status: string, mode: string, extra: object = {}) => ({
  id: crypto.randomUUID(),
  node_id,
  capability_id: `sample.${node_id}`,
  capability_version: "1.0.0",
  capability_version_id: CAP,
  status,
  execution_mode: mode,
  attempt: 1,
  duration_ms: status === "succeeded" ? 1234 : null,
  input_sha256: HASH,
  output_sha256: status === "succeeded" ? HASH : null,
  output_summary: null,
  llm: null,
  error_code: null,
  ...extra,
});
const evidence = (status: string) => ({ document_id: CAP, page: 1, start: 10, end: 24, text_sha256: HASH, status });
const task = (decided: boolean) => ({
  id: REVIEW,
  run_id: RUN,
  node_id: "review",
  status: decided ? "completed" : "pending",
  assigned_to: ME,
  items: [
    { path: "/fields/vendor_name", label: "vendor_name", proposed_value: "架空商事株式会社（TEST ONLY）", origin: "ai_draft", evidence: [evidence("verified")], flags: [] },
    { path: "/fields/total", label: "total", proposed_value: 1000, origin: "ai_draft", evidence: [evidence("unverified")], flags: [] },
    { path: "/fields/memo", label: "memo", proposed_value: null, origin: "ai_draft", evidence: [], flags: [] },
    { path: "/findings/0", label: "TK-001", proposed_value: "合計が明細の和と一致しません", origin: "rule", evidence: [],
      flags: [{ rule_id: "TK-001", severity: "critical", result: "fail" }] },
  ],
  decision: decided ? "approved_with_corrections" : null,
  decided_by: decided ? ME : null,
  decided_at: decided ? NOW : null,
});  // prettier-ignore

type Captured = { method: string; path: string; body: unknown; headers: Record<string, string> };

async function mockApi(page: Page, captured: Captured[]) {
  let decided = false;
  await page.route("**/api/v1/**", async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (req.method() !== "GET") captured.push({ method: req.method(), path, body: req.postDataJSON(), headers: req.headers() });

    if (path === "/api/v1/session") {
      return json({ user: { id: ME, display_name: "試験 太郎", roles: [] }, csrf_token: "c".repeat(64), expires_at: "2099-01-01T00:00:00Z" });
    }
    if (path === `/api/v1/projects/${PROJECT}`) {
      return json({ id: PROJECT, name: "試験案件", business_domain: "経理", description: null, owner_id: ME, created_at: NOW, updated_at: NOW });
    }
    if (path === `/api/v1/projects/${PROJECT}/members`) {
      return json([{ user_id: ME, display_name: "試験 太郎", roles: ["solution_lead", "business_reviewer"] }]);
    }
    if (path === `/api/v1/projects/${PROJECT}/requirements`) return json([]);
    if (path === `/api/v1/projects/${PROJECT}/documents`) return json({ items: [], page: page1(0) });
    if (path === `/api/v1/projects/${PROJECT}/solutions`) {
      return json({ items: [solution(CAP, "validated"), solution(SOLUTION, "approved")], page: page1(2) });
    }
    if (path === "/api/v1/runs") {
      return json({
        items: [run(RUN, "waiting_review", "mixed"), run(CAP, "failed", "real", "budget_exceeded"), run(HASH.slice(0, 8) + RUN.slice(8), "succeeded", "mock")],
        page: page1(3),
      });
    }
    if (path === `/api/v1/solutions/${SOLUTION}/runs`) return json(run(RUN, "pending", "real"), 202);
    if (path === `/api/v1/runs/${RUN}`) return json(run(RUN, decided ? "running" : "waiting_review", "mixed"));
    if (path === `/api/v1/runs/${RUN}/nodes`) {
      return json([
        node("draft", "succeeded", "mock", { output_summary: { fields: 3, findings: 1 }, llm: { provider: "mock" } }),
        node("review", decided ? "succeeded" : "waiting_review", "real"),
        node("summary", "pending", "real"),
      ]);
    }
    if (path === `/api/v1/runs/${RUN}/trace`) {
      const event = (event_type: string, metadata: object, actor: object = { type: "system", id: "executor" }) => ({
        event_id: crypto.randomUUID(), event_type, timestamp: NOW, node_id: "draft", status: "ok", actor, redacted_metadata: metadata,
      });  // prettier-ignore
      return json({
        items: [event("run.started", {}, { type: "user", id: ME }), event("node.started", {}), event("node.completed", {}), event("review.requested", { item_count: 4 })],
        page: page1(4),
      });
    }
    if (path === "/api/v1/reviews") return json({ items: [task(decided)], page: page1(1) });
    if (path === `/api/v1/runs/${RUN}/reviews/${REVIEW}`) return json(task(decided));
    if (path === `/api/v1/runs/${RUN}/reviews/${REVIEW}/decision`) {
      decided = true;
      return json(task(true));
    }
    return json({ code: "not_found", message: "対象が見つかりません。", trace_id: "0".repeat(32) }, 404);
  });
}

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "page must not scroll horizontally (ui-design §9)").toBeLessThanOrEqual(0);
}

async function shoot(page: Page, name: string, project: string) {
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: `${SHOTS}/${project}-${name}.png`, fullPage: true });
}

test("solutions → run monitor → review with a correction (mocked API)", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  page.on("pageerror", (err) => errors.push(err.message));
  const captured: Captured[] = [];
  await mockApi(page, captured);
  const p = info.project.name;

  // Project: solutions (approve / run) and runs with status and mode badges.
  await page.goto(`/projects/${PROJECT}`);
  const solutions = page.getByRole("region", { name: "解決策" });
  await expect(solutions.getByRole("button", { name: "承認" })).toBeVisible();
  const runs = page.getByRole("region", { name: "実行", exact: true });
  await expect(runs.getByText("一部模擬（MOCK）")).toBeVisible();
  await expect(runs.getByText("模擬（MOCK）", { exact: true })).toBeVisible();
  await shoot(page, "10-project-solutions-runs", p);

  await solutions.getByRole("button", { name: "実行" }).click();
  const start = page.getByRole("dialog", { name: "解決策の実行" });
  const runButton = start.getByRole("button", { name: "実行", exact: true });
  await expect(runButton).toBeDisabled(); // required input is empty
  await start.getByLabel(/text/).fill("確認してほしい文書");
  await expect(runButton).toBeEnabled();
  await runButton.click();
  await page.getByRole("dialog", { name: "実行の開始" }).getByRole("button", { name: "実行する" }).click();
  await expect(page).toHaveURL(new RegExp(`/runs/${RUN}$`));
  const started = captured.find((c) => c.path.endsWith("/runs") && c.method === "POST");
  expect(started?.body).toEqual({ inputs: { text: "確認してほしい文書" } });
  expect(started?.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);

  // Run monitor: waiting for review is never shown as finished; mixed mode is labeled.
  await expect(page.getByText("確認待ち").first()).toBeVisible();
  await expect(page.getByText("一部模擬（MOCK）").first()).toBeVisible();
  await expect(page.getByRole("region", { name: "処理の流れ" }).getByText("模擬（MOCK）", { exact: true })).toBeVisible();
  await shoot(page, "11-run-monitor", p);
  await page.getByRole("link", { name: "確認を開く" }).click();

  // Review: approve only without corrections, correct only with a valid change, reject only with a comment.
  await expect(page).toHaveURL(new RegExp(`/runs/${RUN}/reviews/${REVIEW}$`));
  const approve = page.getByRole("button", { name: "承認", exact: true });
  const correct = page.getByRole("button", { name: "修正して承認" });
  const reject = page.getByRole("button", { name: "却下" });
  await expect(approve).toBeEnabled();
  await expect(correct).toBeDisabled();
  await expect(reject).toBeDisabled();
  await expect(page.getByText("AI 下書き").first()).toBeVisible();
  await expect(page.getByText("未確認").first()).toBeVisible();
  await expect(page.getByText("該当あり")).toBeVisible();
  await shoot(page, "12-review", p);

  const total = page.getByRole("textbox", { name: "確認後の値" }).nth(1);
  await total.fill("abc");
  await expect(page.getByText("元の値と同じ形式で入力してください")).toBeVisible();
  await expect(correct).toBeDisabled();
  await total.fill("1200");
  await expect(correct).toBeEnabled();
  await expect(approve).toBeDisabled();
  await expect(page.getByText("修正：1000 → 1200")).toBeVisible();
  await shoot(page, "13-review-corrected", p);

  await correct.click();
  await page.getByRole("dialog").getByRole("button", { name: "修正して承認する" }).click();
  await expect(page.getByText("「修正して承認」を記録しました。")).toBeVisible();
  const decision = captured.find((c) => c.path.endsWith("/decision"));
  expect(decision?.body).toEqual({ decision: "approved_with_corrections", corrections: [{ path: "/fields/total", corrected_value: 1200 }] });
  expect(decision?.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
  await expect(approve).toHaveCount(0); // decided: no more actions

  await page.goto("/reviews");
  await expect(page.getByRole("link", { name: RUN.slice(0, 8) })).toBeVisible();
  await shoot(page, "14-review-list", p);

  expect(errors, "no console errors").toEqual([]);
});
