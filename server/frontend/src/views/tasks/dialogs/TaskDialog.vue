<template>
  <el-dialog v-model="visible" :title="isEdit ? '编辑任务' : '新建任务'" width="1200px" align-center @close="handleClose">
    <div class="max-h-[90vh] overflow-y-auto overflow-x-hidden flex flex-col gap-4">
      <!-- 上区域：任务信息 -->
      <div class="task-info-section p-2 border rounded">
        <el-form :model="formData" label-width="100px">
          <!-- 第一行:名称、优先级、对象 -->
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="任务名称" required>
                <el-input v-model="formData.name" placeholder="请输入任务名称" class="w-70!" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="优先级">
                <el-input-number v-model="formData.priority" :min="0" :max="10" :step="1" class="w-30!" size="small"
                  placeholder="数字越小优先级越高" />
                <el-tooltip content="数字越小优先级越高，高优先级任务没有完成低优先级任务会锁定" placement="bottom">
                  <el-icon class="ml-2">
                    <WarningFilled />
                  </el-icon>
                </el-tooltip>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="布置对象" required>
                <el-checkbox-group v-model="selectedUsers">
                  <el-checkbox :value="3">灿灿</el-checkbox>
                  <el-checkbox :value="4">昭昭</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 第二行：开始日期、总天数 -->
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="开始日期" required>
                <el-date-picker v-model="formData.start_date" type="date" placeholder="选择开始日期" format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD" class="w-68!" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="总天数" required>
                <el-input-number v-model="formData.duration" :min="1" :max="365" class="w-10" size="small" />
                <span class="ml-2 text-xs text-gray-600">到 {{ endDateStr }} 结束</span>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="任务类型" required>
                <el-radio-group v-model="formData.type">
                  <el-radio :value="0">每日任务</el-radio>
                  <el-radio :value="1">持续任务</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 第三行：前置日程 -->
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="前置日程">
                <div class="flex gap-4 items-center w-full">
                  <el-tooltip content="完成了每天的规定日程才能开始当前任务" placement="bottom">
                    <el-icon class="">
                      <WarningFilled />
                    </el-icon>
                  </el-tooltip>
                  <!-- 灿灿日程 -->
                  <div class="flex items-center gap-1 w-[40%]">
                    <span class="w-10 text-sm text-gray-600">灿灿:</span>
                    <el-select :disabled="!selectedUsers.includes(3)" v-model="preTodoCancan" multiple filterable
                      clearable placeholder="请选择灿灿的前置日程" class="flex-1" collapse-tags collapse-tags-tooltip
                      :max-collapse-tags="3">
                      <el-option v-for="todo in cancanTodos" :key="'cancan_' + todo.id" :label="todo.title"
                        :value="todo.id" />
                    </el-select>
                  </div>
                  <!-- 昭昭日程 -->
                  <div class="flex items-center gap-1 w-[40%]">
                    <span class="w-10 text-sm text-gray-600">昭昭:</span>
                    <el-select :disabled="!selectedUsers.includes(4)" v-model="preTodoZhaozhao" multiple filterable
                      clearable placeholder="请选择昭昭的前置日程" class="flex-1" collapse-tags collapse-tags-tooltip
                      :max-collapse-tags="3">
                      <el-option v-for="todo in zhaozhaoTodos" :key="'zhaozhao_' + todo.id" :label="todo.title"
                        :value="todo.id" />
                    </el-select>
                  </div>

                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>

      <!-- 下区域：打卡活动配置 -->
      <div class="checkin-section border rounded">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">打卡活动配置</h3>
          <div class="flex items-center gap-4">
            <!-- 每日分数配置 -->
            <span>{{ formData.type === 1 ? '完成奖励' : `第${selectedDay + 1}天星星` }}</span>
            <el-input-number v-if="formData.type === 1" v-model="dailyScore[0]" :min="0" :max="1000" :step="1"
              placeholder="'奖励'" class="w-36" size="small" :disabled="getAllMaterials().length === 0" />
            <el-input-number v-else-if="selectedDay !== -1" v-model="dailyScore[selectedDay]" :min="0" :max="1000"
              :step="1" :placeholder="'奖励'" class="w-36" size="small"
              :disabled="getDayMaterials(selectedDay).length === 0" />
            <el-button type="primary" size="small" @click="showMaterialSelector = true">
              <el-icon class="mr-1">
                <Plus />
              </el-icon>
              添加素材
            </el-button>
            <el-button type="success" size="small" @click="showQuickAdd = true">
              <el-icon class="mr-1">
                <Plus />
              </el-icon>
              快速添加
            </el-button>
          </div>
        </div>

        <div class="checkin-content flex" style="height: 400px;">
          <!-- 左侧：天数列表（仅每日任务显示） -->
          <div v-if="formData.type === 0" class="day-list w-48 border-r overflow-y-auto">
            <div v-for="dayIndex in Array.from({ length: formData.duration || 1 }, (_, i) => i)" :key="dayIndex"
              class="p-3 cursor-pointer hover:bg-gray-100 transition-all duration-200"
              :class="{ 'bg-blue-50 border-l-4 border-blue-500': selectedDay === dayIndex }"
              @click="selectedDay = dayIndex">
              <div class="font-medium">第{{ dayIndex + 1 }}天 <span class="text-[12px] ml-1">{{ getDayDate(dayIndex)
                  }}</span></div>
              <div class="text-xs text-gray-500 mt-1 flex justify-between">
                <div>{{ getDayMaterialCount(dayIndex) }} 个素材</div>
                <div v-if="isToday(dayIndex)">今</div>
              </div>
            </div>
          </div>

          <!-- 右侧：素材内容 -->
          <div class="material-content flex-1 p-4 overflow-y-auto">
            <!-- 持续任务：显示所有素材 -->
            <div v-if="formData.type === 1">
              <div v-if="getAllMaterials().length === 0" class="text-center text-gray-400 py-20">
                暂无素材，点击“添加素材”按钮添加
              </div>
              <div v-else class="space-y-2">
                <div v-for="(material, index) in getAllMaterials()" :key="index"
                  class="material-item p-3 border rounded flex items-center justify-between hover:bg-gray-50 transition-all duration-200">
                  <div class="flex-1">
                    <div class="font-medium">{{ material.name }}</div>
                    <div class="text-xs text-gray-500 mt-1 flex gap-3">
                      <div>类型：{{ getMaterialTypeName(material.type) }}</div>
                      <div>ID：{{ material.id }}</div>
                    </div>
                  </div>
                  <el-button size="small" type="danger" link @click="removeMaterialFromAll(index)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
            <!-- 每日任务：按天显示 -->
            <div v-else>
              <div v-if="selectedDay === -1" class="text-center text-gray-400 py-20">
                请选择左侧的天数
              </div>
              <div v-else>
                <div v-if="getDayMaterials(selectedDay).length === 0" class="text-center text-gray-400 py-20">
                  暂无素材，点击“添加素材”按钮添加
                </div>
                <div v-else class="space-y-2">
                  <div v-for="(material, index) in getDayMaterials(selectedDay)" :key="index"
                    class="material-item p-3 border rounded flex items-center justify-between hover:bg-gray-50 transition-all duration-200">
                    <div class="flex-1">
                      <div class="font-medium">{{ material.name }}</div>
                      <div class="text-xs text-gray-500 mt-1 flex gap-3">
                        <div>类型：{{ getMaterialTypeName(material.type) }}</div>
                        <div>ID：{{ material.id }}</div>
                      </div>
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
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
    </template>

    <!-- 素材选择器弹窗 -->
    <el-dialog v-model="showMaterialSelector" title="选择素材" width="1100px" append-to-body align-center>
      <div v-loading="materialLoading" element-loading-text="加载中..." style="min-height: 500px;">
        <div class="flex gap-4" style="height: 500px;">
          <!-- 左侧：类别选择 -->
          <div class="w-58 border rounded p-3 overflow-y-auto">
            <el-tree ref="categoryTreeRef" :data="cascaderOptions" :props="treeProps" node-key="id" :indent="10"
              @node-click="handleTreeSelect" highlight-current accordion>
              <template #default="{ node, data }">
                <div class="flex items-center justify-between w-full pr-2">
                  <el-tooltip :content="node.label" placement="top" :disabled="node.label.length <= 10">
                    <span class="truncate max-w-32">{{ node.label }}</span>
                  </el-tooltip>
                  <el-tag size="small" type="primary" v-if="getMaterialCategorySelectedCount(data.id) > 0">
                    {{ getMaterialCategorySelectedCount(data.id) }}
                  </el-tag>
                </div>
              </template>
            </el-tree>
          </div>

          <!-- 右侧：素材列表 -->
          <div class="flex-1 border rounded overflow-hidden">
            <el-table v-if="!materialLoading" ref="materialTableRef" :data="materialList"
              @selection-change="handleMaterialSelectionChange" @row-click="handleRowClick" height="100%">
              <el-table-column type="selection" width="40" />
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="name" label="素材名称" min-width="200" />
              <el-table-column prop="type" label="类型" width="80">
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

    <!-- 快速添加弹窗 -->
    <QuickAdd v-model="showQuickAdd" :form-data="formData" @allocated="handleQuickAddAllocated" />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Plus, WarningFilled } from "@element-plus/icons-vue";
