<template>
  <el-dialog
    v-model="internalVisible"
    title="Cron 表达式生成器"
    width="700"
    :before-close="handleClose"
  >
    <div class="space-y-4 m-4">
      <!-- 秒 -->
      <div>
        <div class="text-sm font-medium mb-2">秒 (0-59)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.second"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每秒钟</el-radio>
            <el-radio label="0" class="!w-[80px]">第0秒</el-radio>
            <el-radio label="30" class="!w-[80px]">第30秒</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.secondCustom"
            placeholder="例如: 0,30 或 */10"
            :disabled="cronBuilder.second !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 分 -->
      <div>
        <div class="text-sm font-medium mb-2">分 (0-59)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.minute"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每分钟</el-radio>
            <el-radio label="0" class="!w-[80px]">第0分</el-radio>
            <el-radio label="30" class="!w-[80px]">第30分</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.minuteCustom"
            placeholder="例如: 0,30 或 */15"
            :disabled="cronBuilder.minute !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 时 -->
      <div>
        <div class="text-sm font-medium mb-2">时 (0-23)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.hour"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每小时</el-radio>
            <el-radio label="0" class="!w-[80px]">0点</el-radio>
            <el-radio label="9" class="!w-[80px]">9点</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.hourCustom"
            placeholder="例如: 9,12,18 或 */2"
            :disabled="cronBuilder.hour !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 日 -->
      <div>
        <div class="text-sm font-medium mb-2">日 (1-31)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.day"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每天</el-radio>
            <el-radio label="1" class="!w-[80px]">每月1号</el-radio>
            <el-radio label="15" class="!w-[80px]">每月15号</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.dayCustom"
            placeholder="例如: 1,15 或 */5"
            :disabled="cronBuilder.day !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 月 -->
      <div>
        <div class="text-sm font-medium mb-2">月 (1-12)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.month"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每月</el-radio>
            <el-radio label="1" class="!w-[80px]">1月</el-radio>
            <el-radio label="6" class="!w-[80px]">6月</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.monthCustom"
            placeholder="例如: 1,6,12 或 */3"
            :disabled="cronBuilder.month !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 周 -->
      <div>
        <div class="text-sm font-medium mb-2">周 (0-7, 0和7表示周日)</div>
        <div class="flex items-center gap-2">
          <el-radio-group
            v-model="cronBuilder.weekday"
            @change="updateCronExpression"
            class="flex items-center"
          >
            <el-radio label="*" class="!w-[80px]">每天</el-radio>
            <el-radio label="1-5" class="!w-[80px]">工作日</el-radio>
            <el-radio label="0,6" class="!w-[80px]">周末</el-radio>
            <el-radio label="custom" class="!w-[80px]">自定义</el-radio>
          </el-radio-group>
          <el-input
            v-model="cronBuilder.weekdayCustom"
            placeholder="例如: 1,3,5 或 1-5"
            :disabled="cronBuilder.weekday !== 'custom'"
            class="!w-[200px]"
            @input="updateCronExpression"
          >
          </el-input>
        </div>
      </div>

      <!-- 生成的 Cron 表达式 -->
      <div class="border-t pt-4">
        <div class="text-sm font-medium mb-2">生成的 Cron 表达式：</div>
        <el-input v-model="cronBuilder.generated" readonly class="mb-2"> </el-input>
        <div class="flex gap-2">
          <el-button type="primary" size="small" @click="handleApply"> 应用 </el-button>
          <el-button type="info" size="small" @click="handlePreview"> 预览执行时间 </el-button>
        </div>
      </div>

      <!-- 常用示例 -->
      <div class="border-t pt-4">
        <div class="text-sm font-medium mb-2">常用示例：</div>
        <div class="space-y-2">
          <div class="flex items-center gap-2 flex-wrap">
            <el-button size="small" @click="applyExample('0 0 * * *')"> 每天0点 </el-button>
            <el-button size="small" @click="applyExample('0 */30 * * *')"> 每30分钟 </el-button>
            <el-button size="small" @click="applyExample('0 0 9 * * 1-5')"> 工作日9点 </el-button>
            <el-button size="small" @click="applyExample('0 0 0 1 * *')"> 每月1号0点 </el-button>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { generateCronExpression, calculateNextCronTimes } from "@/utils/cron";
import { logAndNoticeError } from "@/utils";

interface CronBuilder {
  second: string;
  secondCustom: string;
  minute: string;
  minuteCustom: string;
  hour: string;
  hourCustom: string;
  day: string;
  dayCustom: string;
  month: string;
  monthCustom: string;
  weekday: string;
  weekdayCustom: string;
  generated: string;
}

interface Props {
  visible?: boolean;
  initialCron?: string;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  initialCron: "",
});

const emit = defineEmits<{
  "update:visible": [value: boolean];
  apply: [cronExpr: string];
  preview: [times: string[]];
  close: [];
}>();

const internalVisible = ref(props.visible);

const cronBuilder = ref<CronBuilder>({
  second: "*",
  secondCustom: "",
  minute: "*",
  minuteCustom: "",
  hour: "*",
  hourCustom: "",
  day: "*",
  dayCustom: "",
  month: "*",
  monthCustom: "",
  weekday: "*",
  weekdayCustom: "",
  generated: "",
});

