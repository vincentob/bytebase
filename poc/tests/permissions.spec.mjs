import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { test, expect } from "../../frontend/node_modules/@playwright/test/index.mjs";

const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const yaml = require("js-yaml");
const accounts = yaml.load(readFileSync(new URL("../.state/accounts.yaml", import.meta.url), "utf8"));
const api = "http://127.0.0.1:17880";

async function login(page, role) {
  const result = await page.request.post(api + "/v1/auth/login", {
    data: { ...accounts[role], web: true },
  });
  expect(result.status()).toBe(200);
}

test("owner can manage custom roles", async ({ page }) => {
  await login(page, "owner");
  await page.goto("/projects/poc-sandbox/databases");
  await expect(page.getByRole("link", { name: /members/i }).first()).toBeVisible();
  await page.goto("/roles");
  await expect(page.getByText("PoC pocdeveloper", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create", exact: true })).toBeEnabled();
  await page.screenshot({ path: fileURLToPath(new URL("../artifacts/owner-roles.png", import.meta.url)), fullPage: true });
});

test("developer sees sandbox and cannot open administration routes", async ({ page }) => {
  await login(page, "dev");
  await page.goto("/projects/poc-sandbox/databases");
  await expect(page.getByText("sandbox_poc", { exact: true }).first()).toBeVisible();
  await expect(page.locator('a[href$="/members"], a[href$="/users"], a[href$="/roles"]')).toHaveCount(0);
  await page.screenshot({ path: fileURLToPath(new URL("../artifacts/dev-sandbox.png", import.meta.url)), fullPage: true });
  for (const [path, permission] of [
    ["/roles", "bb.roles.list"],
    ["/users", "bb.users.list"],
    ["/members", "bb.workspaces.getIamPolicy"],
    ["/projects/poc-sandbox/members", "bb.projects.getIamPolicy"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("alert").filter({ hasText: permission })).toBeVisible();
    await expect(page.getByText("PoC pocdeveloper", { exact: true })).toHaveCount(0);
  }
  await page.goto("/projects/poc-prod/databases");
  await expect(page.getByRole("alert").filter({ hasText: /permission/i })).toBeVisible();
  await expect(page.getByText("prod_poc", { exact: true })).toHaveCount(0);
});

test("leader has no management navigation while retaining issue access", async ({ page }) => {
  await login(page, "leader");
  await page.goto("/projects/poc-prod/issues");
  await expect(page.getByRole("link", { name: /issues/i }).first()).toBeVisible();
  await expect(page.locator('a[href$="/members"], a[href$="/users"], a[href$="/roles"]')).toHaveCount(0);
  const snapshot = await page.request.get(api + "/poc/self-permissions?project=projects/poc-prod");
  expect(snapshot.status()).toBe(200);
  const data = await snapshot.json();
  const permissions = data.roles.flatMap((role) => role.permissions ?? []);
  expect(permissions).toContain("bb.issues.create");
  expect(permissions).not.toContain("bb.sql.ddl");
  expect(permissions).not.toContain("bb.rollouts.create");
});
