<template>
  <div class="p-1 max-w-7xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-baseline gap-3">
        <h2 class="text-2xl font-bold text-gray-800">课程表</h2>
        <p class="text-sm text-gray-600">
          当前显示: {{ filterDisplayText }} (共 {{ courseCount }} 门课程)
        </p>
        <p class="text-xs text-gray-500 mt-1">
          最后更新: {{ lastSaveTime }}
        </p>
      </div>
      <div class="flex items-center">
        <el-radio-group v-model="filterChild" size="default" class="mr-8">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="zhaozhao">昭昭</el-radio-button>
          <el-radio-button value="cancan">灿灿</el-radio-button>
        </el-radio-group>
        <el-button plain type="primary" @click="reloadTimetable" :loading="loading" :icon="Refresh" />
        <el-button @click="saveTimetable" type="primary" :loading="loading" :disabled="loading">
          <IMdiContentSave v-if="!loading" />
        </el-button>
      </div>
    </div>

    <div class="overflow-x-auto relative" v-loading="loading">
      <table class="w-full border-collapse bg-white shadow-lg rounded-lg overflow-hidden">
        <thead>
          <tr class="bg-gray-50">
            <th class="border border-gray-200 p-2 text-center font-semibold text-gray-700 min-w-20">
              时间
            </th>
            <th
              v-for="day in weekDays"
              :key="day"
              class="border border-gray-200 p-2 text-center font-semibold text-gray-700 min-w-32"
              :class="{ 'bg-yellow-100': isToday(day) }"
              :colspan="filterChild === 'all' ? 2 : 1"
            >
              {{ day }}
            </th>
          </tr>
          <tr class="bg-blue-50">
            <th class="border border-gray-200 px-4 py-2 text-center"></th>
            <template v-for="day in weekDays" :key="day">
              <th
                v-if="shouldShowSubHeaders || filterChild === 'zhaozhao'"
                class="border border-gray-200 px-1 py-1 text-center"
                :class="{ 'bg-yellow-50': isToday(day) }"
              >
                <div class="text-xs text-gray-600 font-medium">{{ CHILDREN_MAP.zhaozhao }}</div>
              </th>
              <th
                v-if="shouldShowSubHeaders || filterChild === 'cancan'"
                class="border border-gray-200 px-1 py-1 text-center"
                :class="{ 'bg-yellow-50': isToday(day) }"
              >
                <div class="text-xs text-gray-600 font-medium">{{ CHILDREN_MAP.cancan }}</div>
              </th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="hour in hourSlots" :key="hour" class="hover:bg-gray-50">
            <td
              class="border border-gray-200 p-2 text-center text-sm font-bold text-gray-600 bg-gray-50"
            >
              {{ hour }}
            </td>
            <template v-for="day in weekDays" :key="day">
              <!-- 昭昭的课程格子 -->
              <td
                v-if="shouldShowSubHeaders || filterChild === 'zhaozhao'"
                class="border border-gray-200 relative"
                :class="{ 'bg-yellow-50': isToday(day) }"
                :style="{ height: `${CELL_HEIGHT}px` }"
              >
                <div
                  class="w-full h-full bg-blue-50 rounded cursor-pointer hover:bg-blue-100 transition-colors relative"
                  @click="onHourCellClick(day, 'zhaozhao', hour)"
                >
                  <CourseBlock
                    v-for="course in getCoursesForHour(day, 'zhaozhao', hour)"
                    :key="course.startTime"
                    :course="course"
                    :hour="hour"
                    :child-name="'zhaozhao'"
                    :day="day"
                    :course-colors="COURSE_COLORS"
                    @edit="editCourse"
                  />
                </div>
              </td>
              <!-- 灿灿的课程格子 -->
              <td
                v-if="shouldShowSubHeaders || filterChild === 'cancan'"
                class="border border-gray-200 relative"
                :class="{ 'bg-yellow-50': isToday(day) }"
                :style="{ height: `${CELL_HEIGHT}px` }"
              >
                <div
                  class="w-full h-full bg-gray-50 rounded cursor-pointer hover:bg-pink-50 transition-colors relative"
                  @click="onHourCellClick(day, 'cancan', hour)"
                >
                  <CourseBlock
                    v-for="course in getCoursesForHour(day, 'cancan', hour)"
                    :key="course.startTime"
                    :course="course"
                    :hour="hour"
                    :child-name="'cancan'"
                    :day="day"
                    :course-colors="COURSE_COLORS"
                    @edit="editCourse"
                  />
                </div>
              </td>
            </template>
          </tr>
        </tbody>
        <tfoot>
          <tr class="bg-gray-50">
            <th class="border border-gray-200 p-2 text-center font-semibold text-gray-700 min-w-20">
              时间
            </th>
            <th
              v-for="day in weekDays"
              :key="day"
              class="border border-gray-200 p-2 text-center font-semibold text-gray-700 min-w-32"
              :class="{ 'bg-yellow-100': isToday(day) }"
              :colspan="filterChild === 'all' ? 2 : 1"
            >
              {{ day }}
            </th>
          </tr>
        </tfoot>
      </table>

      <!-- 当前时间线 -->
      <div
        v-if="currentTimeLine.visible"
        class="absolute pointer-events-none z-20"
        :style="{
          top: `${currentTimeLine.top + 120}px`,
          left: '30px',
          right: '0'
        }"
      >
        <div class="flex items-center">
          <div class="w-20 text-right pr-2 shrink-0">
            <span class="text-xs font-bold text-red-500 bg-white px-1 rounded shadow">
              {{ dayjs().format('HH:mm') }}
            </span>
          </div>
          <div class="flex-1 h-0.5 bg-red-500"></div>
        </div>
      </div>

      <!-- 空状态提示 -->
      <div
        v-if="courseCount === 0 && !loading"
        class="text-center py-6 bg-blue-50 rounded-lg mt-4 border border-blue-200"
      >
        <div class="flex items-center justify-center space-x-2 text-blue-600">
          <el-icon><InfoFilled /></el-icon>
          <span class="text-sm">暂无课程数据，点击任意时间格子来添加课程</span>
        </div>
        <div class="mt-3 space-x-2">
          <el-button type="info" size="small" @click="reloadTimetable">重新加载</el-button>
          <el-button type="info" size="small" @click="printTimetable">打印课程表</el-button>
        </div>
      </div>

      <!-- 非空状态提示 -->
      <div
        v-if="courseCount > 0 && !loading"
        class="text-center py-4 bg-gray-50 rounded-lg mt-4 border border-gray-200"
      >
        <div class="flex items-center justify-center space-x-2 text-gray-600">
          <el-icon><InfoFilled /></el-icon>
          <span class="text-sm">当前共有 {{ courseCount }} 门课程</span>
        </div>
        <div class="mt-3 space-x-2">
          <el-button type="info" size="small" @click="reloadTimetable">重新加载</el-button>
          <el-button type="info" size="small" @click="printTimetable">打印课程表</el-button>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="showEditModal"
      title="编辑课程"
      width="500px"
      :before-close="closeModal"
      center
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">开始时间:</label>
          <el-select
            v-model="editingCourse.startTime"
            placeholder="请选择开始时间"
            filterable
            class="w-full"
          >
            <el-option v-for="time in startTimeOptions" :key="time" :label="time" :value="time">
              {{ time }}
            </el-option>
          </el-select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">课程名称:</label>
          <el-input
            v-model="editingCourse.name"
            placeholder="请输入课程名称"
            type="textarea"
            :rows="3"
            clearable
          >
          </el-input>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">持续时间(分钟):</label>
          <el-input-number
            v-model="editingCourse.duration"
            :min="10"
            :step="10"
            :max="240"
            placeholder="10"
            class="w-full"
          >
          </el-input-number>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">课程颜色:</label>
          <div class="flex space-x-2">
            <div
              v-for="(color, id) in { 1: '蓝色', 2: '绿色', 3: '紫色', 4: '橙色', 5: '粉色' }"
              :key="id"
              class="w-8 h-8 rounded-full border-2 cursor-pointer transition-all"
              :class="[
                parseInt(id as string) === editingCourse.colorId
                  ? 'border-gray-800 scale-110'
                  : 'border-gray-300',
                getCourseColor(parseInt(id as string) as CourseColorId).bg,
              ]"
              @click="editingCourse.colorId = parseInt(id as string) as CourseColorId"
              :title="color"
            ></div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end space-x-3">
          <el-button @click="deleteCourse" type="danger" size="default"> 删除课程 </el-button>
          <el-button @click="closeModal" size="default"> 取消 </el-button>
          <el-button @click="saveCourse" type="primary" size="default"> 保存 </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { InfoFilled, Refresh } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { getRdsData, setRdsData } from "@/api/api-rds";
