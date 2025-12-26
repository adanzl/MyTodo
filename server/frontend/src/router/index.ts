import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/home",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/views/Home.vue"),
  },
  {
    path: "/lottery",
    name: "Lottery",
    component: () => import("@/views/MyTodo/Lottery.vue"),
  },
  {
    path: "/info",
    name: "Info",
    component: () => import("@/views/MyTodo/Info.vue"),
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("@/views/MyTodo/Chat.vue"),
  },
  {
    path: "/score",
    name: "Score",
    component: () => import("@/views/MyTodo/Score.vue"),
  },
  {
    path: "/timetable",
    name: "Timetable",
    component: () => import("@/views/Timetable.vue"),
  },
  {
    path: "/media",
    name: "Media",
    component: () => import("@/views/Media.vue"),
  },
  {
    path: "/tools",
    name: "Tools",
    component: () => import("@/views/Tools.vue"),
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;


