<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2 gap-2">
      <el-button type="primary" plain size="small" @click="fetchCurrentList" :icon="Refresh" />
      <el-input v-model="searchKeyword" placeholder="搜索名称" size="small" class="w-40!" clearable
        @clear="fetchCurrentList" />
      <el-button type="primary" plain size="small" @click="fetchCurrentList">筛选</el-button>
      <el-button type="success" size="small" @click="handleBatchAdd">批量添加</el-button>
      <el-button type="primary" size="small" @click="handleAddMaterial">添加素材</el-button>
      <el-button type="warning" size="small" @click="handleAddFolder">新建目录</el-button>
    </div>

    <!-- 面包屑导航 -->
    <div class="flex items-center h-8 mb-2 bg-gray-50 px-3 py-2 rounded">
      <el-breadcrumb separator="/" class="flex-1">
        <el-breadcrumb-item v-for="(item, index) in breadcrumbList" :key="item.id"
          @click="handleBreadcrumbClick(item, index)" class="cursor-pointer hover:text-primary">
          {{ item.name }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 表格 -->
    <el-table :data="currentList" v-loading="loading" stripe border style="width: 100%" :height="tableMaxHeight"
      class="[&_.el-table__cell]:py-0!" @row-dblclick="handleRowDblClick">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="名称" min-width="200">
        <template #default="{ row }">
          <div class="flex items-center gap-2"
            :class="row.type === 'folder' ? 'cursor-pointer hover:bg-gray-100 pl-1 text-blue-500' : 'pl-1'"
            @click="row.type === 'folder' && handleEnterFolder(row)">
            <el-icon v-if="row.type === 'folder'" :size="20">
              <Folder />
            </el-icon>
            <el-icon v-else-if="row.type === 0" :size="20">
              <Document />
            </el-icon>
            <el-icon v-else-if="row.type === 1" :size="20">
              <VideoCamera />
            </el-icon>
            <el-icon v-else-if="row.type === 2" :size="20">
              <Headset />
            </el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="80" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <el-tag v-if="row.type === 'folder'" type="info" size="small">目录</el-tag>
            <el-tag v-else-if="row.type === 0" type="success" size="small">PDF</el-tag>
            <el-tag v-else-if="row.type === 1" type="warning" size="small">视频</el-tag>
            <el-tag v-else-if="row.type === 2" type="info" size="small">音频</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <div style="display: flex; align-items: center; overflow: hidden;">
            {{ row.path }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <div style="display: flex; align-items: center; gap: 8px;">
            <template v-if="row.type === 'folder'">
              <el-button size="small" @click="handleEditFolder(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDeleteFolder(row)">删除</el-button>
            </template>
            <template v-else>
              <el-button type="primary" size="small" plain @click="playMaterial(row)">
                <el-icon :size="16">
                  <Reading />
                </el-icon>
              </el-button>
              <el-button size="small" @click="handleViewDetail(row)" :disabled="row.type != 0">详情</el-button>
              <el-button size="small" @click="handleEditMaterial(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDeleteMaterial(row)">删除</el-button>
            </template>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 素材编辑/新增对话框 -->
    <MaterialDialog v-model="materialDialogVisible" :is-edit="isMaterialEdit" :material-data="currentMaterial"
      :category-list="batchAddCategoryList" :default-cate-id="currentParentId" @success="handleMaterialSuccess"
      @view-detail="handleViewDetailFromEdit" />

    <!-- 素材详情对话框 -->
    <MaterialDetailDialog v-model="detailDialogVisible" :material-data="currentMaterial"
      @update:modelValue="handleDetailDialogClose" @edit="handleEditFromDetail" />

    <!-- 素材预览弹窗 -->
    <MaterialPreviewDialog v-model="previewDialogVisible" :material-id="previewMaterialId" />

    <!-- 批量添加素材对话框 -->
    <BatchAddMaterialDialog v-model="batchAddDialogVisible" :category-list="batchAddCategoryList"
      :default-cate-id="currentParentId" @success="handleBatchAddSuccess" />

    <!-- 文件夹编辑/新增对话框 -->
    <el-dialog v-model="folderDialogVisible" :title="isFolderEdit ? '编辑文件夹' : '新建文件夹'" width="500">
      <el-form :model="currentFolder" label-width="100px">
        <el-form-item label="文件夹名称">
          <el-input v-model="currentFolder.name" placeholder="请输入文件夹名称" />
        </el-form-item>
        <el-form-item label="所属目录">
          <el-cascader v-model="currentFolder.parent" :options="folderCategoryOptions"
            :props="{ value: 'id', label: 'name', children: 'children', emitPath: false, checkStrictly: true }"
            placeholder="选择父级目录（不选则为根目录）" clearable class="w-full" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveFolder">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted, h } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Reading, Folder, Document, VideoCamera, Headset } from "@element-plus/icons-vue";
import {
  getMaterialList,
  getMaterialCategoryList,
  addMaterialCategory,
  updateMaterialCategory,
  deleteMaterialCategory,
  deleteMaterial,
  type Material,
  type MaterialCategory,
} from "@/api/api-task";
import MaterialDialog from "./dialogs/MaterialDialog.vue";
import MaterialDetailDialog from "./dialogs/MaterialDetailDialog.vue";
import MaterialPreviewDialog from "./dialogs/MaterialPreviewDialog.vue";
import BatchAddMaterialDialog from "./dialogs/MaterialBatchAdd.vue";

interface FolderItem extends MaterialCategory {
  type: 'folder';
}

interface MixedItem {
  id?: number;
  name: string;
  type: 'folder' | number;
  path?: string;
  cate_id?: number;
  data?: any;
  parent?: number;
}

const tableMaxHeight = ref<number>(600); // 设置默认高度，避免初始抖动
// 计算表格最大高度
const calculateTableHeight = () => {
  nextTick(() => {
    const windowHeight = window.innerHeight;
    const reservedSpace = 300;
    tableMaxHeight.value = windowHeight - reservedSpace;
  });
};

// 状态管理
const loading = ref(false);
const currentList = ref<MixedItem[]>([]);
const searchKeyword = ref("");

// 面包屑导航
interface BreadcrumbItem {
  id: number;
  name: string;
  parent?: number;
}
const breadcrumbList = ref<BreadcrumbItem[]>([
  { id: -1, name: '根目录', parent: undefined }
]);
const currentParentId = ref<number>(-1); // 当前所在父级ID

// 对话框
const materialDialogVisible = ref(false);
const detailDialogVisible = ref(false);
const previewDialogVisible = ref(false);
const batchAddDialogVisible = ref(false);
const folderDialogVisible = ref(false);
const previewMaterialId = ref<number | null>(null);
const isMaterialEdit = ref(false);
const currentMaterial = ref<Partial<Material>>({});
const currentFolder = ref<Partial<FolderItem>>({});
const isFolderEdit = ref(false);
const batchAddCategoryList = ref<{ id: number; name: string }[]>([]); // 批量添加用的目录列表
const folderCategoryOptions = ref<any[]>([]); // 文件夹目录级联选项

// 获取目录列表（用于素材的cate_id）
const fetchCategoryList = async () => {
  try {
    const res = await getMaterialCategoryList(1, 1000);
    if (res.code === 0 && res.data) {
      const list = res.data.data || [];
      batchAddCategoryList.value = list;
      // 构建级联选项
      folderCategoryOptions.value = buildCategoryTree(list);
      return list;
    }
  } catch (error: any) {
    console.error("获取目录列表失败:", error);
  }
  return [];
};

// 构建目录树形结构
const buildCategoryTree = (categories: MaterialCategory[]): any[] => {
  const categoryMap = new Map<number, any>();
  const tree: any[] = [];

  // 先创建所有节点的映射
  categories.forEach(cat => {
    if (cat.id === undefined || cat.id === null) return;
    categoryMap.set(cat.id, {
      id: cat.id,
      name: cat.name,
      parent: cat.parent ?? -1,
      children: []
    });
  });

  // 构建树形结构
  categoryMap.forEach(node => {
    const parentId = node.parent ?? -1;
    if (parentId === -1 || !categoryMap.has(parentId)) {
      // 根节点
      tree.push(node);
    } else {
      // 子节点
      const parent = categoryMap.get(parentId);
      if (parent) {
        parent.children.push(node);
      }
    }
  });

  return tree;
};

// 获取当前目录下的内容（文件夹 + 素材）
const fetchCurrentList = async () => {
  loading.value = true;
  try {
    // 获取当前父级下的子目录
    const categoriesRes = await getMaterialCategoryList(1, 1000, currentParentId.value);
    const folders: FolderItem[] = [];
    if (categoriesRes.code === 0 && categoriesRes.data) {
      const categories = categoriesRes.data.data || [];

      categories.forEach((cat: MaterialCategory) => {
        // 确保 id 存在（id 可能是 0）
        if (cat.id === undefined || cat.id === null) {
          return;
        }
        folders.push({
          ...cat,
          type: 'folder' as const
        });
      });
    }

    // 获取当前父级下的素材（固定1000条）
    const materialsRes = await getMaterialList(currentParentId.value, 1, 1000);
    let materials: Material[] = [];
    if (materialsRes.code === 0 && materialsRes.data) {
      materials = materialsRes.data.data || [];
    }

    // 合并文件夹和素材
    let mixedList: MixedItem[] = [
      ...folders.map(f => ({
        id: f.id,
        name: f.name,
        type: 'folder' as const,
        parent: f.parent
      })),
      ...materials.map(m => ({
        id: m.id,
        name: m.name,
        type: m.type,
        path: m.path,
        cate_id: m.cate_id,
        data: m.data
      }))
    ];

    // 前端搜索过滤
    if (searchKeyword.value) {
      mixedList = mixedList.filter((item) =>
        item.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
      );
    }

    currentList.value = mixedList;
  } catch (error: any) {
    console.error("获取列表失败:", error);
    ElMessage.error(error.message || "获取列表失败");
  } finally {
    loading.value = false;
  }
};

// 面包屑点击
const handleBreadcrumbClick = (item: BreadcrumbItem, index: number) => {
  // 截断面包屑到点击的位置
  breadcrumbList.value = breadcrumbList.value.slice(0, index + 1);
  currentParentId.value = item.id;
  fetchCurrentList();
};

// 进入文件夹
const handleEnterFolder = (row: MixedItem) => {
  if (row.type !== 'folder') {
    return;
  }
  // id 可能是 0，需要用 undefined/null 判断
  if (row.id === undefined || row.id === null) {
    ElMessage.error('文件夹数据异常，无法进入');
    return;
  }

  breadcrumbList.value.push({
    id: row.id,
    name: row.name,
    parent: currentParentId.value
  });
  currentParentId.value = row.id;
  fetchCurrentList();
};

// 双击行进入文件夹
const handleRowDblClick = (row: MixedItem) => {
  if (row.type === 'folder') {
    handleEnterFolder(row);
  } else {
    playMaterial(row as any);
  }
};

// 新建文件夹
const handleAddFolder = () => {
  isFolderEdit.value = false;
  currentFolder.value = {
    name: '',
    parent: -1  // 默认为根目录
  };
  folderDialogVisible.value = true;
};

// 编辑文件夹
const handleEditFolder = (row: MixedItem) => {
  isFolderEdit.value = true;
  currentFolder.value = {
    id: row.id,
    name: row.name,
    parent: row.parent ?? -1
  };
  folderDialogVisible.value = true;
};

// 保存文件夹
const handleSaveFolder = async () => {
  if (!currentFolder.value.name) {
    ElMessage.warning("文件夹名称不能为空");
    return;
  }

  try {
    if (isFolderEdit.value && currentFolder.value.id) {
      // 更新
      await updateMaterialCategory({
        id: currentFolder.value.id,
        name: currentFolder.value.name,
        parent: currentFolder.value.parent ?? -1
      } as MaterialCategory);
      ElMessage.success("更新成功");
    } else {
      // 新增
      await addMaterialCategory({
        name: currentFolder.value.name,
        parent: currentFolder.value.parent ?? -1
      });
      ElMessage.success("创建成功");
    }
    folderDialogVisible.value = false;
    fetchCurrentList();
  } catch (error: any) {
    ElMessage.error(error.message || "操作失败");
  }
};

// 删除文件夹
const handleDeleteFolder = async (row: MixedItem) => {
  try {
    // 创建带复选框的确认对话框
    const deleteMaterials = ref(false);

    await ElMessageBox.confirm(
      h('div', { class: 'flex flex-col gap-3' }, [
        h('p', null, '确定要删除该目录吗？'),
        h('p', { class: 'text-sm text-gray-500' }, '此操作将删除该目录及其所有子目录。'),
        h('label', { class: 'flex items-center gap-2 mt-2 cursor-pointer' }, [
          h('input', {
            type: 'checkbox',
            checked: deleteMaterials.value,
            onChange: (e: Event) => {
              deleteMaterials.value = (e.target as HTMLInputElement).checked;
            },
            class: 'w-4 h-4'
          }),
          h('span', null, '同时删除目录下的所有素材')
        ])
      ]),
      "提示",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
        distinguishCancelAndClose: true,
      }
    );

    if (row.id) {
      // 显示 loading 消息
      const loadingMsg = ElMessage({
        message: '正在删除...',
        type: 'info',
        duration: 0, // 不自动关闭
        icon: h('el-icon-loading', { class: 'is-loading' })
      });

      try {
        await deleteMaterialCategory(row.id, deleteMaterials.value);
        loadingMsg.close();
        ElMessage.success("删除成功");
        fetchCurrentList();
      } catch (error: any) {
        loadingMsg.close();
        throw error;
      }
    }
  } catch (error: any) {
    if (error !== "cancel" && error !== "close") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 新增素材
const handleAddMaterial = () => {
  isMaterialEdit.value = false;
  currentMaterial.value = {
    cate_id: currentParentId.value
  };
  materialDialogVisible.value = true;
};

// 批量添加素材
const handleBatchAdd = () => {
  batchAddDialogVisible.value = true;
};

// 批量添加成功回调
const handleBatchAddSuccess = () => {
  fetchCurrentList();
};

// 查看详情
const handleViewDetail = (row: Material) => {
  currentMaterial.value = row;
  detailDialogVisible.value = true;
};

// 详情对话框关闭
const handleDetailDialogClose = (val: boolean) => {
  detailDialogVisible.value = val;
  if (!val) {
    fetchCurrentList();
  }
};

// 从编辑页打开详情
const handleViewDetailFromEdit = (material: Material) => {
  currentMaterial.value = material;
  detailDialogVisible.value = true;
};

// 从详情页打开编辑
const handleEditFromDetail = (material: Material) => {
  isMaterialEdit.value = true;
  currentMaterial.value = material;
  materialDialogVisible.value = true;
};

// 编辑素材
const handleEditMaterial = (row: Material) => {
  isMaterialEdit.value = true;
  currentMaterial.value = row;
  materialDialogVisible.value = true;
};

// 删除素材
const handleDeleteMaterial = async (row: Material) => {
  try {
    await ElMessageBox.confirm("确定要删除该素材吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    await deleteMaterial(row.id!);
    ElMessage.success("删除成功");
    fetchCurrentList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 素材操作成功回调
const handleMaterialSuccess = () => {
  fetchCurrentList();
};

// 播放/预览素材
const playMaterial = (row: Material) => {
  if (!row.id) return;

  // 将完整的素材数据通过 sessionStorage 传递
  sessionStorage.setItem('previewMaterial', JSON.stringify(row));

  // 打开预览弹窗
  previewMaterialId.value = row.id;
  previewDialogVisible.value = true;
};

// 初始化
onMounted(() => {
  fetchCategoryList();
  fetchCurrentList();
  calculateTableHeight();
  window.addEventListener('resize', calculateTableHeight);

  // 监听刷新事件
  const handleRefresh = () => {
    fetchCurrentList();
  };
  window.addEventListener('refresh-material-tab', handleRefresh);

  onUnmounted(() => {
    window.removeEventListener('resize', calculateTableHeight);
    window.removeEventListener('refresh-material-tab', handleRefresh);
  });
});
</script>