import { addTask, updateTask, getMaterialList, getMaterialCategoryList, type Task, type Material, type MaterialCategory } from "@/api/api-task";
import { getTodoListByTime } from "@/api/api-todo";
import { sortByName } from "@/utils/file";
import dayjs from "dayjs";
import QuickAdd from "./QuickAdd.vue";

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
const selectedDay = ref<number>(-1);
const showMaterialSelector = ref(false);
const showQuickAdd = ref(false);
const materialLoading = ref(false);
const materialList = ref<Material[]>([]);
const selectedMaterials = ref<Material[]>([]);
const categoryList = ref<MaterialCategory[]>([]);
const selectedCategoryId = ref<number | undefined>(undefined);
const materialTableRef = ref();
const categoryTreeRef = ref();

// 前置日程相关
const preTodoZhaozhao = ref<number[]>([]); // 昭昭的前置日程ID列表
const preTodoCancan = ref<number[]>([]); // 灿灿的前置日程ID列表
const zhaozhaoTodos = ref<Array<{ id: number; title: string }>>([]);
const cancanTodos = ref<Array<{ id: number; title: string }>>([]);

// 缓存每个类别的选中数量（key: categoryId, value: count）
const materialCategorySelectedCountCache = ref<Map<number, number>>(new Map());

// 是否正在恢复选中状态（用于防止循环触发事件）
const isRestoringMaterialSelection = ref(false);

