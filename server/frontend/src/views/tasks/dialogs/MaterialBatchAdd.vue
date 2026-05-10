<template>
  <el-dialog v-model="visible" title="批量添加素材" width="1000px" :close-on-click-modal="false"
    :before-close="handleBeforeClose">
    <div v-loading="submitting" element-loading-text="正在添加素材..." class="max-h-[80vh] min-h-100 overflow-y-auto">
      <!-- 配置区域 -->
      <div class="mb-4 p-4 bg-gray-50 rounded">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-2">分类</label>
            <el-cascader v-model="cascaderValue" :options="cascaderOptions" :props="cascaderProps" placeholder="选择分类"
              clearable class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">类型</label>
            <el-radio-group v-model="defaultType">
              <el-radio :value="0">PDF</el-radio>
              <el-radio :value="1">视频</el-radio>
              <el-radio :value="3">文件夹</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>

      <!-- 已添加列表 -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-sm font-medium flex-1">待添加素材 ({{ materialList.length }} 条)</h4>
          <el-button size="small" :type="defaultType === 3 ? 'primary' : 'info'" @click="openFileBrowser">
            {{ defaultType === 3 ? '添加文件夹' : '添加文件' }}
          </el-button>
          <el-button size="small" type="danger" @click="clearMaterialList">清空列表</el-button>
        </div>
        <el-table :data="materialList" border max-height="300" size="small">
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
          <el-table-column label="分类" width="150">
            <template #default="{ row }">
              <el-cascader v-model="row.cate_id" :options="cascaderOptions" :props="cascaderProps" placeholder="选择分类"
                clearable size="small" class="w-full" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.type === 0" type="success" size="small">PDF</el-tag>
              <el-tag v-else-if="row.type === 1" type="primary" size="small">视频</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ $index }">
              <el-button size="small" type="danger" @click="removeMaterial($index)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 错误信息 -->
      <div v-if="errors.length > 0" class="mt-4">
        <h4 class="text-sm font-medium mb-2 text-red-600">错误信息 ({{ errors.length }} 条)</h4>
        <el-alert v-for="(error, index) in errors" :key="index" :title="error" type="error" show-icon class="mb-2"
          :closable="false" />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
        <div class="text-sm text-gray-600">
          已选择 {{ materialList.length }} 个素材
        </div>
        <div>
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting" :disabled="materialList.length === 0">
            确认添加 ({{ materialList.length }})
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>

  <!-- 文件选择对话框 -->
  <FileDialog v-model:visible="fileDialogVisible" title="批量选择文件" :extensions="getExtensionsByType(defaultType)"
    :mode="defaultType === 3 ? 'directory' : 'file'" :multiple="true" @confirm="handleFileConfirm" />
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { addMaterial } from "@/api/api-task";
import FileDialog from "@/views/dialogs/FileDialog.vue";

interface Props {
  modelValue: boolean;
  categoryList: Array<{ id: number; name: string }>;
  defaultCateId?: number; // 默认分类ID
}

interface MaterialItem {
  name: string;
  path: string;
  cate_id: number;
  type: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

// 配置
const defaultCateId = ref<number>();
const defaultType = ref<number>(0);
const fileDialogVisible = ref(false);
const materialList = ref<MaterialItem[]>([]);
const errors = ref<string[]>([]);
const submitting = ref(false);

// Cascader 配置
const cascaderValue = ref<number | null>(null);
const cascaderProps = {
  value: 'id',
  label: 'name',
  children: 'children',
  checkStrictly: true,
  emitPath: false
};

// 构建树形结构
const buildCascaderOptions = (categories: { id: number; name: string; parent?: number }[]) => {
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
  return buildCascaderOptions(props.categoryList || []);
});

// 监听 cascaderValue 变化，更新 defaultCateId
watch(cascaderValue, (val) => {
  if (val !== undefined && val !== null) {
    defaultCateId.value = val;
  }
});