import { logger } from "@/utils/logger";
import CourseBlock from "./components/CourseBlock.vue";
import type {
  Course,
  EditingCourse,
  TimetableData,
  FilterChild,
  Weekday,
  CourseColorId,
  CourseColor,
} from "@/types/timetable";

// ============ 常量定义 ============
const CHILDREN_MAP: Record<string, string> = {
  zhaozhao: "昭昭",
  cancan: "灿灿",
};

const WEEK_DAYS: Weekday[] = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const HOUR_START = 8;
const HOUR_END = 22;
const TIME_STEP_MINUTES = 10;
const DEFAULT_DURATION = 30;
const CELL_HEIGHT = 80; // px

// 课程颜色配置
const COURSE_COLORS: Record<CourseColorId, CourseColor> = {
  1: { bg: "bg-blue-300", border: "border-blue-400", hover: "hover:bg-blue-400" },
  2: { bg: "bg-green-300", border: "border-green-400", hover: "hover:bg-green-400" },
  3: { bg: "bg-purple-300", border: "border-purple-400", hover: "hover:bg-purple-400" },
  4: { bg: "bg-orange-300", border: "border-orange-400", hover: "hover:bg-orange-400" },
  5: { bg: "bg-pink-300", border: "border-pink-400", hover: "hover:bg-pink-400" },
};

