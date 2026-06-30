<template>
  <template v-if="segments.length">
    <div class="flex flex-col gap-1 py-1 min-w-0">
      <div
        v-for="seg in segments"
        :key="seg.userId"
        class="flex flex-wrap items-center gap-1 min-w-0"
      >
        <el-tag size="small" type="info" class="shrink-0">{{ seg.label }}</el-tag>
        <el-tag size="small" :type="seg.typeTag" class="shrink-0">{{ seg.typeShort }}</el-tag>
        <TimeRange
          v-for="(slot, index) in seg.slots"
          :key="index"
          :model-value="slot"
          readonly
        />
      </div>
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
} from "@/api/api-task";
import TimeRange from "./TimeRange.vue";

const props = defineProps<{
  blockTime?: BlockTimeConfig | string;
}>();

const USER_META = [
  { id: BLOCK_TIME_USER_CANCAN, label: "灿灿" },
  { id: BLOCK_TIME_USER_ZHAOZHAO, label: "昭昭" },
] as const;

const segments = computed(() => {
  const config = parseBlockTimeConfig(props.blockTime);
  return USER_META.map(({ id, label }) => {
    const entry = getBlockTimeEntry(config, id);
    const slots = getBlockTimeSlots(entry);
    if (!slots.length) return null;
    const isWhitelist = entry!.type === "whitelist";
    return {
      userId: id,
      label,
      slots,
      typeShort: isWhitelist ? "白" : "黑",
      typeTag: isWhitelist ? ("success" as const) : ("warning" as const),
    };
  }).filter(Boolean) as Array<{
    userId: number;
    label: string;
    slots: ReturnType<typeof getBlockTimeSlots>;
    typeShort: string;
    typeTag: "success" | "warning";
  }>;
});
</script>
