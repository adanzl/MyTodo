<template>
  <div class="p-1 max-w-7xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-800">课程表</h2>
        <p class="text-sm text-gray-600 mt-1">
          当前显示: {{ getFilterDisplayText() }} (共 {{ getCourseCount() }} 门课程)
        </p>
      </div>
      <div class="flex items-center space-x-4">
        <el-radio-group v-model="filterChild" size="default">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="zhaozhao">昭昭</el-radio-button>
          <el-radio-button value="cancan">灿灿</el-radio-button>
        </el-radio-group>
        <el-button @click="reloadTimetable" type="info" :loading="loading" :disabled="loading">
          {{ loading ? "加载中..." : "重新加载" }}
        </el-button>

        <el-button @click="saveTimetable" type="primary" :loading="loading" :disabled="loading">
          {{ loading ? "保存中..." : "保存课程表" }}
        </el-button>
      </div>
    </div>

    <div class="overflow-x-auto" v-loading="loading">
      <table class="w-full border-collapse bg-white shadow-lg rounded-lg overflow-hidden">
        <thead>
          <tr class="bg-gray-50">
            <th
              class="border border-gray-200 px-2 py-2 text-center font-semibold text-gray-700 min-w-20"
            >
              时间
            </th>
            <th
              v-for="day in weekDays"
              :key="day"
              class="border border-gray-200 px-2 py-2 text-center font-semibold text-gray-700 min-w-32"
              :colspan="filterChild === 'all' ? 2 : 1"
            >
              {{ day }}
            </th>
          </tr>
          <tr class="bg-blue-50">
            <th class="border border-gray-200 px-4 py-2 text-center"></th>
            <template v-for="day in weekDays" :key="day">
              <th
                v-if="filterChild === 'all' || filterChild === 'zhaozhao'"
                class="border border-gray-200 px-1 py-1 text-center"
              >
                <div class="text-xs text-gray-600 font-medium">昭昭</div>
              </th>
              <th
                v-if="filterChild === 'all' || filterChild === 'cancan'"
                class="border border-gray-200 px-1 py-1 text-center"
              >
                <div class="text-xs text-gray-600 font-medium">灿灿</div>
              </th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="hour in hourSlots" :key="hour" class="hover:bg-gray-50">
            <td
              class="border border-gray-200 px-2 py-2 text-center text-sm font-bold text-gray-600 bg-gray-50"
            >
              {{ hour }}
            </td>
            <template v-for="day in weekDays" :key="day">
              <td
                v-if="filterChild === 'all' || filterChild === 'zhaozhao'"
                class="border border-gray-200 relative"
                style="height: 80px"
              >
                <div
                  class="w-full h-full bg-blue-50 rounded cursor-pointer hover:bg-blue-100 transition-colors relative"
                  @click="onHourCellClick(day, 'zhaozhao', hour)"
                >
                  <template
                    v-for="course in getCoursesForHour(day, 'zhaozhao', hour)"
                    :key="course.startTime"
                  >
                    <div
                      class="absolute top-0 h-full rounded text-xs flex items-center justify-center cursor-pointer transition-colors"
                      :class="[
                        getCourseColor(course).bg,
                        getCourseColor(course).border,
                        getCourseColor(course).hover,
                        {
                          'border-dashed': course.duration >= 60,
                        },
                      ]"
                      :style="getCourseBlockStyle(course, hour)"
                      @click.stop="editCourse(day, 'zhaozhao', course.startTime)"
                      :title="`${course.name} (${course.startTime}-${getEndTime(course)})`"
                      style="pointer-events: auto; z-index: 10"
                    >
                      <div class="text-center p-2">
                        <div
                          v-if="shouldShowCourseName(course, hour)"
                          class="font-medium whitespace-pre-line leading-tight"
                          :class="{
                            'text-xs': course.duration <= 30,
                            'text-sm': course.duration > 30,
                          }"
                        >
                          {{ course.name }}
                        </div>
                      </div>
                    </div>
                  </template>
                </div>
              </td>
              <td
                v-if="filterChild === 'all' || filterChild === 'cancan'"
                class="border border-gray-200 relative"
                style="height: 80px"
              >
                <div
                  class="w-full h-full bg-gray-50 rounded cursor-pointer hover:bg-pink-50 transition-colors relative"
                  @click="onHourCellClick(day, 'cancan', hour)"
                >
                  <template
                    v-for="course in getCoursesForHour(day, 'cancan', hour)"
                    :key="course.startTime"
                  >
                    <div
                      class="absolute top-0 h-full rounded text-xs flex items-center justify-center cursor-pointer transition-colors"
                      :class="[
                        getCourseColor(course).bg,
                        getCourseColor(course).border,
                        getCourseColor(course).hover,
                        {
                          'border-dashed': course.duration >= 60,
                        },
                      ]"
                      :style="getCourseBlockStyle(course, hour)"
                      @click.stop="editCourse(day, 'cancan', course.startTime)"
                      :title="`${course.name} (${course.startTime}-${getEndTime(course)})`"
                      style="pointer-events: auto; z-index: 10"
                    >
                      <div class="text-center p-2">
                        <div
                          v-if="shouldShowCourseName(course, hour)"
                          class="font-medium whitespace-pre-line leading-tight"
                          :class="{
                            'text-xs': course.duration <= 30,
                            'text-sm': course.duration > 30,
                          }"
                        >
                          {{ course.name }}
                        </div>
                      </div>
                    </div>
                  </template>
                </div>
              </td>
            </template>
          </tr>
        </tbody>
        <tfoot>
          <tr class="bg-gray-50">
            <th
              class="border border-gray-200 px-2 py-2 text-center font-semibold text-gray-700 min-w-20"
            >
              时间
            </th>
            <th
              v-for="day in weekDays"
              :key="day"
              class="border border-gray-200 px-2 py-2 text-center font-semibold text-gray-700 min-w-32"
              :colspan="filterChild === 'all' ? 2 : 1"
            >
              {{ day }}
            </th>
          </tr>
        </tfoot>
      </table>

      <!-- 空状态提示 -->
      <div
        v-if="getCourseCount() === 0 && !loading"
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
        v-if="getCourseCount() > 0 && !loading"
        class="text-center py-4 bg-gray-50 rounded-lg mt-4 border border-gray-200"
      >
        <div class="flex items-center justify-center space-x-2 text-gray-600">
          <el-icon><InfoFilled /></el-icon>
          <span class="text-sm">当前共有 {{ getCourseCount() }} 门课程</span>
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
                parseInt(id as string) == editingCourse.colorId
                  ? 'border-gray-800 scale-110'
                  : 'border-gray-300',
                getCourseColor({ colorId: id }).bg,
              ]"
              @click="editingCourse.colorId = parseInt(id as string)"
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
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { InfoFilled } from "@element-plus/icons-vue";
import { getRdsData, setRdsData } from "@/api/rds";

