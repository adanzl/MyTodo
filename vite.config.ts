/// <reference types="vitest" />

import legacy from "@vitejs/plugin-legacy";
import vue from "@vitejs/plugin-vue";
import path from "path";
import IconsResolver from "unplugin-icons/resolver";
import Icons from "unplugin-icons/vite";
import Components from "unplugin-vue-components/vite";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

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
    Icons({ compiler: "vue3", autoInstall: true }),
    Components({
      resolvers: [
        IconsResolver({
          prefix: "icon", // 自定义前缀，例如 <icon-mdi-account />
        }),
      ],
    }),
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: { theme_color: "#BD34FE" },
    }),
    legacy(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "~icons": "virtual:icons",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
  },
});
