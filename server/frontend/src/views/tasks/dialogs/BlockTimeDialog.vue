<template>
  <el-dialog v-model="visible" title="全局禁用时段" width="560px" align-center @open="loadConfig">
    <div v-loading="loading" class="flex flex-col gap-3 min-h-[120px]">
      <el-text type="info" size="small" class="block w-full text-left">
        <p>对所有任务生效；与任务级禁用时段取并集。</p>
        <p>黑名单：时段内禁止打卡；</p>
        <p>白名单：仅允许时段内打卡。</p>
      </el-text>
      <el-radio-group v-model="blockTimeType" @change="handleBlockTimeTypeChange">
        <el-radio value="blacklist">黑名单</el-radio>
        <el-radio value="whitelist">白名单</el-radio>
      </el-radio-group>
      <div class="flex gap-2 w-full items-center flex-wrap">
        <TimeRange
          v-for="(_, index) in blockTimes"
          :key="index"
          v-model="blockTimes[index]"
          @remove="blockTimes.splice(index, 1)"
        />
        <el-button type="primary" link @click="addBlockTime" :icon="Plus" />
      </div>
    </div>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { Plus } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { ref, watch } from "vue";
import {
  buildBlockTimeConfig,
  getCommonBlockTimeSlots,
  getGlobalBlockTime,
  parseBlockTimeConfig,
  setGlobalBlockTime,
  type TaskBlockTimeConfig,
  type TaskBlockTimeSlot,
} from "@/api/api-task";
import TimeRange from "../components/TimeRange.vue";

interface Props {
  modelValue: boolean;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(props.modelValue);
const loading = ref(false);
const saving = ref(false);
const blockTimeType = ref<"blacklist" | "whitelist">("blacklist");
const blockTimeConfig = ref<TaskBlockTimeConfig>({
  type: "blacklist",
  blacklist: [],
  whitelist: [],
});
const blockTimes = ref<TaskBlockTimeSlot[]>([]);

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
  },
);

watch(visible, (val) => {
  emit("update:modelValue", val);
});

const resetForm = () => {
  blockTimeType.value = "blacklist";
  blockTimeConfig.value = { type: "blacklist", blacklist: [], whitelist: [] };
  blockTimes.value = [];
};

const applyBlockTimesToConfig = (type: "blacklist" | "whitelist") => {
  const config = buildBlockTimeConfig(type, blockTimes.value);
  blockTimeConfig.value = config;
};

const handleBlockTimeTypeChange = (newType: "blacklist" | "whitelist") => {
  if (blockTimeType.value === newType) return;
  applyBlockTimesToConfig(blockTimeType.value);
  blockTimeType.value = newType;
  blockTimeConfig.value.type = newType;
  blockTimes.value = getCommonBlockTimeSlots(blockTimeConfig.value);
};

const addBlockTime = () => {
  blockTimes.value.push({ start: "00:00:00", end: "08:00:00" });
};

const loadConfig = async () => {
  loading.value = true;
  try {
    const config = await getGlobalBlockTime();
    blockTimeConfig.value = parseBlockTimeConfig(config);
    blockTimeType.value = blockTimeConfig.value.type;
    blockTimes.value = getCommonBlockTimeSlots(blockTimeConfig.value);
  } catch (error: any) {
    ElMessage.error(error.message || "加载全局禁用时段失败");
    resetForm();
  } finally {
    loading.value = false;
  }
};

const handleClose = () => {
  visible.value = false;
};

const handleSave = async () => {
  saving.value = true;
  try {
    const config = buildBlockTimeConfig(blockTimeType.value, blockTimes.value);
    await setGlobalBlockTime(config);
    ElMessage.success("保存成功");
    emit("success");
    handleClose();
  } catch (error: any) {
    ElMessage.error(error.message || "保存失败");
  } finally {
    saving.value = false;
  }
};
</script>
