<template>
  <ion-page id="main-content" main class="main-bg">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-menu-button></ion-menu-button>
        </ion-buttons>
        <ion-title>阅读任务</ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button @click="refreshTasks" :icon="refreshOutline"></ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <!-- 用户筛选（仅 admin 可见） -->
    <div v-if="isAdmin" class="flex items-center gap-2 mx-2">
      <ion-segment v-model="selectedUserId" @ionChange="handleUserChange">
        <ion-segment-button value="3">
          <ion-label>灿灿</ion-label>
        </ion-segment-button>
        <ion-segment-button value="4">
          <ion-label>昭昭</ion-label>
        </ion-segment-button>
      </ion-segment>
    </div>
    <!-- 日期导航 -->
    <div class="m-2 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <ion-button fill="clear" color="primary" @click="btnCalendarClk">
          <ion-icon slot="start" :icon="calendarOutline"></ion-icon>
          <span class="ml-2">{{ currentDateStr }}</span>
        </ion-button>
        <ion-button size="small" fill="outline" @click="setToday">今</ion-button>
      </div>

      <!-- 审批入口（仅 admin 可见） -->
      <ion-button v-if="isAdmin" size="small" fill="clear" @click="showApprovalModal = true" class="relative m-0!">
        <ion-icon :icon="checkmarkCircle" class="w-5 h-5" />
        <ion-badge v-if="unlimitCount > 0" color="danger" class="absolute top-0.5 right-0.5 text-xs px-1 min-w-4">{{
          unlimitCount }}</ion-badge>
      </ion-button>

      <ion-button size="" class="w-10! m-0! [&::part(native)]:p-0" fill="clear" id="more-trigger">
        <ion-icon slot="start" class="w-6 h-6" :icon="alertCircleOutline"></ion-icon>
      </ion-button>



      <!-- 更多选项 Popover -->
      <ion-popover trigger="more-trigger" trigger-action="click" class="[--width:90vw] [--max-width:320px]">
        <TaskProgressPopover :tasks="taskList" :user-id="getCurrentUserId() || 0" />
      </ion-popover>
    </div>
    <ion-content class="[&::part(scroll)]:px-4 [&::part(scroll)]:pb-2">
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>

      <!-- 任务列表 -->
      <div v-if="loading" class="flex justify-center items-center py-10">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <div v-else>
        <div v-if="sortedDisplayTasks.length === 0" class="text-center py-10 text-gray-500">
          <p>暂无任务</p>
        </div>

        <ion-accordion-group v-else class="[--ion-item-background:transparent]" :multiple="false"
          :value="expandedAccordionValue" @ionChange="onAccordionChange">
          <ion-accordion v-for="task in sortedDisplayTasks" :key="task.id" :value="String(task.id)"
            class="mb-2 overflow-hidden rounded-lg">
            <ion-item slot="header" color="light" lines="full">
              <ion-icon v-if="isTaskAllCompleted(task)" :icon="checkmarkCircle" slot="start"
                class="text-xl text-green-400 w-6"></ion-icon>
              <ion-icon v-else-if="task.lock" :icon="lockClosed" slot="start"
                class="text-xl text-gray-500 w-6"></ion-icon>
              <ion-icon v-else :icon="checkmarkCircle" slot="start" class="text-xl text-gray-300 w-6"></ion-icon>
              <div class="flex items-baseline w-full mx-2">
                <span class="text-base font-medium flex-1">{{ task.name }}</span>
                <p class="text-xs text-gray-500">
                  {{ getTaskProgressText(task) }}
                </p>
              </div>
            </ion-item>
            <div slot="content" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 p-2">
              <div v-for="material in getSortedMaterialsForTask(task)" :key="material.id"
                class="relative w-full pb-[100%] cursor-pointer" :class="{ 'opacity-90': task.lock }"
                @click="handleMaterialClick(task, material)">
                <div class="absolute inset-0 flex flex-col p-3 bg-white rounded-lg shadow-md">
                  <div class="absolute top-2 inset-x-3 flex items-center justify-between">
                    <ion-icon :icon="checkmarkCircle" class="text-xl" :class="isMaterialCompleted(task, material)
                        ? 'text-green-400'
                        : 'text-gray-300'
                      "></ion-icon>
                    <span class="text-xs text-gray-500">{{ material.id }}</span>
                  </div>
                  <div class="flex-1 flex flex-col items-center justify-center min-h-0 w-full pt-5">
                    <ion-icon :icon="material.type === 1 ? videocamOutline : documentTextOutline" color="primary"
                      class="text-3xl mb-1 shrink-0"></ion-icon>
                    <div class="w-full px-1 h-10 flex items-center justify-center">
                      <div class="w-full text-sm font-medium text-center leading-5 line-clamp-2 wrap-anywhere">
                        {{ material.name }}
                      </div>
                    </div>
                  </div>
                  <div class="shrink-0 h-5 flex items-center justify-center">
                    <ion-icon v-if="task.lock" :icon="lockClosed" class="text-xl text-gray-500"></ion-icon>
                    <span v-else class="text-xs">点击阅读</span>
                  </div>
                </div>
              </div>
            </div>
          </ion-accordion>
        </ion-accordion-group>
      </div>

      <!-- 素材播放弹窗 -->
      <MaterialPlayerDialog v-model:is-open="showPlayerDialog" :material="selectedMaterial" :task="selectedTask"
        :user-id="getCurrentUserId()" :date="selectedDate" @completed="handleMaterialCompleted" />

      <!-- 任务日历弹窗 -->
      <TaskCalendar v-model:is-open="showCalendarDialog" :selected-date="currentDateStr"
        @date-selected="handleDateSelected" />

      <!-- 不限时审批弹窗 -->
      <UnlimitApprovalModal v-model:is-open="showApprovalModal" @approved="onApprovalDone" />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { getTaskList, type TaskWithMaterials, type MaterialItem, listUnlimitApplications } from "@/api/api-task";
