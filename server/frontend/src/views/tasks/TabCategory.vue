<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex-1 flex items-center justify-end gap-2">
        <el-button type="primary" size="small" @click="handleAddCategory">添加分类</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="categoryList" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="分类名称" min-width="200" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEditCategory(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDeleteCategory(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="mt-4 flex justify-end">
      <el-pagination
        v-model:current-page="pageNum"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="totalCount"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 编辑/新增对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑分类' : '新增分类'"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="分类名称" required>
          <el-input v-model="formData.name" placeholder="请输入分类名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getMaterialCategoryList,
  addMaterialCategory,
  updateMaterialCategory,
  deleteMaterialCategory,
  type MaterialCategory,
} from "@/api/api-task";

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const categoryList = ref<MaterialCategory[]>([]);
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);

// 对话框
const dialogVisible = ref(false);
const isEdit = ref(false);
const formData = ref<Partial<MaterialCategory>>({
  name: "",
});
const currentId = ref<number | null>(null);

// 获取分类列表
const fetchCategoryList = async () => {
  loading.value = true;
  try {
    const res = await getMaterialCategoryList(pageNum.value, pageSize.value);
    if (res.code === 0 && res.data) {
      categoryList.value = res.data.data || [];
      totalCount.value = res.data.totalCount || 0;
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取分类列表失败");
  } finally {
    loading.value = false;
  }
};

// 分页变化
const handlePageChange = (page: number) => {
  pageNum.value = page;
  fetchCategoryList();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  pageNum.value = 1;
  fetchCategoryList();
};

// 新增分类
const handleAddCategory = () => {
  isEdit.value = false;
  currentId.value = null;
  formData.value = {
    name: "",
  };
  dialogVisible.value = true;
};

// 编辑分类
const handleEditCategory = (row: MaterialCategory) => {
  isEdit.value = true;
  currentId.value = row.id || null;
  formData.value = {
    name: row.name,
  };
  dialogVisible.value = true;
};

// 删除分类
const handleDeleteCategory = async (row: MaterialCategory) => {
  try {
    await ElMessageBox.confirm("确定要删除该分类吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    await deleteMaterialCategory(row.id!);
    ElMessage.success("删除成功");
    fetchCategoryList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!formData.value.name) {
    ElMessage.warning("请填写分类名称");
    return;
  }

  submitting.value = true;
  try {
    if (isEdit.value && currentId.value) {
      await updateMaterialCategory({
        id: currentId.value,
        name: formData.value.name,
      } as MaterialCategory);
      ElMessage.success("更新成功");
    } else {
      await addMaterialCategory({
        name: formData.value.name,
      });
      ElMessage.success("添加成功");
    }
    dialogVisible.value = false;
    fetchCategoryList();
  } catch (error: any) {
    ElMessage.error(error.message || "操作失败");
  } finally {
    submitting.value = false;
  }
};

// 初始化
onMounted(() => {
  fetchCategoryList();
});
</script>
