<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <el-radio-group size="large" v-model="selectedCateId" @change="onCateChange">
        <el-radio-button v-for="item in categoryList" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>
      <el-button type="primary" class="ml-1" @click="openCategoryDialog">
        <el-icon><Edit /></el-icon>
      </el-button>
      <div class="flex-1 flex items-center justify-end gap-2">
        <el-button type="primary" plain size="small" @click="fetchMaterialList" :icon="Refresh" />
        <el-input
          v-model="searchKeyword"
          placeholder="搜索素材名称"
          size="small"
          class="w-40!"
          clearable
          @clear="fetchMaterialList"
        />
        <el-button type="primary" plain size="small" @click="fetchMaterialList">筛选</el-button>
        <el-button type="primary" size="small" @click="handleAddMaterial">添加素材</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="materialList" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 0 ? 'success' : 'warning'" size="small">
            {{ row.type === 0 ? 'PDF' : 'Video' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
      <el-table-column label="分类" width="120">
        <template #default="{ row }">
          {{ getCategoryName(row.cate_id) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
            <el-button type="primary" size="small" plain @click="playMaterial(row)">
              <el-icon :size="16" ><Reading /></el-icon>
            </el-button>
          <el-button size="small" @click="handleViewDetail(row)">详情</el-button>
          <el-button size="small" @click="handleEditMaterial(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDeleteMaterial(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      layout="sizes, prev, pager, next"
      :total="totalCount"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      :current-page="pageNum"
      class="mt-2"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />

    <!-- 素材编辑/新增对话框 -->
    <MaterialDialog
      v-model="materialDialogVisible"
      :is-edit="isMaterialEdit"
      :material-data="currentMaterial"
      :category-list="categoryList"
      @success="handleMaterialSuccess"
      @view-detail="handleViewDetailFromEdit"
    />

    <!-- 素材详情对话框 -->
    <MaterialDetailDialog
      v-model="detailDialogVisible"
      :material-data="currentMaterial"
      @update:modelValue="handleDetailDialogClose"
      @edit="handleEditFromDetail"
    />

    <!-- 分类管理对话框 -->
    <CategoryDialog v-model="categoryDialogVisible" @change="handleCategoryChange" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Edit, Refresh, Reading } from "@element-plus/icons-vue";
import {
  getMaterialList,
  getMaterialCategoryList,
  deleteMaterial,
  type Material,
} from "@/api/api-task";
import CategoryDialog from "./dialogs/CategoryDialog.vue";
import MaterialDialog from "./dialogs/MaterialDialog.vue";
import MaterialDetailDialog from "./dialogs/MaterialDetailDialog.vue";

const router = useRouter();

// 状态管理
const loading = ref(false);
const materialList = ref<Material[]>([]);
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);
const searchKeyword = ref("");
const selectedCateId = ref<number | undefined>(undefined); // undefined 表示全部
const categoryList = ref<{ id: number; name: string }[]>([]);

// 对话框
const materialDialogVisible = ref(false);
const detailDialogVisible = ref(false);
const isMaterialEdit = ref(false);
const currentMaterial = ref<Partial<Material>>({});

// 分类对话框
const categoryDialogVisible = ref(false);

// 获取分类列表
const fetchCategoryList = async () => {
  try {
    const res = await getMaterialCategoryList(1, 100); // 获取所有分类
    console.log('分类列表响应:', res);
    if (res.code === 0 && res.data) {
      categoryList.value = res.data.data || [];
      console.log('分类列表数据:', categoryList.value);
      // 默认选中第一个分类
      if (categoryList.value.length > 0 && selectedCateId.value === undefined) {
        const firstCategory = categoryList.value.find(c => c.id !== undefined);
        if (firstCategory) {
          selectedCateId.value = firstCategory.id;
        }
      }
    }
  } catch (error: any) {
    console.error("获取分类列表失败:", error);
  }
};

// 打开分类管理对话框
const openCategoryDialog = () => {
  categoryDialogVisible.value = true;
};

// 分类变化回调
const handleCategoryChange = () => {
  fetchCategoryList();
  fetchMaterialList();
};

// 新增素材
const handleAddMaterial = () => {
  isMaterialEdit.value = false;
  currentMaterial.value = {};
  materialDialogVisible.value = true;
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
    // 刷新列表
    fetchMaterialList();
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
    fetchMaterialList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 素材操作成功回调
const handleMaterialSuccess = () => {
  fetchCategoryList();
  fetchMaterialList();
};

// 分类切换
const onCateChange = () => {
  pageNum.value = 1;
  fetchMaterialList();
};

// 获取素材列表
const fetchMaterialList = async () => {
  loading.value = true;
  try {
    // cate_id 为 undefined 时不传筛选条件
    const cateId = selectedCateId.value !== undefined ? selectedCateId.value : undefined;
    const res = await getMaterialList(cateId, pageNum.value, pageSize.value);
    console.log("获取素材列表响应:", res);
    if (res.code === 0 && res.data) {
      let list = res.data.data || [];
      console.log("素材列表:", list);
      // 前端搜索过滤
      if (searchKeyword.value) {
        list = list.filter((item) =>
          item.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
        );
      }
      materialList.value = list;
      totalCount.value = res.data.totalCount || 0;
    } else {
      console.error("获取素材列表失败:", res);
    }
  } catch (error: any) {
    console.error("获取素材列表异常:", error);
    ElMessage.error(error.message || "获取素材列表失败");
  } finally {
    loading.value = false;
    detailDialogVisible.value = false;
  }
};

// 分页变化
const handlePageChange = (page: number) => {
  pageNum.value = page;
  fetchMaterialList();
};

// 播放/预览素材
const playMaterial = (row: Material) => {
  if (!row.id) return;

  // 将完整的素材数据通过 sessionStorage 传递
  sessionStorage.setItem('previewMaterial', JSON.stringify(row));

  router.push({
    path: "/tasks-preview",
    query: {
      materialId: row.id,
    },
  });
};

// 获取分类名称
const getCategoryName = (cateId: number): string => {
  if (!categoryList.value || categoryList.value.length === 0) {
    return `分类${cateId}`;
  }
  const category = categoryList.value.find((c) => c.id === cateId);
  return category?.name || `分类${cateId}`;
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  pageNum.value = 1;
  fetchMaterialList();
};

// 初始化
onMounted(() => {
  fetchCategoryList();
  fetchMaterialList();
});
</script>
