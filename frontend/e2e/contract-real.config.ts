import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "contract-real.spec.ts",
  timeout: 240_000,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  outputDir: process.env.E2E_ARTIFACT_DIR ?? "test-results/contract-real",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173",
    browserName: "chromium",
    channel: "chrome",
    headless: true,
    viewport: { width: 1440, height: 900 },
    locale: "ja-JP",
    timezoneId: "Asia/Tokyo",
    reducedMotion: "reduce",
    trace: "off",
    video: "off",
    screenshot: "off",
  },
});