// ============ 响应式数据 ============
const timetableData = ref<TimetableData>({});
const loading = ref(false);
const showEditModal = ref(false);
const filterChild = ref<FilterChild>("all");
const lastSaveTime = ref<string>("");
const currentTimeLine = ref<{ top: number; visible: boolean }>({ top: 0, visible: false });
const editingCourse = ref<EditingCourse>({
  day: "",
  child: "zhaozhao",
  startTime: "",
  name: "",
  duration: DEFAULT_DURATION,
  colorId: 1,
});

// ============ 计算属性 ============
const weekDays = computed(() => WEEK_DAYS);

// 获取今天是星期几（0=周一, 1=周二, ..., 6=周日）
const todayIndex = computed(() => {
  return dayjs().day() - 1; // dayjs: 0=周日, 1=周一, ..., 7=周六
});

const isToday = (day: Weekday): boolean => {
  return weekDays.value.indexOf(day) === todayIndex.value;
};

const hourSlots = computed(() => {
  const slots: string[] = [];
  for (let hour = HOUR_START; hour <= HOUR_END; hour++) {
    slots.push(`${hour.toString().padStart(2, "0")}:00`);
  }
  return slots;
});

const startTimeOptions = computed(() => {
  const options: string[] = [];
  for (let hour = HOUR_START; hour <= HOUR_END; hour++) {
    for (let min = 0; min < 60; min += TIME_STEP_MINUTES) {
      options.push(
        `${hour.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}`
      );
    }
  }
  return options;
});

const courseCount = computed(() => {
  let count = 0;
  Object.keys(timetableData.value).forEach(key => {
    if (filterChild.value === "all" || key.includes(filterChild.value)) {
      count += timetableData.value[key].length;
    }
  });
  return count;
});

const filterDisplayText = computed(() => {
  switch (filterChild.value) {
    case "zhaozhao":
      return "突出显示昭昭的课程";
    case "cancan":
      return "突出显示灿灿的课程";
    default:
      return "显示全部课程";
  }
});

const shouldShowSubHeaders = computed(() => filterChild.value === "all");

// ============ 工具函数 ============

/**
 * 获取课程颜色配置
 */