import dayjs from "dayjs";
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import MaterialPlayerDialog from "./dialogs/MaterialPlayerDialog.vue";
import TaskProgressPopover from "./dialogs/TaskProgressPopover.vue";
import TaskCalendar from "./dialogs/TaskCalendar.vue";
import UnlimitApprovalModal from "./dialogs/UnlimitApprovalModal.vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import {
  IonAccordion,
  IonAccordionGroup,
  IonBadge,
  IonButtons,
  IonHeader,
  IonLabel,
  IonPage,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSpinner,
  IonToolbar,
  IonPopover,
  onIonViewDidEnter,
} from "@ionic/vue";
import {
  alertCircleOutline,
  calendarOutline,
  checkmarkCircle,
  documentTextOutline,
  lockClosed,
  refreshOutline,
  videocamOutline,
} from "ionicons/icons";
import { computed, inject, ref, watch } from "vue";

// 状态管理
const loading = ref(false);
const taskList = ref<TaskWithMaterials[]>([]); // 当前选中日期的任务（含当天素材详情）
const startDate = ref(new Date());
const currentDate = ref(new Date());
const totalCount = ref(0);
const selectedUserId = ref("3");

// 播放弹窗状态
const showPlayerDialog = ref(false);
const selectedMaterial = ref<any>(null);
const selectedTask = ref<TaskWithMaterials | null>(null);
const selectedDate = ref<string>(""); // 素材对应的日期

// 日历弹窗状态
const showCalendarDialog = ref(false);

// 审批弹窗状态（仅 admin）
const showApprovalModal = ref(false);
const unlimitCount = ref(0);

// 当前日期字符串（使用 dayjs 避免 UTC 时区偏移）
const currentDateStr = computed(() => {
  return dayjs(currentDate.value).format("YYYY-MM-DD");
});

// 获取全局变量
const globalVar: any = inject("globalVar");

// 是否为 admin
const isAdmin = computed(() => {
  return globalVar?.user?.admin === 1;
});

const expandedAccordionValue = ref<string | undefined>(undefined);

// 任务列表排序（与原先扁平列表规则一致）：
// 1) 每日任务 > 持续任务（type=1 视为持续任务）
// 2) 有未完成素材 > 全部已完成
// 3) 优先级数字小 > 数字大
const sortedDisplayTasks = computed((): TaskWithMaterials[] => {
  return taskList.value
    .filter((task) => getTaskMaterialList(task).length > 0)
    .sort((a, b) => {
      const isContinuousA = a.type === 1;
      const isContinuousB = b.type === 1;
      if (isContinuousA !== isContinuousB) {
        return isContinuousA ? 1 : -1;
      }

      const allDoneA = isTaskAllCompleted(a);
      const allDoneB = isTaskAllCompleted(b);
      if (allDoneA !== allDoneB) {
        return allDoneA ? 1 : -1;
      }

      const priorityA = a.priority ?? Number.MAX_SAFE_INTEGER;
      const priorityB = b.priority ?? Number.MAX_SAFE_INTEGER;
      return priorityA - priorityB;
    });
});

const getSortedMaterialsForTask = (task: TaskWithMaterials): MaterialItem[] => {
  return [...getTaskMaterialList(task)].sort((a, b) => {
    const completedA = isMaterialCompleted(task, a);
    const completedB = isMaterialCompleted(task, b);
    if (completedA !== completedB) {
      return completedA ? 1 : -1;
    }
    return a.name.localeCompare(b.name, "zh-CN");
  });
};

const isTaskAllCompleted = (task: TaskWithMaterials): boolean => {
  const materials = getTaskMaterialList(task);
  if (materials.length === 0) {
    return false;
  }
  return materials.every((material) => isMaterialCompleted(task, material));
};