// 课程颜色常量
const COURSE_COLORS: Record<number, { bg: string; border: string; hover: string }> = {
  1: { bg: "bg-blue-300", border: "border-blue-400", hover: "hover:bg-blue-400" },
  2: { bg: "bg-green-300", border: "border-green-400", hover: "hover:bg-green-400" },
  3: { bg: "bg-purple-300", border: "border-purple-400", hover: "hover:bg-purple-400" },
  4: { bg: "bg-orange-300", border: "border-orange-400", hover: "hover:bg-orange-400" },
  5: { bg: "bg-pink-300", border: "border-pink-400", hover: "hover:bg-pink-400" },
};

// 响应式数据
const timetableData = ref<Record<string, any[]>>({}); // { '周一-zhaozhao': [ { startTime, name, duration } ] }
const loading = ref(false);
const showEditModal = ref(false);
const filterChild = ref("all"); // 筛选功能：all, zhaozhao, cancan
const editingCourse = ref<{
  day: string;
  child: string;
  startTime: string;
  name: string;
  duration: number;
  colorId?: number;
  originalStartTime?: string | null;
}>({
  day: "",
  child: "",
  startTime: "",
  name: "",
  duration: 10,
  colorId: 1,
});

// 星期
const weekDays = ref(["周一", "周二", "周三", "周四", "周五", "周六", "周日"]);