const getCourseColor = (colorId?: CourseColorId): CourseColor => {
  const id = (colorId || 1) as CourseColorId;
  return COURSE_COLORS[id] || COURSE_COLORS[1];
};

/**
 * 计算课程结束时间
 */
const getEndTime = (course: Course): string => {
  const [h, m] = course.startTime.split(":").map(Number);
  const totalMinutes = m + course.duration;
  const endHour = h + Math.floor(totalMinutes / 60);
  const endMin = totalMinutes % 60;
  return `${endHour.toString().padStart(2, "0")}:${endMin.toString().padStart(2, "0")}`;
};

/**
 * 清理时间格式为 HH:MM
 */
const cleanTimeFormat = (timeStr: string): string => {
  if (!timeStr) return timeStr;
  return timeStr.length > 5 ? timeStr.substring(0, 5) : timeStr;
};

/**
 * 创建日期对象用于时间比较
 */
const createTimeDate = (timeStr: string): Date => {
  return new Date(`2000-01-01 ${timeStr}`);
};

/**
 * 检查两个时间段是否重叠
 */
const isTimeOverlap = (
  start1: Date,
  end1: Date,
  start2: Date,
  end2: Date
): boolean => {
  return start1 < end2 && end1 > start2;
};

/**
 * 获取某天某孩子某小时的课程列表
 */
const getCoursesForHour = (
  day: Weekday,
  child: "zhaozhao" | "cancan",
  hour: string
): Course[] => {
  const key = `${day}-${child}`;
  const courses = timetableData.value[key] || [];
  const hourStartTime = createTimeDate(`${hour}:00`);
  const hourEndTime = createTimeDate(`${hour.split(":")[0]}:59`);

  return courses
    .filter((course: Course) => {
      const courseStartTime = createTimeDate(course.startTime);
      const courseEndTime = createTimeDate(getEndTime(course));
      return isTimeOverlap(courseStartTime, courseEndTime, hourStartTime, hourEndTime);
    })
    .sort((a: Course, b: Course) => a.startTime.localeCompare(b.startTime));
};

/**
 * 计算指定小时块内可以开始的最早时间
 */
const getEarliestAvailableTime = (
  day: Weekday,
  child: "zhaozhao" | "cancan",
  hour: string
): string | null => {
  const key = `${day}-${child}`;
  const existingCourses = timetableData.value[key] || [];
  const hourNum = parseInt(hour.split(":")[0]);
  const hourStartTime = createTimeDate(`${hourNum.toString().padStart(2, "0")}:00`);
  const hourEndTime = createTimeDate(`${hourNum.toString().padStart(2, "0")}:59`);

  // 获取所有影响当前小时块的课程
  const relevantCourses = existingCourses
    .filter((course: Course) => {
      const courseStart = createTimeDate(course.startTime);
      const courseEnd = new Date(courseStart.getTime() + course.duration * 60000);
      return (
        (courseStart >= hourStartTime && courseStart < hourEndTime) ||
        (courseStart < hourStartTime && courseEnd > hourStartTime)
      );
    })
    .sort((a: Course, b: Course) => a.startTime.localeCompare(b.startTime));

  // 如果没有课程，返回整点时间
  if (relevantCourses.length === 0) {
    return `${hourNum.toString().padStart(2, "0")}:00`;
  }

  // 寻找第一个可用时间段
  let currentTime = new Date(hourStartTime);

  for (const course of relevantCourses) {
    const courseStart = createTimeDate(course.startTime);
    const courseEnd = new Date(courseStart.getTime() + course.duration * 60000);

    // 如果当前时间在课程开始之前，且间隔足够（至少10分钟），则可用
    if (currentTime < courseStart) {
      const timeDiff = (courseStart.getTime() - currentTime.getTime()) / 60000;
      if (timeDiff >= TIME_STEP_MINUTES) {
        const hours = currentTime.getHours();
        const minutes = currentTime.getMinutes();
        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
      }
    }

    // 更新当前时间为课程结束时间
    currentTime = new Date(Math.max(currentTime.getTime(), courseEnd.getTime()));
  }

  // 检查最后一个课程结束后是否有足够时间
  if (currentTime < hourEndTime) {
    const hours = currentTime.getHours();
    const minutes = currentTime.getMinutes();
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
  }

  return null;
};

