import { shallowRef } from "vue";
import { setupChunkReloadGuard } from "@/utils/chunk-reload";
import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
  type RouteLocationNormalized,
} from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/home",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/views/PageHome.vue"),
  },
  {
    path: "/lottery",
    name: "Lottery",
    component: () => import("@/views/lottery/PageLottery.vue"),
  },
  {
    path: "/schedule",
    name: "Schedule",
    component: () => import("@/views/schedule/PageSchedule.vue"),
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("@/views/my-todo/PageChat.vue"),
  },
  {
    path: "/score",
    name: "Score",
    component: () => import("@/views/score/PageScore.vue"),
  },
  {
    path: "/statistics",
    name: "Statistics",
    component: () => import("@/views/my-todo/PageStats.vue"),
  },
  {
    path: "/timetable",
    name: "Timetable",
    component: () => import("@/views/timetable/PageTimetable.vue"),
  },
  {
    path: "/media",
    name: "Media",
    component: () => import("@/views/media/PageMedia.vue"),
  },
  {
    path: "/tools",
    name: "Tools",
    component: () => import("@/views/tools/PageTools.vue"),
  },
  // 每日打卡
  {
    path: "/tasks",
    name: "Tasks",
    component: () => import("@/views/tasks/PageTasks.vue"),
  },
  {
    path: "/browser",
    name: "Browser",
    component: () => import("@/views/browser/PageBrowser.vue"),
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

// 在异步路由组件加载前反馈导航状态；旧导航结束不能清除新导航的提示。
export const pendingRoute = shallowRef<RouteLocationNormalized | null>(null);
router.beforeEach(to => {
  pendingRoute.value = to;
});
router.afterEach(to => {
  if (pendingRoute.value === to) pendingRoute.value = null;
});
router.onError((_error, to) => {
  if (pendingRoute.value === to) pendingRoute.value = null;
});

setupChunkReloadGuard(router);

export default router;
