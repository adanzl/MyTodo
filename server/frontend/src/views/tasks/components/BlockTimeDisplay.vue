<template>
  <template v-if="slots.length">
    <el-tooltip placement="top" :disabled="slots.length <= 1">
      <template #content>
        <div>{{ typeLabel }}</div>
        <div v-for="(slot, index) in slots" :key="index">
          {{ blockSlotText(slot) }}
        </div>
      </template>
      <div class="flex items-center gap-1 py-1">
        <el-tag size="small" :type="typeTag">{{ typeShortLabel }}</el-tag>
        <TimeRange :model-value="slots[0]" readonly />
        <el-tag
          v-if="slots.length > 1"
          class="text-xs text-gray-500 shrink-0"
          size="small"
          type="info"
        >
          +{{ slots.length - 1 }}
        </el-tag>
      </div>
    </el-tooltip>
  </template>
  <span v-else class="text-gray-400">-</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  getCommonBlockTimeSlots,
  parseBlockTimeConfig,
  type TaskBlockTimeConfig,
  type TaskBlockTimeSlot,
} from "@/api/api-task";
import { formatWeekdaysShort } from "@/utils/date";
import TimeRange from "./TimeRange.vue";

const props = defineProps<{
  blockTime?: TaskBlockTimeConfig | string;
}>();

const slots = computed(() => getCommonBlockTimeSlots(props.blockTime));
const typeLabel = computed(() =>
  parseBlockTimeConfig(props.blockTime).type === "whitelist" ? "白名单" : "黑名单",
);
const typeShortLabel = computed(() => typeLabel.value.charAt(0));
const typeTag = computed(() =>
  parseBlockTimeConfig(props.blockTime).type === "whitelist" ? "success" : "warning",
);

const blockSlotText = (slot: TaskBlockTimeSlot) => {
  const weekday = formatWeekdaysShort(slot.weekdays);
  const time = `${slot.start.slice(0, 5)} - ${slot.end.slice(0, 5)}`;
  return weekday ? `${weekday} ${time}` : time;
};
</script>
