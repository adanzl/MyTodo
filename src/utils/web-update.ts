import { alertController } from "@ionic/vue";
import type { Router } from "vue-router";

const VERSION_URL = `${import.meta.env.BASE_URL}version.json`.replace(/\/+/g, "/");
const POLL_MS = 5 * 60 * 1000;
const PROMPT_KEY = "app-update-prompted";
const PENDING_VERSION_KEY = "app-update-pending-version";

let promptOpen = false;
let versionCheckInFlight = false;
let pwaUpdateSW: ((reloadPage?: boolean) => Promise<void> | void) | null = null;
let applyingUpdate = false;

function clearAppliedPendingVersion(): void {
  if (sessionStorage.getItem(PENDING_VERSION_KEY) === __APP_VERSION__) {
    sessionStorage.removeItem(PENDING_VERSION_KEY);
    sessionStorage.removeItem(PROMPT_KEY);
  }
}

function hardReload(targetVersion?: string): void {
  const url = new URL(window.location.href);
  if (targetVersion) {
    url.searchParams.set("_v", targetVersion);
  }
  url.searchParams.set("_ts", String(Date.now()));
  window.location.replace(url.toString());
}

async function applyUpdate(targetVersion?: string): Promise<void> {
  if (applyingUpdate) return;

  applyingUpdate = true;
  try {
    sessionStorage.removeItem(PROMPT_KEY);
    if (targetVersion) {
      sessionStorage.setItem(PENDING_VERSION_KEY, targetVersion);
    }

    if (pwaUpdateSW) {
      await pwaUpdateSW(true);
      return;
    }

    hardReload(targetVersion);
  } finally {
    applyingUpdate = false;
  }
}

async function promptReload(onConfirm: () => void): Promise<void> {
  if (promptOpen) return;
  if (sessionStorage.getItem(PROMPT_KEY) === "1") return;

  promptOpen = true;
  try {
    const alert = await alertController.create({
      header: "发现新版本",
      message: "请点击刷新以使用最新功能。",
      buttons: [
        {
          text: "稍后",
          role: "cancel",
          handler: (): void => {
            sessionStorage.setItem(PROMPT_KEY, "1");
          },
        },
        {
          text: "刷新",
          handler: (): void => {
            onConfirm();
          },
        },
      ],
    });
    await alert.present();
    await alert.onDidDismiss();
  } finally {
    promptOpen = false;
  }
}

function initPwaUpdate(): void {
  if (!import.meta.env.PROD) return;

  import("virtual:pwa-register")
    .then(({ registerSW }) => {
      pwaUpdateSW = registerSW({
        immediate: true,
        onNeedRefresh() {
          void promptReload(() => {
            void applyUpdate();
          });
        },
      });
    })
    .catch(() => {
      // 未生成 SW 时忽略（如 preview 未启用 PWA）
    });
}

async function checkRemoteVersion(): Promise<void> {
  if (!import.meta.env.PROD) return;
  if (promptOpen || sessionStorage.getItem(PROMPT_KEY) === "1") return;
  if (versionCheckInFlight) return;

  versionCheckInFlight = true;
  try {
    const res = await fetch(VERSION_URL, { cache: "no-store" });
    if (!res.ok) return;

    const data = (await res.json()) as { version?: string };
    if (data.version && data.version !== __APP_VERSION__) {
      if (sessionStorage.getItem(PENDING_VERSION_KEY) === data.version) {
        return;
      }
      await promptReload(() => {
        void applyUpdate(data.version);
      });
    }
  } catch {
    // 网络异常时跳过
  } finally {
    versionCheckInFlight = false;
  }
}

function startVersionPolling(): void {
  if (!import.meta.env.PROD) return;

  void checkRemoteVersion();
  window.setInterval((): void => {
    void checkRemoteVersion();
  }, POLL_MS);
  document.addEventListener("visibilitychange", (): void => {
    if (document.visibilityState === "visible") {
      void checkRemoteVersion();
    }
  });
}

const CHUNK_ERROR_RE =
  /Failed to fetch dynamically imported module|Loading chunk|Importing a module script failed/;

export function setupChunkReloadGuard(router: Router): void {
  router.onError((error, to) => {
    const msg = String((error as Error)?.message ?? error);
    if (!CHUNK_ERROR_RE.test(msg)) return;

    const key = `chunk-reload:${to.fullPath}`;
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, "1");
      window.location.assign(to.fullPath);
      return;
    }
    sessionStorage.removeItem(key);
  });
}

/** 生产环境：PWA 更新提示、版本轮询、chunk 加载失败自动恢复 */
export function initWebUpdate(router: Router): void {
  clearAppliedPendingVersion();
  setupChunkReloadGuard(router);
  if (!import.meta.env.PROD) return;
  initPwaUpdate();
  startVersionPolling();
}