// 生成小时数组（08:00~22:00）
const hourSlots = ref<string[]>([]);
for (let hour = 8; hour <= 22; hour++) {
  hourSlots.value.push(`${hour.toString().padStart(2, "0")}:00`);
}

// 生成10分钟间隔的下拉选项（HH:MM格式，不包含秒）
const startTimeOptions = ref<string[]>([]);
for (let hour = 8; hour <= 22; hour++) {
  for (let min = 0; min < 60; min += 10) {
    startTimeOptions.value.push(
      `${hour.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}`
    );
  }
}

// 获取课程颜色
const getCourseColor = (course: any) => {
  const colorId = course.colorId || 1; // 默认使用颜色1
  return COURSE_COLORS[colorId] || COURSE_COLORS[1];
};

// 计算课程结束时间
const getEndTime = (course: any) => {
  const [h, m] = course.startTime.split(":").map(Number);
  let endMin = m + course.duration;
  let endHour = h;
  if (endMin >= 60) {
    endHour += Math.floor(endMin / 60);
    endMin = endMin % 60;
  }
  return `${endHour.toString().padStart(2, "0")}:${endMin.toString().padStart(2, "0")}`;
};

// 获取某天某孩子某小时的课程
const getCoursesForHour = (day: string, child: string, hour: string) => {
  const key = `${day}-${child}`;
  const courses = timetableData.value[key] || [];

  const filteredCourses = courses
    .filter(c => {
      // 检查课程是否在当前小时内有显示部分
      const courseStart = c.startTime;
      const courseEnd = getEndTime(c);
      const hourStart = `${hour}:00`;
      const hourEnd = `${hour.split(":")[0]}:59`;

      // 使用时间比较而不是字符串比较
      const courseStartTime = new Date(`2000-01-01 ${courseStart}`);
      const courseEndTime = new Date(`2000-01-01 ${courseEnd}`);
      const hourStartTime = new Date(`2000-01-01 ${hourStart}`);
      const hourEndTime = new Date(`2000-01-01 ${hourEnd}`);

      // 过滤条件：课程结束时间 > 小时块开始时间 且 课程开始时间 <= 小时块结束时间
      const shouldInclude =
        (courseEndTime > hourStartTime && courseStartTime <= hourEndTime) ||
        (courseStartTime <= hourStartTime && courseEndTime > hourStartTime);

      return shouldInclude;
    })
    .sort((a, b) => a.startTime.localeCompare(b.startTime));

  return filteredCourses;
};

// 计算课程块样式 - 超过60分钟的课程显示为连续色块
const getCourseBlockStyle = (course: any, hour: string) => {
  const [h] = course.startTime.split(":").map(Number);
  const currentHour = parseInt(hour.split(":")[0]);

  // 如果课程不在当前小时开始，不显示（避免重复显示）
  if (h !== currentHour) {
    return {
      display: "none",
    };
  }

  // 计算课程在当前小时内的位置和高度
  const [_, minPart] = course.startTime.split(":").map(Number);
  const top = (minPart / 60) * 100;

  // 计算课程的总高度（以小时为单位）
  const totalHeight = (course.duration / 60) * 100;

  return {
    top: `${top}%`,
    height: `${totalHeight}%`,
    position: "absolute",
    width: "100%",
    zIndex: 10,
  };
};

// 判断是否应该显示课程名称 - 只在开始的小时块显示
const shouldShowCourseName = (course: any, hour: string) => {
  const [h] = course.startTime.split(":").map(Number);
  const currentHour = parseInt(hour.split(":")[0]);

  // 只有课程开始的小时块才显示名称
  return h === currentHour;
};

