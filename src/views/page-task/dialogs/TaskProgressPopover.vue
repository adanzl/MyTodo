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
        <div class="flex justify-between items-endy">
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
import type { Task } from '@/api/api-task';

const props = defineProps<{
  tasks: Task[];
  userId: number;
  date?: string; // 选中的日期，默认为今天
}>();

interface TaskProgress {
  taskId: number;
  taskName: string;
  completedMaterials: number;
  totalMaterials: number;
  progressPercent: number;
  todayScore: number;
}

// 计算任务进度
const calculateTaskProgress = (task: Task, userId: number, targetDate: Date): TaskProgress => {
  try {
    const taskData = typeof task.data === 'string' ? JSON.parse(task.data) : task.data;
    const dailyMaterials = taskData.dailyMaterials || {};
    const dailyScore = taskData.dailyScore || {};
    
    // 计算目标日期是任务的第几天
    const start = new Date(task.start_date);
    const diffDaysCount = Math.floor((targetDate.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDaysCount < 0 || diffDaysCount >= task.duration) {
      return {
        taskId: task.id!,
        taskName: task.name,
        completedMaterials: 0,
        totalMaterials: 0,
        progressPercent: 0,
        todayScore: 0,
      };
    }
    
    // type=1（持续任务）：始终检查第0天
    const materialsIndex = task.type === 1 ? 0 : diffDaysCount;
    const materials = dailyMaterials[String(materialsIndex)] || [];
    
    // 统计已完成的素材数
    const completedMaterials = materials.filter((m: any) => {
      return m.status && m.status[String(userId)] === 1;
    }).length;
    
    const totalMaterials = materials.length;
    const progressPercent = totalMaterials > 0 ? (completedMaterials / totalMaterials) * 100 : 0;
    const todayScore = dailyScore[String(materialsIndex)] || 0;
    
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
  // 使用传入的日期，如果没有则使用今天
  const targetDate = props.date ? new Date(props.date) : new Date();
  return props.tasks.map(task => calculateTaskProgress(task, props.userId, targetDate));
});
</script>
