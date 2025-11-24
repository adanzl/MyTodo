import { getList } from "./net_util.js";
const CryptoJS = window.CryptoJS;
const { createApp, ref, onMounted } = window.Vue;
const { ElMessage } = window.ElementPlus;
const _ = window._;
document.addEventListener("DOMContentLoaded", async () => {
  // 添加时间戳避免缓存
  const timestamp = `?t=${Date.now()}`;
  
  const { default: Info } = await import(`../view/info.js${timestamp}`);

  const routes = [
    { path: "/", redirect: "/home" },
    { path: "/home", component: () => import(`../view/home.js${timestamp}`).then((m) => m.default) },
    { path: "/lottery", component: () => import(`../view/lottery.js${timestamp}`).then((m) => m.default) },
    { path: "/info", component: Info },
    { path: "/chat", component: () => import(`../view/chat.js${timestamp}`).then((m) => m.default) },
    { path: "/color", component: () => import(`../view/home.js${timestamp}`).then((m) => m.default) },
    { path: "/score", component: () => import(`../view/score.js${timestamp}`).then((m) => m.default) },
    { path: "/timetable", component: () => import(`../view/timetable.js${timestamp}`).then((m) => m.default) },
    { path: "/device", component: () => import(`../view/device.js${timestamp}`).then((m) => m.default) },
  ];
  // 创建路由实例
  const router = window.VueRouter.createRouter({
    history: window.VueRouter.createWebHashHistory(),
    routes,
  });
  const app = createApp({
    setup() {
      const KEY_USER_ID = "user_id";
      const isCollapse = ref(false);
      const curUser = ref({ bLogin: false, id: null, name: null, ico: null });
      const userList = ref([]);
      const user = ref({
        id: null,
        password: "",
      });
      const loading = ref(false);
      const refreshUserList = async () => {
        loading.value = true;
        const data = await getList("t_user");
        // console.log("getUserList", data.data);
        Object.assign(userList.value, data.data); // 浅合并
        loading.value = false;
      };
      const doLogin = async () => {
        // console.log("doLogin", user.value);
        if (user.value.id) {
          const uu = _.find(userList.value, { id: user.value.id });
          // console.log("uu", uu);
          if (uu && (uu.pwd === null || uu.pwd === CryptoJS.MD5(user.value.password).toString())) {
            curUser.value.bLogin = true;
            curUser.value.id = uu.id;
            curUser.value.name = uu.name;
            curUser.value.ico = uu.icon;
            window.curUser = curUser.value;
            localStorage.setItem(KEY_USER_ID, uu.id);
          } else {
            ElMessage.error("用户名或密码错误 ");
          }
        }
      };
      const doLogout = () => {
        curUser.value.bLogin = false;
        localStorage.removeItem(KEY_USER_ID);
      };
      onMounted(async () => {
        await refreshUserList();
        const uId = localStorage.getItem(KEY_USER_ID);
        if (uId) {
          curUser.value.bLogin = true;
          const u = _.find(userList.value, (item) => item.id == uId);
          if (u) {
            curUser.value.id = u.id;
            curUser.value.name = u.name;
            curUser.value.ico = u.icon;
            window.curUser = curUser.value;
          }
        }
      });

      return {
        isCollapse,
        curUser,
        userList,
        loading,
        user,
        doLogin,
        doLogout,
      };
    },
    data() {
      return {
        message: "欢迎使用 Flask and ElementPlus",
      };
    },
    methods: {
      handleMenuSelect() {
        // console.log("menu select ", obj.index);
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
  app.use(window.vant);
  app.mount("#app");
});