// 计算指定小时块内可以开始的最早时间
const getEarliestAvailableTime = (day: string, child: string, hour: string) => {
  const key = `${day}-${child}`;
  const existingCourses = timetableData.value[key] || [];
  const hourNum = parseInt(hour.split(":")[0]);

  // 获取所有影响当前小时块的课程（包括跨小时的课程）
  const allRelevantCourses = existingCourses
    .filter(course => {
      const courseStart = parseInt(course.startTime.split(":")[0]);
      const courseEnd = new Date(`2000-01-01 ${course.startTime}`);
      courseEnd.setMinutes(courseEnd.getMinutes() + course.duration);
      const courseEndHour = courseEnd.getHours();

      // 包括：1. 在当前小时开始的课程 2. 从上一小时开始但延续到当前小时的课程
      return courseStart === hourNum || (courseStart < hourNum && courseEndHour >= hourNum);
    })
    .sort((a, b) => a.startTime.localeCompare(b.startTime));

  // 如果没有课程，返回整点时间
  if (allRelevantCourses.length === 0) {
    return `${hourNum.toString().padStart(2, "0")}:00`;
  }

  // 检查整点时间是否可用
  const firstCourse = allRelevantCourses[0];
  const firstCourseStart = parseInt(firstCourse.startTime.split(":")[0]);
  if (
    firstCourseStart > hourNum ||
    (firstCourseStart === hourNum &&
      firstCourse.startTime !== `${hourNum.toString().padStart(2, "0")}:00`)
  ) {
    return `${hourNum.toString().padStart(2, "0")}:00`;
  }

  // 寻找第一个可用时间段
  let currentTime = new Date(`2000-01-01 ${hourNum.toString().padStart(2, "0")}:00`);

  for (const course of allRelevantCourses) {
    const courseStart = new Date(`2000-01-01 ${course.startTime}`);
    const courseEnd = new Date(`2000-01-01 ${course.startTime}`);
    courseEnd.setMinutes(courseEnd.getMinutes() + course.duration);

    // 如果当前时间在课程开始之前，且间隔足够（至少10分钟），则可用
    if (currentTime < courseStart) {
      const timeDiff = (courseStart.getTime() - currentTime.getTime()) / (1000 * 60); // 转换为分钟
      if (timeDiff >= 10) {
        const hours = currentTime.getHours();
        const minutes = currentTime.getMinutes();
        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
      }
    }

    // 更新当前时间为课程结束时间
    currentTime = new Date(courseEnd);
  }

  // 检查最后一个课程结束后是否有足够时间
  const lastCourse = allRelevantCourses[allRelevantCourses.length - 1];
  const lastCourseEnd = new Date(`2000-01-01 ${lastCourse.startTime}`);
  lastCourseEnd.setMinutes(lastCourseEnd.getMinutes() + lastCourse.duration);

  const hourEnd = new Date(`2000-01-01 ${hourNum.toString().padStart(2, "0")}:59`);

  if (lastCourseEnd < hourEnd) {
    const hours = lastCourseEnd.getHours();
    const minutes = lastCourseEnd.getMinutes();
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
  }

  // 如果没有可用时间，返回null
  return null;
};

// 点击小时格子新建课程
const onHourCellClick = (day: string, child: string, hour: string) => {
  // 计算该小时块内可以开始的最早时间
  const earliestTime = getEarliestAvailableTime(day, child, hour);

  if (earliestTime === null) {
    ElMessage.warning("该小时块已无可用时间段");
    return;
  }

  // 打开编辑对话框，设置计算出的开始时间
  editingCourse.value = {
    day,
    child,
    startTime: earliestTime,
    name: "",
    duration: 30,
    colorId: 1,
    originalStartTime: null, // 新建课程时设为null
  };
  showEditModal.value = true;
};

