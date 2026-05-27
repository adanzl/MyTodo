<template>
    <div class="p-4">
        <div class="flex gap-5 h-10">
            <el-button size="small" @click="fetchTaskList" :loading="loading" :icon="Refresh" type="primary" plain />
            <!-- 用户筛选 -->
            <div class="mb-4 flex items-center gap-2">
                <el-radio-group v-model="selectedUserId" @change="handleUserChange">
                    <el-radio :value="3">灿灿</el-radio>
                    <el-radio :value="4">昭昭</el-radio>
                </el-radio-group>
            </div>

            <!-- 日期导航 -->
            <div class="mb-4 flex items-center gap-2">
                <el-button type="primary" plain @click="btnCalendarClk">
                    <el-icon>
                        <Calendar />
                    </el-icon>
                    <span class="ml-2">{{ currentDateStr }}</span>
                </el-button>
                <el-button size="small" @click="setToday">今</el-button>
                <span class="items-baseline text-xs text-gray-500">注：此页面的锁定图标只是标识锁定状态，不是真的锁定</span>
            </div>
        </div>

        <!-- 任务列表 -->
        <div v-if="loading" class="flex justify-center items-center py-10">
            <el-icon class="is-loading" :size="40" color="#409eff">
                <Loading />
            </el-icon>
        </div>
        <div v-else class=" h-[calc(100vh-15rem)] overflow-y-auto p-4 border border-gray-300">
            <div v-if="!hasDisplayableMaterials" class="text-center py-10 text-gray-500">
                <p>暂无任务</p>
            </div>

            <div v-else class="space-y-4">
                <!-- 所有素材网格 -->
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                    <div v-for="item in displayMaterials" :key="`${item.task.id}_${item.material.id}`"
                            class="relative flex flex-col items-center justify-center p-4 bg-white rounded-lg shadow-md cursor-pointer hover:shadow-2xl transition-shadow"
                            @click="openMaterialPlayer(item.task, item.material)">
                            <!-- 任务名称角标 -->
                            <div
                                class="absolute top-2 left-3 text-xs text-gray-500 max-w-[90%] flex gap-2 items-center min-w-0 w-full">
                                <el-tag :type="item.completed ? 'success' : 'info'"
                                    :effect="item.completed ? 'dark' : 'plain'"
                                    size="small" class="shrink-0">
                                    {{ item.completed ? '已完成' : '未完成' }}
                                </el-tag>
                                <span class="truncate flex-1 min-w-0">{{ item.task.name }}</span>
                                <span class="shrink-0">{{ item.task.priority }}</span>
                            </div>

                            <el-icon :size="40" color="#409EFF" class="mb-1 mt-6">
                                <Document v-if="item.material.type == 0"/>
                                <VideoPlay v-else-if="item.material.type == 1"/>
                            </el-icon>
                            <el-tooltip :content="`[${item.material.id}]${item.material.name}`" placement="top"
                                :show-after="400" popper-class="max-w-xs wrap-break-word">
                                <div
                                    class="w-full min-w-0 mb-1 px-1 text-sm font-medium text-center text-gray-900 line-clamp-2 wrap-break-word">
                                    {{ item.material.name }}
                                </div>
                            </el-tooltip>
                            <div v-if="item.task.lock" class="mt-2">
                                <el-icon :size="24" class="text-gray-500">
                                    <Lock />
                                </el-icon>
                            </div>
                            <div v-else class="text-[10px] flex items-center mt-2">点击阅读</div>
                        </div>
                </div>
            </div>
        </div>

        <!-- 素材播放弹窗 -->
        <MaterialPreviewDialog v-model="showPlayerDialog" :material-id="selectedMaterial?.id || null" />

        <!-- 任务日历弹窗 -->
        <TaskCalendar v-model="showCalendarDialog" :selected-date="currentDateStr" :user-id="Number(selectedUserId)"
            @date-selected="handleDateSelected" />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Calendar, Document, Loading, VideoPlay, Refresh, Lock } from '@element-plus/icons-vue';
import { getTaskList, getMaterialListByIds, type Task, type MaterialItem } from '@/api/api-task';
import { getDaysDiff } from '@/utils/date';
import MaterialPreviewDialog from './dialogs/MaterialPreviewDialog.vue';
import TaskCalendar from './dialogs/TaskCalendar.vue';

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const materialMap = ref<Map<number, MaterialItem>>(new Map());
const startDate = ref(new Date());
const currentDate = ref(new Date());
const totalCount = ref(0);
const selectedUserId = ref(3);

