<template>
  <ion-page id="main-content" main>
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

    <ion-content class="ion-padding">
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>

      <!-- 用户筛选（仅 admin 可见） -->
      <div v-if="isAdmin" class="mb-4 flex items-center gap-2">
        <ion-segment v-model="selectedUserId" @ionChange="handleUserChange">
          <ion-segment-button value="0">
            <ion-label>全部</ion-label>
          </ion-segment-button>
          <ion-segment-button value="3">
            <ion-label>灿灿</ion-label>
          </ion-segment-button>
          <ion-segment-button value="4">
            <ion-label>昭昭</ion-label>
          </ion-segment-button>
        </ion-segment>
      </div>

      <!-- 日期导航 -->
      <div class="mb-4 flex items-center gap-2">
        <ion-button fill="clear" color="primary" @click="btnCalendarClk">
            <ion-icon slot="start" :icon="calendarOutline"></ion-icon>
            <span class="ml-2">{{ currentDateStr }}</span>
        </ion-button>
        <ion-button size="small" fill="outline" @click="setToday">今</ion-button>
      </div>

      <!-- 任务列表 -->
      <div v-if="loading" class="flex justify-center items-center py-10">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <div v-else>
        <div v-if="displayTasks.length === 0" class="text-center py-10 text-gray-500">
          <p>暂无任务</p>
        </div>

        <div v-else class="space-y-4">
          <!-- 所有素材网格 -->
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            <template v-for="task in displayTasks" :key="task.id">
              <div
                v-for="material in getTaskMaterialList(task)"
                :key="`${task.id}_${material.id}`"
                class="relative flex flex-col items-center justify-center p-4 bg-white rounded-lg shadow aspect-square cursor-pointer"
                @click="openMaterialPlayer(task, material)"
              >
                <!-- 任务名称角标 -->
                <div class="absolute top-2 left-3 text-xs text-gray-500 truncate max-w-[80%] flex gap-2 items-center">
                    <ion-icon
                      :icon="checkmarkCircle"
                      class="text-xl"
                      :class="isMaterialCompleted(task, material, currentDate) ? 'text-green-400' : 'text-gray-300'"
                    ></ion-icon>
                    {{ task.name }}
                </div>
                
                <ion-icon
                  :icon="documentTextOutline"
                  :color="'primary'"
                  class="text-4xl mb-1 mt-6"
                ></ion-icon>
                <div class="text-sm font-medium text-center line-clamp-2 mb-1">{{ material.name }}</div>
                <div class="mb-1 text-xs items-center flex gap-2">
  
                    <div class=" text-gray-600"> 页数:  {{ (material.data && typeof material.data === 'object' ? (material.data as any).pdfLength : '-') }}</div>
                </div>
                <div class=" text-[10px] flex items-center"> 点击阅读</div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 素材播放弹窗 -->
      <MaterialPlayerDialog
        v-model:is-open="showPlayerDialog"
        :material="selectedMaterial"
        :task="selectedTask"
      />

      <!-- 任务日历弹窗 -->
      <TaskCalendar
        v-model:is-open="showCalendarDialog"
        :selected-date="currentDateStr"
        @date-selected="handleDateSelected"
      />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { getTaskList, getMaterialListByIds, type Task, type MaterialItem } from '@/api/api-task';
import { getTodayStr, diffDays } from '@/utils/date-util';
import ServerRemoteBadge from '@/components/ServerRemoteBadge.vue';
import MaterialPlayerDialog from './dialogs/MaterialPlayerDialog.vue';
import TaskCalendar from './dialogs/TaskCalendar.vue';
import {
    IonButtons,
    IonHeader,
    IonLabel,
    IonPage,
    IonRefresher,
    IonRefresherContent,
    IonSegment,
    IonSegmentButton,
    IonSpinner,
    IonToolbar
} from '@ionic/vue';
import {
    calendarOutline,
    checkmarkCircle,
    documentTextOutline,
    refreshOutline,
} from 'ionicons/icons';
import { computed, inject, onMounted, ref } from 'vue';

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const materialMap = ref<Map<number, MaterialItem>>(new Map());
const startDate = ref(new Date());
const currentDate = ref(new Date());
const totalCount = ref(0);
const selectedUserId = ref('0');