// 编辑课程
const editCourse = (day: string, child: string, startTime: string) => {
  const key = `${day}-${child}`;
  const course = (timetableData.value[key] || []).find(c => c.startTime === startTime);
  if (course) {
    editingCourse.value = {
      day,
      child,
      startTime: course.startTime,
      name: course.name,
      duration: course.duration,
      colorId: course.colorId || 1,
      originalStartTime: course.startTime, // 保存原始开始时间
    };
    showEditModal.value = true;
  }
};

// 清理时间格式，确保都是HH:MM格式
const cleanTimeFormat = (timeStr: string) => {
  if (!timeStr) return timeStr;
  // 如果包含秒数，只取前5个字符（HH:MM）
  if (timeStr.length > 5) {
    return timeStr.substring(0, 5);
  }
  return timeStr;
};

// 保存课程
const saveCourse = () => {
  const { day, child, startTime, name, duration } = editingCourse.value;
  if (!name.trim()) {
    ElMessage.warning("请输入课程名称");
    return;
  }

  const key = `${day}-${child}`;
  if (!timetableData.value[key]) timetableData.value[key] = [];

  // 检查时间冲突（在删除原有课程之前）
  const existingCourses = timetableData.value[key];
  const newStartTime = new Date(`2000-01-01 ${startTime}`);
  const newEndTime = new Date(`2000-01-01 ${startTime}`);
  newEndTime.setMinutes(newEndTime.getMinutes() + duration);

  for (const course of existingCourses) {
    // 跳过当前正在编辑的课程（避免自己与自己冲突）
    if (
      editingCourse.value.originalStartTime &&
      course.startTime === editingCourse.value.originalStartTime
    ) {
      continue;
    }

    const courseStartTime = new Date(`2000-01-01 ${course.startTime}`);
    const courseEndTime = new Date(`2000-01-01 ${course.startTime}`);
    courseEndTime.setMinutes(courseEndTime.getMinutes() + course.duration);

    // 检查时间重叠：新课程开始时间 < 现有课程结束时间 且 新课程结束时间 > 现有课程开始时间
    if (newStartTime < courseEndTime && newEndTime > courseStartTime) {
      ElMessage.error("课程时间冲突，请选择其他时间");
      return;
    }
  }

  // 如果是编辑，删除原有同startTime的课程
  if (editingCourse.value.originalStartTime) {
    timetableData.value[key] = timetableData.value[key].filter(
      c => c.startTime !== editingCourse.value.originalStartTime
    );
  }

  // 添加新课程
  timetableData.value[key].push({
    startTime: cleanTimeFormat(startTime),
    name: name.trim(),
    duration: parseInt(duration.toString()),
    colorId: editingCourse.value.colorId || 1,
  });

  showEditModal.value = false;
};

// 删除课程
const deleteCourse = () => {
  const { day, child, startTime } = editingCourse.value;
  const key = `${day}-${child}`;
  timetableData.value[key] = (timetableData.value[key] || []).filter(
    c => c.startTime !== startTime
  );
  showEditModal.value = false;
  ElMessage.success("课程删除成功");
};

// 关闭弹窗
const closeModal = () => {
  showEditModal.value = false;
};

// 重新加载课程表数据
const reloadTimetable = async () => {
  try {
    loading.value = true;
    await loadTimetableData();
    ElMessage.success("课程表数据已重新加载！");
  } catch (error) {
    console.error("重新加载失败:", error);
    ElMessage.error("重新加载失败，请重试");
  } finally {
    loading.value = false;
  }
};

// 获取筛选显示文本
const getFilterDisplayText = () => {
  switch (filterChild.value) {
    case "zhaozhao":
      return "突出显示昭昭的课程";
    case "cancan":
      return "突出显示灿灿的课程";
    default:
      return "显示全部课程";
  }
};

