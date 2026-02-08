<template>
  <ion-page id="main-content" main>
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <div class="px-2">课程表</div>
        </ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button @click="refreshData" fill="clear" class="text-gray-400 pr-2">
            <ion-icon :icon="refreshOutline"></ion-icon>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <!-- 星期选择 -->
    <div class="p-1 bg-gray-50">
      <ion-segment v-model="selectedWeekday" @ionChange="onWeekdayChange" class="rounded-lg">
        <ion-segment-button value="周一" class="rounded-l-lg">
          <ion-label>周一</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周二">
          <ion-label>周二</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周三">
          <ion-label>周三</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周四">
          <ion-label>周四</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周五">
          <ion-label>周五</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周六">
          <ion-label>周六</ion-label>
        </ion-segment-button>
        <ion-segment-button value="周日" class="rounded-r-lg">
          <ion-label>周日</ion-label>
        </ion-segment-button>
      </ion-segment>
    </div>

    <!-- 固定的表头区域 -->
    <div class="flex border-b border-gray-200 bg-white">
      <!-- 时间轴表头 -->
      <div
        class="w-20 h-8 flex items-center justify-center text-xs font-bold border-r border-gray-200 bg-gray-50 text-gray-800">
        时间
      </div>
      <!-- 昭昭表头 -->
      <div
        class="flex-1 h-8 flex items-center justify-center text-xs font-bold border-r border-gray-200 bg-blue-50 text-blue-800">
        昭昭
      </div>
      <!-- 灿灿表头 -->
      <div class="flex-1 h-8 flex items-center justify-center text-xs font-bold bg-green-50 text-green-800">
        灿灿
      </div>
    </div>

    <!-- 滚动内容区域 -->
    <ion-content class="ion-no-padding" ref="scrollContainer">
      <div class="flex">
        <!-- 时间轴 -->
        <div class="w-20 border-r border-gray-200">
          <div class="relative bg-gray-50">
            <div
              v-for="time in timeSlots"
              :key="time"
              class="h-15 flex items-center justify-center text-xs border-b border-gray-100 text-gray-600">
              {{ time }}
            </div>
          </div>
        </div>

        <!-- 课程内容区域 -->
        <div class="flex-1 flex relative">
          <!-- 当前时间线 -->
          <div
            v-if="currentTimePosition !== null"
            class="absolute left-0 right-0 z-20 pointer-events-none current-time-line"
            :style="{ top: `${currentTimePosition}px` }">
            <div class="relative">
              <div class="h-0.5 bg-red-500 shadow-lg"></div>
              <div class="absolute -top-1 -left-1 w-3 h-3 bg-red-500 rounded-full shadow-lg current-time-dot"></div>
              <!-- 时间显示在水平线中间 -->
              <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div class="bg-red-500 text-white text-[8px] px-1 py-0.5 rounded-full font-bold shadow-lg whitespace-nowrap">
                  {{ currentTimeDisplay }}
                </div>
              </div>
            </div>
          </div>

          <!-- 昭昭的课程 -->
          <div class="flex-1 relative border-r border-gray-200">
            <div class="relative">
              <!-- 时间网格背景 -->
              <div class="absolute inset-0 z-0">
                <div
                  v-for="(_, index) in TIME_CONFIG.endHour - TIME_CONFIG.startHour + 1"
                  :key="index"
                  :data-index="index"
                  class="absolute w-full border-b border-gray-100"
                  :style="{
                    top: `${index * TIME_CONFIG.hourHeight}px`,
                    height: `${TIME_CONFIG.hourHeight}px`,
                  }"
                  @click="addCourse($event, 'zhaozhao')"></div>
              </div>
              <div
                v-for="course in zhaozhaoCourses"
                :key="course.id"
                :class="getCourseClasses(course)"
                :style="getCourseStyle(course)"
                @click.stop="editCourse(course, 'zhaozhao')"
                class="relative z-10">
                <!-- 课程时间显示 -->
                <div class="absolute -top-1 right-0 text-[8px] font-bold text-gray-800 px-1 pt-1.5 pb-0.5 z-20 leading-tight">
                  <div>{{ course.startTime }}</div>
                  <div>{{ formatCourseEndTime(course.startTime, course.duration) }}</div>
                </div>
                <div class="font-bold leading-tight" :class="getCourseTextClass(course)">
                  {{ course.name }}
                </div>
              </div>
            </div>
          </div>

          <!-- 灿灿的课程 -->
          <div class="flex-1 relative">
            <div class="relative">
              <!-- 时间网格背景 -->
              <div class="absolute inset-0 z-0">
                <div
                  v-for="(_, index) in TIME_CONFIG.endHour - TIME_CONFIG.startHour + 1"
                  :key="index"
                  :data-index="index"
                  class="absolute w-full border-b border-gray-100"
                  :style="{
                    top: `${index * TIME_CONFIG.hourHeight}px`,
                    height: `${TIME_CONFIG.hourHeight}px`,
                  }"
                  @click="addCourse($event, 'cancan')"></div>
              </div>
              <div
                v-for="course in cancanCourses"
                :key="course.id"
                :class="getCourseClasses(course)"
                :style="getCourseStyle(course)"
                @click.stop="editCourse(course, 'cancan')"
                class="relative z-10">
                <!-- 课程时间显示 -->
                <div class="absolute -top-1 right-0 text-[8px] font-bold text-gray-800 px-1 pt-1.5 pb-0.5 z-20 leading-tight">
                  <div>{{ course.startTime }}</div>
                  <div>{{ formatCourseEndTime(course.startTime, course.duration) }}</div>
                </div>
                <div class="font-bold leading-tight" :class="getCourseTextClass(course)">
                  {{ course.name }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ion-content>

    <!-- 编辑课程弹窗 -->

    <ion-modal :is-open="isEditModalOpen" @willDismiss="closeEditModal" mode="ios" class="backdrop">
      <ion-item>
        <ion-title>编辑课程</ion-title>
        <!-- 删除按钮 - 右上角 -->
        <ion-button
          v-if="isEditingExistingCourse"
          @click="deleteCourse"
          slot="end"
          fill="clear"
          color="danger">
          <ion-icon :icon="trashOutline"></ion-icon>
        </ion-button>
      </ion-item>
      <ion-content class="ion-padding">
        <ion-item>
          <Icon icon="mdi:clock-outline" class="w-[1.6em] h-[1.6em] mr-2" slot="start" />
          <ion-label>开始时间</ion-label>
          <ion-select
            v-model="editingCourse.startTime"
            interface="popover"
            placeholder="选择时间"
            class="flex-1 text-left">
            <ion-select-option v-for="time in timeOptions" :key="time.value" :value="time.value">
              {{ time.label }}
            </ion-select-option>
          </ion-select>
        </ion-item>

        <ion-item>
          <Icon icon="mdi:clock-end-outline" class="w-[1.6em] h-[1.6em] mr-2" slot="start" />
          <ion-label>结束时间</ion-label>
          <ion-label slot="end" class="text-gray-500 w-[50%]">{{ endTimeDisplay }}</ion-label>
        </ion-item>
        <ion-item>
          <Icon icon="mdi:timer-outline" class="w-[1.6em] h-[1.6em] mr-2" slot="start" />
          <ion-label>持续时间</ion-label>
          <div slot="end" class="flex items-center gap-2 w-[50%]">
            <ion-button @click="adjustDuration(-10)" fill="outline" size="small" style="margin-right: auto;">
              <ion-icon :icon="removeOutline"></ion-icon>
            </ion-button>
            <ion-label class="w-12 text-center">{{ editingCourse.duration || 60 }}</ion-label>
            <ion-button @click="adjustDuration(10)" fill="outline" size="small">
              <ion-icon :icon="addOutline"></ion-icon>
            </ion-button>
          </div>
        </ion-item>
                <ion-item>
          <Icon icon="mdi:card-text-outline" class="w-[1.6em] h-[1.6em] mr-2 self-start mt-2" slot="start" />
          <ion-textarea
            v-model="editingCourse.name"
            placeholder="输入课程名称"
            :rows="3"
            :auto-grow="true">
          </ion-textarea>
        </ion-item>
        <ion-item lines="none">
          <Icon icon="mdi:palette-outline" class="w-[1.6em] h-[1.6em] mr-2" slot="start" />
          <ion-label>颜色</ion-label>
          <div slot="end" class="flex gap-2">
            <div
              v-for="(color, id) in COURSE_COLORS"
              :key="id"
              class="w-6 h-6 rounded-full cursor-pointer border-2 transition-all duration-200"
              :class="[
                color.bg,
                editingCourse.colorId == id ? 'border-gray-800 scale-110' : 'border-gray-300',
              ]"
              @click="editingCourse.colorId = Number(id)"></div>
          </div>
        </ion-item>
      </ion-content>
      <ion-footer class="flex!">
        <ion-button class="flex-1 text-gray-400" fill="clear" @click="closeEditModal">
          取消
        </ion-button>
        <ion-button class="flex-1 text-orange-400" fill="clear" @click="saveCourse">
          确定
        </ion-button>
      </ion-footer>
    </ion-modal>
  </ion-page>
