<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="1200px"
    align-center
    @close="handleClose"
  >
    <div class="max-h-[90vh] overflow-y-auto overflow-x-hidden flex flex-col gap-4">
      <!-- 上区域：任务信息 -->
      <div class="task-info-section p-2 border rounded">
        <el-form :model="formData" label-width="100px">
          <!-- 第一行：名称、状态、对象 -->
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="任务名称" required>
                <el-input v-model="formData.name" placeholder="请输入任务名称" class="w-70!" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="状态">
                <el-select v-model="formData.status" placeholder="请选择状态" class="w-30!">
                  <el-option label="未开启" :value="-1" />
                  <el-option label="未开始" :value="0" />
                  <el-option label="进行中" :value="1" />
                  <el-option label="已结束" :value="2" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="布置对象" required>
                <el-checkbox-group v-model="selectedUsers">
                  <el-checkbox :label="3">灿灿</el-checkbox>
                  <el-checkbox :label="4">昭昭</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 第二行：开始日期、总天数 -->
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="开始日期" required>
                <el-date-picker
                  v-model="formData.start_date"
                  type="date"
                  placeholder="选择开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  class="w-68!"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="总天数" required>
                <el-input-number v-model="formData.duration" :min="1" :max="365" class="w-10" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>

      <!-- 下区域：打卡活动配置 -->
      <div class="checkin-section border rounded">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">打卡活动配置</h3>
          <el-button type="primary" size="small" @click="showMaterialSelector = true">
            <el-icon><Plus /></el-icon>
            添加素材
          </el-button>
        </div>

        <div class="checkin-content flex" style="height: 400px;">
          <!-- 左侧：天数列表 -->
          <div class="day-list w-48 border-r overflow-y-auto">
            <div
              v-for="day in formData.duration || 1"
              :key="day"
              class="p-3 cursor-pointer hover:bg-gray-100 transition-all duration-200"
              :class="{ 'bg-blue-50 border-l-4 border-blue-500': selectedDay === day }"
              @click="selectedDay = day"
            >
              <div class="font-medium">第{{ day }}天</div>
              <div class="text-xs text-gray-500 mt-1">
                {{ getDayMaterialCount(day) }} 个素材
              </div>
            </div>
          </div>

          <!-- 右侧：素材内容 -->
          <div class="material-content flex-1 p-4 overflow-y-auto">
            <div v-if="!selectedDay" class="text-center text-gray-400 py-20">
              请选择左侧的天数
            </div>
            <div v-else>
              <div v-if="getDayMaterials(selectedDay).length === 0" class="text-center text-gray-400 py-20">
                暂无素材，点击“添加素材”按钮添加
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="(material, index) in getDayMaterials(selectedDay)"
                  :key="index"
                  class="material-item p-3 border rounded flex items-center justify-between hover:bg-gray-50 transition-all duration-200"
                >
                  <div class="flex-1">
                    <div class="font-medium">{{ material.name }}</div>
                    <div class="text-xs text-gray-500 mt-1">类型：{{ getMaterialTypeName(material.type) }}</div>
                  </div>
                  <el-button size="small" type="danger" link @click="removeMaterial(selectedDay, index)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
    </template>

    <!-- 素材选择器弹窗 -->
    <el-dialog
      v-model="showMaterialSelector"
      title="选择素材"
      width="900px"
      append-to-body
      align-center
    >
      <div v-loading="materialLoading" element-loading-text="加载中..." style="min-height: 500px;">
        <div class="flex gap-4" style="height: 500px;">
        <!-- 左侧：类别列表 -->
        <div class="w-48 border rounded overflow-y-auto">
          <div
            v-for="cat in categoryList"
            :key="cat.id"
            class="p-3 cursor-pointer hover:bg-gray-100 transition-all duration-200"
            :class="{ 'bg-blue-50 border-l-4 border-blue-500': selectedCategoryId === cat.id }"
            @click="selectedCategoryId = cat.id"
          >
            <div class="font-medium">{{ cat.name }}</div>
          </div>
        </div>

        <!-- 右侧：素材列表 -->
        <div class="flex-1 border rounded overflow-hidden">
          <el-table
            ref="materialTableRef"
            :data="materialList"
            @selection-change="handleMaterialSelectionChange"
            @row-click="handleRowClick"
            max-height="460"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="name" label="素材名称" min-width="200" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                {{ getMaterialTypeName(row.type) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      </div>
      <template #footer>
        <el-button @click="showMaterialSelector = false">取消</el-button>
        <el-button type="primary" @click="confirmAddMaterials">确定添加</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import { addTask, updateTask, getMaterialList, getMaterialCategoryList, type Task, type Material, type MaterialCategory } from "@/api/api-task";

interface Props {
  modelValue: boolean;
  isEdit?: boolean;
  taskData?: Partial<Task>;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
}

const props = withDefaults(defineProps<Props>(), {
  isEdit: false,
  taskData: () => ({}),
});

const emit = defineEmits<Emits>();

const visible = ref(props.modelValue);
const submitting = ref(false);
const selectedUsers = ref<number[]>([]);
const selectedDay = ref<number>(1);
const showMaterialSelector = ref(false);
const materialLoading = ref(false);
const materialList = ref<Material[]>([]);
const selectedMaterials = ref<Material[]>([]);
const categoryList = ref<MaterialCategory[]>([]);
const selectedCategoryId = ref<number | undefined>(undefined);
const materialTableRef = ref();

// 每日素材数据：{ dayNumber: [materials] }
const dailyMaterials = ref<Record<number, Array<{ id: number; name: string; type: number }>>>({});

const formData = ref<Partial<Task>>({
  name: "",
  start_date: new Date().toISOString().split("T")[0],
  duration: 1,
  user_id: "",
  status: 1,
});

// 监听外部传入的 taskData
watch(
  () => props.taskData,
  (newData) => {
    if (newData && Object.keys(newData).length > 0) {
      formData.value = {
        name: newData.name || "",
        start_date: newData.start_date || "",
        duration: newData.duration || 1,
        user_id: newData.user_id || "",
        status: newData.status ?? 1,
      };

      // 解析 user_id，如果是多个用户用逗号分隔
      if (newData.user_id) {
        const userIds = String(newData.user_id).split(",").map(Number);
        selectedUsers.value = userIds.filter((id) => [3, 4].includes(id));
      } else {
        selectedUsers.value = [];
      }

      // 初始化每日素材数据
      if (newData.data) {
        try {
          const parsedData = typeof newData.data === 'string' ? JSON.parse(newData.data) : newData.data;
          dailyMaterials.value = parsedData.dailyMaterials || {};
        } catch (e) {
          console.error('解析任务数据失败:', e);
          dailyMaterials.value = {};
        }
      } else {
        dailyMaterials.value = {};
      }
    } else {
      // 新建模式，初始化空数据
      dailyMaterials.value = {};
    }
  },
  { immediate: true, deep: true }
);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  (newVal) => {
    visible.value = newVal;
  }
);

// 监听 visible 变化
watch(visible, (newVal) => {
  emit("update:modelValue", newVal);
});

// 关闭对话框
const handleClose = () => {
  visible.value = false;
  resetForm();
};

// 重置表单
const resetForm = () => {
  formData.value = {
    name: "",
    start_date: new Date().toISOString().split("T")[0],
    duration: 1,
    user_id: "",
    status: 1,
  };
  selectedUsers.value = [];
  selectedDay.value = 1;
  dailyMaterials.value = {};
};

// 获取某天的素材列表
const getDayMaterials = (day: number) => {
  return dailyMaterials.value[day] || [];
};

// 获取某天的素材数量
const getDayMaterialCount = (day: number) => {
  return getDayMaterials(day).length;
};

// 获取素材类型名称
const getMaterialTypeName = (type: number) => {
  const typeMap: Record<number, string> = {
    0: "PDF",
    1: "视频",
    2: "音频",
  };
  return typeMap[type] || "未知_" + type;
};

// 删除素材
const removeMaterial = (day: number, index: number) => {
  const materials = dailyMaterials.value[day];
  if (materials) {
    materials.splice(index, 1);
  }
};

// 加载分类列表
const loadCategoryList = async () => {
  materialLoading.value = true;
  try {
    const res = await getMaterialCategoryList(1, 1000);
    if (res.code === 0 && res.data) {
      categoryList.value = res.data.data || [];
      // 默认选中第一个类别
      if (categoryList.value.length > 0) {
        selectedCategoryId.value = categoryList.value[0].id;
      }
    }
  } catch (error: any) {
    console.error("获取分类列表失败:", error);
  }
};

// 加载素材列表
const loadMaterialList = async () => {
  materialLoading.value = true;
  try {
    const res = await getMaterialList(selectedCategoryId.value, 1, 1000);
    if (res.code === 0 && res.data) {
      materialList.value = res.data.data || [];
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取素材列表失败");
  } finally {
    materialLoading.value = false;
  }
};

// 监听分类变化，重新加载素材
watch(selectedCategoryId, () => {
  if (showMaterialSelector.value) {
    loadMaterialList();
  }
});
watch(showMaterialSelector, async (newVal) => {
  if (newVal) {
    await loadCategoryList();
    await loadMaterialList();
    // 自动选中当前天数已添加的素材
    await nextTick();
    const currentMaterials = getDayMaterials(selectedDay.value);
    const materialIds = new Set(currentMaterials.map((m) => m.id));

    // 使用表格的 toggleRowSelection 方法设置勾选状态
    materialList.value.forEach((row) => {
      if (row.id && materialIds.has(row.id)) {
        materialTableRef.value?.toggleRowSelection(row, true);
      }
    });
  }
});

// 素材选择变化
const handleMaterialSelectionChange = (selection: Material[]) => {
  selectedMaterials.value = selection;
};

// 行点击事件
const handleRowClick = (row: Material) => {
  // PDF类型：单选逻辑
  if (row.type === 1) {
    materialTableRef.value?.clearSelection();
    materialTableRef.value?.toggleRowSelection(row, true);
  } else {
    // 非PDF类型：切换选中状态
    materialTableRef.value?.toggleRowSelection(row);
  }
};

// 确认添加素材
const confirmAddMaterials = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning("请至少选择一个素材");
    return;
  }

  // 将选中的素材添加到当前选中的天数
  if (!dailyMaterials.value[selectedDay.value]) {
    dailyMaterials.value[selectedDay.value] = [];
  }

  selectedMaterials.value.forEach((material) => {
    dailyMaterials.value[selectedDay.value].push({
      id: material.id!,
      name: material.name,
      type: material.type,
    });
  });

  ElMessage.success(`已添加 ${selectedMaterials.value.length} 个素材`);
  showMaterialSelector.value = false;
  selectedMaterials.value = [];
};

