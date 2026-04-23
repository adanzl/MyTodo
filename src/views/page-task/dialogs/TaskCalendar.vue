<template>
  <ion-modal 
    :is-open="isOpen" 
    @did-dismiss="handleDismiss"
    class="[--height:calc(min(90vh,90vw))] [--width:min(90vh,90vw)] [--min-height:28rem]"
  >
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="handleDismiss">
            <ion-icon :icon="closeOutline" />
          </ion-button>
        </ion-buttons>
        <ion-title>任务日历</ion-title>
      </ion-toolbar>
    </ion-header>
    
    <ion-content class="ion-padding">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center h-full">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <!-- 日历内容 -->
      <div v-else class="calendar-wrapper h-full flex flex-col overflow-hidden">
        <!-- 导航栏 -->
        <div class="flex items-center justify-between mb-2 shrink-0 px-2">
          <!-- 月份选择器 -->
          <ion-datetime-button datetime="monthPicker" class="text-sm"></ion-datetime-button>
          
          <!-- 左右箭头 -->
          <div class="flex items-center gap-1">
            <ion-button size="small" fill="clear" @click="prevMonth">
              <ion-icon :icon="chevronBackOutline" />
            </ion-button>
            <ion-button size="small" fill="clear" @click="nextMonth">
              <ion-icon :icon="chevronForwardOutline" />
            </ion-button>
          </div>
        </div>
        
        <!-- 日期选择弹窗 -->
        <ion-modal :keep-contents-mounted="true" @did-dismiss="fetchCalendarData">
          <ion-datetime
            id="monthPicker"
            presentation="month-year"
            :value="currentDate.format('YYYY-MM-DD')"
            @ionChange="handleDateTimeChange"
          ></ion-datetime>
        </ion-modal>
        
        <!-- 日历网格 -->
        <div class="grid grid-cols-7 gap-1 flex-1 content-start overflow-hidden">
          <!-- 星期标题 -->
          <div v-for="day in weekDays" :key="day" class="text-center text-xs font-medium py-1">
            {{ day }}
          </div>
          
          <!-- 日期格子 -->
          <div 
            v-for="date in calendarDates" 
            :key="date.dateStr"
            class="aspect-square flex flex-col items-center justify-center p-0.5 rounded cursor-pointer relative"
            :class="{
                'bg-blue-200 text-black': isToday(date.dateStr),
                'bg-blue-600 text-white': isSelectedDate(date.dateStr) && !isToday(date.dateStr),
                'bg-white text-black': !isToday(date.dateStr) && !isSelectedDate(date.dateStr),
                'hover:bg-gray-100': !isToday(date.dateStr) && !isSelectedDate(date.dateStr),
                'opacity-50': !date.isCurrentMonth
            }"
            @click="selectDate(date.dateStr)"
          >
            <!-- 未完成红点 -->
            <div 
              v-if="hasIncompleteTasks(date.dateStr)" 
              class="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full"
            ></div>
            
            <span class="text-xs">{{ date.day }}</span>
            <div v-if="getTaskStats(date.dateStr).total > 0" class="text-[8px] mt-0.5">
              {{ getTaskStats(date.dateStr).completed }}/{{ getTaskStats(date.dateStr).total }}
            </div>
          </div>
        </div>
      </div>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import {
    IonModal,
    IonHeader,
    IonToolbar,
    IonButtons,
    IonButton,
    IonTitle,
    IonContent,
    IonIcon,
    IonSpinner,
    IonDatetime,
    IonDatetimeButton
} from '@ionic/vue';
import { closeOutline, chevronBackOutline, chevronForwardOutline } from 'ionicons/icons';
import { ref, watch } from 'vue';
import { getTaskCalendar, type TaskCalendarResponse } from '@/api/api-task';
import { getTodayStr } from '@/utils/date-util';
import dayjs from 'dayjs';

interface Props {
    isOpen: boolean;
    selectedDate?: string; // 选中的日期 YYYY-MM-DD
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: 'update:isOpen', value: boolean): void;
    (e: 'dismiss'): void;
    (e: 'date-selected', date: string): void;
}>();

const loading = ref(false);
const calendarData = ref<TaskCalendarResponse | null>(null);
const currentDate = ref(dayjs());

const weekDays = ['日', '一', '二', '三', '四', '五', '六'];

// 生成日历日期
const calendarDates = ref<Array<{
    dateStr: string;
    day: number;
    isCurrentMonth: boolean;
}>>([]);

// 获取日历数据
const fetchCalendarData = async () => {
    if (!props.isOpen) return;

    loading.value = true;
    try {
        const dateStr = currentDate.value.format('YYYY-MM-DD');
        const data = await getTaskCalendar(dateStr);
        calendarData.value = data;
        generateCalendarDates(data.year, data.month);
    } catch (error) {
        console.error('获取任务日历失败:', error);
    } finally {
        loading.value = false;
    }
};

// 生成日历日期网格
const generateCalendarDates = (year: number, month: number) => {
    const dates: Array<{ dateStr: string; day: number; isCurrentMonth: boolean }> = [];

    const firstDay = dayjs(`${year}-${month}-01`);
    const lastDay = firstDay.endOf('month');
    const startDay = firstDay.startOf('week');
    const endDay = lastDay.endOf('week');

    let current = startDay;
    while (current.isBefore(endDay) || current.isSame(endDay)) {
        dates.push({
            dateStr: current.format('YYYY-MM-DD'),
            day: current.date(),
            isCurrentMonth: current.month() === month - 1
        });
        current = current.add(1, 'day');
    }

    calendarDates.value = dates;
};

// 判断是否是今天
const isToday = (dateStr: string) => {
    return dateStr === getTodayStr();
};

// 判断是否是选中日期
const isSelectedDate = (dateStr: string) => {
    return props.selectedDate === dateStr;
};

// 获取该日期的任务统计
const getTaskStats = (dateStr: string) => {
    const tasks = calendarData.value?.calendar[dateStr]?.tasks || [];
    // completed 是已完成素材数，total 是总素材数
    const totalMaterials = tasks.reduce((sum, t) => sum + t.total, 0);
    const completedMaterials = tasks.reduce((sum, t) => sum + t.completed, 0);
    return { total: totalMaterials, completed: completedMaterials };
};

// 判断是否有未完成任务
const hasIncompleteTasks = (dateStr: string) => {
    const stats = getTaskStats(dateStr);
    return stats.total > 0 && stats.completed < stats.total;
};

// 选择日期
const selectDate = (dateStr: string) => {
    emit('date-selected', dateStr);
    emit('update:isOpen', false);
};

// 上一月
const prevMonth = () => {
    currentDate.value = currentDate.value.subtract(1, 'month');
    fetchCalendarData();
};

// 下一月
const nextMonth = () => {
    currentDate.value = currentDate.value.add(1, 'month');
    fetchCalendarData();
};

// 日期时间变化
const handleDateTimeChange = (event: any) => {
    const selectedDate = dayjs(event.detail.value);
    currentDate.value = selectedDate;
};

const handleDismiss = () => {
    emit('update:isOpen', false);
    emit('dismiss');
};

// 监听弹窗打开，加载数据
watch(() => props.isOpen, (newVal) => {
    if (newVal) {
        fetchCalendarData();
    }
});
</script>
