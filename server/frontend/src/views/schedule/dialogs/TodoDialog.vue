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
          class="w-full!"
        />
      </el-form-item>

      <el-form-item label="结束时间" prop="endTs">
        <el-date-picker
          v-model="formData.endTs"
          type="date"
          placeholder="选择结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="w-full!"
        />
      </el-form-item>

      <el-form-item label="重复频率" prop="repeat">
        <el-select v-model="formData.repeat" placeholder="选择重复频率" class="w-full!">
          <el-option label="无" value="0" />
          <el-option label="每天" value="1" />
          <el-option label="每星期" value="2" />
          <el-option label="每月" value="3" />
          <el-option label="每年" value="4" />
          <el-option label="工作日" value="5" />
          <el-option label="每周末" value="6" />
          <el-option label="自定义" :value="String(CUSTOM_REPEAT_ID)" />
        </el-select>
      </el-form-item>

      <el-form-item
        v-if="isCustomRepeat"
        label="自定义日期"
        prop="customWeekdays"
      >
        <div class="w-full">
          <el-checkbox-group v-model="customWeekdays" class="flex flex-wrap gap-x-3 gap-y-1">
            <el-checkbox
              v-for="(label, idx) in WEEK"
              :key="idx"
              :value="idx"
              :label="idx"
            >
              {{ label }}
            </el-checkbox>
          </el-checkbox-group>
          <p v-if="customWeekdays.length" class="mt-1 text-xs text-gray-400">
            {{ buildCustomRepeatLabel({ week: customWeekdays }) }}
          </p>
          <p v-else class="mt-1 text-xs text-gray-400">请选择自定义重复的日期</p>
        </div>
      </el-form-item>

      <el-form-item
        v-if="formData.repeat && formData.repeat !== '0'"
        label="重复结束"
        prop="repeatEndTs"
      >
        <el-date-picker
          v-model="formData.repeatEndTs"
          type="date"
          placeholder="选择重复结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="w-full!"
        />
      </el-form-item>

      <el-form-item label="全天" prop="allDay">
        <el-switch v-model="formData.allDay" />
      </el-form-item>

      <el-form-item label="分类" prop="groupId">
        <el-radio-group v-model="formData.groupId" size="small" class="flex flex-wrap">
          <el-radio-button
            v-for="op in GroupOptions"
            :key="op.id"
            :value="op.id"
          >
            {{ op.label }}
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="颜色" prop="color">
        <div class="flex flex-wrap gap-2 items-center">
          <button
            v-for="op in colorOptions"
            :key="op.id"
            type="button"
            class="w-8 h-8 rounded-full border-2 transition-transform hover:scale-110"
            :class="formData.color === op.id ? 'border-violet-600 scale-110' : 'border-gray-300'"
            :style="{ backgroundColor: op.color }"
            :title="op.name"
            @click="formData.color = op.id"
          />
          <span v-if="!colorOptions.length" class="text-xs text-gray-400">暂无颜色配置</span>
        </div>
      </el-form-item>

      <el-form-item label="分数" prop="score">
        <el-input-number v-model="formData.score" :min="0" :max="100" step="1" size="small"/>
      </el-form-item>

      <el-form-item label="优先级" prop="priority">
        <el-radio-group v-model="formData.priority" size="small" class="flex flex-wrap">
          <el-radio-button :value="0">Ⅰ</el-radio-button>
          <el-radio-button :value="1">Ⅱ</el-radio-button>
          <el-radio-button :value="2">Ⅲ</el-radio-button>
          <el-radio-button :value="3">Ⅳ</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="子任务">
        <div class="w-full">
          <div
            v-for="(subtask, index) in formData.subtasks || []"
            :key="index"
            class="flex items-center gap-2 p-2 mb-1 bg-gray-50 rounded"
          >
            <el-input
              v-model="subtask.name"
              placeholder="请输入子任务名称"
              size="small"
            />
            <el-button type="danger" size="small" circle @click="removeSubtask(index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button type="primary" size="small" plain @click="addSubtask">
            + 添加子任务
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Delete } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import dayjs from "dayjs";
import { updateTodo, createTodo } from "@/api/api-todo";
import type { ScheduleData } from "@/api/api-todo";
import { getList } from "@/api/api-common";
import { WEEK, CUSTOM_REPEAT_ID, GroupOptions } from "@/constants/schedule";
import { buildCustomRepeatLabel } from "@/utils/schedule";

interface ColorItem {
  id: number;
  name?: string;
  color?: string;
}

const props = defineProps<{
  visible: boolean;
  todoData: ScheduleData | null;
  isEdit?: boolean;
  userId?: number;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "success"): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const isEdit = computed(() => props.isEdit ?? false);

const formRef = ref<FormInstance>();
const submitting = ref(false);
const customWeekdays = ref<number[]>([]);
const colorOptions = ref<ColorItem[]>([]);

const formData = ref<Partial<ScheduleData> & { repeat?: string | number }>({
  id: 0,
  title: "",
  startTs: "",
  endTs: "",
  repeat: "0",
  repeatData: { week: [] },
  repeatEndTs: "",
  allDay: false,
  score: 0,
  subtasks: [],
  userId: 0,
  color: 0,
  priority: -1,
  groupId: 0,
  order: 0,
  reminder: 0,
});

