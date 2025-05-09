const { createApp, ref } = window.Vue;
document.addEventListener("DOMContentLoaded", async () => {
  const { default: Home } = await import("../view/home.js");
  const { default: Lottery } = await import("../view/lottery.js");
  const { default: Info } = await import("../view/info.js");

  const routes = [
    { path: "/", redirect: "/home" },
    { path: "/home", component: Home },
    { path: "/lottery", component: Lottery },
    { path: "/info", component: Info },
    { path: "/chat", component: Home },
    { path: "/color", component: Home },
  ];
  // 创建路由实例
  const router = window.VueRouter.createRouter({
    history: window.VueRouter.createWebHashHistory(),
    routes,
  });
  const app = createApp({
    setup() {
      const isCollapse = ref(false);

      return {
        isCollapse,
      };
    },
    data() {
      return {
        message: "欢迎使用 Flask and ElementPlus",
      };
    },
    methods: {
      handleClick() {
        this.message = "你点击了按钮！";
        console.log(window.ElementPlusIconsVue);
      },

      handleMenuSelect(obj) {
        console.log("menu select ", obj.index);
      },
    },
  });
  for (const [name, component] of Object.entries(window.ElementPlusIconsVue)) {
    if (name === "Menu") {
      app.component("ElIconMenu", component); // 重命名为 ElMenuIcon
    } else {
      app.component(name, component);
    }
  }
  app.use(router);
  app.use(window.ElementPlus);
  app.mount("#app");
});