</template>

<script setup lang="ts">
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { getRdsData, setRdsData } from "@/api/data";
import EventBus, { C_EVENT } from "@/types/EventBus";
import {
  IonButton,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonPage,
  IonSegment,
  IonSegmentButton,
  IonTextarea,
  IonIcon,
  IonSelect,
  IonSelectOption,
  alertController,
  IonModal,
  IonToolbar,
} from "@ionic/vue";
import { trashOutline, removeOutline, addOutline, refreshOutline } from "ionicons/icons";
import { computed, onMounted, onUnmounted, onBeforeUnmount, ref } from "vue";

// 课程数据 - 从RDS加载
const timetableData = ref({});

// 响应式数据
const selectedWeekday = ref("");
const isEditModalOpen = ref(false);
const editingCourse = ref<any>({});
const editingChild = ref("");
const isEditingExistingCourse = ref(false);
const scrollContainer = ref<any>();
const currentTime = ref(new Date());

// 获取当前星期
const getCurrentWeekday = () => {
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  const today = new Date().getDay();
  return weekdays[today];
};

// 初始化选中星期
const initializeWeekday = () => {
  selectedWeekday.value = getCurrentWeekday();
};

const COURSE_COLORS = {
  1: { bg: "bg-blue-300", border: "border-blue-600", hover: "hover:bg-blue-400" },
  2: { bg: "bg-green-300", border: "border-green-400", hover: "hover:bg-green-400" },
  3: { bg: "bg-purple-300", border: "border-purple-400", hover: "hover:bg-purple-400" },
  4: { bg: "bg-orange-300", border: "border-orange-400", hover: "hover:bg-orange-400" },
  5: { bg: "bg-pink-300", border: "border-pink-400", hover: "hover:bg-pink-400" },
};

