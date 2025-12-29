import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
// Element Plus 全量导入样式（避免开发时频繁刷新）
import "element-plus/dist/index.css";
// Element Plus 组件和 API 通过自动导入插件处理
import Vant from "vant";
import "vant/lib/index.css";
import "@vant/touch-emulator"; // 在桌面浏览器中模拟移动端触摸事件
import "./styles/main.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
// Element Plus 已通过自动导入插件处理，无需手动导入
app.use(Vant);
app.mount("#app");
