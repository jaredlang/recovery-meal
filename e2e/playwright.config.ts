import { defineConfig, devices } from "@playwright/test";

const live = process.env.E2E_LIVE === "true";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: live ? 15 * 60_000 : 3 * 60_000,
  expect: { timeout: live ? 10 * 60_000 : 30_000 },
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5184",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
