<template>
  <el-dialog v-model="visible" title="批量添加素材" width="1200px" :close-on-click-modal="false" align-center
    :before-close="handleBeforeClose">
    <div v-loading="submitting" element-loading-text="正在添加素材..." class="h-[75vh] min-h-100 overflow-y-auto">
      <!-- 配置区域 -->
      <div class="mb-4 p-4 bg-gray-50 rounded">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-2">目录</label>
            <el-cascader v-model="cascaderValue" :options="cascaderOptions" :props="cascaderProps" placeholder="选择目录"
              clearable class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">类型</label>
            <el-radio-group v-model="defaultType">
              <el-radio :value="0">PDF</el-radio>
              <el-radio :value="1">视频</el-radio>
              <el-radio :value="3">目录</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>

      <!-- 已添加列表 -->
      <div class="mb-4 flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-sm font-medium flex-1">待添加素材 ({{ materialList.length }} 条)</h4>
          <el-button size="small" :type="defaultType === 3 ? 'primary' : 'info'" @click="openFileBrowser">
            {{ defaultType === 3 ? '添加文件夹' : '添加文件' }}
          </el-button>
          <el-button size="small" type="danger" @click="clearMaterialList">清空列表</el-button>
        </div>
        <el-table :data="materialList" border size="small" :height="tableHeight">
          <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="flex items-center gap-2 whitespace-nowrap overflow-hidden text-ellipsis">
                <el-icon v-if="row.isFolder" :size="16">
                  <Folder />
                </el-icon>
                <span class="truncate">{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
          <el-table-column label="目录" width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.folderPath" class="text-blue-600">{{ row.folderPath }}</span>
              <span v-else>{{ getCategoryName(row.cate_id) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.isFolder" type="info" size="small">目录</el-tag>
              <el-tag v-else-if="row.type === 0" type="success" size="small">PDF</el-tag>
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

  <!-- 目录扫描对话框 -->
  <FileDialog v-model:visible="directoryDialogVisible" title="选择要扫描的目录" mode="directory" :multiple="false"
    :confirm-loading="submitting" confirm-button-text="开始扫描" @confirm="handleDirectoryConfirm" />
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Folder } from "@element-plus/icons-vue";
import { addMaterial, addMaterialCategory } from "@/api/api-task";
import { listDirectory, type DirectoryItem } from "@/api/api-file";
import { sortMaterials, buildCategoryTree, CATEGORY_CASCADER_PROPS } from "@/utils/file";
import FileDialog from "@/views/dialogs/FileDialog.vue";

type CategoryOption = { id: number; name: string; parent?: number };

const FILE_TYPE_BY_EXTENSION: Record<string, number> = {
  pdf: 0,
  mp4: 1,
  avi: 1,
  mkv: 1,
  mov: 1,
  wmv: 1,
  flv: 1,
  webm: 1,
};

const SCAN_EXTENSIONS = Object.keys(FILE_TYPE_BY_EXTENSION).join(",");

interface Props {
  modelValue: boolean;
  categoryList: CategoryOption[];
  defaultCateId?: number; // 默认目录ID
}

interface MaterialItem {
  name: string;
  path: string;
  cate_id: number;
  type: number;
  isFolder?: boolean; // 是否为文件夹
  children?: MaterialItem[]; // 子项（用于树形展示）
  folderPath?: string; // 所属文件夹完整路径（用于动态创建目录）
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
const directoryDialogVisible = ref(false); // 目录选择对话框
const materialList = ref<MaterialItem[]>([]);
const errors = ref<string[]>([]);
const submitting = ref(false);
const tableHeight = ref<number>(400); // 表格高度

// Cascader 配置
const cascaderValue = ref<number | null>(null);
const cascaderProps = CATEGORY_CASCADER_PROPS;

// 计算级联选项
const cascaderOptions = computed(() => buildCategoryTree(props.categoryList || []));

// 获取目录名称
const getCategoryName = (cateId: number): string => {
  const category = props.categoryList.find(c => c.id === cateId);
  return category ? category.name : '未知';
};

const buildCategoryPathMaps = (categories: CategoryOption[]) => {
  const categoryById = new Map(categories.map(category => [category.id, category]));
  const pathById = new Map<number, string>();

  const resolvePath = (categoryId: number, visited = new Set<number>()): string => {
    if (pathById.has(categoryId)) {
      return pathById.get(categoryId)!;
    }

    if (visited.has(categoryId)) {
      return categoryById.get(categoryId)?.name || '';
    }

    const category = categoryById.get(categoryId);
    if (!category) {
      return '';
    }

    visited.add(categoryId);
    const parentId = category.parent;
    const parentPath = parentId === undefined || parentId === null || parentId === -1
      ? ''
      : resolvePath(parentId, visited);
    visited.delete(categoryId);

    const fullPath = parentPath ? `${parentPath}/${category.name}` : category.name;
    pathById.set(categoryId, fullPath);
    return fullPath;
  };

  const idByPath = new Map<string, number>();
  for (const category of categories) {
    const fullPath = resolvePath(category.id);
    if (fullPath) {
      idByPath.set(fullPath, category.id);
    }
  }

  return { pathById, idByPath };
};

const categoryPathMaps = computed(() => buildCategoryPathMaps(props.categoryList || []));

const getSelectedCategoryId = (): number => {
  return cascaderValue.value ?? defaultCateId.value ?? props.categoryList[0]?.id ?? 1;
};

const getSelectedCategoryPath = (): string => {
  const targetId = cascaderValue.value ?? defaultCateId.value;
  if (targetId === undefined || targetId === null) {
    return '';
  }
  return categoryPathMaps.value.pathById.get(targetId) || '';
};

const getFileType = (name: string): number => {
  const ext = name.split('.').pop()?.toLowerCase();
  return ext ? (FILE_TYPE_BY_EXTENSION[ext] ?? -1) : -1;
};

const resetDialogState = () => {
  materialList.value = [];
  errors.value = [];
};

const confirmDiscardChanges = async (): Promise<boolean> => {
  if (materialList.value.length === 0) {
    return true;
  }

  try {
    await ElMessageBox.confirm("确定要关闭并清空所有待添加素材吗？", "提示", { type: "warning" });
    return true;
  } catch {
    return false;
  }
};

// 监听 cascaderValue 变化，更新 defaultCateId
watch(cascaderValue, (val) => {
  if (val !== undefined && val !== null) {
    defaultCateId.value = val;
  }
});

// 初始化默认目录
watch(
  () => [props.categoryList, props.defaultCateId, visible.value] as const,
  ([list, defaultId, isVisible]) => {
    if (isVisible && list && list.length > 0) {
      // 如果有传入的默认目录ID且在列表中，优先使用
      if (defaultId !== undefined && defaultId !== null && list.some((cate: { id: number; name: string }) => cate.id === defaultId)) {
        defaultCateId.value = defaultId;
        cascaderValue.value = defaultId;
      } else if (defaultCateId.value === undefined || defaultCateId.value === null || !list.some((cate: { id: number; name: string }) => cate.id === defaultCateId.value)) {
        // 如果当前默认目录不在列表中，使用第一个目录
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
  if (defaultType.value === 3) {
    // 文件夹类型：打开目录扫描对话框
    directoryDialogVisible.value = true;
  } else {
    // 其他类型：打开文件选择对话框
    fileDialogVisible.value = true;
  }
};

// 目录选择确认
const handleDirectoryConfirm = async (dirPaths: string[]) => {
  if (!dirPaths || dirPaths.length === 0) return;

  const dirPath = dirPaths[0];
  submitting.value = true;

  try {
    const result = await listDirectory(dirPath, SCAN_EXTENSIONS, true);

    if (!result || !Array.isArray(result)) {
      ElMessage.error('扫描目录失败');
      return;
    }
    const scannedItems = convertScanResultToMaterials(result, getSelectedCategoryPath());

    // 添加到素材列表
    materialList.value.push(...scannedItems);

    // 排序：先目录后文件，名称自然排序
    sortMaterials(materialList.value);

    ElMessage.success(`已扫描 ${scannedItems.length} 个文件`);
    directoryDialogVisible.value = false;
  } catch (error: any) {
    console.error('扫描目录失败:', error);
    ElMessage.error(error.message || '扫描目录失败');
  } finally {
    submitting.value = false;
  }
};

// 将扫描结果转换为 MaterialItem（扁平化）
const convertScanResultToMaterials = (
  items: DirectoryItem[],
  baseCategoryPath?: string // 基础目录路径（如 "咱们裸熊/sub"）
): MaterialItem[] => {
  const result: MaterialItem[] = [];
  const defaultCategoryId = getSelectedCategoryId();

  const processItems = (items: DirectoryItem[], currentCategoryPath?: string) => {
    items.forEach(item => {
      if (item.isDirectory) {
        const folderCategoryPath = currentCategoryPath
          ? `${currentCategoryPath}/${item.name}`
          : (baseCategoryPath ? `${baseCategoryPath}/${item.name}` : item.name);

        if (item.subItems && item.subItems.length > 0) {
          processItems(item.subItems, folderCategoryPath);
        }
      } else {
        const type = getFileType(item.name);
        if (type !== -1) {
          result.push({
            name: item.name,
            path: item.path || '',
            cate_id: defaultCategoryId,
            type,
            isFolder: false,
            folderPath: currentCategoryPath || baseCategoryPath,
          });
        }
      }
    });
  };

  processItems(items, baseCategoryPath);
  return result;
};

// 文件选择确认
const handleFileConfirm = (filePaths: string[]) => {
  if (!filePaths?.length) return;

  let addedCount = 0;
  let skippedCount = 0;
  const defaultCategoryId = getSelectedCategoryId();

  filePaths.forEach((filePath) => {
    const fileName = filePath.split('/').pop() || filePath;
    const type = getFileType(fileName);

    if (type !== -1) {
      materialList.value.push({
        name: fileName.replace(/\.[^/.]+$/, ""),
        path: filePath,
        cate_id: defaultCategoryId,
        type,
      });
      addedCount++;
    } else {
      skippedCount++;
    }
  });

  if (addedCount > 0) {
    // 排序：先目录后文件，名称自然排序
    sortMaterials(materialList.value);

    ElMessage.success(`已添加 ${addedCount} 个文件${skippedCount > 0 ? `，跳过 ${skippedCount} 个不支持的文件` : ''}`);
  } else {
    ElMessage.warning('没有可添加的文件（仅支持 PDF 和视频文件）');
  }
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
    resetDialogState();
  } catch { }
};

// 取消按钮
const handleCancel = async () => {
  if (!await confirmDiscardChanges()) {
    return;
  }
  resetDialogState();
  visible.value = false;
};

// 关闭前确认（用于点击右上角关闭按钮）
const handleBeforeClose = async (done?: () => void) => {
  if (!await confirmDiscardChanges()) {
    return;
  }
  resetDialogState();
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
  const materials = [...materialList.value];

  try {
    const categoryMap = await createMissingCategories(materials);

    updateMaterialCategoryIds(materials, categoryMap);

    const failedItems = await addMaterialsBatch(materials);

    handleSubmissionResult(materials, failedItems);
  } catch (error: any) {
    console.error('批量添加失败:', error);
    ElMessage.error('批量添加失败');
  } finally {
    submitting.value = false;
  }
};

// 收集并创建缺失的目录
const createMissingCategories = async (materials: MaterialItem[]): Promise<Map<string, number>> => {
  const categoryMap = new Map<string, number>();
  const existingCategoryPathMap = categoryPathMaps.value.idByPath;

  const allFolderPaths = new Set<string>();
  for (const material of materials) {
    if (material.folderPath) {
      allFolderPaths.add(material.folderPath);

      // 同时添加所有父路径
      const parts = material.folderPath.split('/');
      for (let i = 1; i < parts.length; i++) {
        const parentPath = parts.slice(0, i).join('/');
        if (parentPath) {
          allFolderPaths.add(parentPath);
        }
      }
    }
  }

  const sortedFolderPaths = Array.from(allFolderPaths).sort((a, b) => {
    const depthDiff = a.split('/').length - b.split('/').length;
    if (depthDiff !== 0) {
      return depthDiff;
    }

    return a.localeCompare(b, 'zh-CN', { numeric: true, sensitivity: 'base' });
  });

  // 目录必须按层级从浅到深创建，否则第一个子目录会在父目录尚未存在时落到根目录
  for (const folderPath of sortedFolderPaths) {
    const existingCategoryId = existingCategoryPathMap.get(folderPath);
    if (existingCategoryId !== undefined) {
      categoryMap.set(folderPath, existingCategoryId);
      continue;
    }

    const categoryName = folderPath.split('/').pop() || folderPath;

    // 获取父目录ID
    let parentId = -1; // 默认根目录
    const parentPath = folderPath.split('/').slice(0, -1).join('/');
    if (parentPath && categoryMap.has(parentPath)) {
      parentId = categoryMap.get(parentPath)!;
    }

    try {
      const result = await addMaterialCategory({ name: categoryName, parent: parentId });
      let newCategoryId: number | undefined;
      if (typeof result === 'number') {
        newCategoryId = result;
      } else if (result && typeof result === 'object' && 'id' in result) {
        newCategoryId = (result as any).id;
      }

      if (newCategoryId !== undefined) {
        categoryMap.set(folderPath, newCategoryId);
      }
    } catch (error: any) {
      console.error(`创建目录 "${categoryName}" 失败:`, error);
      throw new Error(`创建目录 "${categoryName}" 失败`);
    }
  }

  return categoryMap;
};

// 更新素材的目录ID
const updateMaterialCategoryIds = (materials: MaterialItem[], categoryMap: Map<string, number>) => {
  for (const material of materials) {
    if (material.folderPath && categoryMap.has(material.folderPath)) {
      material.cate_id = categoryMap.get(material.folderPath)!;
    }
  }
};

// 批量添加素材
const addMaterialsBatch = async (materials: MaterialItem[]): Promise<string[]> => {
  const failedItems: string[] = [];

  for (const material of materials) {
    try {
      // 清理前端专用字段，只提交数据库需要的字段
      const materialData = {
        name: material.name,
        path: material.path,
        cate_id: material.cate_id,
        type: material.type,
      };

      await addMaterial(materialData);
    } catch (error: any) {
      console.error(`[添加失败] ${material.name}:`, error);
      console.error(`[错误详情]`, error.response?.data || error.message);
      failedItems.push(material.name);
    }
  }

  return failedItems;
};

// 处理提交结果
const handleSubmissionResult = (materials: MaterialItem[], failedItems: string[]) => {
  const successCount = materials.length - failedItems.length;

  if (!failedItems.length) {
    ElMessage.success(`成功添加 ${successCount} 个素材`);
    emit("success");
    visible.value = false;
    materialList.value = [];
    errors.value = [];
  } else {
    errors.value = failedItems.map(name => `添加失败: ${name}`);
    ElMessage.warning(`添加完成：成功 ${successCount} 个，失败 ${failedItems.length} 个`);
    // 保留失败的项
    materialList.value = materialList.value.filter(m => failedItems.includes(m.name));
  }
};

// 计算表格最大高度
const calculateTableHeight = () => {
  nextTick(() => {
    const windowHeight = window.innerHeight;
    tableHeight.value = windowHeight - 480;
  });
};

// 监听对话框打开，重置数据
watch(visible, (newVal) => {
  if (newVal) {
    resetDialogState();
  }
});
onMounted(() => {
  calculateTableHeight();
  window.addEventListener('resize', calculateTableHeight);
});

onUnmounted(() => {
  window.removeEventListener('resize', calculateTableHeight);
});
</script>
