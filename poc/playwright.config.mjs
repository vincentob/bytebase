import { defineConfig } from "../frontend/node_modules/@playwright/test/index.mjs";

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.mjs",
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { outputFolder: "artifacts/browser-report", open: "never" }]],
  outputDir: "artifacts/browser-results",
  use: {
    baseURL: "http://127.0.0.1:17880",
    headless: true,
    locale: "en-US",
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
