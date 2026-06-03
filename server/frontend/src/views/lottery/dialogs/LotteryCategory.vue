<template>
  <el-dialog v-model="visible" title="类别管理" width="800" destroy-on-close align-center>
    <el-table :data="categoryList">
      <el-table-column property="id" label="ID" width="50" />
      <el-table-column property="name" label="Name" width="150">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.name" size="small" />
            </template>
            <template v-else>
              <span> {{ row.name }} </span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="OP">
        <template #default="{ row }">
          <el-button
            v-if="row.edited"
            class="w-16"
            size="small"
            type="primary"
            @click="handleCateSave(row)"
          >
            Save
          </el-button>
          <el-button
            v-if="row.edited"
            class="w-16"
            size="small"
            @click="handleCateCancel(row)"
          >
            Cancel
          </el-button>
          <el-button v-else size="small" class="w-16" @click="handleCateEdit(row)">
            Edit
          </el-button>
          <el-button
            v-if="row.id !== -1"
            class="w-16"
            size="small"
            type="danger"
            @click="handleCateDelete(row)"
          >
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { getGiftCategoryList, setGiftCategory, deleteGiftCategory } from "@/api/api-lottery";
import type { GiftCategory } from "@/types/lottery";

interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "refresh"): void;
}>();

const visible = ref(props.modelValue);
const categoryList = ref<GiftCategory[]>([]);

watch(
  () => props.modelValue,
  newVal => {
    visible.value = newVal;
    if (newVal) {
      refreshCategoryList();
    }
  }
);

watch(visible, newVal => {
  emit("update:modelValue", newVal);
});

const refreshCategoryList = async () => {
  try {
    const response = await getGiftCategoryList<GiftCategory>();
    const list = response.data?.data ?? [];
    categoryList.value = [
      { id: -1, name: "", edited: true },
      ...list.map(item => ({ id: item.id, name: item.name, edited: false })),
    ];
  } catch (err) {
    console.error(err);
    ElMessage.error("获取类别失败");
  }
};

const handleCateSave = async (item: GiftCategory) => {
  try {
    await setGiftCategory({ id: item.id, name: item.name });
    await refreshCategoryList();
    emit("refresh");
  } catch (error) {
    console.error("保存类别失败:", error);
    ElMessage.error("保存类别失败");
  }
};

const handleCateDelete = async (item: GiftCategory) => {
  try {
    await deleteGiftCategory(item.id);
    await refreshCategoryList();
    emit("refresh");
  } catch (error) {
    console.error("删除类别失败:", error);
    ElMessage.error("删除类别失败");
  }
};

const handleCateEdit = (item: GiftCategory) => {
  item.edited = true;
};

const handleCateCancel = (item: GiftCategory) => {
  if (item.id === -1) {
    item.name = "";
  } else {
    item.edited = false;
  }
};
</script>
<style scoped></style>