// 时间配置
const TIME_CONFIG = {
  startHour: 7,
  endHour: 22,
  hourHeight: 60, // 每小时的像素高度
  minHeight: 20, // 最小高度
};

// 生成时间槽 (7:00-22:00, 每小时显示一次)
const timeSlots = computed(() => {
  const slots = [];
  for (let hour = TIME_CONFIG.startHour; hour <= TIME_CONFIG.endHour; hour++) {
    const time = `${hour.toString().padStart(2, "0")}:00`;
    slots.push(time);
  }
  return slots;
});

// 生成时间选项 (6:00-22:00, 每10分钟一个间隔)
const timeOptions = computed(() => {
  const options = [];
  for (let hour = 6; hour <= 22; hour++) {
    for (let minute = 0; minute < 60; minute += 10) {
      const timeValue = `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`;
      const timeLabel = `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`;
      options.push({
        value: timeValue,
        label: timeLabel,
      });
    }
  }
  return options;
});

// 获取当前选中星期的课程
const zhaozhaoCourses = computed(() => {
  const key = `${selectedWeekday.value}-zhaozhao`;
  return timetableData.value[key] || [];
});

const cancanCourses = computed(() => {
  const key = `${selectedWeekday.value}-cancan`;
  return timetableData.value[key] || [];
});

