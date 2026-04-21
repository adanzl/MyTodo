<template>
  <el-dialog
    v-model="visible"
    title="分类管理"
    width="800"
    destroy-on-close
    @close="handleClose"
  >
    <el-table :data="categoryPopList">
      <el-table-column property="id" label="ID" width="50" />
      <el-table-column property="name" label="Name" width="150">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.name" size="small"
                @blur="handleCateBlur(row)" />
            </template>
            <template v-else>
              <span>{{ row.name }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="OP">
        <template #default="{ row }">
          <el-button v-if="row.edited" class="w-16" size="small" type="primary"
            @click="handleCateSave(row)">
            Save
          </el-button>
          <el-button v-if="row.edited" class="w-16" size="small"
            @click="handleCateCancel(row, categoryPopList.indexOf(row))">
            Cancel
          </el-button>
          <el-button v-else size="small" class="w-16" @click="handleCateEdit(row)">
            Edit
          </el-button>
          <el-button v-if="row.id !== -1" class="w-16" size="small" type="danger" @click="handleCateDelete(row)">
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import * as _ from "lodash-es";
import {
  getMaterialCategoryList,
  addMaterialCategory,
  updateMaterialCategory,
  deleteMaterialCategory,
  type MaterialCategory,
} from "@/api/api-task";

interface CategoryPopItem extends MaterialCategory {
  edited?: boolean;
  originalName?: string;
}

interface Props {
  modelValue: boolean;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "change"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(props.modelValue);
const categoryPopList = ref<CategoryPopItem[]>([]);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val) {
      fetchCategoryList();
    }
  }
);

// 监听 visible 变化
watch(visible, (val) => {
  emit("update:modelValue", val);
});

// 获取分类列表
const fetchCategoryList = async () => {
  try {
    const res = await getMaterialCategoryList(1, 100);
    if (res.code === 0 && res.data) {
      const list = res.data.data || [];

      // 构建弹窗列表
      categoryPopList.value = [];
      categoryPopList.value.push({ id: -1, name: "", edited: true });
      _.forEach(list, (item: MaterialCategory) => {
        categoryPopList.value.push({
          id: item.id,
          name: item.name,
          edited: false,
        });
      });
    }
  } catch (error: any) {
    console.error("获取分类列表失败:", error);
    ElMessage.error("获取分类列表失败");
  }
};

// 编辑分类
const handleCateEdit = (row: CategoryPopItem) => {
  row.originalName = row.name;
  row.edited = true;
};

// 保存分类
const handleCateSave = async (row: CategoryPopItem) => {
  if (!row.name) {
    ElMessage.warning("分类名称不能为空");
    return;
  }

  try {
    if (row.id === -1) {
      // 新增
      const res = await addMaterialCategory({ name: row.name });
      row.id = res.id;
      ElMessage.success("添加成功");
    } else {
      // 更新
      await updateMaterialCategory({ id: row.id, name: row.name } as MaterialCategory);
      ElMessage.success("更新成功");
    }
    row.edited = false;
    await fetchCategoryList();
    emit("change");
  } catch (error: any) {
    ElMessage.error(error.message || "操作失败");
  }
};

// 取消编辑
const handleCateCancel = (row: CategoryPopItem, index: number) => {
  if (row.id === -1) {
    // 新增的取消，直接删除
    categoryPopList.value.splice(index, 1);
  } else {
    // 编辑的取消，恢复原名
    row.name = row.originalName || row.name;
    row.edited = false;
  }
};

// 失焦自动保存（可选）
const handleCateBlur = (row: CategoryPopItem) => {
  if (row.name && row.name !== row.originalName) {
    handleCateSave(row);
  }
};

// 删除分类
const handleCateDelete = async (row: CategoryPopItem) => {
  try {
    await ElMessageBox.confirm("确定要删除该分类吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    await deleteMaterialCategory(row.id!);
    ElMessage.success("删除成功");
    await fetchCategoryList();
    emit("change");
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 关闭对话框
const handleClose = () => {
  visible.value = false;
};
</script>
