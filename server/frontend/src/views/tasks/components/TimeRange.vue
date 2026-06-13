<template>
  <div class="flex items-center gap-2 text-sm">
    <el-tag
      size="small"
      type="info"
      :closable="!readonly"
      :class="{ 'cursor-pointer': !readonly }"
      @click="!readonly && openDialog()"
      @close="emit('remove')"
    >
      <span v-if="weekdayLabel" class="mr-1">{{ weekdayLabel }}</span>
      {{ model.start.slice(0, 5) }} - {{ model.end.slice(0, 5) }}
    </el-tag>

    <el-dialog v-if="!readonly" v-model="visible" title="编辑时段" width="480px" append-to-body align-center>
      <el-form label-width="72px">
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="draft.start"
            format="HH:mm"
            value-format="HH:mm:ss"
            placeholder="选择开始时间"
            class="w-full!"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="draft.end"
            format="HH:mm"
            value-format="HH:mm:ss"
            placeholder="选择结束时间"
            class="w-full!"
          />
        </el-form-item>
        <el-form-item label="限定周几">
          <el-checkbox-group v-model="draftWeekdays">
            <el-checkbox v-for="w in WEEKDAYS" :key="w.value" :value="w.value">{{ w.label }}</el-checkbox>
          </el-checkbox-group>
          <div class="text-xs text-gray-400 mt-1">不选表示每天都生效</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="confirm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { TaskBlockTimeSlot } from "@/api/api-task";
import { formatWeekdaysShort } from "@/utils/date";

defineProps<{ readonly?: boolean }>();

const model = defineModel<TaskBlockTimeSlot>({ required: true });
const emit = defineEmits<{ remove: [] }>();

const WEEKDAYS = [
  { value: 0, label: "周日" },
  { value: 1, label: "周一" },
  { value: 2, label: "周二" },
  { value: 3, label: "周三" },
  { value: 4, label: "周四" },
  { value: 5, label: "周五" },
  { value: 6, label: "周六" },
] as const;

const visible = ref(false);
const draft = reactive<Pick<TaskBlockTimeSlot, "start" | "end">>({ start: "00:00:00", end: "08:00:00" });
const draftWeekdays = ref<number[]>([]);

const weekdayLabel = computed(() => formatWeekdaysShort(model.value.weekdays));

const openDialog = () => {
  draft.start = model.value.start;
  draft.end = model.value.end;
  draftWeekdays.value = [...(model.value.weekdays ?? [])];
  visible.value = true;
};

const confirm = () => {
  if (!draft.start || !draft.end || draft.start >= draft.end) {
    ElMessage.warning("结束时间必须晚于开始时间");
    return;
  }
  const next: TaskBlockTimeSlot = { start: draft.start, end: draft.end };
  if (draftWeekdays.value.length > 0 && draftWeekdays.value.length < 7) {
    next.weekdays = [...draftWeekdays.value].sort((a, b) => a - b);
  }
  model.value = next;
  visible.value = false;
};
</script>