/**
 * 点击小时格子新建课程
 */
const onHourCellClick = (day: Weekday, child: "zhaozhao" | "cancan", hour: string) => {
  const earliestTime = getEarliestAvailableTime(day, child, hour);

  if (earliestTime === null) {
    ElMessage.warning("该小时块已无可用时间段");
    return;
  }

  editingCourse.value = {
    day,
    child,
    startTime: earliestTime,
    name: "",
    duration: DEFAULT_DURATION,
    colorId: 1,
    originalStartTime: null,
  };
  showEditModal.value = true;
};

/**
 * 编辑现有课程
 */
const editCourse = (day: Weekday, child: "zhaozhao" | "cancan", startTime: string) => {
  const key = `${day}-${child}`;
  const course = (timetableData.value[key] || []).find(
    (c: Course) => c.startTime === startTime
  );

  if (course) {
    editingCourse.value = {
      day,
      child,
      startTime: course.startTime,
      name: course.name,
      duration: course.duration,
      colorId: course.colorId || 1,
      originalStartTime: course.startTime,
    };
    showEditModal.value = true;
  }
};

/**
 * 保存课程（新增或编辑）
 */
const saveCourse = () => {
  const { day, child, startTime, name, duration } = editingCourse.value;

  if (!name.trim()) {
    ElMessage.warning("请输入课程名称");
    return;
  }

  const key = `${day}-${child}`;
  if (!timetableData.value[key]) {
    timetableData.value[key] = [];
  }

  // 检查时间冲突
  const newStartTime = createTimeDate(startTime);
  const newEndTime = new Date(newStartTime.getTime() + duration * 60000);

  for (const course of timetableData.value[key]) {
    // 跳过当前正在编辑的课程
    if (
      editingCourse.value.originalStartTime &&
      course.startTime === editingCourse.value.originalStartTime
    ) {
      continue;
    }

    const courseStart = createTimeDate(course.startTime);
    const courseEnd = new Date(courseStart.getTime() + course.duration * 60000);

    if (isTimeOverlap(newStartTime, newEndTime, courseStart, courseEnd)) {
      ElMessage.error("课程时间冲突，请选择其他时间");
      return;
    }
  }

  // 如果是编辑，先删除原有课程
  if (editingCourse.value.originalStartTime) {
    timetableData.value[key] = timetableData.value[key].filter(
      (c: Course) => c.startTime !== editingCourse.value.originalStartTime
    );
  }

  // 添加新课程
  timetableData.value[key].push({
    startTime: cleanTimeFormat(startTime),
    name: name.trim(),
    duration: parseInt(duration.toString()),
    colorId: (editingCourse.value.colorId || 1) as CourseColorId,
  });

  showEditModal.value = false;
};

/**
 * 删除课程
 */
const deleteCourse = () => {
  const { day, child, startTime } = editingCourse.value;
  const key = `${day}-${child}`;

  timetableData.value[key] = (timetableData.value[key] || []).filter(
    (c: Course) => c.startTime !== startTime
  );

  showEditModal.value = false;
  ElMessage.success("课程删除成功");
};

/**
 * 关闭编辑弹窗
 */
const closeModal = () => {
  showEditModal.value = false;
};

/**
 * 重新加载课程表数据
 */
const reloadTimetable = async () => {
  try {
    loading.value = true;
    await loadTimetableData();
    ElMessage.success("课程表数据已重新加载！");
  } catch (error) {
    logger.error("重新加载失败:", error);
    ElMessage.error("重新加载失败，请重试");
  } finally {
    loading.value = false;
  }
};

/**
 * 更新当前时间线位置
 */
const updateCurrentTimeLine = () => {
  const now = dayjs();
  const currentHour = now.hour();
  const currentMinute = now.minute();

  // 检查是否在当前显示的时间范围内
  if (currentHour < HOUR_START || currentHour > HOUR_END) {
    currentTimeLine.value.visible = false;
    return;
  }

  // 计算相对于表格顶部的位置
  const hourIndex = currentHour - HOUR_START;
  const minuteOffset = (currentMinute / 60) * CELL_HEIGHT;
  const top = hourIndex * CELL_HEIGHT + minuteOffset;

  currentTimeLine.value = {
    top,
    visible: true,
  };
};

