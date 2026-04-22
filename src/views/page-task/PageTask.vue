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
      <div class="mb-4 flex items-center justify-between">
        <ion-button size="small" fill="clear" @click="decreaseDays">
          <ion-icon :icon="chevronBackOutline" slot="icon-only"></ion-icon>
        </ion-button>
        
        <ion-datetime-button datetime="startDatePicker"></ion-datetime-button>
        
        <ion-button size="small" fill="clear" @click="setToday">今</ion-button>
        
        <ion-button size="small" fill="clear" @click="increaseDays">
          <ion-icon :icon="chevronForwardOutline" slot="icon-only"></ion-icon>
        </ion-button>
      </div>

      <ion-modal :keep-contents-mounted="true">
        <ion-datetime
          id="startDatePicker"
          presentation="date"
          :value="startDate.toISOString()"
          @ionChange="handleDateChange"
        ></ion-datetime>
      </ion-modal>

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
                v-for="material in getTaskMaterials(task)"
                :key="`${task.id}_${material.id}`"
                class="relative flex flex-col items-center justify-center p-4 bg-white rounded-lg shadow aspect-square cursor-pointer"
                @click="openMaterialPlayer(task, material.id)"
              >
                <!-- 任务名称角标 -->
                <div class="absolute top-1 left-1 text-xs text-gray-500 truncate max-w-[80%]">{{ task.name }}</div>
                
                <ion-icon
                  :icon="getMaterialIcon(material.type)"
                  :color="getMaterialColor(material.type)"
                  class="text-3xl mb-2"
                ></ion-icon>
                <div class="text-sm font-medium text-center line-clamp-2 mt-6">{{ material.name }}</div>
                <ion-icon
                  :icon="isMaterialCompleted(task, material, currentDate) ? checkmarkCircle : closeCircle"
                  :color="isMaterialCompleted(task, material, currentDate) ? 'success' : 'danger'"
                  class="text-xl mt-2"
                ></ion-icon>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 素材播放弹窗 -->
      <MaterialPlayerDialog
        v-model:is-open="showPlayerDialog"
        :material="selectedMaterial"
      />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { getTaskList, getMaterial, type Task } from '@/api/api-task';
import { getMediaFileUrl } from '@/utils/file';
import ServerRemoteBadge from '@/components/ServerRemoteBadge.vue';
import MaterialPlayerDialog from './dialogs/MaterialPlayerDialog.vue';
import {
    IonButtons,
    IonDatetime,
    IonDatetimeButton,
    IonHeader,
    IonLabel,
    IonModal,
    IonPage,
    IonRefresher,
    IonRefresherContent,
    IonSegment,
    IonSegmentButton,
    IonSpinner,
    IonToolbar
} from '@ionic/vue';
import {
    checkmarkCircle,
    chevronBackOutline,
    chevronForwardOutline,
    closeCircle,
    documentTextOutline,
    headsetOutline,
    refreshOutline,
    videocamOutline,
} from 'ionicons/icons';
import { computed, inject, onMounted, ref } from 'vue';

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const startDate = ref(new Date());
const currentDate = ref(new Date());
const totalCount = ref(0);
const selectedUserId = ref('0');

// 播放弹窗状态
const showPlayerDialog = ref(false);
const selectedMaterial = ref<any>(null);

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

// 格式化日期
const getTaskMaterials = (task: Task) => {
    try {
        const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;
        const dailyMaterials = taskData.dailyMaterials || {};

        // 获取当前日期的素材
        const taskStartDate = new Date(task.start_date);
        const diffTime = currentDate.value.getTime() - taskStartDate.getTime();
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 0 || diffDays >= task.duration) {
            return [];
        }

        const dayNumber = diffDays + 1;
        return dailyMaterials[dayNumber] || [];
    } catch (error) {
        return [];
    }
};

// 获取素材图标
const getMaterialIcon = (type: number) => {
    switch (type) {
        case 0:
            return documentTextOutline;
        case 1:
            return headsetOutline;
        case 2:
            return videocamOutline;
        default:
            return documentTextOutline;
    }
};

// 获取素材颜色
const getMaterialColor = (type: number) => {
    switch (type) {
        case 0:
            return 'danger';
        case 1:
            return 'primary';
        case 2:
            return 'tertiary';
        default:
            return 'medium';
    }
};

// 检查素材是否完成
const isMaterialCompleted = (task: Task, material: any, date: Date) => {
    try {
        const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;
        const progress = taskData.progress || {};

        const taskStartDate = new Date(task.start_date);
        const diffTime = date.getTime() - taskStartDate.getTime();
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 0 || diffDays >= task.duration) {
            return false;
        }

        const dayNumber = diffDays + 1;
        const materialProgress = progress[material.id];
        return materialProgress && materialProgress[String(dayNumber)] === 1;
    } catch (error) {
        return false;
    }
};

// 打开素材播放器
const openMaterialPlayer = async (task: Task, materialId: number) => {
    try {
        const materialDetail = await getMaterial(materialId);
        const url = getMediaFileUrl(materialDetail.path);
        
        selectedMaterial.value = {
            id: materialDetail.id,
            name: materialDetail.name,
            type: materialDetail.type,
            url: url,
        };
        showPlayerDialog.value = true;
    } catch (error) {
        console.error('Failed to load material:', error);
    }
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

        // 计算今天的日期字符串（YYYY-MM-DD）
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];

        // 查询条件：start_date <= today AND end_date >= today
        const res = await getTaskList(userId, 1, 100, todayStr, todayStr);
        
        if (res.code === 0 && res.data) {
            taskList.value = res.data.data || [];
            totalCount.value = res.data.totalCount || 0;
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

// 日期变化
const handleDateChange = (event: any) => {
    startDate.value = new Date(event.detail.value);
    currentDate.value = new Date(event.detail.value);
    fetchTaskList();
};

// 设置为今天
const setToday = () => {
    startDate.value = new Date();
    currentDate.value = new Date();
    fetchTaskList();
};

// 减少天数
const decreaseDays = () => {
    const newDate = new Date(startDate.value);
    newDate.setDate(newDate.getDate() - 7);
    startDate.value = newDate;
    currentDate.value = newDate;
    fetchTaskList();
};

// 增加天数
const increaseDays = () => {
    const newDate = new Date(startDate.value);
    newDate.setDate(newDate.getDate() + 7);
    startDate.value = newDate;
    currentDate.value = newDate;
    fetchTaskList();
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
