import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const LOGIN_ID = process.env.E2E_LOGIN_ID ?? "";
const PASSWORD = process.env.E2E_PASSWORD ?? "";
const SHOTS = process.env.E2E_SCREENSHOT_DIR ?? "test-results/screens";
const EXAMPLES = join(import.meta.dirname, "..", "..", "contracts", "examples", "capabilities");

test.skip(!LOGIN_ID || !PASSWORD, "E2E_LOGIN_ID / E2E_PASSWORD are not set");

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "page must not scroll horizontally (ui-design §9)").toBeLessThanOrEqual(0);
}

async function shoot(page: Page, name: string, project: string) {
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: `${SHOTS}/${project}-${name}.png`, fullPage: true });
}

test.beforeAll(async ({ request }) => {
  // Register the six example capability versions through the API (idempotent: 201 or 200).
  const login = await request.post("/api/v1/session", {
    data: { login_id: LOGIN_ID, password: PASSWORD },
    headers: { Origin: "http://localhost:5173" },
  });
  expect(login.ok()).toBeTruthy();
  const { csrf_token } = (await login.json()) as { csrf_token: string };
  for (const file of readdirSync(EXAMPLES)) {
    const res = await request.post("/api/v1/capabilities", {
      data: JSON.parse(readFileSync(join(EXAMPLES, file), "utf-8")),
      headers: { Origin: "http://localhost:5173", "X-CSRF-Token": csrf_token },
    });
    expect([200, 201]).toContain(res.status());
  }
});

test("login → project → requirement → catalog", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    // The session probe answers 401 before login by contract (openapi getSession); Chrome logs it as an error.
    const expected = msg.text().includes("401") && msg.location().url.endsWith("/api/v1/session");
    if (msg.type() === "error" && !expected) errors.push(`${msg.text()} @ ${msg.location().url}`);
  });
  page.on("pageerror", (err) => errors.push(err.message));
  const p = info.project.name;

  await page.goto("/projects");
  await expect(page).toHaveURL(/\/login$/);
  const loginButton = page.getByRole("button", { name: "ログイン" });
  await expect(loginButton).toBeDisabled();
  await shoot(page, "01-login", p);
  await page.getByLabel(/ユーザー ID/).fill(LOGIN_ID);
  await page.getByLabel(/パスワード/).fill(PASSWORD);
  await loginButton.click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByText("検証用（本番利用不可）")).toBeVisible();

  const name = `請求書処理 POC ${p} ${Date.now()}`;
  await page.getByRole("button", { name: "新規作成" }).click();
  const dialog = page.getByRole("dialog", { name: "プロジェクトの作成" });
  const create = dialog.getByRole("button", { name: "作成", exact: true });
  await expect(create).toBeDisabled();
  await dialog.getByRole("textbox", { name: "プロジェクト名" }).fill(name);
  await dialog.getByRole("textbox", { name: "業務区分" }).fill("経理");
  await expect(create).toBeEnabled();
  await create.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();

  await page.getByLabel(/新しい要件/).fill("合成の請求書から請求元・金額・登録番号を抽出し、合計の不一致を確認する。");
  await page.getByRole("button", { name: "版を登録" }).click();
  await expect(page.getByRole("cell", { name: "第 1 版" })).toBeVisible();
  await expect(page.getByText("未承認")).toBeVisible();
  await shoot(page, "02-project-detail", p);

  await page.getByRole("link", { name: "プロジェクト一覧" }).first().click();
  await page.getByPlaceholder("プロジェクト名で検索").fill(name);
  await expect(page.getByRole("link", { name })).toBeVisible();
  await shoot(page, "03-project-list", p);

  await page.goto("/catalog");
  await expect(page.getByText("document.parser@1.0.0")).toBeVisible();
  await page.getByLabel("接続方式").selectOption("llm");
  await expect(page.getByText("document.extractor@1.0.0")).toBeVisible();
  await expect(page.getByText("document.parser@1.0.0")).toHaveCount(0);
  await shoot(page, "04-catalog-list", p);
  await page.getByRole("link", { name: "Structured Extractor" }).click();
  await expect(page.getByRole("heading", { name: "出力の契約" })).toBeVisible();
  await shoot(page, "05-capability-detail", p);

  expect(errors, "no console errors").toEqual([]);
});
