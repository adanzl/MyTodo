<template>
    <el-dialog v-model="visible" title="任务日历" width="600px" @close="handleClose">
        <!-- 加载状态 -->
        <div v-if="loading" class="flex justify-center items-center h-40">
            <el-icon class="is-loading" :size="40" color="#409eff">
                <Loading />
            </el-icon>
        </div>

        <!-- 日历内容 -->
        <div v-else class="calendar-wrapper">
            <!-- 导航栏 -->
            <div class="flex items-center justify-between mb-4">
                <el-button size="small" @click="prevMonth">
                    <el-icon>
                        <ArrowLeft />
                    </el-icon>
                </el-button>

                <div class="text-lg font-medium">
                    {{ currentDate.format('YYYY年MM月') }}
                </div>

                <el-button size="small" @click="nextMonth">
                    <el-icon>
                        <ArrowRight />
                    </el-icon>
                </el-button>
            </div>

            <!-- 日历网格 -->
            <div class="grid grid-cols-7 gap-1">
                <!-- 星期标题 -->
                <div v-for="day in weekDays" :key="day" class="text-center text-sm font-medium py-2">
                    {{ day }}
                </div>

                <!-- 日期格子 -->
                <div v-for="date in calendarDates" :key="date.dateStr"
                    class="aspect-square flex flex-col items-center justify-center p-1 rounded cursor-pointer relative border"
                    :class="{
                        'bg-blue-100 border-blue-300': isToday(date.dateStr),
                        'bg-blue-500 text-white border-blue-600': isSelectedDate(date.dateStr) && !isToday(date.dateStr),
                        'bg-white border-gray-200': !isToday(date.dateStr) && !isSelectedDate(date.dateStr),
                        'hover:bg-gray-50': !isToday(date.dateStr) && !isSelectedDate(date.dateStr),
                        'opacity-50': !date.isCurrentMonth
                    }" @click="selectDate(date.dateStr)">
                    <!-- 未完成红点 -->
                    <div v-if="hasIncompleteTasks(date.dateStr)"
                        class="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full"></div>

                    <span class="text-xs">{{ date.day }}</span>
                    <div v-if="getTaskStats(date.dateStr).total > 0" class="text-[8px] mt-0.5">
                        {{ getTaskStats(date.dateStr).completed }}/{{ getTaskStats(date.dateStr).total }}
                    </div>
                </div>
            </div>
        </div>

        <template #footer>
            <el-button @click="handleClose">取消</el-button>
            <el-button type="primary" @click="confirmSelection">确定</el-button>
        </template>
    </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ArrowLeft, ArrowRight, Loading } from '@element-plus/icons-vue';
import dayjs from 'dayjs';
import { formatDate } from '@/utils/date';
import { getTaskCalendar, type TaskCalendarResponse } from '@/api/api-task';

interface Props {
    modelValue: boolean;
    selectedDate?: string; // 选中的日期 YYYY-MM-DD
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: false,
    selectedDate: () => formatDate(new Date()),
});

const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void;
    (e: 'date-selected', date: string): void;
}>();

const visible = ref(false);
const loading = ref(false);
const currentDate = ref(dayjs());
const selectedDateInternal = ref(props.selectedDate);
const calendarData = ref<TaskCalendarResponse | null>(null);

const weekDays = ['日', '一', '二', '三', '四', '五', '六'];

// 生成日历日期
const calendarDates = ref<Array<{
    dateStr: string;
    day: number;
    isCurrentMonth: boolean;
}>>([]);

// 监听 modelValue 变化
watch(
    () => props.modelValue,
    (val) => {
        visible.value = val;
        if (val) {
            selectedDateInternal.value = props.selectedDate;
            fetchCalendarData();
        }
    }
);

// 监听 visible 变化
watch(visible, (val) => {
    emit('update:modelValue', val);
});

// 获取日历数据
const fetchCalendarData = async () => {
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
    return dateStr === formatDate(new Date());
};

// 判断是否是选中日期
const isSelectedDate = (dateStr: string) => {
    return selectedDateInternal.value === dateStr;
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
    selectedDateInternal.value = dateStr;
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

// 确认选择
const confirmSelection = () => {
    emit('date-selected', selectedDateInternal.value);
    handleClose();
};

// 关闭对话框
const handleClose = () => {
    visible.value = false;
};
</script>

<style scoped>
/* 全部使用 Tailwind CSS，无需额外自定义样式 */
</style>