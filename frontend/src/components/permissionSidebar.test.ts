import { describe, expect, test } from "vitest";
import { setRoutePermissionIndex } from "@/app/router/navigation";
import { filterPermissionSidebar } from "./permissionSidebar";

describe("filterPermissionSidebar", () => {
  test("removes inaccessible pages and empty groups", () => {
    setRoutePermissionIndex(
      new Map([
        ["projects", () => []],
        ["members", () => ["bb.users.list"]],
        ["roles", () => ["bb.roles.list"]],
      ])
    );
    const items = [
      { name: "projects", type: "route" },
      {
        type: "div",
        children: [
          { name: "members", type: "route" },
          { name: "roles", type: "route" },
        ],
      },
    ];
    expect(filterPermissionSidebar(items, () => false)).toEqual([items[0]]);
    expect(filterPermissionSidebar(items, () => true)).toEqual(items);
  });

  test("requires every route permission and denies unregistered routes", () => {
    setRoutePermissionIndex(
      new Map([
        ["members", () => ["bb.projects.get", "bb.projects.getIamPolicy"]],
      ])
    );
    expect(
      filterPermissionSidebar(
        [
          { path: "members", type: "div" },
          { path: "unknown", type: "div" },
        ],
        (permission) => permission === "bb.projects.get"
      )
    ).toEqual([]);
  });
});
