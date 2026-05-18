<template>
  <div
    class="absolute top-0 h-full rounded text-xs flex items-center justify-center cursor-pointer transition-colors"
    :class="[
      courseColor.bg,
      courseColor.border,
      courseColor.hover,
      {
        'border-dashed': course.duration >= 60,
      },
    ]"
    :style="blockStyle"
    @click.stop="handleClick"
    :title="`${course.name} (${course.startTime}-${endTime})`"
    style="pointer-events: auto; z-index: 10"
  >
    <div class="text-center p-2">
      <div
        v-if="showName"
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

<script setup lang="ts">
import { computed } from "vue";
import type { Course, Weekday, CourseColorId, CourseColor } from "@/types/timetable";

interface Props {
  course: Course;
  hour: string;
  childName: "zhaozhao" | "cancan";
  day: Weekday;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "edit", day: Weekday, child: "zhaozhao" | "cancan", startTime: string): void;
}>();

// 课程颜色常量
const COURSE_COLORS: Record<CourseColorId, CourseColor> = {
  1: { bg: "bg-blue-300", border: "border-blue-400", hover: "hover:bg-blue-400" },
  2: { bg: "bg-green-300", border: "border-green-400", hover: "hover:bg-green-400" },
  3: { bg: "bg-purple-300", border: "border-purple-400", hover: "hover:bg-purple-400" },
  4: { bg: "bg-orange-300", border: "border-orange-400", hover: "hover:bg-orange-400" },
  5: { bg: "bg-pink-300", border: "border-pink-400", hover: "hover:bg-pink-400" },
};

// 计算属性
const courseColor = computed(() => {
  const colorId = (props.course.colorId || 1) as CourseColorId;
  return COURSE_COLORS[colorId] || COURSE_COLORS[1];
});

const endTime = computed(() => {
  const [h, m] = props.course.startTime.split(":").map(Number);
  const totalMinutes = m + props.course.duration;
  const endHour = h + Math.floor(totalMinutes / 60);
  const endMin = totalMinutes % 60;
  return `${endHour.toString().padStart(2, "0")}:${endMin.toString().padStart(2, "0")}`;
});

const blockStyle = computed(() => {
  const [startHour] = props.course.startTime.split(":").map(Number);
  const currentHour = parseInt(props.hour.split(":")[0]);

  // 只在课程开始的小时块显示
  if (startHour !== currentHour) {
    return { display: "none" };
  }

  const [_, minutes] = props.course.startTime.split(":").map(Number);
  const top = (minutes / 60) * 100;
  const height = (props.course.duration / 60) * 100;

  return {
    top: `${top}%`,
    height: `${height}%`,
    position: "absolute",
    width: "100%",
    zIndex: "10",
  };
});

const showName = computed(() => {
  const [startHour] = props.course.startTime.split(":").map(Number);
  const currentHour = parseInt(props.hour.split(":")[0]);
  return startHour === currentHour;
});

// 事件处理
const handleClick = () => {
  emit("edit", props.day, props.childName, props.course.startTime);
};
</script>

<style scoped></style>
