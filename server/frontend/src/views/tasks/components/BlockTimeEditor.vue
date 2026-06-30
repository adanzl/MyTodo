<template>
  <div class="flex flex-col gap-3 w-full min-w-0">
    <div
      v-for="row in USER_ROWS"
      :key="row.id"
      class="flex items-center gap-3 w-full min-w-0"
      :class="{ 'opacity-60': isRowDisabled(row.id) }"
    >
      <div class="flex items-center gap-2 shrink-0 pt-0.5">
        <span class="w-10 text-sm text-gray-600">{{ row.label }}</span>
        <el-radio-group
          :model-value="getUserState(row.id).type"
          :disabled="isRowDisabled(row.id)"
          @change="(val: 'blacklist' | 'whitelist') => handleTypeChange(row.id, val)"
        >
          <el-radio value="blacklist">黑名单</el-radio>
          <el-radio value="whitelist">白名单</el-radio>
        </el-radio-group>
      </div>
      <div class="flex flex-wrap gap-2 flex-1 min-w-0 items-center">
        <TimeRange
          v-for="(_, index) in getUserState(row.id).slots"
          :key="index"
          v-model="getUserState(row.id).slots[index]"
          :readonly="isRowDisabled(row.id)"
          @remove="removeSlot(row.id, index)"
        />
        <el-button
          v-if="!isRowDisabled(row.id)"
          type="primary"
          link
          @click="addSlot(row.id)"
          :icon="Plus"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from "@element-plus/icons-vue";
import { nextTick, ref, watch } from "vue";
import {
  BLOCK_TIME_USER_CANCAN,
  BLOCK_TIME_USER_ZHAOZHAO,
  getBlockTimeEntry,
  getBlockTimeSlots,
  parseBlockTimeConfig,
  pruneBlockTimeConfig,
  setBlockTimeEntry,
  type BlockTimeConfig,
  type TaskBlockTimeSlot,
} from "@/api/api-task";
import TimeRange from "./TimeRange.vue";

interface UserBlockState {
  type: "blacklist" | "whitelist";
  slots: TaskBlockTimeSlot[];
}

const USER_ROWS = [
  { id: BLOCK_TIME_USER_CANCAN, label: "灿灿" },
  { id: BLOCK_TIME_USER_ZHAOZHAO, label: "昭昭" },
] as const;

const ALL_USER_IDS = USER_ROWS.map((r) => r.id);

const props = withDefaults(
  defineProps<{
    modelValue?: BlockTimeConfig | string;
    /** 已选布置对象；不在列表中的用户行 disable，但不隐藏 */
    userIds?: number[];
  }>(),
  {
    userIds: () => [BLOCK_TIME_USER_CANCAN, BLOCK_TIME_USER_ZHAOZHAO],
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: BlockTimeConfig): void;
}>();

const userStates = ref<Record<number, UserBlockState>>({});
const syncingFromProps = ref(false);

const isRowDisabled = (uid: number) => !props.userIds.includes(uid);

const getUserState = (uid: number): UserBlockState => {
  if (!userStates.value[uid]) {
    userStates.value[uid] = { type: "blacklist", slots: [] };
  }
  return userStates.value[uid];
};

const buildConfig = (): BlockTimeConfig => {
  let config: BlockTimeConfig = {};
  for (const uid of ALL_USER_IDS) {
    const state = userStates.value[uid];
    if (!state) continue;
    config = setBlockTimeEntry(config, uid, state.type, state.slots);
  }
  return pruneBlockTimeConfig(config);
};

const flushToConfig = () => {
  if (syncingFromProps.value) return;
  emit("update:modelValue", buildConfig());
};

const loadFromConfig = (config?: BlockTimeConfig | string) => {
  syncingFromProps.value = true;
  const parsed = parseBlockTimeConfig(config);
  const next: Record<number, UserBlockState> = {};
  for (const uid of ALL_USER_IDS) {
    const entry = getBlockTimeEntry(parsed, uid);
    next[uid] = {
      type: entry?.type ?? "blacklist",
      slots: entry ? [...getBlockTimeSlots(entry)] : [],
    };
  }
  userStates.value = next;
  nextTick(() => {
    syncingFromProps.value = false;
  });
};

const handleTypeChange = (uid: number, newType: "blacklist" | "whitelist") => {
  if (isRowDisabled(uid)) return;
  const state = getUserState(uid);
  if (state.type === newType) return;
  state.type = newType;
  flushToConfig();
};

const addSlot = (uid: number) => {
  if (isRowDisabled(uid)) return;
  getUserState(uid).slots.push({ start: "00:00:00", end: "08:00:00" });
  flushToConfig();
};

const removeSlot = (uid: number, index: number) => {
  if (isRowDisabled(uid)) return;
  getUserState(uid).slots.splice(index, 1);
  flushToConfig();
};

watch(
  () => props.modelValue,
  (val) => loadFromConfig(val),
  { immediate: true },
);

watch(userStates, () => flushToConfig(), { deep: true });
</script>
