import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import Icons from "unplugin-icons/vite";
import IconsResolver from "unplugin-icons/resolver";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import AutoImport from "unplugin-auto-import/vite";

// https://vite.dev/config/
export default defineConfig({
  base: "/web/", // 使用 /web/ 作为基础路径，匹配服务器配置
  plugins: [
    vue(),
    // 自动导入 Element Plus API（ElMessage, ElNotification 等）
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ["vue", "vue-router", "pinia"],
      dts: true, // 生成类型定义文件
      eslintrc: {
        enabled: true, // 生成 ESLint 配置
      },
    }),
    // 自动导入组件
    Components({
      resolvers: [
        ElementPlusResolver({
          importStyle: false, // 禁用按需导入样式，改用全量导入（在 main.ts 中）
        }),
        IconsResolver({
          prefix: "i",
          enabledCollections: ["ion", "mdi"],
        }),
      ],
    }),
    Icons({
      compiler: "vue3",
      autoInstall: true,
    }),
  ],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  optimizeDeps: {
    include: ["element-plus", "element-plus/es"],
    exclude: [],
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    chunkSizeWarningLimit: 1000, // 提高警告阈值到1MB
    // 确保 chunk 加载顺序正确
    commonjsOptions: {
      include: [/node_modules/],
    },
    rollupOptions: {
      // 确保入口点的签名，帮助 Rollup 正确分析依赖关系
      preserveEntrySignatures: "strict",
      output: {
        // 使用 contenthash 而不是 hash，只有内容改变时才会改变文件名
        // 使用更短的哈希（8位）以减少文件名长度，同时保持唯一性
        assetFileNames: assetInfo => {
          const info = assetInfo.name?.split(".") || [];
          const ext = info[info.length - 1];
          // 图片等静态资源使用更稳定的命名
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/.test(assetInfo.name || "")) {
            return `assets/images/[name]-[hash:8].[ext]`;
          }
          // CSS 文件
          if (ext === "css") {
            return `assets/css/[name]-[hash:8].[ext]`;
          }
          // 其他资源
          return `assets/[name]-[hash:8].[ext]`;
        },
        chunkFileNames: "assets/js/[name]-[hash:8].js",
        entryFileNames: "assets/js/[name]-[hash:8].js",
        // 启用代码分割，将第三方库和业务代码分离
        // 这样只有业务代码改变时，vendor 文件不会改变
        manualChunks(id) {
          // 业务代码不分割，保持在一个文件中
          if (!id.includes("node_modules")) {
            return;
          }
          // Vue 核心库必须最先加载（Element Plus 依赖它）
          if (id.includes("vue") || id.includes("vue-router") || id.includes("pinia")) {
            return "vue-vendor";
          }
          // Element Plus 单独分割，但它会依赖 vue-vendor
          // Rollup 会自动处理依赖关系，确保 vue-vendor 先加载
          if (id.includes("element-plus") || id.includes("@element-plus/icons-vue")) {
            return "element-plus";
          }
          // 工具库
          if (
            id.includes("axios") ||
            id.includes("lodash-es") ||
            id.includes("crypto-js") ||
            id.includes("dayjs")
          ) {
            return "utils";
          }
          // Socket.io
          if (id.includes("socket.io-client")) {
            return "socket";
          }
          // Vant UI 库
          if (id.includes("vant")) {
            return "vant";
          }
          // 其他第三方库
          return "vendor";
        },
      },
    },
  },
});
