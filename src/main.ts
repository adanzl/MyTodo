import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import EventBus from "@/types/EventBus";

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css";

/* Basic CSS for apps built with Ionic */
import "@ionic/vue/css/normalize.css";
import "@ionic/vue/css/structure.css";
import "@ionic/vue/css/typography.css";

/* Optional CSS utils that can be commented out */
import "@ionic/vue/css/display.css";
import "@ionic/vue/css/flex-utils.css";
import "@ionic/vue/css/float-elements.css";
import "@ionic/vue/css/padding.css";
import "@ionic/vue/css/text-alignment.css";
import "@ionic/vue/css/text-transformation.css";

import { defineCustomElements } from "@ionic/pwa-elements/loader";

defineCustomElements(window);

/**
 * Ionic Dark Mode
 * -----------------------------------------------------
 * For more info, please see:
 * https://ionicframework.com/docs/theming/dark-mode
 */

/* @import '@ionic/vue/css/palettes/dark.always.css'; */
/* @import '@ionic/vue/css/palettes/dark.class.css'; */
// import "@ionic/vue/css/palettes/dark.system.css";

/* Theme variables */
import "./theme/variables.css";
// import GConfig from "@/components/GConfig.vue";
import { Icon } from "@iconify/vue";
import {
  IonAlert,
  IonBackdrop,
  IonButton,
  IonButtons,
  IonChip,
  IonContent,
  IonDatetime,
  IonFooter,
  IonHeader,
  IonIcon,
  IonicVue,
  IonInput,
  IonItem,
  IonLabel,
  IonList,
  IonLoading,
  IonModal,
  IonPage,
  IonTitle,
  IonToast,
  IonToggle,
  IonToolbar,
} from "@ionic/vue";

import { initNet, checkAndSwitchServer, isLocalIpAvailable } from "@/utils/NetUtil";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import isToday from "dayjs/plugin/isToday";
import localizedFormat from "dayjs/plugin/localizedFormat";
dayjs.extend(localizedFormat);
dayjs.extend(isToday);
dayjs.locale("zh-cn", {
  weekStart: 0, // 1 表示星期一，0 表示星期日
});
export const GlobalVar: any = {};
const app = createApp(App).use(IonicVue).use(router);
app.provide("eventBus", EventBus);
app.provide("globalVar", GlobalVar);

app.component("ion-content", IonContent);
app.component("ion-footer", IonFooter);
app.component("ion-label", IonLabel);
app.component("ion-button", IonButton);
app.component("ion-list", IonList);
app.component("ion-title", IonTitle);
app.component("ion-icon", IonIcon);
app.component("ion-item", IonItem);
app.component("ion-toolbar", IonToolbar);
app.component("ion-page", IonPage);
app.component("ion-datetime", IonDatetime);
app.component("ion-buttons", IonButtons);
app.component("ion-header", IonHeader);
app.component("ion-chip", IonChip);
app.component("ion-input", IonInput);
app.component("ion-toast", IonToast);
app.component("ion-alert", IonAlert);
app.component("ion-backdrop", IonBackdrop);
app.component("ion-toggle", IonToggle);
app.component("ion-modal", IonModal);
// eslint-disable-next-line vue/multi-word-component-names
app.component("Icon", Icon);
app.component("iconify-icon", Icon);
app.component("ion-loading", IonLoading);

console.log(`当前 Vue 版本是：${app.version}`);

// console.log(GConfig);
// GConfig.init__();
// https://ionicframework.com/docs/vue/pwa
// npm cache verify

router.isReady().then(async () => {
  initNet();
  // 定时检测本地/远程地址：本地可用时每 5 秒检查，本地不可用时每 60 秒检查（减少 console 的 ERR_CONNECTION_TIMED_OUT 输出）
  const CHECK_WHEN_LOCAL_MS = 5000;
  const CHECK_WHEN_REMOTE_MS = 60000;

  function scheduleNextCheck() {
    const interval =
      isLocalIpAvailable() === false ? CHECK_WHEN_REMOTE_MS : CHECK_WHEN_LOCAL_MS;
    setTimeout(() => {
      checkAndSwitchServer();
      scheduleNextCheck();
    }, interval);
  }
  scheduleNextCheck();
  app.mount("#app");
});
// ignore
console.log(import.meta.env, navigator.userAgent);
if (!import.meta.env.PROD) {
  // import VConsole from "vconsole";
  // new VConsole();
}