// 重置 Cron 构建器
const resetCronBuilder = (builder: CronBuilder) => {
  builder.second = "*";
  builder.secondCustom = "";
  builder.minute = "*";
  builder.minuteCustom = "";
  builder.hour = "*";
  builder.hourCustom = "";
  builder.day = "*";
  builder.dayCustom = "";
  builder.month = "*";
  builder.monthCustom = "";
  builder.weekday = "*";
  builder.weekdayCustom = "";
  builder.generated = "";
};

// 解析 Cron 表达式到构建器对象
const parseCronExpression = (cronExpr: string, builder: CronBuilder) => {
  try {
    if (!cronExpr || typeof cronExpr !== "string") {
      resetCronBuilder(builder);
      return;
    }
    const parts = String(cronExpr).trim().split(/\s+/);
    let sec: string, min: string, hour: string, day: string, month: string, weekday: string;

    if (parts.length === 5) {
      const [first, second, third, fourth, fifth] = parts;
      if (first === "0" && second && second.startsWith("*/")) {
        sec = "0";
        min = second;
        hour = third || "*";
        day = fourth || "*";
        month = fifth || "*";
        weekday = "*";
      } else {
        min = first;
        hour = second;
        day = third;
        month = fourth;
        weekday = fifth;
        sec = "0";
      }
    } else if (parts.length === 6) {
      [sec, min, hour, day, month, weekday] = parts;
    } else {
      console.warn("Cron 表达式格式错误，部分数量:", parts.length);
      resetCronBuilder(builder);
      return;
    }

    if (parts.length === 5 || parts.length === 6) {
      // 解析秒
      if (sec === "*") {
        builder.second = "*";
        builder.secondCustom = "";
      } else if (sec === "0") {
        builder.second = "0";
        builder.secondCustom = "";
      } else {
        builder.second = "custom";
        builder.secondCustom = sec;
      }

      // 解析分
      if (min === "*") {
        builder.minute = "*";
        builder.minuteCustom = "";
      } else if (min === "0") {
        builder.minute = "0";
        builder.minuteCustom = "";
      } else if (min.startsWith("*/")) {
        builder.minute = "custom";
        builder.minuteCustom = min;
      } else {
        builder.minute = "custom";
        builder.minuteCustom = min;
      }

      // 解析时
      if (hour === "*") {
        builder.hour = "*";
        builder.hourCustom = "";
      } else if (hour === "0") {
        builder.hour = "0";
        builder.hourCustom = "";
      } else {
        builder.hour = "custom";
        builder.hourCustom = hour;
      }

      // 解析日
      if (day === "*") {
        builder.day = "*";
        builder.dayCustom = "";
      } else {
        builder.day = "custom";
        builder.dayCustom = day;
      }

      // 解析月
      if (month === "*") {
        builder.month = "*";
        builder.monthCustom = "";
      } else {
        builder.month = "custom";
        builder.monthCustom = month;
      }

      // 解析周
      if (weekday === "*") {
        builder.weekday = "*";
        builder.weekdayCustom = "";
      } else if (weekday === "1-5") {
        builder.weekday = "1-5";
        builder.weekdayCustom = "";
      } else if (weekday === "0,6" || weekday === "6,0") {
        builder.weekday = "0,6";
        builder.weekdayCustom = "";
      } else {
        builder.weekday = "custom";
        builder.weekdayCustom = weekday;
      }
    } else {
      console.warn("Cron 表达式格式错误，部分数量:", parts.length);
      resetCronBuilder(builder);
    }
  } catch (error) {
    console.error("解析 Cron 表达式失败:", error);
    resetCronBuilder(builder);
  }
};

// 更新生成的 Cron 表达式
const updateCronExpression = () => {
  cronBuilder.value.generated = generateCronExpression(cronBuilder.value);
};

// 处理关闭
const handleClose = () => {
  internalVisible.value = false;
  emit("close");
};

// 处理应用
const handleApply = () => {
  if (!cronBuilder.value.generated) {
    ElMessage.warning("请先生成 Cron 表达式");
    return;
  }
  emit("apply", cronBuilder.value.generated);
  handleClose();
};

// 处理预览
const handlePreview = () => {
  const cronExpr = cronBuilder.value.generated;
  if (!cronExpr) {
    ElMessage.warning("请先生成 Cron 表达式");
    return;
  }
  try {
    const times = calculateNextCronTimes(cronExpr, 5);
    emit("preview", times);
  } catch (error) {
    logAndNoticeError(error as Error, "预览失败");
  }
};

// 应用示例
const applyExample = (example: string) => {
  try {
    parseCronExpression(example, cronBuilder.value);
    updateCronExpression();
    nextTick(() => {
      if (cronBuilder.value.generated) {
        emit("apply", cronBuilder.value.generated);
        ElMessage.success("示例已应用");
      }
    });
  } catch (error) {
    logAndNoticeError(error as Error, "应用示例失败");
  }
};

// 监听 visible 变化，初始化 Cron 表达式
watch(
  () => props.visible,
  newVal => {
    internalVisible.value = newVal;
    if (newVal) {
      if (props.initialCron) {
        parseCronExpression(props.initialCron, cronBuilder.value);
      } else {
        resetCronBuilder(cronBuilder.value);
      }
      updateCronExpression();
    }
  },
  { immediate: true }
);

// 监听 initialCron 变化
watch(
  () => props.initialCron,
  newVal => {
    if (props.visible && newVal) {
      parseCronExpression(newVal, cronBuilder.value);
      updateCronExpression();
    }
  }
);

// 监听 internalVisible 变化
watch(internalVisible, newVal => {
  if (newVal !== props.visible) {
    emit("update:visible", newVal);
  }
});
</script>
