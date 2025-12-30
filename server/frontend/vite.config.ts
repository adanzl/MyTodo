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
      output: {
        // 确保资源路径正确
        assetFileNames: "assets/[name].[hash].[ext]",
        chunkFileNames: "assets/[name].[hash].js",
        entryFileNames: "assets/[name].[hash].js",
        // 暂时禁用手动代码分割，让 Vite 自动处理以避免模块加载顺序问题
        // 如果打包体积过大，可以后续再优化
        // manualChunks(id) {
        //   if (!id.includes("node_modules")) {
        //     return;
        //   }
        //   if (id.includes("vue") || id.includes("vue-router") || id.includes("pinia")) {
        //     return "vue-vendor";
        //   }
        //   if (id.includes("element-plus") && !id.includes("@element-plus/icons-vue")) {
        //     return "element-plus";
        //   }
        //   if (id.includes("@element-plus/icons-vue")) {
        //     return "element-plus-icons";
        //   }
        //   if (
        //     id.includes("axios") ||
        //     id.includes("lodash-es") ||
        //     id.includes("crypto-js") ||
        //     id.includes("dayjs")
        //   ) {
        //     return "utils";
        //   }
        //   if (id.includes("socket.io-client")) {
        //     return "socket";
        //   }
        //   if (id.includes("vant")) {
        //     return "vant";
        //   }
        //   return "vendor";
        // },
      },
    },
  },
});
