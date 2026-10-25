import { execSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, join } from "path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import legacy from "@vitejs/plugin-legacy";
import Vue from "@vitejs/plugin-vue";
import path from "path";
import IconsResolver from "unplugin-icons/resolver";
import Icons from "unplugin-icons/vite";
import Components from "unplugin-vue-components/vite";
import { defineConfig, type Plugin } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

const __viteConfigDir = dirname(fileURLToPath(import.meta.url));

function resolveAppVersion(): string {
  if (process.env.APP_VERSION) return process.env.APP_VERSION;
  try {
    return execSync("git rev-parse --short HEAD", {
      cwd: __viteConfigDir,
      encoding: "utf-8",
    }).trim();
  } catch {
    return `${process.env.npm_package_version ?? "0.0.1"}-${Date.now()}`;
  }
}

/** dev/build 启动时把 pdfjs-dist 的 wasm 等拷到 public/pdfjs（与 npm 脚本同源） */
function pdfjsCopyAssetsPlugin() {
  return {
    name: "pdfjs-copy-assets",
    buildStart() {
      try {
        execSync("node scripts/copy-pdfjs-assets.mjs", {
          cwd: __viteConfigDir,
          stdio: "inherit",
        });
      } catch {
        console.warn("[vite] pdfjs-copy-assets 失败，请先在该目录执行 npm install");
      }
    },
  };
}

function appVersionJsonPlugin(version: string): Plugin {
  return {
    name: "app-version-json",
    apply: "build",
    closeBundle() {
      const outDir = join(__viteConfigDir, "dist");
      writeFileSync(
        join(outDir, "version.json"),
        JSON.stringify({ version, builtAt: new Date().toISOString() }, null, 2),
        "utf-8",
      );
      console.log(`[build] version.json → ${version}`);
    },
  };
}

const appVersion = resolveAppVersion();

// https://vitejs.dev/config/
export default defineConfig({
  assetsInclude: ["**/*.svg"],
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
        manualChunks(id) {
          if (id.includes("node_modules")) {
            return id.toString().split("node_modules/")[1].split("/")[0].toString();
          }
        },
      },
    },
  },
  plugins: [
    pdfjsCopyAssetsPlugin(),
    Icons({ compiler: "vue3", autoInstall: true }),
    Components({
      resolvers: [
        IconsResolver({
          prefix: "icon", // 自定义前缀，例如 <icon-mdi-account />
        }),
      ],
    }),
    Vue(),
    VitePWA({
      registerType: "prompt",
      injectRegister: "auto",
      workbox: {
        // 入口 HTML 不进 precache，也不接管导航请求：
        // 否则 NavigationRoute 永远用缓存里的旧 index.html 响应，nginx 的 no-store 形同失效，
        // 新构建的 hash 资源永远拉不到，只能手动清缓存。
        // 带 hash 的 js/css 仍走 immutable 长期缓存，刷新即拿最新 HTML + 新 hash 资源。
        globPatterns: ["**/*.{js,css,ico,png,svg,woff2}"],
        navigateFallback: null,
        // 导航请求：先走网络拿最新 HTML（3s 超时才落缓存），断网时仍可用上次的 HTML
        runtimeCaching: [
          {
            urlPattern: ({ request }) => request.mode === "navigate",
            handler: "NetworkFirst",
            options: {
              cacheName: "html-navigation",
              networkTimeoutSeconds: 3,
            },
          },
        ],
      },
      manifest: {
        name: "MyTodo",
        short_name: "MyTodo",
        theme_color: "#2196F3",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
      },
    }),
    appVersionJsonPlugin(appVersion),
    legacy(),
    tailwindcss(),
  ] as any,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "~icons": "virtual:icons",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/unit/**/*.spec.ts", "src/**/*.spec.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      include: ["src/utils/Auth.ts", "src/utils/LocalCache.ts", "src/api/user.ts", "src/api/api-chat.ts", "src/api/api-schedule.ts"],
      exclude: ["src/**/*.spec.ts", "src/**/*.d.ts", "node_modules"],
    },
  },
});
