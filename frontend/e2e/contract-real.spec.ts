// 契約書devの実API接続試験。模擬API・精度評価・原文ビューアの試験ではない。
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import type { Schemas } from "../src/api/client";

const ROOT = join(import.meta.dirname, "..", "..");
const OUT = join(ROOT, "reports", "review", "2026-10-26-contract-ui");
const PDF = join(ROOT, "fixtures", "contract", "dev", "documents", "con-0001.pdf");
const PROJECT = process.env.E2E_PROJECT_ID ?? "";
const SOLUTION = process.env.E2E_SOLUTION_ID ?? "";
const LOGIN = process.env.E2E_LOGIN_ID ?? "";
const PASSWORD = process.env.E2E_PASSWORD ?? "";
const CORRECTED = "画面確認用の架空会社 TEST ONLY";

test.use({ trace: "off", video: "off", screenshot: "off" });
test.skip(
  process.env.E2E_CONTRACT_REAL !== "1" || !PROJECT || !SOLUTION || !LOGIN || !PASSWORD,
  "専用環境のE2E_CONTRACT_REAL・案件/解決策・認証情報が未設定",
);

function sha256(data: Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

async function shoot(page: Page, name: string): Promise<void> {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "画面全体に横スクロールがない").toBeLessThanOrEqual(0);
  await page.screenshot({ path: join(OUT, name), fullPage: true });
}

