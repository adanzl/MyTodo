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
  // PDF阅读打卡系统 - 前台用户端
  {
    path: "/daily-tasks",
    name: "DailyTasks",
    component: () => import("@/views/pdf-checkin/PageDailyTasks.vue"),
  },
  {
    path: "/pdf-reader",
    name: "PDFReader",
    component: () => import("@/views/pdf-checkin/PagePDFReader.vue"),
  },
  {
    path: "/checkin-success",
    name: "CheckinSuccess",
    component: () => import("@/views/pdf-checkin/PageCheckinSuccess.vue"),
  },
  // PDF阅读打卡系统 - 后台管理端
  {
    path: "/admin/material-library",
    name: "MaterialLibrary",
    component: () => import("@/views/pdf-checkin/admin/PageMaterialLibrary.vue"),
  },
  {
    path: "/admin/textbook-select",
    name: "TextbookSelect",
    component: () => import("@/views/pdf-checkin/admin/PageTextbookSelect.vue"),
  },
  {
    path: "/admin/lesson-select",
    name: "LessonSelect",
    component: () => import("@/views/pdf-checkin/admin/PageLessonSelect.vue"),
  },
  {
    path: "/admin/courseware-generate",
    name: "CoursewareGenerate",
    component: () => import("@/views/pdf-checkin/admin/PageCoursewareGenerate.vue"),
  },
  {
    path: "/admin/audio-edit",
    name: "AudioEdit",
    component: () => import("@/views/pdf-checkin/admin/PageAudioEdit.vue"),
  },
  {
    path: "/admin/task-settings",
    name: "TaskSettings",
    component: () => import("@/views/pdf-checkin/admin/PageTaskSettings.vue"),
  },
  {
    path: "/admin/task-status",
    name: "TaskStatus",
    component: () => import("@/views/pdf-checkin/admin/PageTaskStatus.vue"),
  },
  {
    path: "/admin/task-content-config",
    name: "TaskContentConfig",
    component: () => import("@/views/pdf-checkin/admin/PageTaskContentConfig.vue"),
  },
  {
    path: "/admin/resource-library",
    name: "ResourceLibrary",
    component: () => import("@/views/pdf-checkin/admin/PageResourceLibrary.vue"),
  },
  {
    path: "/admin/folder-detail",
    name: "FolderDetail",
    component: () => import("@/views/pdf-checkin/admin/PageFolderDetail.vue"),
  },
  {
    path: "/admin/video-upload",
    name: "VideoUpload",
    component: () => import("@/views/pdf-checkin/admin/PageVideoUpload.vue"),
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
