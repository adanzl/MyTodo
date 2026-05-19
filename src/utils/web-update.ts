import { alertController } from "@ionic/vue";
import type { Router } from "vue-router";

const VERSION_URL = `${import.meta.env.BASE_URL}version.json`.replace(/\/+/g, "/");
const POLL_MS = 5 * 60 * 1000;
const PROMPT_KEY = "app-update-prompted";

let promptOpen = false;

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
  } finally {
    promptOpen = false;
  }
}

function initPwaUpdate(): void {
  if (!import.meta.env.PROD) return;

  import("virtual:pwa-register")
    .then(({ registerSW }) => {
      const updateSW = registerSW({
        immediate: true,
        onNeedRefresh() {
          void promptReload(() => {
            sessionStorage.removeItem(PROMPT_KEY);
            void updateSW(true);
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

  try {
    const res = await fetch(VERSION_URL, { cache: "no-store" });
    if (!res.ok) return;

    const data = (await res.json()) as { version?: string };
    if (data.version && data.version !== __APP_VERSION__) {
      await promptReload(() => {
        sessionStorage.removeItem(PROMPT_KEY);
        window.location.reload();
      });
    }
  } catch {
    // 网络异常时跳过
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
  setupChunkReloadGuard(router);
  if (!import.meta.env.PROD) return;
  initPwaUpdate();
  startVersionPolling();
}
