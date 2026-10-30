import { fromJson, type JsonValue } from "@bufbuild/protobuf";
import { IamPolicySchema } from "@/types/proto-es/v1/iam_policy_pb";
import { RoleSchema } from "@/types/proto-es/v1/role_service_pb";

export const permissionPoCEnabled = () =>
  import.meta.env.BB_PERMISSION_POC === "1";

export async function fetchSelfPermissionSnapshot(project?: string) {
  const url = new URL("/poc/self-permissions", window.location.origin);
  if (project) url.searchParams.set("project", project);
  const response = await fetch(url, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Unable to load current-user permissions");
  const data = (await response.json()) as {
    roles: JsonValue[];
    workspacePolicy: JsonValue;
    projectPolicies: Record<string, JsonValue>;
  };
  return {
    roles: data.roles.map((role) => fromJson(RoleSchema, role)),
    workspacePolicy: fromJson(IamPolicySchema, data.workspacePolicy),
    projectPolicies: Object.fromEntries(
      Object.entries(data.projectPolicies).map(([name, policy]) => [
        name,
        fromJson(IamPolicySchema, policy),
      ])
    ),
  };
}
