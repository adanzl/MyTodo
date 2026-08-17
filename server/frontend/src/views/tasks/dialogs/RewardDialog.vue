<template>
  <el-dialog v-model="visible" title="全勤奖励" width="480px" align-center @open="loadConfig">
    <div v-loading="loading" class="flex flex-col gap-4 min-h-30">
      <el-text type="info" size="small" class="block w-full text-left">
        活动期内，当天所有每日任务（非持续）完成后发放额外星星。持续任务不计入。
      </el-text>
      <el-form label-width="96px">
        <el-form-item label="奖励星星">
          <el-input-number v-model="form.reward" :min="0" :max="10000" :step="1" class="w-40" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="w-48" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" class="w-48" />
        </el-form-item>
      </el-form>
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
import { getTaskRewardConfig, setTaskRewardConfig, type TaskRewardConfig } from "@/api/api-task";

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
const form = ref<TaskRewardConfig>({ reward: 0, start_date: "", end_date: "" });

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
    form.value = await getTaskRewardConfig();
  } catch (error: any) {
    ElMessage.error(error.message || "加载全勤奖励失败");
    form.value = { reward: 0, start_date: "", end_date: "" };
  } finally {
    loading.value = false;
  }
};

const handleClose = () => {
  visible.value = false;
};

const handleSave = async () => {
  if (form.value.reward > 0 && (!form.value.start_date || !form.value.end_date)) {
    ElMessage.warning("请填写开始和结束日期");
    return;
  }
  if (form.value.start_date && form.value.end_date && form.value.start_date > form.value.end_date) {
    ElMessage.warning("开始日期不能晚于结束日期");
    return;
  }
  saving.value = true;
  try {
    await setTaskRewardConfig(form.value);
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
