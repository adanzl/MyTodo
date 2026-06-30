<template>
  <el-dialog v-model="visible" title="全局禁用时段" width="600px" align-center @open="loadConfig">
    <div v-loading="loading" class="flex flex-col gap-3 min-h-[120px]">
      <el-text type="info" size="small" class="block w-full text-left">
        <p>按人配置，与任务级禁用时段取并集。</p>
        <p>黑名单：时段内禁止打卡；白名单：仅允许时段内打卡。</p>
      </el-text>
      <BlockTimeEditor v-model="blockTimeConfig" />
    </div>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { ref, watch } from "vue";
import {
  getGlobalBlockTime,
  setGlobalBlockTime,
  type BlockTimeConfig,
} from "@/api/api-task";
import BlockTimeEditor from "../components/BlockTimeEditor.vue";

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
const blockTimeConfig = ref<BlockTimeConfig>({});

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
  },
);

watch(visible, (val) => {
  emit("update:modelValue", val);
});

const loadConfig = async () => {
  loading.value = true;
  try {
    blockTimeConfig.value = await getGlobalBlockTime();
  } catch (error: any) {
    ElMessage.error(error.message || "加载全局禁用时段失败");
    blockTimeConfig.value = {};
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
    await setGlobalBlockTime(blockTimeConfig.value);
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
