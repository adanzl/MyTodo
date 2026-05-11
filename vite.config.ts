import { execSync } from "node:child_process";
import { dirname } from "path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import legacy from "@vitejs/plugin-legacy";
import Vue from "@vitejs/plugin-vue";
import path from "path";
import IconsResolver from "unplugin-icons/resolver";
import Icons from "unplugin-icons/vite";
import Components from "unplugin-vue-components/vite";
import { defineConfig } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

const __viteConfigDir = dirname(fileURLToPath(import.meta.url));

/** dev/build 启动时把 pdfjs-dist 的 wasm/cmaps 等拷到 public/pdfjs（与 npm 脚本同源） */
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

// https://vitejs.dev/config/
export default defineConfig({
  assetsInclude: ["**/*.svg"],
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
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
      registerType: "autoUpdate",
      manifest: { theme_color: "#BD34FE" },
    }),
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
