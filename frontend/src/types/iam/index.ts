import type { Permission } from "./permission";
import PERMISSION_DATA from "./permission.yaml";

interface PermissionYamlData {
  permissions: Permission[];
}

export const PERMISSIONS: Permission[] = (
  PERMISSION_DATA as unknown as PermissionYamlData
).permissions;

// BASIC_WORKSPACE_PERMISSIONS is the minimum permissions to initalize the workspace
export const BASIC_WORKSPACE_PERMISSIONS: Permission[] = [
  ...(import.meta.env.BB_PERMISSION_POC === "1"
    ? []
    : (["bb.roles.list", "bb.workspaces.getIamPolicy"] as Permission[])),
  "bb.settings.getWorkspaceProfile",
];

export * from "./permission";

export * from "./role";