// 播放弹窗状态
const showPlayerDialog = ref(false);
const selectedMaterial = ref<any>(null);
const selectedTask = ref<Task | null>(null);

// 日历弹窗状态
const showCalendarDialog = ref(false);

// 当前日期字符串
const currentDateStr = computed(() => {
    return currentDate.value.toISOString().split('T')[0];
});

// 获取全局变量
const globalVar: any = inject('globalVar');

// 是否为 admin
const isAdmin = computed(() => {
    return globalVar?.user?.admin === 1;
});

// 显示的任务列表（直接使用 API 返回的数据）
const displayTasks = computed(() => {
    return taskList.value;
});

// 获取任务当天的素材存档列表（从 task.data 中直接获取）
const getTaskMaterialSaveList = (task: Task): any[] => {
    try {
        const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;
        const dailyMaterials = taskData.dailyMaterials || {};

        // 计算当前日期是任务的第几天（从0开始）
        const diffDaysCount = diffDays(currentDate.value, task.start_date);

        if (diffDaysCount < 0 || diffDaysCount >= task.duration) {
            return [];
        }

        // 直接返回对应天数的素材存档数组（索引从0开始）
        return dailyMaterials[String(diffDaysCount)] || [];
    } catch (error) {
        console.error('解析任务数据失败:', error);
        return [];
    }
};

// 获取任务当天的素材基础信息列表
const getTaskMaterialList = (task: Task): MaterialItem[] => {
    const saves = getTaskMaterialSaveList(task);
    return saves
        .map((save: any) => materialMap.value.get(save.id))
        .filter((m): m is MaterialItem => m !== undefined);
};


// 检查素材是否完成
const isMaterialCompleted = (task: Task, material: any, date: Date) => {
    try {
        const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;

        // 检查 dailyMaterials 中的 status
        if (taskData.dailyMaterials) {
            const diffDaysCount = diffDays(date, task.start_date);
            if (diffDaysCount < 0 || diffDaysCount >= task.duration) {
                return false;
            }

            // 使用从0开始的索引
            const materials = taskData.dailyMaterials[String(diffDaysCount)];
            if (materials) {
                const found = materials.find((m: any) => m.id === material.id);
                return found?.status === 1;
            }
        }

        return false;
    } catch (error) {
        return false;
    }
};

// 打开素材播放器
const openMaterialPlayer = async (task: Task, material: MaterialItem) => {
    selectedMaterial.value = {
        id: material.id,
        name: material.name,
        type: material.type,
        data: material.data,
        path: material.path,
    };
    selectedTask.value = task;
    showPlayerDialog.value = true;
};

// 获取任务列表
const fetchTaskList = async () => {
    loading.value = true;
    try {
        let userId: number | undefined;

        if (isAdmin.value) {
            // Admin 用户：根据选择的筛选条件，0 表示全部
            const selectedId = Number(selectedUserId.value);
            userId = selectedId === 0 ? undefined : selectedId;
        } else {
            // 非 Admin 用户：只能看自己的
            userId = globalVar?.user?.id;
        }

        // 使用当前选中的日期，而不是今天
        const selectedDateStr = currentDate.value.toISOString().split('T')[0];

        // 查询条件：start_date <= selectedDate AND end_date >= selectedDate
        const res = await getTaskList(userId, 1, 100, selectedDateStr, selectedDateStr);

        if (res.code === 0 && res.data) {
            taskList.value = res.data.data || [];
            totalCount.value = res.data.totalCount || 0;

            // 收集所有素材 ID
            const materialIds = new Set<number>();
            taskList.value.forEach(task => {
                const saves = getTaskMaterialSaveList(task);
                saves.forEach((save: any) => {
                    if (save && save.id) {
                        materialIds.add(save.id);
                    }
                });
            });

            // 批量获取素材详情
            if (materialIds.size > 0) {
                const materials = await getMaterialListByIds(Array.from(materialIds));
                materials.forEach(material => {
                    materialMap.value.set(material.id, material);
                });
            }
        }
    } catch (error: any) {
        console.error('获取任务列表失败:', error);
    } finally {
        loading.value = false;
    }
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
const handleRefresh = async (event: any) => {
    await fetchTaskList();
    event.target.complete();
};

// 初始化
onMounted(() => {
    fetchTaskList();
});
</script>

<style scoped>
ion-card {
    --background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
