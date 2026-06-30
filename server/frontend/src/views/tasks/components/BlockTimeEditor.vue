<template>
  <div class="flex flex-col gap-2 w-full min-w-0">
    <el-tabs v-model="activeTab" class="block-time-tabs">
      <el-tab-pane
        v-for="uid in visibleUserIds"
        :key="uid"
        :label="userLabel(uid)"
        :name="String(uid)"
      >
        <div class="flex flex-col gap-2 pt-1">
          <el-radio-group
            :model-value="getUserState(uid).type"
            @change="(val) => handleTypeChange(uid, val as 'blacklist' | 'whitelist')"
          >
            <el-radio value="blacklist">黑名单</el-radio>
            <el-radio value="whitelist">白名单</el-radio>
          </el-radio-group>
          <div class="flex flex-wrap gap-2 w-full items-center">
            <TimeRange
              v-for="(_, index) in getUserState(uid).slots"
              :key="index"
              v-model="getUserState(uid).slots[index]"
              @remove="removeSlot(uid, index)"
            />
            <el-button type="primary" link @click="addSlot(uid)" :icon="Plus" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { Plus } from "@element-plus/icons-vue";
import { computed, nextTick, ref, watch } from "vue";
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

const props = withDefaults(
  defineProps<{
    modelValue?: BlockTimeConfig | string;
    userIds?: number[];
  }>(),
  {
    userIds: () => [BLOCK_TIME_USER_CANCAN, BLOCK_TIME_USER_ZHAOZHAO],
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: BlockTimeConfig): void;
}>();

const visibleUserIds = computed(() =>
  props.userIds.filter((id) => id === BLOCK_TIME_USER_CANCAN || id === BLOCK_TIME_USER_ZHAOZHAO),
);

const activeTab = ref(String(visibleUserIds.value[0] ?? BLOCK_TIME_USER_CANCAN));
const userStates = ref<Record<number, UserBlockState>>({});
const syncingFromProps = ref(false);

const userLabel = (uid: number) => (uid === BLOCK_TIME_USER_CANCAN ? "灿灿" : "昭昭");

const getUserState = (uid: number): UserBlockState => {
  if (!userStates.value[uid]) {
    userStates.value[uid] = { type: "blacklist", slots: [] };
  }
  return userStates.value[uid];
};

const buildConfig = (): BlockTimeConfig => {
  let config: BlockTimeConfig = {};
  for (const uid of visibleUserIds.value) {
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
  for (const uid of visibleUserIds.value) {
    const entry = getBlockTimeEntry(parsed, uid);
    next[uid] = {
      type: entry?.type ?? "blacklist",
      slots: entry ? [...getBlockTimeSlots(entry)] : [],
    };
  }
  userStates.value = next;
  if (!visibleUserIds.value.some((id) => String(id) === activeTab.value)) {
    activeTab.value = String(visibleUserIds.value[0] ?? BLOCK_TIME_USER_CANCAN);
  }
  nextTick(() => {
    syncingFromProps.value = false;
  });
};

const handleTypeChange = (uid: number, newType: "blacklist" | "whitelist") => {
  const state = getUserState(uid);
  if (state.type === newType) return;
  state.type = newType;
  flushToConfig();
};

const addSlot = (uid: number) => {
  getUserState(uid).slots.push({ start: "00:00:00", end: "08:00:00" });
  flushToConfig();
};

const removeSlot = (uid: number, index: number) => {
  getUserState(uid).slots.splice(index, 1);
  flushToConfig();
};

watch(
  () => props.modelValue,
  (val) => loadFromConfig(val),
  { immediate: true },
);

watch(visibleUserIds, () => loadFromConfig(props.modelValue), { deep: true });

watch(userStates, () => flushToConfig(), { deep: true });
</script>

<style scoped>
.block-time-tabs :deep(.el-tabs__header) {
  margin-bottom: 4px;
}
</style>