const getTaskProgressText = (task: TaskWithMaterials): string => {
  const materials = getTaskMaterialList(task);
  const done = materials.filter((m) => isMaterialCompleted(task, m)).length;
  return `${done}/${materials.length}`;
};

const syncExpandedAccordionValue = () => {
  const firstIncomplete = sortedDisplayTasks.value.find((task) => !isTaskAllCompleted(task));
  expandedAccordionValue.value = firstIncomplete ? String(firstIncomplete.id) : undefined;
};

const onAccordionChange = (event: CustomEvent) => {
  expandedAccordionValue.value = event.detail.value || undefined;
};

watch(sortedDisplayTasks, syncExpandedAccordionValue);

// 获取任务当天的素材列表（直接使用后端返回的 today_materials）
const getTaskMaterialList = (task: TaskWithMaterials): MaterialItem[] => {
  return task.today_materials || [];
};

// 检查素材是否完成（从 today_materials 中查找 status）
const isMaterialCompleted = (task: TaskWithMaterials, material: MaterialItem) => {
  const materials = task.today_materials || [];
  const found = materials.find((m) => m.id === material.id);
  const userId = getCurrentUserId();
  if (userId && found?.status) {
    return found.status[String(userId)] === 1;
  }
  return false;
};

// 处理素材点击
const handleMaterialClick = (task: TaskWithMaterials, material: MaterialItem) => {
  // 直接使用后端返回的锁定状态
  if (task.lock) {
    EventBus.$emit(C_EVENT.TOAST, task.msg || "任务已锁定");
    return;
  }
  openMaterialPlayer(task, material);
};

// 获取当前用户ID（与获取任务列表相同的逻辑）
const getCurrentUserId = (): number | undefined => {
  if (isAdmin.value) {
    const selectedId = Number(selectedUserId.value);
    return selectedId === 0 ? undefined : selectedId;
  } else {
    return globalVar?.user?.id;
  }
};

// 处理素材完成事件
const handleMaterialCompleted = () => {
  console.log("素材已完成，刷新列表");
  // 刷新任务列表以更新完成状态
  fetchTaskList();
};

// 拉取不限时审批列表（仅 admin）
const fetchUnlimitList = async () => {
  if (!isAdmin.value) return;
  try {
    const res = await listUnlimitApplications('pending');
    unlimitCount.value = res.total;
  } catch (e) {
    console.error('获取审批列表失败:', e);
  }
};

// 审批完成回调
const onApprovalDone = () => {
  fetchUnlimitList();
};

// 打开素材播放器
const openMaterialPlayer = async (task: TaskWithMaterials, material: MaterialItem) => {
  selectedMaterial.value = {
    id: material.id,
    name: material.name,
    type: material.type,
    data: material.data,
    path: material.path,
  };
  selectedTask.value = task;
  // 计算素材对应的日期（使用 dayjs 避免 UTC 时区偏移）
  selectedDate.value = dayjs(currentDate.value).format("YYYY-MM-DD");
  showPlayerDialog.value = true;
};

// 获取任务列表（下拉刷新时由 ion-refresher 展示进度，不再显示页面 loading）
const fetchTaskList = async (showLoading = true) => {
  if (showLoading) {
    loading.value = true;
  }
  try {
    const userId = getCurrentUserId();

    // 使用当前选中的日期，而不是今天（使用 dayjs 避免 UTC 时区偏移）
    const selectedDateStr = dayjs(currentDate.value).format("YYYY-MM-DD");

    if (!userId) {
      taskList.value = [];
      totalCount.value = 0;
      return;
    }

    // 单次调用获取任务列表 + 当天素材详情
    const res = await getTaskList(userId, 1, 100, selectedDateStr, selectedDateStr);

    if (res.code === 0 && res.data) {
      taskList.value = res.data.data || [];
      totalCount.value = res.data.totalCount || 0;
    }
  } catch (error: any) {
    console.error("获取任务列表失败:", error);
  } finally {
    if (showLoading) {
      loading.value = false;
    }
  }

  // Admin 同时拉取审批列表
  fetchUnlimitList();
};

// 刷新任务
const refreshTasks = () => {
  fetchTaskList();
};

// 用户选择变化（仅 Admin）
const handleUserChange = () => {
  fetchTaskList();
};

// 设置为今天
const setToday = () => {
  startDate.value = new Date();
  currentDate.value = new Date();
  fetchTaskList();
};

// 处理日期选择
const handleDateSelected = (dateStr: string) => {
  currentDate.value = new Date(dateStr);
  fetchTaskList();
};

const btnCalendarClk = () => {
  showCalendarDialog.value = true;
};

// 下拉刷新
const handleRefresh = async (event: CustomEvent) => {
  await fetchTaskList(false);
  (event.target as HTMLIonRefresherElement).complete();
};

// 页签激活时自动刷新（与 PageSchedule 一致）
onIonViewDidEnter(() => {
  fetchTaskList();
});
</script>
