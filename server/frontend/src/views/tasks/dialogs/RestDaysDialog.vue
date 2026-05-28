<template>
  <el-dialog
    v-model="visible"
    title="维护休息日"
    width="720px"
    align-center
    @close="handleCancel"
  >
    <div class="flex flex-col gap-4">
      <div class="text-xs text-gray-500">
        规则：命中 <span class="font-medium">补班</span> 则强制工作；否则命中周几/指定休即为休息日（休息日不计入任务天数）
      </div>

      <el-form label-width="110px">
        <el-form-item label="每周">
          <el-checkbox-group v-model="draftWeekdays">
            <el-checkbox v-for="w in WEEKDAYS" :key="w.value" :value="w.value">{{ w.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="特定休息日">
          <el-date-picker
            v-model="draftDates"
            type="dates"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            placeholder="选择休息日（可多选）"
            class="w-full"
          />
          <div class="mt-2 ml-3 w-full">
            <div class="max-h-22 overflow-auto min-h-6">
              <div class="flex flex-wrap gap-1">
                <el-tag
                  v-for="d in sortedDraftDates"
                  :key="d"
                  size="small"
                  closable
                  class="h-5 leading-5"
                  @close="removeDraftDate(d)"
                >
                  {{ d }}
                </el-tag>
                <el-tag
                  v-if="sortedDraftDates.length === 0"
                  size="small"
                  type="info"
                  class="h-5 leading-5 pr-[22px] inline-flex items-center justify-center"
                >
                  未选择
                </el-tag>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="补班">
          <el-date-picker
            v-model="draftWorkDates"
            type="dates"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            placeholder="选择补班日（可多选）"
            class="w-full"
          />
          <div class="mt-2 ml-3 w-full">
            <div class="max-h-22 overflow-auto min-h-6">
              <div class="flex flex-wrap gap-1">
                <el-tag
                  v-for="d in sortedDraftWorkDates"
                  :key="d"
                  size="small"
                  type="warning"
                  closable
                  class="h-5 leading-5"
                  @close="removeDraftWorkDate(d)"
                >
                  {{ d }}
                </el-tag>
                <el-tag
                  v-if="sortedDraftWorkDates.length === 0"
                  size="small"
                  type="info"
                  class="h-5 leading-5 pr-[22px] inline-flex items-center justify-center"
                >
                  未选择
                </el-tag>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button plain @click="handleClear">清空</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { formatRestDaysFullText, parseRestDays, type RestDaysRule } from "@/utils/date";

interface Props {
  modelValue: boolean;
  restDays?: unknown;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "update:restDays", value: RestDaysRule): void;
  (e: "update:summary", value: string): void;
  /** 点击确定并关闭后触发，用于刷新父级工作日历展示 */
  (e: "confirmed", value: RestDaysRule): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit("update:modelValue", v),
});

const draftWeekdays = ref<number[]>([]);
const draftDates = ref<string[]>([]);
const draftWorkDates = ref<string[]>([]);

const sortedDraftDates = computed(() => [...new Set(draftDates.value)].slice().sort());
const sortedDraftWorkDates = computed(() => [...new Set(draftWorkDates.value)].slice().sort());

const removeDraftDate = (d: string) => {
  draftDates.value = draftDates.value.filter((x) => x !== d);
};

const removeDraftWorkDate = (d: string) => {
  draftWorkDates.value = draftWorkDates.value.filter((x) => x !== d);
};

const WEEKDAYS = [
  { value: 0, label: "周日" },
  { value: 1, label: "周一" },
  { value: 2, label: "周二" },
  { value: 3, label: "周三" },
  { value: 4, label: "周四" },
  { value: 5, label: "周五" },
  { value: 6, label: "周六" },
] as const;

const buildSummary = (rule: Required<RestDaysRule>) => formatRestDaysFullText(rule);

const syncFromProps = () => {
  const rule = parseRestDays(props.restDays);
  draftWeekdays.value = [...rule.weekdays];
  draftDates.value = [...rule.dates];
  draftWorkDates.value = [...rule.work_dates];
  emit("update:summary", buildSummary(rule));
};

watch(
  () => props.modelValue,
  (open) => {
    if (open) syncFromProps();
  },
  { immediate: false }
);

watch(() => props.restDays, () => {
  // 外部直接清空/初始化 restDays 时，同步摘要（不要求弹窗打开）
  const rule = parseRestDays(props.restDays);
  emit("update:summary", buildSummary(rule));
});

const handleCancel = () => {
  visible.value = false;
};

const handleClear = () => {
  draftWeekdays.value = [];
  draftDates.value = [];
  draftWorkDates.value = [];
  emit("update:summary", "");
};

const handleConfirm = () => {
  const next: RestDaysRule = {
    weekdays: Array.from(new Set(draftWeekdays.value)).sort((a, b) => a - b),
    dates: Array.from(new Set(draftDates.value)).sort(),
    work_dates: Array.from(new Set(draftWorkDates.value)).sort(),
  };
  emit("update:restDays", next);
  emit("update:summary", buildSummary(parseRestDays(next)));
  visible.value = false;
  emit("confirmed", next);
};
</script>