// Tree 配置
const treeProps = {
  label: 'name',
  children: 'children',
};

// 构建树形结构
const buildCascaderOptions = (categories: MaterialCategory[]) => {
  const map = new Map<number, any>();
  const roots: any[] = [];

  categories.forEach(item => {
    map.set(item.id, { ...item, children: [] });
  });

  categories.forEach(item => {
    const node = map.get(item.id);
    if (node) {
      const parentId = item.parent ?? -1;
      if (parentId === -1) {
        roots.push(node);
      } else {
        const parent = map.get(parentId);
        if (parent) {
          if (!parent.children) {
            parent.children = [];
          }
          parent.children.push(node);
        }
      }
    }
  });

  return roots;
};

// 计算级联选项
const cascaderOptions = computed(() => {
  return buildCascaderOptions(categoryList.value);
});

/**
 * 获取某类别已选中的素材数量（带缓存）
 */
const getMaterialCategorySelectedCount = (categoryId: number) => {
  // 先从缓存中获取
  if (materialCategorySelectedCountCache.value.has(categoryId)) {
    return materialCategorySelectedCountCache.value.get(categoryId) || 0;
  }

  // 缓存中没有，计算并缓存
  const categoryMaterialIds = materialList.value
    .filter(m => m.cate_id === categoryId)
    .map(m => m.id);

  const count = selectedMaterials.value.filter(m => categoryMaterialIds.includes(m.id)).length;
  materialCategorySelectedCountCache.value.set(categoryId, count);
  return count;
};