// 计算当前时间在时间轴上的位置
const currentTimePosition = computed(() => {
  const now = currentTime.value;
  const hours = now.getHours();
  const minutes = now.getMinutes();
  
  // 如果当前时间不在显示范围内，返回null
  if (hours < TIME_CONFIG.startHour || hours > TIME_CONFIG.endHour) {
    return null;
  }
  
  // 计算相对于开始时间的分钟数
  const totalMinutes = hours * 60 + minutes;
  const startTimeMinutes = TIME_CONFIG.startHour * 60;
  const relativeMinutes = totalMinutes - startTimeMinutes;
  
  // 转换为像素位置
  const position = (relativeMinutes / 60) * TIME_CONFIG.hourHeight;
  return position;
});

// 格式化当前时间显示
const currentTimeDisplay = computed(() => {
  const now = currentTime.value;
  return `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
});

// 计算结束时间
const endTimeDisplay = computed(() => {
  if (!editingCourse.value.startTime || !editingCourse.value.duration) {
    return "";
  }
  
  const [hours, minutes] = editingCourse.value.startTime.split(":").map(Number);
  const startMinutes = hours * 60 + minutes;
  const endMinutes = startMinutes + editingCourse.value.duration;
  
  const endHours = Math.floor(endMinutes / 60);
  const endMins = endMinutes % 60;
  
  return `${endHours.toString().padStart(2, "0")}:${endMins.toString().padStart(2, "0")}`;
});

// 方法
const onWeekdayChange = (event: any) => {
  selectedWeekday.value = event.detail.value;
  // 星期切换后滚动到最早课程
  setTimeout(() => {
    scrollToEarliestCourse();
  }, 50);
};

const getCourseStyle = (course: any) => {
  const [hours, minutes] = course.startTime.split(":").map(Number);
  const startMinutes = hours * 60 + minutes;
  const startTimeMinutes = TIME_CONFIG.startHour * 60;
  const top = ((startMinutes - startTimeMinutes) / 60) * TIME_CONFIG.hourHeight;
  const height = (course.duration / 60) * TIME_CONFIG.hourHeight;

  return {
    position: "absolute" as const,
    top: `${top}px`,
    height: `${height}px`,
    minHeight: `${TIME_CONFIG.minHeight}px`,
  };
};

const getCourseClasses = (course: any) => {
  const colorId = course.colorId || 1;
  const colorConfig = COURSE_COLORS[colorId] || COURSE_COLORS[1];

  return [
    "absolute left-2 right-2 rounded p-2 text-xs overflow-hidden cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-md",
    colorConfig.bg,
    colorConfig.border,
    colorConfig.hover,
  ].join(" ");
};

// 获取课程文本显示类
const getCourseTextClass = (course: any) => {
  const duration = course.duration || 60;

  // 计算允许显示的行数：每20分钟1行
  const allowedLines = Math.floor(duration / 20);

  // 根据允许的行数设置显示类
  if (allowedLines <= 1) {
    return "truncate"; // 单行显示，超出部分省略
  } else {
    // 使用 Tailwind 的 line-clamp 类
    const lineClampClass = `line-clamp-${Math.min(allowedLines, 6)}`; // 最多6行
    return `whitespace-pre-line ${lineClampClass}`;
  }
};

const editCourse = (course: any, child: string) => {
  editingCourse.value = { 
    ...course,
    colorId: course.colorId || 1 // 如果没有颜色ID，默认使用1
  };
  editingChild.value = child;
  isEditingExistingCourse.value = true;
  isEditModalOpen.value = true;
};

const addCourse = (event: MouseEvent, child: string) => {
  // 获取点击的网格索引
  const clickedElement = event.currentTarget as HTMLElement;
  const gridIndex = parseInt(clickedElement.getAttribute("data-index") || "0");

  // 根据网格索引计算对应的小时
  const clickedHour = TIME_CONFIG.startHour + gridIndex;

  // 确保时间在有效范围内
  const validHour = Math.max(TIME_CONFIG.startHour, Math.min(TIME_CONFIG.endHour, clickedHour));

  // 查找该小时的最早可用时间
  const availableTime = findAvailableTimeInHour(validHour, child);

  // 创建新课程
  editingCourse.value = {
    id: Date.now(),
    name: "",
    startTime: `${availableTime.hour.toString().padStart(2, "0")}:${availableTime.minute
      .toString()
      .padStart(2, "0")}`,
    duration: 60,
    colorId: 1,
  };
  editingChild.value = child;
  isEditingExistingCourse.value = false;
  isEditModalOpen.value = true;
};

// 查找指定小时内的最早可用时间
const findAvailableTimeInHour = (targetHour: number, child: string) => {
  const key = `${selectedWeekday.value}-${child}`;
  const courses = timetableData.value[key] || [];

  // 按开始时间排序
  const sortedCourses = courses.sort((a: any, b: any) => {
    const timeA = a.startTime.split(":").map(Number);
    const timeB = b.startTime.split(":").map(Number);
    return timeA[0] * 60 + timeA[1] - (timeB[0] * 60 + timeB[1]);
  });

  // 在该小时内查找最早可用时间（10分钟间隔）
  for (let minute = 0; minute < 60; minute += 10) {
    const timeInMinutes = targetHour * 60 + minute;
    if (!isTimeOccupiedByMinutes(timeInMinutes, sortedCourses)) {
      return { hour: targetHour, minute: minute };
    }
  }

  // 如果该小时内没有可用时间，查找下一个小时的可用时间
  for (let hour = targetHour + 1; hour <= TIME_CONFIG.endHour; hour++) {
    for (let minute = 0; minute < 60; minute += 10) {
      const timeInMinutes = hour * 60 + minute;
      if (!isTimeOccupiedByMinutes(timeInMinutes, sortedCourses)) {
        return { hour: hour, minute: minute };
      }
    }
  }

  // 如果都不可用，返回目标小时的00分钟
  return { hour: targetHour, minute: 0 };
};

// 检查指定分钟时间是否被占用
const isTimeOccupiedByMinutes = (timeInMinutes: number, courses: any[]) => {
  return courses.some((course: any) => {
    const [courseHour, courseMinute] = course.startTime.split(":").map(Number);
    const courseStart = courseHour * 60 + courseMinute;
    const courseEnd = courseStart + course.duration;

    // 检查目标时间是否与现有课程重叠
    return timeInMinutes >= courseStart && timeInMinutes < courseEnd;
  });
};

// 检查时间冲突
const checkTimeConflicts = () => {
  const key = `${selectedWeekday.value}-${editingChild.value}`;
  const courses = timetableData.value[key] || [];
  const conflicts: string[] = [];

  // 获取当前编辑课程的时间信息
  const [editHour, editMinute] = editingCourse.value.startTime.split(":").map(Number);
  const editStart = editHour * 60 + editMinute;
  const editEnd = editStart + editingCourse.value.duration;

  // 检查与其他课程的冲突
  courses.forEach((course: any) => {
    // 跳过当前正在编辑的课程
    if (course.id === editingCourse.value.id) {
      return;
    }

    const [courseHour, courseMinute] = course.startTime.split(":").map(Number);
    const courseStart = courseHour * 60 + courseMinute;
    const courseEnd = courseStart + course.duration;

    // 检查时间重叠
    if (
      (editStart >= courseStart && editStart < courseEnd) ||
      (editEnd > courseStart && editEnd <= courseEnd) ||
      (editStart <= courseStart && editEnd >= courseEnd)
    ) {
      const conflictTime = `${course.startTime} - ${formatTime(courseStart + course.duration)}`;
      conflicts.push(`与课程"${course.name}"时间冲突 (${conflictTime})`);
    }
  });

  return conflicts;
};

// 格式化时间
const formatTime = (minutes: number) => {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
};

// 格式化课程结束时间
const formatCourseEndTime = (startTime: string, duration: number) => {
  const [hours, minutes] = startTime.split(":").map(Number);
  const startMinutes = hours * 60 + minutes;
  const endMinutes = startMinutes + duration;
  
  const endHours = Math.floor(endMinutes / 60);
  const endMins = endMinutes % 60;
  
  return `${endHours.toString().padStart(2, "0")}:${endMins.toString().padStart(2, "0")}`;
};

const adjustDuration = (change: number) => {
  const currentDuration = Number(editingCourse.value.duration) || 60;
  const newDuration = currentDuration + change;

  // 限制最小10分钟，最大240分钟（4小时）
  if (newDuration >= 10 && newDuration <= 240) {
    editingCourse.value.duration = newDuration;
  }
};

const deleteCourse = async () => {
  // 创建确认对话框
  const alert = await alertController.create({
    header: "确认删除",
    message: `确定要删除课程"${editingCourse.value.name || "未命名课程"}"吗？`,
    buttons: [
      {
        text: "取消",
        role: "cancel",
      },
      {
        text: "删除",
        role: "destructive",
        handler: async () => {
          const key = `${selectedWeekday.value}-${editingChild.value}`;

          if (timetableData.value[key]) {
            // 从数组中移除课程
            timetableData.value[key] = timetableData.value[key].filter(
              (course: any) => course.id !== editingCourse.value.id
            );

            // 保存到RDS
            try {
              await setRdsData("t_timetable", 0, JSON.stringify(timetableData.value));
              EventBus.$emit(C_EVENT.TOAST, "已删除课程");
            } catch (error) {
              console.error("删除课程失败:", error);
              EventBus.$emit(C_EVENT.TOAST, "删除课程失败");
            }
          }

          closeEditModal();
        },
      },
    ],
  });

  await alert.present();
};

const closeEditModal = () => {
  isEditModalOpen.value = false;
  editingCourse.value = {};
  editingChild.value = "";
  isEditingExistingCourse.value = false;
};

const saveCourse = async () => {
  const key = `${selectedWeekday.value}-${editingChild.value}`;
  if (!timetableData.value[key]) {
    timetableData.value[key] = [];
  }

  // 检查时间冲突
  const conflicts = checkTimeConflicts();
  if (conflicts.length > 0) {
    // 显示冲突提示
    const alert = await alertController.create({
      header: "时间冲突",
      message: `检测到以下时间冲突：\n${conflicts.join('\n')}\n\n请调整课程时间后重试。`,
      buttons: [
        {
          text: "确定",
          role: "cancel",
        },
      ],
    });
    await alert.present();
    return;
  }

  // 检查是新增还是编辑
  const existingIndex = timetableData.value[key].findIndex(
    (c: any) => c.id === editingCourse.value.id
  );

  if (existingIndex !== -1) {
    // 编辑现有课程
    timetableData.value[key][existingIndex] = { ...editingCourse.value };
  } else {
    // 新增课程
    timetableData.value[key].push({ ...editingCourse.value });
  }

  // 保存到RDS
  try {
    await setRdsData("t_timetable", 0, JSON.stringify(timetableData.value));
  } catch (error) {
    console.error("保存课程表数据失败:", error);
  }

  closeEditModal();
};

// 加载数据
const loadTimetableData = async () => {
  try {
    const data = await getRdsData("t_timetable", 0);
    if (data) {
      timetableData.value = JSON.parse(data as string);
    } else {
      // 如果没有数据，初始化为空对象
      timetableData.value = {};
    }
  } catch (error) {
    console.error("加载课程表数据失败:", error);
    // 初始化为空对象
    timetableData.value = {};
  }
};

// 刷新数据
const refreshData = async () => {
  try {
    await loadTimetableData();
    // 刷新后滚动到最早课程
    setTimeout(() => {
      scrollToEarliestCourse();
    }, 100);
    // 发送刷新成功提示
    EventBus.$emit(C_EVENT.TOAST, "课程表数据刷新成功");
  } catch (error) {
    // 发送错误提示
    EventBus.$emit(C_EVENT.TOAST, JSON.stringify(error));
  }
};

// 定时器引用
let timeUpdateInterval: ReturnType<typeof setInterval> | null = null;

// 更新时间
const updateCurrentTime = () => {
  currentTime.value = new Date();
};

onMounted(async () => {
  await loadTimetableData();
  initializeWeekday();
  scrollToEarliestCourse();
  
  // 启动定时器，每1分钟更新一次时间
  timeUpdateInterval = setInterval(updateCurrentTime, 60000);
});

onBeforeUnmount(() => {
  // 在组件销毁前清理定时器
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }
});

onUnmounted(() => {
  // 确保定时器被清理
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }
});

// 滚动到当天最早的课程
const scrollToEarliestCourse = () => {
  // 等待DOM更新完成
  setTimeout(() => {
    if (scrollContainer.value) {
      // 获取当天所有课程
      const allCourses = [...zhaozhaoCourses.value, ...cancanCourses.value];

      if (allCourses.length > 0) {
        // 找到最早的课程
        const earliestCourse = allCourses.reduce((earliest, course) => {
          const [earliestHour, earliestMinute] = earliest.startTime.split(":").map(Number);
          const [courseHour, courseMinute] = course.startTime.split(":").map(Number);
          const earliestMinutes = earliestHour * 60 + earliestMinute;
          const courseMinutes = courseHour * 60 + courseMinute;
          return courseMinutes < earliestMinutes ? course : earliest;
        });

        // 计算滚动位置
        const [hours, minutes] = earliestCourse.startTime.split(":").map(Number);
        const startMinutes = hours * 60 + minutes;
        const startTimeMinutes = TIME_CONFIG.startHour * 60;
        const scrollTop = ((startMinutes - startTimeMinutes) / 60) * TIME_CONFIG.hourHeight;

        // 使用 ion-content 的滚动方法
        const contentElement = scrollContainer.value.$el;
        if (contentElement) {
          const scrollElement = contentElement.shadowRoot?.querySelector('.inner-scroll');
          if (scrollElement) {
            scrollElement.scrollTop = Math.max(0, scrollTop - 60);
          }
        }
      }
    }
  }, 100);
};
</script>

<style scoped>
ion-modal {
  --height: 70%;
  --width: 95%;
}

/* 确保星期选择器按钮平均分配宽度 */
ion-segment {
  display: flex;
  width: 100%;
}

ion-segment-button {
  flex: 1;
  min-width: 0;
}

/* 去掉ion-segment-button下button的padding */
ion-segment-button::part(native) {
  padding: 0;
}

/* 隐藏ion-content的滚动条但保持滚动功能 */
ion-content {
  --overflow: auto;
}

ion-content::part(scroll) {
  overflow: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

ion-content::part(scroll)::-webkit-scrollbar {
  display: none; /* Chrome, Safari and Opera */
}

/* 当前时间线动画效果 */
.current-time-line {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* 时间线圆点动画 */
.current-time-dot {
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}

</style>
