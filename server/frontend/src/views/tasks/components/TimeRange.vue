<template>
  <div class="flex items-center gap-2 text-sm">
    <el-tag
      size="small"
      type="info"
      :closable="!readonly"
      :class="{ 'cursor-pointer': !readonly }"
      @click="!readonly && openDialog()"
      @close="emit('remove')"
    >
      {{ model.start.slice(0, 5) }} - {{ model.end.slice(0, 5) }}
    </el-tag>

    <el-dialog v-if="!readonly" v-model="visible" title="编辑时段" width="360px" append-to-body align-center>
      <el-form label-width="72px">
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="draft.start"
            format="HH:mm"
            value-format="HH:mm:ss"
            placeholder="选择开始时间"
            class="w-full!"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="draft.end"
            format="HH:mm"
            value-format="HH:mm:ss"
            placeholder="选择结束时间"
            class="w-full!"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="confirm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { TaskBlockTimeSlot } from "@/api/api-task";

defineProps<{ readonly?: boolean }>();

const model = defineModel<TaskBlockTimeSlot>({ required: true });
const emit = defineEmits<{ remove: [] }>();

const visible = ref(false);
const draft = reactive<TaskBlockTimeSlot>({ start: "00:00:00", end: "08:00:00" });

const openDialog = () => {
  draft.start = model.value.start;
  draft.end = model.value.end;
  visible.value = true;
};

const confirm = () => {
  if (!draft.start || !draft.end || draft.start >= draft.end) {
    ElMessage.warning("结束时间必须晚于开始时间");
    return;
  }
  model.value = { start: draft.start, end: draft.end };
  visible.value = false;
};
</script>
