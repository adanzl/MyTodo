<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑日程' : '添加日程'"
    width="600px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="标题" prop="title">
        <el-input v-model="formData.title" placeholder="请输入标题" />
      </el-form-item>

      <el-form-item label="开始时间" prop="startTs">
        <el-date-picker
          v-model="formData.startTs"
          type="date"
          placeholder="选择开始日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="结束时间" prop="endTs">
        <el-date-picker
          v-model="formData.endTs"
          type="date"
          placeholder="选择结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="重复频率" prop="repeat">
        <el-select v-model="formData.repeat" placeholder="选择重复频率" style="width: 100%">
          <el-option label="无" value="0" />
          <el-option label="每天" value="1" />
          <el-option label="每星期" value="2" />
          <el-option label="每月" value="3" />
          <el-option label="每年" value="4" />
          <el-option label="工作日" value="5" />
          <el-option label="每周末" value="6" />
          <el-option label="自定义" value="999" />
        </el-select>
      </el-form-item>

      <el-form-item label="重复结束" prop="repeatEndTs" v-if="formData.repeat && formData.repeat !== '0'">
        <el-date-picker
          v-model="formData.repeatEndTs"
          type="date"
          placeholder="选择重复结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="全天" prop="allDay">
        <el-switch v-model="formData.allDay" />
      </el-form-item>

      <el-form-item label="分数" prop="score">
        <el-input-number v-model="formData.score" :min="0" :max="100" style="width: 100%" />
      </el-form-item>

      <el-form-item label="子任务">
        <div class="w-full">
          <div v-for="(subtask, index) in (formData.subtasks || [])" :key="index" class="flex justify-between items-center p-2 mb-1 bg-gray-50 rounded">
            <span>{{ subtask.name || subtask.title }}</span>
            <el-button
              type="danger"
              size="small"
              @click="removeSubtask(index)"
              link
            >
              删除
            </el-button>
          </div>
          <el-button
            type="primary"
            size="small"
            @click="addSubtask"
            plain
          >
            + 添加子任务
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import dayjs from 'dayjs';
import { updateTodo, createTodo } from '@/api/api-todo';
import type { ScheduleData } from '@/api/api-todo';

const props = defineProps<{
  visible: boolean;
  todoData: ScheduleData | null;
  isEdit?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'success'): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const isEdit = computed(() => props.isEdit ?? false);

const formRef = ref<FormInstance>();
const submitting = ref(false);

const formData = ref<Partial<ScheduleData>>({
  id: 0,
  title: '',
  startTs: '',
  endTs: '',
  repeat: '0',
  repeatEndTs: '',
  allDay: false,
  score: 0,
  subtasks: [],
});

const rules: FormRules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  startTs: [
    { required: true, message: '请选择开始时间', trigger: 'change' }
  ],
  endTs: [
    { required: true, message: '请选择结束时间', trigger: 'change' }
  ]
};

// 监听 todoData 变化，填充表单
watch(() => props.todoData, (newData) => {
  console.log('TodoDialog received data:', newData);
  if (newData && isEdit.value) {
    console.log('Subtasks:', newData.subtasks);
    formData.value = {
      id: newData.id,
      title: newData.title,
      startTs: newData.startTs,
      endTs: newData.endTs,
      repeat: String(newData.repeat) || '0',
      repeatEndTs: newData.repeatEndTs,
      allDay: newData.allDay || false,
      score: newData.score || 0,
      subtasks: newData.subtasks || [],
    };
  } else if (!isEdit.value) {
    // 添加模式，重置表单
    formData.value = {
      id: 0,
      title: '',
      startTs: dayjs().format('YYYY-MM-DD'),
      endTs: dayjs().format('YYYY-MM-DD'),
      repeat: '0',
      repeatEndTs: '',
      allDay: false,
      score: 0,
      subtasks: [],
    };
  }
}, { immediate: true });

const addSubtask = () => {
  const name = prompt('请输入子任务名称：');
  if (name && name.trim()) {
    if (!formData.value.subtasks) {
      formData.value.subtasks = [];
    }
    formData.value.subtasks.push({
      id: Date.now(),
      name: name.trim()
    });
  }
};

const removeSubtask = (index: number) => {
  if (formData.value.subtasks) {
    formData.value.subtasks.splice(index, 1);
  }
};

const handleClose = () => {
  emit('update:visible', false);
  formRef.value?.resetFields();
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    submitting.value = true;

    if (isEdit.value && formData.value.id) {
      await updateTodo(formData.value.id, formData.value);
      ElMessage.success('更新成功');
    } else {
      await createTodo(formData.value);
      ElMessage.success('添加成功');
    }

    emit('success');
    handleClose();
  } catch (err) {
    if (err !== false) {
      console.error('操作失败:', err);
      ElMessage.error(isEdit.value ? '更新失败' : '添加失败');
    }
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped></style>
