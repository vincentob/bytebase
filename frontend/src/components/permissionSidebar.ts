import { getRoutePermissions } from "@/app/router/navigation";

export type PermissionSidebarItem = {
  name?: string;
  path?: string;
  hide?: boolean;
  type: string;
  children?: PermissionSidebarItem[];
};

export function filterPermissionSidebar<T extends PermissionSidebarItem>(
  items: T[],
  hasPermission: (permission: string) => boolean
): T[] {
  return items.flatMap((item) => {
    if (item.hide) return [];
    if (item.children?.length) {
      const children = filterPermissionSidebar(item.children, hasPermission);
      return children.length ? [{ ...item, children } as T] : [];
    }
    const name = item.name || item.path;
    if (!name || item.type === "link" || item.type === "divider") return [item];
    const permissions = getRoutePermissions(name);
    return permissions?.every(hasPermission) ? [item] : [];
  });
}
