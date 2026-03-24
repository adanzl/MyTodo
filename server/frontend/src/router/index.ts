import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/home",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/views/home.vue"),
  },
  {
    path: "/lottery",
    name: "Lottery",
    component: () => import("@/views/lottery/index.vue"),
  },
  {
    path: "/info",
    name: "Info",
    component: () => import("@/views/my-todo/info.vue"),
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("@/views/my-todo/chat.vue"),
  },
  {
    path: "/score",
    name: "Score",
    component: () => import("@/views/my-todo/score.vue"),
  },
  {
    path: "/timetable",
    name: "Timetable",
    component: () => import("@/views/timetable.vue"),
  },
  {
    path: "/media",
    name: "Media",
    component: () => import("@/views/media/index.vue"),
  },
  {
    path: "/tools",
    name: "Tools",
    component: () => import("@/views/tools/index.vue"),
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
