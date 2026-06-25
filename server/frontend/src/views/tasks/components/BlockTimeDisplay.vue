<template>
  <template v-if="slots.length">
    <div class="flex flex-wrap items-center gap-1 py-1 min-w-0">
      <el-tag size="small" :type="typeTag" class="shrink-0">{{ typeShortLabel }}</el-tag>
      <TimeRange
        v-for="(slot, index) in slots"
        :key="index"
        :model-value="slot"
        readonly
      />
    </div>
  </template>
  <span v-else class="text-gray-400">-</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  getCommonBlockTimeSlots,
  parseBlockTimeConfig,
  type TaskBlockTimeConfig,
} from "@/api/api-task";
import TimeRange from "./TimeRange.vue";

const props = defineProps<{
  blockTime?: TaskBlockTimeConfig | string;
}>();

const slots = computed(() => getCommonBlockTimeSlots(props.blockTime));
const typeShortLabel = computed(() =>
  (parseBlockTimeConfig(props.blockTime).type === "whitelist" ? "白名单" : "黑名单").charAt(0),
);
const typeTag = computed(() =>
  parseBlockTimeConfig(props.blockTime).type === "whitelist" ? "success" : "warning",
);
</script>
