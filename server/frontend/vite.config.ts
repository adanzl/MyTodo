import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import Icons from "unplugin-icons/vite";
import IconsResolver from "unplugin-icons/resolver";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import AutoImport from "unplugin-auto-import/vite";

// https://vite.dev/config/
// 生产用 base: "/"，构建输出 /assets/...，由 deploy.js 统一改为 /web/assets/（Vite 用 /web/ 或 /web 都会拼成 /webassets/）
export default defineConfig({
  base: "/web/",
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
    host: "localhost", // 仅允许本地访问
    port: 5174, // 指定端口；也可用 npm run dev -- --port 端口号 临时覆盖
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
      // 使用 false 减少入口点签名导致的 chunk 边界变化，提高文件名稳定性
      preserveEntrySignatures: false,
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
        manualChunks(id) {
          // 第三方库分割 - 使用更严格的匹配，确保只匹配 node_modules
          if (id.includes("node_modules")) {
            // Vue 核心库必须最先加载（Element Plus 依赖它）
            // 使用更精确的匹配，避免误匹配业务代码
            if (
              id.includes("node_modules/vue/") ||
              id.includes("node_modules/vue-router/") ||
              id.includes("node_modules/pinia/") ||
              id.includes("node_modules/@vue/")
            ) {
              return "vue-vendor";
            }
            // Element Plus 单独分割
            if (
              id.includes("node_modules/element-plus/") ||
              id.includes("node_modules/@element-plus/")
            ) {
              return "element-plus";
            }
            // 工具库
            if (
              id.includes("node_modules/axios/") ||
              id.includes("node_modules/lodash-es/") ||
              id.includes("node_modules/crypto-js/") ||
              id.includes("node_modules/dayjs/")
            ) {
              return "utils";
            }
            // Socket.io
            if (id.includes("node_modules/socket.io-client/")) {
              return "socket";
            }
            // Vant UI 库
            if (id.includes("node_modules/vant/")) {
              return "vant";
            }
            // 其他第三方库
            return "vendor";
          }

          // 将 API + types + utils 打成一个 shared 包，避免 api-shared <-> types-shared <-> utils-shared 循环依赖
          if (
            (id.includes("/api/") ||
              id.includes("/types/") ||
              id.includes("/utils/") ||
              id.includes("/constants/")) &&
            !id.includes("/views/") &&
            !id.includes("node_modules")
          ) {
            return "shared";
          }

          // 业务代码让 Vite 自动处理（按路由分割）
        },
      },
    },
  },
});