// 提交表单
const handleSubmit = async () => {
  if (!formData.value.name) {
    ElMessage.warning("请填写任务名称");
    return;
  }
  if (!formData.value.start_date) {
    ElMessage.warning("请选择开始日期");
    return;
  }

  submitting.value = true;
  try {
    // 将选中的用户ID转换为字符串存储
    const userIdStr = selectedUsers.value.join(",");

    // 构建任务数据，确保所有必需字段都有值
    const taskData: Omit<Task, "id"> = {
      name: formData.value.name || "",
      start_date: formData.value.start_date || "",
      duration: formData.value.duration || 1,
      user_id: userIdStr,
      status: formData.value.status ?? 1,
      data: JSON.stringify({
        dailyMaterials: dailyMaterials.value,
      }),
    };

    console.log("提交任务数据:", taskData);

    if (props.isEdit && props.taskData?.id) {
      await updateTask({
        id: props.taskData.id,
        ...taskData,
      } as Task);
      ElMessage.success("更新成功");
    } else {
      await addTask(taskData as Omit<Task, "id">);
      ElMessage.success("添加成功");
    }

    emit("success");
    handleClose();
  } catch (error: any) {
    ElMessage.error(error.message || "操作失败");
  } finally {
    submitting.value = false;
  }
};
</script>