/**
 * 格式化时间为本地字符串
 */
const formatDateTime = (date: Date): string => {
  return dayjs(date).format("YYYY-MM-DD HH:mm:ss");
};

/**
 * 保存课程表到服务器
 */
const saveTimetable = async () => {
  try {
    loading.value = true;

    // 更新最后保存时间
    const now = formatDateTime(new Date());
    lastSaveTime.value = now;

    // 将保存时间也存入数据中
    const dataToSave = {
      ...timetableData.value,
      _lastSaveTime: now,
    };

    const jsonData = JSON.stringify(dataToSave);
    await setRdsData("t_timetable", 0, jsonData);

    ElMessage.success("课程表保存成功！");
  } catch (error) {
    logger.error("保存失败:", error);
    ElMessage.error("保存失败，请重试");
  } finally {
    loading.value = false;
  }
};

/**
 * 打印课程表
 */
const printTimetable = () => {
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    ElMessage.warning("无法打开打印窗口，请检查浏览器设置");
    return;
  }

  const generatePrintContent = (): string => {
    const rows = hourSlots.value.map(hour => {
      const cells = weekDays.value
        .map(day => {
          const zhaozhaoCourses = getCoursesForHour(day, "zhaozhao", hour);
          const cancanCourses = getCoursesForHour(day, "cancan", hour);

          const content = [
            ...zhaozhaoCourses.map(c => `${c.name} (${c.startTime}-${getEndTime(c)})`),
            ...cancanCourses.map(c => `${c.name} (${c.startTime}-${getEndTime(c)})`),
          ].join("<br>");

          return `<td style="border: 1px solid #000; padding: 8px; text-align: left; vertical-align: top; min-height: 40px;">${content}</td>`;
        })
        .join("");

      return `
        <tr>
          <td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold; background-color: #f9f9f9;">${hour}</td>
          ${cells}
        </tr>
      `;
    }).join("");

    return `
      <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="text-align: center; margin-bottom: 30px;">课程表</h1>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
          <thead>
            <tr style="background-color: #f5f5f5;">
              <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">时间</th>
              ${weekDays.value
        .map(
          day =>
            `<th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">${day}</th>`
        )
        .join("")}
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  };

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>课程表</title>
        <style>
          body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
          @media print {
            body { margin: 0; }
            table { page-break-inside: auto; }
            tr { page-break-inside: avoid; page-break-after: auto; }
          }
        </style>
      </head>
      <body>${generatePrintContent()}</body>
    </html>
  `);
  printWindow.document.close();

  printWindow.onload = () => {
    printWindow.print();
    printWindow.close();
  };
};

/**
 * 加载课程表数据
 */
const loadTimetableData = async () => {
  try {
    loading.value = true;
    const data = await getRdsData("t_timetable", 0);

    if (data) {
      const rawData = JSON.parse(data as string) as any;

      // 提取最后保存时间
      if (rawData._lastSaveTime) {
        lastSaveTime.value = rawData._lastSaveTime;
        delete rawData._lastSaveTime; // 从课程数据中移除
      }

      // 清理所有课程的开始时间格式
      Object.keys(rawData).forEach(key => {
        if (Array.isArray(rawData[key])) {
          rawData[key].forEach((course: Course) => {
            if (course.startTime) {
              course.startTime = cleanTimeFormat(course.startTime);
            }
            // 确保 colorId 是有效的值
            if (course.colorId && (course.colorId < 1 || course.colorId > 5)) {
              course.colorId = 1;
            }
          });
        }
      });

      timetableData.value = rawData;
    }

    // 初始化当前时间线
    updateCurrentTimeLine();
  } catch (error) {
    logger.error("加载数据失败:", error);
    timetableData.value = {};
  } finally {
    loading.value = false;
  }
};

// ============ 生命周期 ============
onMounted(async () => {
  await loadTimetableData();

  // 每5s更新一次当前时间线
  setInterval(updateCurrentTimeLine, 5000);
});
</script>

<style scoped></style>