// 初始化默认分类
watch(
  () => [props.categoryList, props.defaultCateId, visible.value] as const,
  ([list, defaultId, isVisible]) => {
    if (isVisible && list && list.length > 0) {
      // 如果有传入的默认分类ID且在列表中，优先使用
      if (defaultId !== undefined && list.some((cate: { id: number; name: string }) => cate.id === defaultId)) {
        defaultCateId.value = defaultId;
        cascaderValue.value = defaultId;
      } else if (!defaultCateId.value || !list.some((cate: { id: number; name: string }) => cate.id === defaultCateId.value)) {
        // 如果当前默认分类不在列表中，使用第一个分类
        defaultCateId.value = list[0].id;
        cascaderValue.value = list[0].id;
      }
    }
  },
  { immediate: true }
);

// 根据类型获取扩展名
const getExtensionsByType = (type: number): string => {
  if (type === 0) return ".pdf";
  if (type === 1) return ".mp4,.avi,.mkv,.mov,.wmv,.flv,.webm";
  if (type === 3) return ""; // 文件夹不需要扩展名过滤
  return "";
};

// 打开文件浏览器
const openFileBrowser = () => {
  fileDialogVisible.value = true;
};


// 文件选择确认
const handleFileConfirm = (filePaths: string[]) => {
  if (!filePaths?.length) return;

  filePaths.forEach((filePath) => {
    const fileName = filePath.split('/').pop() || filePath;
    materialList.value.push({
      name: fileName.replace(/\.[^/.]+$/, ""),
      path: filePath,
      cate_id: defaultCateId.value || props.categoryList[0]?.id || 1,
      type: defaultType.value,
    });
  });

  ElMessage.success(`已添加 ${filePaths.length} 个文件`);
};

// 移除素材
const removeMaterial = (index: number) => {
  materialList.value.splice(index, 1);
};

// 清空素材列表
const clearMaterialList = async () => {
  if (materialList.value.length === 0) return;

  try {
    await ElMessageBox.confirm("确定要清空所有待添加素材吗？", "提示", { type: "warning" });
    materialList.value = [];
    errors.value = [];
  } catch { }
};

// 取消按钮
const handleCancel = async () => {
  if (materialList.value.length > 0) {
    try {
      await ElMessageBox.confirm("确定要关闭并清空所有待添加素材吗？", "提示", { type: "warning" });
    } catch {
      return;
    }
  }
  // 直接清空，不再调用 clearMaterialList（避免二次确认）
  materialList.value = [];
  errors.value = [];
  visible.value = false;
};

// 关闭前确认（用于点击右上角关闭按钮）
const handleBeforeClose = async (done?: () => void) => {
  if (materialList.value.length > 0) {
    try {
      await ElMessageBox.confirm("确定要关闭并清空所有待添加素材吗？", "提示", { type: "warning" });
    } catch {
      return;
    }
  }
  // 直接清空，不再调用 clearMaterialList（避免二次确认）
  materialList.value = [];
  errors.value = [];
  done ? done() : (visible.value = false);
};

// 提交批量添加
const handleSubmit = async () => {
  if (!materialList.value.length) {
    ElMessage.warning("请至少添加一个素材");
    return;
  }

  submitting.value = true;
  errors.value = [];
  const failedItems: string[] = [];

  for (const material of materialList.value) {
    try {
      await addMaterial(material);
    } catch (error: any) {
      console.error(`添加素材 "${material.name}" 失败:`, error);
      failedItems.push(material.name);
    }
  }

  const successCount = materialList.value.length - failedItems.length;
  if (!failedItems.length) {
    ElMessage.success(`成功添加 ${successCount} 个素材`);
    emit("success");
    visible.value = false;
    materialList.value = [];
  } else {
    errors.value = failedItems.map((name) => `添加失败: ${name}`);
    ElMessage.warning(`添加完成：成功 ${successCount} 个，失败 ${failedItems.length} 个`);
    materialList.value = materialList.value.filter((m) => failedItems.includes(m.name));
  }
  submitting.value = false;
};

// 监听对话框打开，重置数据
watch(visible, (newVal) => {
  if (newVal) {
    materialList.value = [];
    errors.value = [];
  }
});
</script>
