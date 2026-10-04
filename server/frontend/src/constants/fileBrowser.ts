/**
 * 文件选择器可浏览的根目录。
 * 在 /mnt 下只展示这些目录，不能继续向上或进入其它挂载。
 */
export const FILE_BROWSER_ROOTS = ["/mnt/ext_base", "/mnt/ext_chen"] as const;

export const FILE_BROWSER_DEFAULT_PATH = FILE_BROWSER_ROOTS[0];

export const FILE_BROWSER_HUB_PATH = "/mnt";

function normalizePath(path: string): string {
  const trimmed = String(path || "").trim();
  if (!trimmed || trimmed === "/") {
    return "/";
  }
  return trimmed.replace(/\/+$/, "") || "/";
}

export function isAllowedBrowserPath(path: string): boolean {
  const n = normalizePath(path);
  if (n === FILE_BROWSER_HUB_PATH) {
    return true;
  }
  return FILE_BROWSER_ROOTS.some(root => isPathInRoot(n, root));
}

export function clampBrowserPath(path: string, fallback = FILE_BROWSER_DEFAULT_PATH): string {
  const n = normalizePath(path);
  return isAllowedBrowserPath(n) ? n : fallback;
}

export function joinBrowserPath(base: string, name: string): string {
  const n = normalizePath(base);
  const segment = String(name || "").replace(/^\/+|\/+$/g, "");
  if (!segment) {
    return n;
  }
  return n === "/" ? `/${segment}` : `${n}/${segment}`;
}

export function isPathInRoot(path: string, root: string): boolean {
  const n = normalizePath(path);
  const r = normalizePath(root);
  return n === r || n.startsWith(`${r}/`);
}

export function canNavigateBrowserUp(path: string): boolean {
  const n = normalizePath(path);
  return !!n && n !== FILE_BROWSER_HUB_PATH && n !== "/";
}

export function parentBrowserPath(path: string): string {
  const n = normalizePath(path);
  if (!canNavigateBrowserUp(n)) {
    return FILE_BROWSER_HUB_PATH;
  }
  const parts = n.split("/").filter(Boolean);
  parts.pop();
  return parts.length > 0 ? `/${parts.join("/")}` : FILE_BROWSER_HUB_PATH;
}

export function filterBrowserList<T extends { name: string; isDirectory?: boolean }>(
  path: string,
  items: T[]
): T[] {
  if (normalizePath(path) !== FILE_BROWSER_HUB_PATH) {
    return items;
  }
  const allowedNames = new Set(FILE_BROWSER_ROOTS.map(root => root.split("/").pop() || ""));
  return items.filter(item => item.isDirectory && allowedNames.has(item.name));
}
