import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

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
    path: "/info",
    name: "Info",
    component: () => import("@/views/my-todo/PageInfo.vue"),
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("@/views/my-todo/PageChat.vue"),
  },
  {
    path: "/score",
    name: "Score",
    component: () => import("@/views/my-todo/PageScore.vue"),
  },
  {
    path: "/statistics",
    name: "Statistics",
    component: () => import("@/views/my-todo/PageStats.vue"),
  },
  {
    path: "/timetable",
    name: "Timetable",
    component: () => import("@/views/PageTimetable.vue"),
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
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
