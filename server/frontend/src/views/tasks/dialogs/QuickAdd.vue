<template>
  <el-dialog v-model="visible" title="快速添加素材" width="1000px" align-center @close="handleClose">
    <div class="flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
      <!-- 分配配置区 -->
      <div class="allocation-section border rounded p-4">
        <h3 class="font-semibold mb-3">分配配置</h3>
        <el-form label-width="120px">
          <el-row>
            <el-col :span="6">
              <el-form-item label="开始天数">
                <el-input-number v-model="startDay" :min="1" :max="formData.duration || 1" :step="1" size="small"
                  class="w-full" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="结束天数">
                <el-input-number v-model="endDay" :min="startDay" :max="formData.duration || 1" :step="1" size="small"
                  class="w-full" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="分配基数">
                <div class="flex items-center">
                  <el-checkbox v-model="useBatchSize" />
                  <el-input-number v-model="batchSize" :min="1" :max="10" :step="1" size="small" class="w-25! ml-2"
                    :disabled="!useBatchSize" />
                  <span class="ml-2 text-gray-600 text-xs" v-if="useBatchSize">每次分配 {{ batchSize }} 个素材</span>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="分配方式">
            <el-radio-group v-model="allocationType">
              <el-radio :value="0">平均分配</el-radio>
              <el-radio :value="1">循环分配</el-radio>
              <el-radio :value="2">全部添加到每一天</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item class="flex w-full">
            <div class="flex-1 text-gray-600">{{ descriptionText }}</div>
            <span class="mr-4 text-gray-600">已选中 {{ selectedMaterials.length }} 个素材</span>
            <el-button type="primary" @click="allocateMaterials" :disabled="selectedMaterials.length === 0">
              <el-icon class="mr-1">
                <Check />
              </el-icon>
              确认分配
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 素材选择区 -->
      <div class="material-selection-section border rounded p-4">
        <h3 class="font-semibold mb-3">选择素材</h3>
        <div v-loading="materialLoading" element-loading-text="加载中..." style="min-height: 300px;">
          <div class="flex gap-4" style="height: 400px;">
            <!-- 左侧：类别选择 -->
            <div class="w-60 border rounded p-1 overflow-y-auto">
              <el-tree :data="cascaderOptions" :props="treeProps" node-key="id" @node-click="handleTreeSelect"
                highlight-current accordion :indent="6">
                <template #default="{ node, data }">
                  <div class="flex items-center justify-between w-full pr-2">
                    <el-tooltip :content="node.label" placement="top" :disabled="node.label.length <= 10">
                      <span class="truncate max-w-32">{{ node.label }}</span>
                    </el-tooltip>
                    <el-tag size="small" type="primary" v-if="getCategorySelectedCount(data.id) > 0">
                      {{ getCategorySelectedCount(data.id) }}
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
                <el-table-column prop="name" label="素材名称" min-width="220" />
                <el-table-column prop="type" label="类型" width="80">
                  <template #default="{ row }">
                    {{ getMaterialTypeName(row.type) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { Check } from "@element-plus/icons-vue";
import { getMaterialList, getMaterialCategoryList, type Material, type MaterialCategory, type Task } from "@/api/api-task";
import { sortByName } from "@/utils/file";

// ==================== 类型定义 ====================
interface Props {
  modelValue: boolean;
  formData: Partial<Task>;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "allocated", materials: Array<{ id: number; name: string; type: number }>, startDay: number, endDay: number, allocationType: number): void;
}

// ==================== Props & Emits ====================
const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// ==================== 响应式数据 ====================
const visible = ref(props.modelValue);
const materialLoading = ref(false);
const materialList = ref<Material[]>([]);
const selectedMaterials = ref<Material[]>([]);
const categoryList = ref<MaterialCategory[]>([]);
const selectedCategoryId = ref<number | undefined>(undefined);
const materialTableRef = ref();

// 缓存每个类别的选中数量（key: categoryId, value: count）
const categorySelectedCountCache = ref<Map<number, number>>(new Map());

// 是否正在恢复选中状态（用于防止循环触发事件）
const isRestoringSelection = ref(false);

// 分配配置
const startDay = ref(1);
const endDay = ref(1);
const allocationType = ref(0); // 0: 平均分配, 1: 循环分配, 2: 全部添加到每一天
const useBatchSize = ref(false); // 是否启用分配基数
const batchSize = ref(1); // 分配基数：每次分配的素材数量

// ==================== Tree 配置 ====================
const treeProps = {
  label: 'name',
  children: 'children'
};

// ==================== 工具函数 ====================
/**
 * 获取素材类型名称
 */
const getMaterialTypeName = (type: number) => {
  const typeMap: Record<number, string> = {
    0: "PDF",
    1: "视频",
    2: "音频",
  };
  return typeMap[type] || "未知_" + type;
};

/**
 * 构建树形结构
 */
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

// ==================== 计算属性 ====================
/**
 * 计算级联选项
 */
const cascaderOptions = computed(() => {
  return buildCascaderOptions(categoryList.value);
});

/**
 * 获取某类别已选中的素材数量（带缓存）
 */
const getCategorySelectedCount = (categoryId: number) => {
  // 先从缓存中获取
  if (categorySelectedCountCache.value.has(categoryId)) {
    return categorySelectedCountCache.value.get(categoryId) || 0;
  }

  // 缓存中没有，计算并缓存
  const categoryMaterialIds = materialList.value
    .filter(m => m.cate_id === categoryId)
    .map(m => m.id);

  const count = selectedMaterials.value.filter(m => categoryMaterialIds.includes(m.id)).length;
  categorySelectedCountCache.value.set(categoryId, count);
  return count;
};

/**
 * 计算描述文字
 */
const descriptionText = computed(() => {
  if (selectedMaterials.value.length === 0) {
    return '请先选择素材';
  }

  const totalDays = endDay.value - startDay.value + 1;
  // 只有平均分配和循环分配才显示基数信息
  const showBatchInfo = useBatchSize.value && allocationType.value !== 2;
  const batchInfo = showBatchInfo ? `（每次${batchSize.value}个）` : '';

  switch (allocationType.value) {
    case 0: // 平均分配
      if (useBatchSize.value && batchSize.value > 1) {
        // 启用基数：强制每天分配 batchSize 个素材
        const requiredMaterials = totalDays * batchSize.value;
        if (selectedMaterials.value.length >= requiredMaterials) {
          const remaining = selectedMaterials.value.length - requiredMaterials;
          return `每天分配 ${batchSize.value} 个素材，共需 ${requiredMaterials} 个，将舍弃 ${remaining} 个多余素材`;
        } else {
          const canFillDays = Math.floor(selectedMaterials.value.length / batchSize.value);
          const unfilledDays = totalDays - canFillDays;
          return `每天分配 ${batchSize.value} 个素材，素材不足，只能填充 ${canFillDays} 天，剩余 ${unfilledDays} 天不分配`;
        }
      } else {
        // 未启用基数：原有逻辑
        const perDay = Math.floor(selectedMaterials.value.length / totalDays);
        const remaining = selectedMaterials.value.length % totalDays;
        if (remaining === 0) {
          return `每天分配 ${perDay} 个素材${batchInfo}`;
        } else {
          return `前 ${remaining} 天分配 ${perDay + 1} 个，其余天分配 ${perDay} 个${batchInfo}`;
        }
      }
    case 1: // 循环分配
      return `循环分配 ${selectedMaterials.value.length} 个素材到 ${totalDays} 天${batchInfo}`;
    case 2: // 全部添加到每一天
      return `每天分配 ${selectedMaterials.value.length} 个素材`;
    default:
      return '';
  }
});

// ==================== 数据加载 ====================
/**
 * 加载目录列表
 */
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
  } finally {
    materialLoading.value = false;
  }
};

