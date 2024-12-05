import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css";

/* Basic CSS for apps built with Ionic */
import "@ionic/vue/css/normalize.css";
import "@ionic/vue/css/structure.css";
import "@ionic/vue/css/typography.css";

/* Optional CSS utils that can be commented out */
import "@ionic/vue/css/padding.css";
import "@ionic/vue/css/float-elements.css";
import "@ionic/vue/css/text-alignment.css";
import "@ionic/vue/css/text-transformation.css";
import "@ionic/vue/css/flex-utils.css";
import "@ionic/vue/css/display.css";

/**
 * Ionic Dark Mode
 * -----------------------------------------------------
 * For more info, please see:
 * https://ionicframework.com/docs/theming/dark-mode
 */

/* @import '@ionic/vue/css/palettes/dark.always.css'; */
/* @import '@ionic/vue/css/palettes/dark.class.css'; */
import "@ionic/vue/css/palettes/dark.system.css";

/* Theme variables */
import "./theme/variables.css";
import GConfig from "@/components/GConfig.vue";
import {
  IonContent,
  IonicVue,
  IonPage,
  IonLabel,
  IonList,
  IonItem,
  IonToolbar,
  IonTitle,
  IonButton,
  IonIcon,
} from "@ionic/vue";

const app = createApp(App).use(IonicVue).use(router);

app.component("ion-content", IonContent);
app.component("ion-label", IonLabel);
app.component("ion-button", IonButton);
app.component("ion-list", IonList);
app.component("ion-title", IonTitle);
app.component("ion-icon", IonIcon);
app.component("ion-item", IonItem);
app.component("ion-toolbar", IonToolbar);
app.component("ion-page", IonPage);

console.log(`当前 Vue 版本是：${app.version}`);
console.log(GConfig);
// GConfig.init__();
// https://ionicframework.com/docs/vue/pwa
router.isReady().then(() => {
  app.mount("#app");
});
