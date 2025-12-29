import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import Vant from "vant";
import "vant/lib/index.css";
import "@vant/touch-emulator"; // 在桌面浏览器中模拟移动端触摸事件
import "./styles/main.css";

const app = createApp(App);
const pinia = createPinia();

// 注册 Element Plus Icons
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  if (name === "Menu") {
    app.component("ElIconMenu", component);
  } else if (name === "VideoPlay") {
    app.component("ElIconVideoPlay", component);
  } else {
    app.component(name, component);
  }
}

app.use(pinia);
app.use(router);
app.use(ElementPlus);
app.use(Vant);
app.mount("#app");