/**
 * 加载素材列表
 */
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
        categorySelectedCountCache.value.set(selectedCategoryId.value, count);
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
      isRestoringSelection.value = true;

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
      isRestoringSelection.value = false;
    }
  }
};

// ==================== 事件处理 ====================
/**
 * 树节点点击事件
 */
const handleTreeSelect = (data: any) => {
  selectedCategoryId.value = data.id;
};

/**
 * 素材选择变化（跨类别累加）
 */
const handleMaterialSelectionChange = (selection: Material[]) => {
  if (isRestoringSelection.value) return;

  const currentIds = new Set(materialList.value.map(m => m.id));
  selectedMaterials.value = [
    ...selectedMaterials.value.filter(m => !currentIds.has(m.id)),
    ...selection
  ];

  Array.from(categorySelectedCountCache.value.keys()).forEach(catId => {
    if (materialList.value.some(m => m.cate_id === catId)) {
      const count = materialList.value
        .filter(m => m.cate_id === catId && selectedMaterials.value.some(sm => sm.id === m.id))
        .length;
      categorySelectedCountCache.value.set(catId, count);
    }
  });
};

/**
 * 行点击事件（PDF单选，其他多选）
 */
const handleRowClick = (row: Material) => {
  if (row.type === 1) {
    // PDF类型：单选逻辑
    materialTableRef.value?.clearSelection();
    materialTableRef.value?.toggleRowSelection(row, true);
  } else {
    // 非PDF类型：切换选中状态
    materialTableRef.value?.toggleRowSelection(row);
  }
};