const isCustomRepeat = computed(
  () => Number(formData.value.repeat) === CUSTOM_REPEAT_ID
);

const normalizeGroupId = (groupId?: number) => {
  if (groupId === undefined || groupId === null || groupId < 0) return 0;
  return groupId;
};

const parseRepeatData = (raw: unknown): { week: number[] } => {
  if (!raw) return { week: [] };
  try {
    const data = typeof raw === "string" ? JSON.parse(raw) : raw;
    const week = Array.isArray((data as { week?: number[] })?.week)
      ? [...(data as { week: number[] }).week]
      : [];
    return { week };
  } catch {
    return { week: [] };
  }
};

const rules: FormRules = {
  title: [
    { required: true, message: "请输入标题", trigger: "blur" },
    { min: 1, max: 100, message: "长度在 1 到 100 个字符", trigger: "blur" },
  ],
  startTs: [{ required: true, message: "请选择开始时间", trigger: "change" }],
  endTs: [{ required: true, message: "请选择结束时间", trigger: "change" }],
};

const fetchColors = async () => {
  try {
    const response = await getList<ColorItem>("t_colors", undefined, 1, 100);
    colorOptions.value = response.data?.data || [];
  } catch (err) {
    console.error("获取颜色列表失败:", err);
    colorOptions.value = [];
  }
};

const resetForm = (userId?: number) => {
  formData.value = {
    id: 0,
    title: "",
    startTs: dayjs().format("YYYY-MM-DD"),
    endTs: dayjs().format("YYYY-MM-DD"),
    repeat: "0",
    repeatData: { week: [] },
    repeatEndTs: "",
    allDay: false,
    score: 0,
    subtasks: [],
    userId: userId ?? 0,
    color: colorOptions.value[0]?.id ?? 0,
    priority: 0,
    groupId: 0,
    order: 0,
    reminder: 0,
  };
  customWeekdays.value = [];
};

// 监听 todoData 变化，填充表单
watch(
  () => props.todoData,
  (newData) => {
    if (newData && isEdit.value) {
      const repeatData = parseRepeatData(newData.repeatData);
      formData.value = {
        id: newData.id,
        title: newData.title,
        startTs: newData.startTs,
        endTs: newData.endTs,
        repeat: String(newData.repeat ?? 0),
        repeatData,
        repeatEndTs: newData.repeatEndTs,
        allDay: newData.allDay || false,
        score: newData.score || 0,
        subtasks: newData.subtasks || [],
        userId: newData.userId,
        color: newData.color ?? 0,
        priority: newData.priority === -1 ? 0 : newData.priority || 0,
        groupId: normalizeGroupId(newData.groupId),
        order: newData.order || 0,
        reminder: newData.reminder || 0,
      };
      customWeekdays.value = [...repeatData.week];
    } else if (!isEdit.value) {
      resetForm(props.userId);
    }
  },
  { immediate: true }
);

// 打开弹窗时刷新颜色列表
watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      await fetchColors();
    }
  }
);

// 切换筛选用户时，同步到添加中的表单
watch(
  () => props.userId,
  (uid) => {
    if (!isEdit.value && uid != null) {
      formData.value.userId = uid;
    }
  }
);

// 自定义星期与 repeatData 双向同步
watch(customWeekdays, (days) => {
  formData.value.repeatData = { week: [...days].sort((a, b) => a - b) };
});

const addSubtask = () => {
  if (!formData.value.subtasks) {
    formData.value.subtasks = [];
  }
  formData.value.subtasks.push({
    id: Date.now(),
    name: "",
  });
};

const removeSubtask = (index: number) => {
  formData.value.subtasks?.splice(index, 1);
};

const handleClose = () => {
  emit("update:visible", false);
  formRef.value?.resetFields();
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();

    if (isCustomRepeat.value && customWeekdays.value.length === 0) {
      ElMessage.warning("请选择自定义重复的日期");
      return;
    }

    submitting.value = true;

    const submitData: Record<string, unknown> = {};
    Object.keys(formData.value).forEach((key) => {
      const value = (formData.value as Record<string, unknown>)[key];
      if (value !== undefined && value !== null) {
        submitData[key] = value;
      }
    });

    if (!isEdit.value) {
      submitData.userId = props.userId ?? formData.value.userId;
      if (!submitData.userId) {
        ElMessage.error("请先选择用户");
        return;
      }
    }

    submitData.repeat = Number(submitData.repeat);
    submitData.color = Number(submitData.color ?? 0);
    submitData.groupId = normalizeGroupId(Number(submitData.groupId));
    if (Number(submitData.repeat) === CUSTOM_REPEAT_ID) {
      submitData.repeatData = {
        week: [...customWeekdays.value].sort((a, b) => a - b),
      };
    } else {
      submitData.repeatData = formData.value.repeatData || {};
    }

    if (typeof submitData.allDay === "boolean") {
      submitData.allDay = submitData.allDay ? 1 : 0;
    }

    if (isEdit.value && formData.value.id) {
      await updateTodo(formData.value.id, submitData);
      ElMessage.success("更新成功");
    } else {
      await createTodo(submitData);
      ElMessage.success("添加成功");
    }

    emit("success");
    handleClose();
  } catch (err) {
    if (err !== false) {
      console.error("操作失败:", err);
      ElMessage.error(isEdit.value ? "更新失败" : "添加失败");
    }
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  fetchColors();
});
</script>
