<template>
  <div class="text-lg font-semibold m-3">
      任务进度
  </div>
  <ion-content class="ion-padding">
    <div v-if="taskProgressList.length === 0" class="text-center py-10 text-gray-500">
      <p>今天暂无任务</p>
    </div>
    
    <div v-else class="flex flex-col gap-3">
      <div 
        v-for="task in taskProgressList" 
        :key="task.taskId"
        class="bg-white rounded-lg p-4 shadow"
      >
        <div class="flex justify-between items-end">
          <p class="font-semibold text-gray-800 text-xl">{{ task.taskName }}</p>
          <span class="text-sm text-gray-600">
            {{ task.completedMaterials }}/{{ task.totalMaterials }}
          </span>
        </div>
        
        <!-- 进度条 -->
        <div class="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            :style="{ width: `${task.progressPercent}%` }"
          ></div>
        </div>
        
        <!-- 今日可获得星星数 -->
        <div class="mt-2 text-sm text-gray-600">
          今日可获得: <span class="font-semibold text-red-500">{{ task.todayScore }}</span> 星
        </div>
      </div>
    </div>
  </ion-content>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { IonContent } from '@ionic/vue';
import type { TaskWithMaterials } from '@/api/api-task';

const props = defineProps<{
  tasks: TaskWithMaterials[];
  userId: number;
}>();

interface TaskProgress {
  taskId: number;
  taskName: string;
  completedMaterials: number;
  totalMaterials: number;
  progressPercent: number;
  todayScore: number;
}

// 计算任务进度（直接使用 today_materials）
const calculateTaskProgress = (task: TaskWithMaterials, userId: number): TaskProgress => {
  try {
    const materials = task.today_materials || [];
    
    // 统计已完成的素材数
    const completedMaterials = materials.filter((m) => {
      return m.status && m.status[String(userId)] === 1;
    }).length;
    
    const totalMaterials = materials.length;
    const progressPercent = totalMaterials > 0 ? (completedMaterials / totalMaterials) * 100 : 0;
    
    // todayScore 待后端扩展后支持
    const todayScore = 0;
    
    return {
      taskId: task.id!,
      taskName: task.name,
      completedMaterials,
      totalMaterials,
      progressPercent,
      todayScore,
    };
  } catch (error) {
    console.error('计算任务进度失败:', error);
    return {
      taskId: task.id!,
      taskName: task.name,
      completedMaterials: 0,
      totalMaterials: 0,
      progressPercent: 0,
      todayScore: 0,
    };
  }
};

// 计算任务进度列表
const taskProgressList = computed(() => {
  return props.tasks.map(task => calculateTaskProgress(task, props.userId));
});
</script>