/**
 * 执行分配
 */
const allocateMaterials = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning("请先选择素材");
    return;
  }

  if (startDay.value > endDay.value) {
    ElMessage.warning("起始天数不能大于结束天数");
    return;
  }

  // 根据 useBatchSize、batchSize 和 allocationType 对素材进行分组处理
  let processedMaterials: Array<{ id: number; name: string; type: number }> = [];

  if (!useBatchSize.value || batchSize.value === 1) {
    // 未启用基数或基数为1，直接传递所有素材
    processedMaterials = selectedMaterials.value.map(m => ({
      id: m.id!,
      name: m.name,
      type: m.type
    }));
  } else if (allocationType.value === 0) {
    // 启用基数且为平均分配：强制每天分配 batchSize 个素材
    const totalDays = endDay.value - startDay.value + 1;
    const requiredMaterials = totalDays * batchSize.value;

    if (selectedMaterials.value.length >= requiredMaterials) {
      // 素材充足：只取需要的数量，舍弃多余的
      const materialsToUse = selectedMaterials.value.slice(0, requiredMaterials);
      processedMaterials = materialsToUse.map(m => ({
        id: m.id!,
        name: m.name,
        type: m.type
      }));
    } else {
      // 素材不足：只取可用的素材
      processedMaterials = selectedMaterials.value.map(m => ({
        id: m.id!,
        name: m.name,
        type: m.type
      }));
    }
  } else {
    // 其他分配方式：按批次复制素材
    const batches = Math.ceil(selectedMaterials.value.length / batchSize.value);
    for (let i = 0; i < batches; i++) {
      const start = i * batchSize.value;
      const end = Math.min(start + batchSize.value, selectedMaterials.value.length);
      const batch = selectedMaterials.value.slice(start, end);

      // 将这批素材添加到结果中
      batch.forEach(m => {
        processedMaterials.push({
          id: m.id!,
          name: m.name,
          type: m.type
        });
      });
    }
  }

  // 触发分配事件
  emit("allocated",
    processedMaterials,
    startDay.value,
    endDay.value,
    allocationType.value
  );

  ElMessage.success("素材分配成功");
  handleClose();
};

// ==================== 生命周期 & 监听 ====================
// 监听外部传入的 modelValue
watch(
  () => props.modelValue,
  (newVal) => {
    visible.value = newVal;
    if (newVal) {
      // 初始化分配范围
      startDay.value = 1;
      endDay.value = props.formData.duration || 1;
      allocationType.value = 0;
      loadCategoryList();
      loadMaterialList();
    }
  }
);

// 监听 visible 变化
watch(visible, (newVal) => {
  emit("update:modelValue", newVal);
});

// 监听目录变化，重新加载素材
watch(selectedCategoryId, () => {
  if (visible.value) {
    loadMaterialList();
  }
});

// ==================== 对话框管理 ====================
/**
 * 关闭对话框
 */
const handleClose = () => {
  visible.value = false;
  resetForm();
};

/**
 * 重置表单
 */
const resetForm = () => {
  selectedMaterials.value = [];
  startDay.value = 1;
  endDay.value = 1;
  allocationType.value = 0;
  useBatchSize.value = false;
  batchSize.value = 1;
  categorySelectedCountCache.value.clear();
};
</script>
