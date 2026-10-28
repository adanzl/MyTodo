import { defineStore } from "pinia";
import { computed, ref } from "vue";

/** 主题：亮色 / 暗色（首次跟随系统，用户切换后记住选择） */
export type ThemeName = "light" | "dark";

const THEME_STORAGE_KEY = "mytodo-theme-mode";

/** 系统当前偏好 */
export function systemTheme(): ThemeName {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** 读取用户手动选过的主题；没选过返回 null，表示跟随系统 */
export function readStoredTheme(): ThemeName | null {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // 隐私模式等场景 localStorage 不可用，按跟随系统处理
  }
  return null;
}

/**
 * 把主题落到 <html>：暗色时挂 class="dark"，
 * Element Plus 的暗色变量（theme-chalk/dark/css-vars.css）依赖这个 class。
 */
export function applyTheme(theme: ThemeName) {
  const isDark = theme === "dark";
  const root = document.documentElement;
  root.classList.toggle("dark", isDark);
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

export const useAppStore = defineStore("app", () => {
  const theme = ref<ThemeName>(readStoredTheme() ?? systemTheme());
  const isDark = computed(() => theme.value === "dark");

  const setTheme = (next: ThemeName) => {
    theme.value = next;
    applyTheme(next);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // 存不下就算了，本次会话内仍然生效
    }
  };

  applyTheme(theme.value);

  // 用户还没手动选过主题时跟随系统实时变化；手动切换过就不再跟随
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (readStoredTheme() !== null) {
      return;
    }
    theme.value = systemTheme();
    applyTheme(theme.value);
  });

  return {
    theme,
    isDark,
    setTheme,
  };
});