// 获取当前筛选模式下的课程数量
const getCourseCount = () => {
  let count = 0;
  Object.keys(timetableData.value).forEach(key => {
    if (filterChild.value === "all" || key.includes(filterChild.value)) {
      count += timetableData.value[key].length;
    }
  });
  return count;
};

// 保存课程表到服务器
const saveTimetable = async () => {
  try {
    loading.value = true;
    const jsonData = JSON.stringify(timetableData.value);
    await setRdsData("t_timetable", 0, jsonData);
    ElMessage.success("课程表保存成功！");
  } catch (error) {
    console.error("保存失败:", error);
    ElMessage.error("保存失败，请重试");
  } finally {
    loading.value = false;
  }
};

// 打印课程表
const printTimetable = () => {
  // 创建打印内容
  const printContent = document.createElement("div");
  printContent.innerHTML = `
    <div style="font-family: Arial, sans-serif; padding: 20px;">
      <h1 style="text-align: center; margin-bottom: 30px;">课程表</h1>
      <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
        <thead>
          <tr style="background-color: #f5f5f5;">
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">时间</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周一</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周二</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周三</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周四</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周五</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周六</th>
            <th style="border: 1px solid #000; padding: 10px; text-align: center; font-weight: bold;">周日</th>
          </tr>
          <tr style="background-color: #e8f4fd;">
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;"></th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">昭昭</th>
          </tr>
          <tr style="background-color: #ffe8f8;">
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;"></th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
            <th style="border: 1px solid #000; padding: 5px; text-align: center; font-size: 12px;">灿灿</th>
          </tr>
        </thead>
        <tbody>
          ${hourSlots.value
            .map(hour => {
              const row = [hour];
              weekDays.value.forEach(day => {
                const zhaozhaoCourses = getCoursesForHour(day, "zhaozhao", hour);
                const cancanCourses = getCoursesForHour(day, "cancan", hour);

                let cellContent = "";
                if (zhaozhaoCourses.length > 0) {
                  cellContent += zhaozhaoCourses
                    .map(c => `${c.name} (${c.startTime}-${getEndTime(c)})`)
                    .join("<br>");
                }
                if (cancanCourses.length > 0) {
                  if (cellContent) cellContent += "<br>";
                  cellContent += cancanCourses
                    .map(c => `${c.name} (${c.startTime}-${getEndTime(c)})`)
                    .join("<br>");
                }

                row.push(cellContent || "");
              });

              return `
                <tr>
                  ${row
                    .map((content, index) =>
                      index === 0
                        ? `<td style="border: 1px solid #000; padding: 8px; text-align: center; font-weight: bold; background-color: #f9f9f9;">${content}</td>`
                        : `<td style="border: 1px solid #000; padding: 8px; text-align: left; vertical-align: top; min-height: 40px;">${content}</td>`
                    )
                    .join("")}
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;

  // 创建打印窗口
  const printWindow = window.open("", "_blank");
  if (!printWindow) return;

  printWindow.document.write(`
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
      <body>
        ${printContent.innerHTML}
      </body>
    </html>
  `);
  printWindow.document.close();

  // 等待内容加载完成后打印
  printWindow.onload = () => {
    printWindow.print();
    printWindow.close();
  };
};

// 加载课程表数据
const loadTimetableData = async () => {
  try {
    loading.value = true;
    const data = await getRdsData("t_timetable", 0);
    if (data) {
      const rawData = JSON.parse(data as string);
      // 清理所有课程的开始时间格式
      Object.keys(rawData).forEach(key => {
        if (Array.isArray(rawData[key])) {
          rawData[key].forEach((course: any) => {
            if (course.startTime) {
              course.startTime = cleanTimeFormat(course.startTime);
            }
          });
        }
      });
      timetableData.value = rawData;
    }
  } catch (error) {
    console.error("加载数据失败:", error);
    timetableData.value = {};
  } finally {
    loading.value = false;
  }
};

// 组件挂载时加载数据
onMounted(async () => {
  await loadTimetableData();
});
</script>

<style scoped></style>