test("契約書dev：登録から確認値修正・根拠表示・実ファイル出力まで", async ({ page, baseURL }) => {
  test.setTimeout(300_000);
  expect(baseURL, "専用画面のURLが必要").toBeTruthy();
  const origin = new URL(baseURL ?? "http://invalid.invalid");
  expect(["localhost", "127.0.0.1"]).toContain(origin.hostname);
  expect(origin.protocol).toBe("http:");
  expect(PROJECT).toMatch(/^[0-9a-f-]{36}$/);
  expect(SOLUTION).toMatch(/^[0-9a-f-]{36}$/);
  mkdirSync(OUT, { recursive: true });
  const network: { method: string; path: string; status?: number; failure?: string }[] = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/")) network.push({ method: response.request().method(), path: url.pathname, status: response.status() });
  });
  page.on("requestfailed", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) network.push({ method: request.method(), path: url.pathname, failure: request.failure()?.errorText });
  });
  let pageErrors = 0;
  let consoleErrors = 0;
  page.on("pageerror", () => { pageErrors += 1; });
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const expected = message.text().includes("401") && new URL(message.location().url || baseURL!).pathname === "/api/v1/session";
    if (!expected) consoleErrors += 1;
  });

  // ブラウザのログインで取得したCookieをそのまま実APIへ送る。値自体は記録しない。
  await page.goto(`/projects/${PROJECT}`);
  await expect(page).toHaveURL(/\/login$/);
  const login = page.getByRole("button", { name: "ログイン", exact: true });
  await expect(login).toBeDisabled();
  await page.getByLabel(/ユーザー ID/).fill(LOGIN);
  await page.getByLabel(/パスワード/).fill(PASSWORD);
  await expect(login).toBeEnabled();
  expect((await page.getByLabel(/パスワード/).inputValue()) === PASSWORD).toBe(true);
  const loginResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === "/api/v1/session", { timeout: 20_000 });
  await login.click();
  try {
    expect((await loginResponse).status()).toBe(200);
    await expect(page).not.toHaveURL(/\/login$/);
  } catch (error) {
    writeFileSync(join(OUT, "login-diagnostic.json"), JSON.stringify({
      network, page_error_count: pageErrors, console_error_count: consoleErrors,
      login_button_disabled: await login.isDisabled(),
      password_length: (await page.getByLabel(/パスワード/).inputValue()).length,
      alerts: await page.getByRole("alert").allTextContents(),
    }, null, 2) + "\n", "utf-8");
    throw error;
  }
  await page.goto(`/projects/${PROJECT}`);
  await expect(page.getByRole("region", { name: "文書", exact: true })).toBeVisible();

  const documents = page.getByRole("region", { name: "文書", exact: true });
  await documents.getByRole("button", { name: "登録", exact: true }).click();
  const upload = page.getByRole("dialog", { name: "文書の登録" });
  const register = upload.getByRole("button", { name: "登録", exact: true });
  await expect(register).toBeDisabled();
  await upload.getByLabel(/ファイル/).setInputFiles({
    name: "拒否確認.svg", mimeType: "image/svg+xml", buffer: Buffer.from("<svg/>"),
  });
  await expect(register).toBeDisabled();
  await expect(upload.getByText("PDF・PNG・JPEG のファイルを選択してください。").first()).toBeVisible();
  await upload.getByLabel(/ファイル/).setInputFiles(PDF);
  await expect(register).toBeEnabled();
  const documentResponse = page.waitForResponse((r) =>
    r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v1/projects/${PROJECT}/documents`,
  );
  await register.click();
  const registered = await documentResponse;
  expect(registered.status()).toBe(201);
  const document = await registered.json() as Schemas["Document"];
  expect(document.project_id).toBe(PROJECT);
  expect(document.data_origin).toBe("synthetic");
  expect(document.sha256).toBe(sha256(readFileSync(PDF)));
  await expect(page.getByText("文書を登録しました。")).toBeVisible();
  await shoot(page, "01-document-registered.png");

  const solutions = page.getByRole("region", { name: "解決策", exact: true });
  const solutionResponse = await page.request.get(`/api/v1/solutions/${SOLUTION}`);
  expect(solutionResponse.status()).toBe(200);
  const solution = await solutionResponse.json() as Schemas["Solution"];
  expect(solution.project_id).toBe(PROJECT);
  expect(solution.state).toBe("approved");
  const workflow = solution.workflow as unknown as { name: string; version: number };
  expect(typeof workflow.name).toBe("string");
  expect(workflow.version).toBe(3);
  const solutionRow = solutions.getByRole("row").filter({ hasText: workflow.name });
  await expect(solutionRow).toHaveCount(1);
  await solutionRow.getByRole("button", { name: "実行", exact: true }).click();
  const start = page.getByRole("dialog", { name: "解決策の実行" });
  await expect(start.getByRole("button", { name: "実行", exact: true })).toBeDisabled();
  await start.getByLabel(/document/).selectOption(document.id);
  await start.getByRole("button", { name: "実行", exact: true }).click();
  const runResponse = page.waitForResponse((r) =>
    r.request().method() === "POST" && new URL(r.url()).pathname === `/api/v1/solutions/${SOLUTION}/runs`,
  );
  await page.getByRole("dialog", { name: "実行の開始" }).getByRole("button", { name: "実行する" }).click();
  const started = await runResponse;
  expect(started.status()).toBe(202);
  const run = await started.json() as Schemas["Run"];
  await expect(page).toHaveURL(new RegExp(`/runs/${run.id}$`));
  await expect(page.getByRole("link", { name: "確認を開く" })).toBeVisible({ timeout: 180_000 });
  await shoot(page, "02-waiting-review.png");
  await page.getByRole("link", { name: "確認を開く" }).click();
  await expect(page).toHaveURL(new RegExp(`/runs/${run.id}/reviews/[0-9a-f-]{36}$`));
  const reviewMatch = new URL(page.url()).pathname.match(/\/reviews\/([0-9a-f-]{36})$/);
  expect(reviewMatch).not.toBeNull();
  const reviewId = reviewMatch?.[1] ?? "";
  const reviewPath = `/api/v1/runs/${run.id}/reviews/${reviewId}`;
  const reviewResponse = await page.request.get(reviewPath);
  expect(reviewResponse.status()).toBe(200);
  const review = await reviewResponse.json() as Schemas["ReviewTask"];
  const party = review.items.find((item) => item.path === "/fields/party_a");
  expect(party).toBeDefined();
  expect(typeof party?.proposed_value).toBe("string");
  expect(party?.proposed_value).not.toBe(CORRECTED);
  const evidenceItem = review.items.find((item) => item.path.startsWith("/fields/") && item.evidence.some((e) => e.status === "verified"));
  expect(evidenceItem).toBeDefined();
  const evidence = evidenceItem?.evidence.find((item) => item.status === "verified");
  expect(evidence).toBeDefined();
  expect(evidence?.document_id).toBe(document.id);
  const fields = page.getByRole("region", { name: "確認する項目", exact: true });
  const evidenceRow = fields.getByRole("listitem").filter({ has: page.getByText(evidenceItem?.label ?? "", { exact: true }) });
  await expect(evidenceRow.getByText("照合済み", { exact: true }).first()).toBeVisible();
  await expect(evidenceRow.getByText(`${evidence?.page} ページ ${evidence?.start}–${evidence?.end}`, { exact: true })).toBeVisible();
  await evidenceRow.scrollIntoViewIfNeeded();
  await shoot(page, "03a-review-evidence.png");
  const row = fields.getByRole("listitem").filter({ has: page.getByText(party?.label ?? "", { exact: true }) });
  await expect(page.getByRole("button", { name: "修正して承認", exact: true })).toBeDisabled();
  const comment = page.getByLabel("コメント", { exact: true });
  await comment.fill("あ".repeat(2001));
  await expect(comment).toHaveAttribute("aria-invalid", "true");
  for (const name of ["承認", "修正して承認", "却下"]) {
    await expect(page.getByRole("button", { name, exact: true })).toBeDisabled();
  }
  await shoot(page, "03b-invalid-comment.png");
  await comment.fill("");
  await expect(comment).toHaveAttribute("aria-invalid", "false");
  await row.getByLabel("確認後の値", { exact: true }).fill(CORRECTED);
  await expect(page.getByRole("button", { name: "承認", exact: true })).toBeDisabled();
  await shoot(page, "03-review-correction-evidence.png");
  await page.getByRole("button", { name: "修正して承認", exact: true }).click();
  const decisionResponse = page.waitForResponse((r) =>
    r.request().method() === "POST" && new URL(r.url()).pathname === `${reviewPath}/decision`,
  );
  await page.getByRole("dialog", { name: "確認の決定：修正して承認" })
    .getByRole("button", { name: "修正して承認する" }).click();
  const decided = await decisionResponse;
  expect(decided.status()).toBe(200);
  expect(decided.request().postDataJSON()).toEqual({
    decision: "approved_with_corrections", corrections: [{ path: "/fields/party_a", corrected_value: CORRECTED }],
  });
  await expect(page.getByText("「修正して承認」を記録しました。")).toBeVisible();
  await page.goto(`/runs/${run.id}`);
  await expect(page.getByRole("link", { name: "JSON で出力" })).toBeVisible({ timeout: 90_000 });
  const finishedResponse = await page.request.get(`/api/v1/runs/${run.id}`);
  expect(finishedResponse.status()).toBe(200);
  const finished = await finishedResponse.json() as Schemas["Run"];
  expect(finished.status).toBe("succeeded");
  expect(finished.execution_mode).toBe("real");
  const nodesResponse = await page.request.get(`/api/v1/runs/${run.id}/nodes`);
  expect(nodesResponse.status()).toBe(200);
  const nodes = await nodesResponse.json() as Schemas["NodeRun"][];
  expect(nodes).toHaveLength(6);
  for (const node of nodes) {
    expect(node.status).toBe("succeeded");
    expect(node.execution_mode).toBe("real");
  }
  await expect(page.getByRole("region", { name: "処理の流れ" }).getByText("実行", { exact: true }).first()).toBeVisible();
  await shoot(page, "04-success-export.png");

  const exports: Record<string, { file: string; sha256: string; bytes: number }> = {};
  for (const format of ["json", "csv"] as const) {
    const downloadReady = page.waitForEvent("download");
    await page.getByRole("link", { name: format === "json" ? "JSON で出力" : "CSV で出力" }).click();
    const download = await downloadReady;
    expect(await download.failure()).toBeNull();
    const filename = `export.${format}`;
    await download.saveAs(join(OUT, filename));
    const content = readFileSync(join(OUT, filename));
    exports[format] = { file: filename, sha256: sha256(content), bytes: content.length };
  }
  const exported = JSON.parse(readFileSync(join(OUT, "export.json"), "utf-8")) as {
    run_id: string; export_id: string; decision: string; fields: Record<string, unknown>;
  };
  expect(exported.run_id).toBe(run.id);
  expect(exported.decision).toBe("approved_with_corrections");
  expect(exported.fields.party_a).toBe(CORRECTED);
  const csv = readFileSync(join(OUT, "export.csv"), "utf-8");
  expect(csv.startsWith("\uFEFF")).toBeTruthy();
  expect(csv).toContain("契約書レビュー結果\r\n");
  expect(csv).toContain("区分,名前,値,重要度,結果\r\n");
  expect(csv).toContain(`項目,party_a,${CORRECTED},,\r\n`);
  const traceResponse = await page.request.get(`/api/v1/runs/${run.id}/trace?limit=200`);
  expect(traceResponse.status()).toBe(200);
  const trace = await traceResponse.json() as { items: { event_id: string; event_type: string; redacted_metadata: Record<string, unknown> }[] };
  const correction = trace.items.find((event) => event.redacted_metadata.decision === "approved_with_corrections");
  expect(correction?.redacted_metadata.correction_count).toBe(1);
  expect(pageErrors, "ブラウザの未処理エラーなし").toBe(0);
  expect(consoleErrors, "想定した未認証session確認以外のconsole errorなし").toBe(0);
  writeFileSync(join(OUT, "evidence.json"), JSON.stringify({
    captured_at: new Date().toISOString(), api_mode: "real", viewport: page.viewportSize(),
    project_id: PROJECT, solution_id: SOLUTION, document_id: document.id, dev_document_sha256: document.sha256,
    run_id: run.id, trace_id: finished.trace_id, workflow_hash: finished.workflow_hash,
    run_status: finished.status, execution_mode: finished.execution_mode, review_id: reviewId,
    nodes: nodes.map((node) => ({ node_id: node.node_id, status: node.status, execution_mode: node.execution_mode })),
    test_sha256: sha256(readFileSync(join(ROOT, "frontend/e2e/contract-real.spec.ts"))),
    implementation_manifest_sha256: sha256(readFileSync(join(ROOT, "backend/app/catalog/implementation_manifest.json"))),
    corrected_path: "/fields/party_a", correction_count: 1, correction_event_id: correction?.event_id,
    evidence_displayed: evidence, export_id: exported.export_id, downloads: exports,
    screenshots: ["01-document-registered.png", "02-waiting-review.png", "03a-review-evidence.png", "03b-invalid-comment.png", "03-review-correction-evidence.png", "04-success-export.png"],
    console_error_count: consoleErrors,
    input_rejection: ["SVGは登録ボタン無効", "2001文字のコメントは入力エラー、決定ボタン無効"], page_error_count: pageErrors,
    limitations: ["原文ビューア・品質評価・モバイルは未検証", "専用APIによる案件・解決策等の事前準備あり", "自己診断であり第三者診断ではない"],
  }, null, 2) + "\n", "utf-8");
});