// 树节点点击事件
const handleTreeSelect = (data: any) => {
  selectedCategoryId.value = data.id;
};

// 每日素材数据：{ dayNumber: [materials] }
const dailyMaterials = ref<Record<number, Array<{ id: number; name: string; type: number }>>>({});
// 每日分数数据：{ dayNumber: score }
const dailyScore = ref<Record<number, number>>({});

const formData = ref<Partial<Task>>({
  name: "",
  start_date: dayjs().format('YYYY-MM-DD'),
  duration: 1,
  user_id: "",
  status: 1,
  type: 0,
  priority: 0,
});

// 计算结束日期
const endDateStr = computed(() => {
  if (!formData.value.start_date || !formData.value.duration) return '';
  return dayjs(formData.value.start_date).add((formData.value.duration || 1) - 1, 'day').format('MM月DD日');
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
        type: Number(newData.type) ?? 0,
        priority: newData.priority ?? 0,
      };

      // 解析 user_id，如果是多个用户用逗号分隔
      if (newData.user_id) {
        const userIds = String(newData.user_id).split(",").map(Number);
        selectedUsers.value = userIds.filter((id) => [3, 4].includes(id));
      } else {
        selectedUsers.value = [];
      }

      // 初始化前置日程ID
      if (newData.pre_todo) {
        try {
          const preTodoData = typeof newData.pre_todo === 'string' ? JSON.parse(newData.pre_todo) : newData.pre_todo;
          preTodoZhaozhao.value = Array.isArray(preTodoData['4']) ? preTodoData['4'] : [];
          preTodoCancan.value = Array.isArray(preTodoData['3']) ? preTodoData['3'] : [];
        } catch (e) {
          console.error('解析前置日程数据失败:', e);
          preTodoZhaozhao.value = [];
          preTodoCancan.value = [];
        }
      } else {
        preTodoZhaozhao.value = [];
        preTodoCancan.value = [];
      }

      // 初始化每日素材数据和每日分数
      if (newData.data) {
        try {
          const parsedData = typeof newData.data === 'string' ? JSON.parse(newData.data) : newData.data;
          dailyMaterials.value = parsedData.dailyMaterials || {};
          dailyScore.value = parsedData.dailyScore || {};
        } catch (e) {
          console.error('解析任务数据失败:', e);
          dailyMaterials.value = {};
          dailyScore.value = {};
        }
      } else {
        dailyMaterials.value = {};
        dailyScore.value = {};
      }

      // 默认选中第一天
      selectedDay.value = 0;
    } else {
      // 新建模式，初始化空数据
      dailyMaterials.value = {};
      dailyScore.value = {};
      preTodoZhaozhao.value = [];
      preTodoCancan.value = [];
      // 默认选中第一天
      selectedDay.value = 0;
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

// 监听 duration 变化，确保选中第一天
watch(
  () => formData.value.duration,
  (newDuration) => {
    if (newDuration && newDuration > 0) {
      selectedDay.value = 0;
    }
  }
);

// 监听 type 变化，持续任务时默认选中第0天
watch(
  () => formData.value.type,
  (newType) => {
    if (newType === 1) {
      // 持续任务：选中第0天
      selectedDay.value = 0;
    } else if (newType === 0) {
      // 每日任务：选中第0天
      selectedDay.value = 0;
    }
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
    start_date: dayjs().format('YYYY-MM-DD'),
    duration: 1,
    user_id: "",
    status: 1,
    priority: 0,
  };
  selectedUsers.value = [];
  selectedDay.value = -1;
  dailyMaterials.value = {};
  dailyScore.value = {};
  preTodoZhaozhao.value = [];
  preTodoCancan.value = [];
};

// 获取某天的素材列表
const getDayMaterials = (day: number) => {
  return dailyMaterials.value[day] || [];
};

// 获取某天的素材数量
const getDayMaterialCount = (day: number) => {
  return getDayMaterials(day).length;
};

// 获取某天的具体日期
const getDayDate = (dayIndex: number) => {
  if (!formData.value.start_date) return '';
  return dayjs(formData.value.start_date).add(dayIndex, 'day').format('MM月DD日');
};

// 判断是否是今天
const isToday = (dayIndex: number) => {
  if (!formData.value.start_date) return false;
  const dayDate = dayjs(formData.value.start_date).add(dayIndex, 'day').format('YYYY-MM-DD');
  return dayDate === dayjs().format('YYYY-MM-DD');
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

// 获取所有素材（持续任务用）
const getAllMaterials = () => {
  // 持续任务只返回第0天的素材
  return dailyMaterials.value[0] || [];
};

// 从所有素材中删除（持续任务用）
const removeMaterialFromAll = (index: number) => {
  const allMaterials = getAllMaterials();
  if (index >= 0 && index < allMaterials.length) {
    const materialToRemove = allMaterials[index];
    // 找到并删除该素材
    for (const day in dailyMaterials.value) {
      const materials = dailyMaterials.value[Number(day)];
      const matIndex = materials.findIndex(
        (m) => m.id === materialToRemove.id && m.name === materialToRemove.name
      );
      if (matIndex !== -1) {
        materials.splice(matIndex, 1);
        break;
      }
    }
  }
};

// 加载目录列表
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
    console.error("获取目录列表失败:", error);
  }
};

