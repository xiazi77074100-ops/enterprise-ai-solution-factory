import { defineConfig, devices } from "@playwright/test";

// Expects the backend on :8000 and `npm run dev` on :5173 (see docs/design/dev_setup.md).
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  // reducedMotion: screenshots must not catch the page fade-in midway (theme.css stops animation).
  use: { baseURL: "http://localhost:5173", locale: "ja-JP", timezoneId: "Asia/Tokyo", reducedMotion: "reduce" },
  projects: [
    { name: "desktop-1440", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "mobile-390", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } },
  ],
});