// 播放弹窗状态
const showPlayerDialog = ref(false);
const selectedMaterial = ref<MaterialItem | null>(null);
const selectedTask = ref<Task | null>(null);

// 日历弹窗状态
const showCalendarDialog = ref(false);

// 当前日期字符串
const currentDateStr = computed(() => {
  return currentDate.value.toISOString().split('T')[0];
});

// 检查是否有可显示的素材
const hasDisplayableMaterials = computed(() => displayMaterials.value.length > 0);

// 获取任务当天的素材存档列表（从 task.data 中直接获取）
const getTaskMaterialSaveList = (task: Task): any[] => {
  try {
    const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;
    const dailyMaterials = taskData.dailyMaterials || {};

    // 计算当前日期是任务的第几天
    const diffDaysCount = getDaysDiff(task.start_date, currentDate.value);

    if (diffDaysCount < 0 || diffDaysCount >= task.duration) {
      return [];
    }

    // type=1（持续任务）：只看第0天的素材
    const materialsIndex = task.type === 1 ? 0 : diffDaysCount;
    // 直接返回对应天数的素材存档数组
    return dailyMaterials[materialsIndex] || [];
  } catch (error) {
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
const isMaterialCompleted = (task: Task, material: MaterialItem, date: Date) => {
  try {
    const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;

    // 检查 dailyMaterials 中的 status
    if (taskData.dailyMaterials) {
      const diffDaysCount = getDaysDiff(task.start_date, date);
      if (diffDaysCount < 0 || diffDaysCount >= task.duration) {
        return false;
      }

      // type=1（持续任务）：只看第0天的素材
      const materialsIndex = task.type === 1 ? 0 : diffDaysCount;
      const dayKey = String(materialsIndex);
      const materials = taskData.dailyMaterials[dayKey];
      if (materials) {
        const found = materials.find((m: any) => m.id === material.id);
        if (!found || !found.status) return false;

        // status 现在是 Record<user_id, status>
        const selectedId = Number(selectedUserId.value);
        if (selectedId === 0) {
          // 全部用户：检查是否有任意用户完成
          return Object.values(found.status).some((s: any) => s === 1);
        } else {
          // 特定用户：检查该用户的状态
          return found.status[String(selectedId)] === 1;
        }
      }
    }

    return false;
  } catch (error) {
    return false;
  }
};

// 显示的素材列表（未完成优先，其次按任务优先级排序）
const displayMaterials = computed(() => {
  const items = taskList.value.flatMap(task =>
    getTaskMaterialList(task).map(material => ({
      task,
      material,
      completed: isMaterialCompleted(task, material, currentDate.value),
      priority: task.priority || 999,
    }))
  );
  return items.sort((a, b) => {
    if (a.completed !== b.completed) {
      return a.completed ? 1 : -1;
    }
    return a.priority - b.priority;
  });
});

// 打开素材播放器
const openMaterialPlayer = async (task: Task, material: MaterialItem) => {
  selectedMaterial.value = material;
  selectedTask.value = task;

  // 将素材数据存储到 sessionStorage 供预览组件使用
  sessionStorage.setItem('previewMaterial', JSON.stringify(material));

  showPlayerDialog.value = true;
};

// 获取任务列表
const fetchTaskList = async () => {
  loading.value = true;
  try {
    let userId: number | undefined;

    // 根据选择的筛选条件，0 表示全部
    const selectedId = Number(selectedUserId.value);
    userId = selectedId === 0 ? undefined : selectedId;

    // 使用当前选中的日期进行范围查询
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
          materialMap.value.set(material.id!, material);
        });
      }
    }
  } catch (error: any) {
    console.error('获取任务列表失败:', error);
    ElMessage.error(error.message || '获取任务列表失败');
  } finally {
    loading.value = false;
  }
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

// 初始化
onMounted(() => {
  fetchTaskList();

  // 监听刷新事件
  const handleRefresh = () => {
    fetchTaskList();
  };
  window.addEventListener('refresh-preview-tab', handleRefresh);

  // 组件卸载时移除监听器
  onUnmounted(() => {
    window.removeEventListener('refresh-preview-tab', handleRefresh);
  });
});
</script>

<style scoped>
/* 全部使用 Tailwind CSS，无需额外自定义样式 */
</style>
