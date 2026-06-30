<template>
  <template v-if="segments.length">
    <div :class="rootClass">
      <el-tooltip
        v-for="seg in segments"
        :key="seg.userId"
        placement="top"
        :disabled="!seg.showOverflow"
      >
        <template #content>
          <div>{{ seg.label }} · {{ seg.typeFull }}</div>
          <div v-for="(slot, index) in seg.slots" :key="index">
            {{ blockSlotText(slot) }}
          </div>
        </template>
        <div :class="rowClass">
          <el-tag size="small" type="info" class="shrink-0">{{ seg.label }}</el-tag>
          <el-tag size="small" :type="seg.typeTag" class="shrink-0">{{ seg.typeShort }}</el-tag>
          <TimeRange :model-value="seg.slots[0]" readonly />
          <el-tag
            v-if="seg.overflowCount > 0"
            class="text-xs text-gray-500 shrink-0 px-0"
            size="small"
            type="info"
          >
            +{{ seg.overflowCount }}
          </el-tag>
        </div>
      </el-tooltip>
    </div>
  </template>
  <span v-else class="text-gray-400">-</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  BLOCK_TIME_USER_CANCAN,
  BLOCK_TIME_USER_ZHAOZHAO,
  getBlockTimeEntry,
  getBlockTimeSlots,
  parseBlockTimeConfig,
  type BlockTimeConfig,
  type TaskBlockTimeSlot,
} from "@/api/api-task";
import { formatWeekdaysShort } from "@/utils/date";
import TimeRange from "./TimeRange.vue";

const props = withDefaults(
  defineProps<{
    blockTime?: BlockTimeConfig | string;
    /** true：每人一行；false：单行紧凑排列 */
    wrap?: boolean;
  }>(),
  {
    wrap: true,
  },
);

const USER_META = [
  { id: BLOCK_TIME_USER_CANCAN, label: "灿灿" },
  { id: BLOCK_TIME_USER_ZHAOZHAO, label: "昭昭" },
] as const;

const rootClass = computed(() =>
  props.wrap
    ? "flex flex-col gap-1 py-1 min-w-0"
    : "flex flex-row flex-nowrap items-center gap-2 py-1 min-w-0 overflow-hidden",
);

const rowClass = computed(() =>
  props.wrap
    ? "flex flex-wrap items-center gap-1 min-w-0"
    : "flex flex-nowrap items-center gap-1 shrink-0",
);

const blockSlotText = (slot: TaskBlockTimeSlot) => {
  const weekday = formatWeekdaysShort(slot.weekdays);
  const time = `${slot.start.slice(0, 5)} - ${slot.end.slice(0, 5)}`;
  return weekday ? `${weekday} ${time}` : time;
};

const segments = computed(() => {
  const config = parseBlockTimeConfig(props.blockTime);
  return USER_META.map(({ id, label }) => {
    const entry = getBlockTimeEntry(config, id);
    const slots = getBlockTimeSlots(entry);
    if (!slots.length) return null;
    const isWhitelist = entry!.type === "whitelist";
    const overflowCount = Math.max(0, slots.length - 1);
    return {
      userId: id,
      label,
      slots,
      typeShort: isWhitelist ? "白" : "黑",
      typeFull: isWhitelist ? "白名单" : "黑名单",
      typeTag: isWhitelist ? ("success" as const) : ("warning" as const),
      overflowCount,
      showOverflow: slots.length > 1,
    };
  }).filter(Boolean) as Array<{
    userId: number;
    label: string;
    slots: ReturnType<typeof getBlockTimeSlots>;
    typeShort: string;
    typeFull: string;
    typeTag: "success" | "warning";
    overflowCount: number;
    showOverflow: boolean;
  }>;
});
</script>