// 加载日程列表
const loadTodoList = async () => {
  try {
    // 清空现有数据
    zhaozhaoTodos.value = [];
    cancanTodos.value = [];

    // 使用任务的开始和结束时间作为范围
    if (!formData.value.start_date || !formData.value.duration) {
      return;
    }

    const startDate = formData.value.start_date;
    const endDate = dayjs(startDate).add(formData.value.duration - 1, 'day').format('YYYY-MM-DD');

    // 根据选中的用户加载对应的日程
    if (selectedUsers.value.includes(4)) {
      // 昭昭 (user_id=4)
      const result = await getTodoListByTime(startDate, endDate, 4);
      zhaozhaoTodos.value = (result.data || []).map((todo: any) => ({
        id: todo.id,
        title: todo.title
      }));
    }

    if (selectedUsers.value.includes(3)) {
      // 灿灿 (user_id=3)
      const result = await getTodoListByTime(startDate, endDate, 3);
      cancanTodos.value = (result.data || []).map((todo: any) => ({
        id: todo.id,
        title: todo.title
      }));
    }
  } catch (error: any) {
    console.error("获取日程列表失败:", error);
  }
};

// 加载素材列表
const loadMaterialList = async () => {
  materialLoading.value = true;
  try {
    const res = await getMaterialList(selectedCategoryId.value, 1, 1000);
    if (res.code === 0 && res.data) {
      let materials = res.data.data || [];

      // 排序：按名称自然排序
      sortByName(materials);

      materialList.value = materials;

      // 重新计算当前类别的选中数量缓存
      if (selectedCategoryId.value !== undefined) {
        const categoryMaterialIds = materialList.value
          .filter(m => m.cate_id === selectedCategoryId.value)
          .map(m => m.id);
        const count = selectedMaterials.value.filter(m => categoryMaterialIds.includes(m.id)).length;
        materialCategorySelectedCountCache.value.set(selectedCategoryId.value, count);
      }
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取素材列表失败");
  } finally {
    materialLoading.value = false;

    // loading 结束后恢复勾选状态
    await nextTick();
    if (materialTableRef.value) {
      // 设置标志位，防止触发 selection-change 事件
      isRestoringMaterialSelection.value = true;

      // 先清空表格的所有选中
      materialTableRef.value.clearSelection();

      // 收集需要恢复的行
      const rowsToRestore = materialList.value.filter(row =>
        selectedMaterials.value.some(m => m.id === row.id)
      );

      // 批量恢复选中
      rowsToRestore.forEach(row => {
        materialTableRef.value.toggleRowSelection(row, true);
      });

      // 恢复标志位
      isRestoringMaterialSelection.value = false;
    }
  }
};

// 监听目录变化，重新加载素材
watch(selectedCategoryId, () => {
  if (showMaterialSelector.value) {
    loadMaterialList();
  }
});

// 监听用户选择变化，重新加载日程列表
watch(selectedUsers, () => {
  if (visible.value) {
    loadTodoList();
  }
});

watch(showMaterialSelector, async (newVal) => {
  if (newVal) {
    await loadCategoryList();
    await loadMaterialList();
    // 自动选中当前天数已添加的素材
    await nextTick();
    const currentMaterials = formData.value.type === 1 ? getAllMaterials() : getDayMaterials(selectedDay.value);
    const materialIds = new Set(currentMaterials.map((m) => m.id));

    // 使用表格的 toggleRowSelection 方法设置勾选状态
    materialList.value.forEach((row) => {
      if (row.id && materialIds.has(row.id)) {
        materialTableRef.value?.toggleRowSelection(row, true);
      }
    });

    // 确保 el-tree 正确高亮显示选中的节点
    await nextTick();
    if (selectedCategoryId.value !== undefined && categoryTreeRef.value) {
      categoryTreeRef.value.setCurrentKey(selectedCategoryId.value);
    }
  }
});

// 组件挂载时加载日程列表
onMounted(() => {
  loadTodoList();
});

const handleMaterialSelectionChange = (selection: Material[]) => {
  if (isRestoringMaterialSelection.value) return;

  const currentIds = new Set(materialList.value.map(m => m.id));
  selectedMaterials.value = [
    ...selectedMaterials.value.filter(m => !currentIds.has(m.id)),
    ...selection
  ];

  Array.from(materialCategorySelectedCountCache.value.keys()).forEach(catId => {
    if (materialList.value.some(m => m.cate_id === catId)) {
      const count = materialList.value
        .filter(m => m.cate_id === catId && selectedMaterials.value.some(sm => sm.id === m.id))
        .length;
      materialCategorySelectedCountCache.value.set(catId, count);
    }
  });
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

  // 持续任务：添加到第0天
  const targetDay = formData.value.type === 1 ? 0 : selectedDay.value;

  // 将选中的素材添加到目标天数
  if (!dailyMaterials.value[targetDay]) {
    dailyMaterials.value[targetDay] = [];
  }

  let addedCount = 0;
  selectedMaterials.value.forEach((material) => {
    // 检查是否已存在
    const exists = dailyMaterials.value[targetDay].some(
      (m) => m.id === material.id
    );

    if (!exists) {
      dailyMaterials.value[targetDay].push({
        id: material.id!,
        name: material.name,
        type: material.type,
      });
      addedCount++;
    }
  });

  if (addedCount > 0) {
    ElMessage.success(`已添加 ${addedCount} 个素材`);
  } else {
    ElMessage.warning("所选素材已全部存在");
  }

  showMaterialSelector.value = false;
  selectedMaterials.value = [];
  materialCategorySelectedCountCache.value.clear();
};

// 处理快速添加分配
const handleQuickAddAllocated = (
  materials: Array<{ id: number; name: string; type: number }>,
  startDay: number,
  endDay: number,
  allocationType: number
) => {
  // 根据分配类型进行分配
  switch (allocationType) {
    case 0: // 平均分配
      allocateMaterialsEvenly(materials, startDay, endDay);
      break;
    case 1: // 循环分配
      allocateMaterialsCircularly(materials, startDay, endDay);
      break;
    case 2: // 全部添加到每一天
      allocateMaterialsToAllDays(materials, startDay, endDay);
      break;
    default:
      ElMessage.warning("未知的分配类型");
  }
};

// 平均分配素材
const allocateMaterialsEvenly = (
  materials: Array<{ id: number; name: string; type: number }>,
  startDay: number,
  endDay: number
) => {
  const totalDays = endDay - startDay + 1;
  const materialsPerDay = Math.floor(materials.length / totalDays);
  const remainingMaterials = materials.length % totalDays;

  let materialIndex = 0;
  for (let day = startDay; day <= endDay; day++) {
    // 转换为内部索引（从0开始）
    const internalDay = day - 1;
    if (!dailyMaterials.value[internalDay]) {
      dailyMaterials.value[internalDay] = [];
    }

    // 计算当天应该分配的素材数量
    const countForThisDay = materialsPerDay + (day - startDay < remainingMaterials ? 1 : 0);

    for (let i = 0; i < countForThisDay && materialIndex < materials.length; i++) {
      const material = materials[materialIndex];
      // 检查是否已存在
      const exists = dailyMaterials.value[internalDay].some(
        (m) => m.id === material.id
      );

      if (!exists) {
        dailyMaterials.value[internalDay].push({
          id: material.id,
          name: material.name,
          type: material.type,
        });
      }
      materialIndex++;
    }
  }

  ElMessage.success(`已平均分配 ${materials.length} 个素材到 ${totalDays} 天`);
};

// 循环分配素材
const allocateMaterialsCircularly = (
  materials: Array<{ id: number; name: string; type: number }>,
  startDay: number,
  endDay: number
) => {
  const totalDays = endDay - startDay + 1;

  for (let i = 0; i < materials.length; i++) {
    // 转换为内部索引（从0开始）
    const day = startDay + (i % totalDays);
    const internalDay = day - 1;
    if (!dailyMaterials.value[internalDay]) {
      dailyMaterials.value[internalDay] = [];
    }

    const material = materials[i];
    // 检查是否已存在
    const exists = dailyMaterials.value[internalDay].some(
      (m) => m.id === material.id
    );

    if (!exists) {
      dailyMaterials.value[internalDay].push({
        id: material.id,
        name: material.name,
        type: material.type,
      });
    }
  }

  ElMessage.success(`已循环分配 ${materials.length} 个素材到 ${totalDays} 天`);
};

// 将所有素材添加到每一天
const allocateMaterialsToAllDays = (
  materials: Array<{ id: number; name: string; type: number }>,
  startDay: number,
  endDay: number
) => {
  for (let day = startDay; day <= endDay; day++) {
    // 转换为内部索引（从0开始）
    const internalDay = day - 1;
    if (!dailyMaterials.value[internalDay]) {
      dailyMaterials.value[internalDay] = [];
    }

    materials.forEach((material) => {
      // 检查是否已存在
      const exists = dailyMaterials.value[internalDay].some(
        (m) => m.id === material.id
      );

      if (!exists) {
        dailyMaterials.value[internalDay].push({
          id: material.id,
          name: material.name,
          type: material.type,
        });
      }
    });
  }

  const totalDays = endDay - startDay + 1;
  ElMessage.success(`已将 ${materials.length} 个素材添加到 ${totalDays} 天`);
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

    // 计算结束日期
    const endDateStr = dayjs(formData.value.start_date).add((formData.value.duration || 1) - 1, 'day').format('YYYY-MM-DD');

    // 构建任务数据,确保所有必需字段都有值
    const preTodoData: Record<string, number[]> = {};
    if (preTodoZhaozhao.value.length > 0) {
      preTodoData['4'] = preTodoZhaozhao.value;
    }
    if (preTodoCancan.value.length > 0) {
      preTodoData['3'] = preTodoCancan.value;
    }

    const taskData: Omit<Task, "id"> = {
      name: formData.value.name || "",
      start_date: formData.value.start_date || "",
      end_date: endDateStr,
      duration: formData.value.duration || 1,
      user_id: userIdStr,
      type: formData.value.type ?? 0,
      status: formData.value.status ?? 1,
      priority: formData.value.priority ?? 1,
      pre_todo: Object.keys(preTodoData).length > 0 ? JSON.stringify(preTodoData) : undefined,
      data: JSON.stringify({
        dailyMaterials: dailyMaterials.value,
        dailyScore: dailyScore.value,
      }),
    };


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
