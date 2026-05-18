<template>
  <el-dialog v-model="visible" title="类别管理" width="800" destroy-on-close align-center>
    <el-table :data="categoryList">
      <el-table-column property="id" label="ID" width="50" />
      <el-table-column property="name" label="Name" width="150">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.name" size="small"
                @blur="handleCateBlur(row, 'name', categoryList.indexOf(row))" />
            </template>
            <template v-else>
              <span> {{ row.name }} </span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="OP">
        <template #default="{ row }">
          <el-button v-if="row.edited" class="w-16" size="small" type="primary"
            @click="handleCateSave(row, categoryList.indexOf(row))">
            Save
          </el-button>
          <el-button v-if="row.edited" class="w-16" size="small"
            @click="handleCateCancel(row, categoryList.indexOf(row))">
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
import { ElMessage } from "element-plus";
import { getList, setData, delData } from "@/api/api-common";
import * as _ from "lodash-es";
import type { GiftCategory } from "@/types/lottery";

interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'refresh'): void;
}>();

const visible = ref(props.modelValue);
const categoryList = ref<GiftCategory[]>([]);

watch(() => props.modelValue, (newVal) => {
  visible.value = newVal;
  if (newVal) {
    refreshCategoryList();
  }
});

watch(visible, (newVal) => {
  emit('update:modelValue', newVal);
});

const refreshCategoryList = async () => {
  try {
    const response = await getList<GiftCategory>("t_gift_category");
    if (response && response.data) {
      const d = response.data.data || [];

      categoryList.value = [];
      categoryList.value.push({ id: -1, name: "", edited: true });
      _.forEach(d, (item: GiftCategory) => {
        categoryList.value.push({
          id: item.id,
          name: item.name,
          edited: false,
        });
      });
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(JSON.stringify(err));
  }
};

const handleCateBlur = (item: GiftCategory, key: string, _idx: number) => {
  console.log("handleCateBlur", item, key);
};

const handleCateSave = async (item: GiftCategory, _idx: number) => {
  try {
    const data = {
      id: item.id,
      name: item.name,
    };
    await setData("t_gift_category", data);
    await refreshCategoryList();
    emit('refresh');
  } catch (error) {
    console.error("保存类别失败:", error);
    ElMessage.error("保存类别失败");
  }
};

const handleCateDelete = async (item: GiftCategory) => {
  try {
    await delData("t_gift_category", item.id);
    await refreshCategoryList();
    emit('refresh');
  } catch (error) {
    console.error("删除类别失败:", error);
    ElMessage.error("删除类别失败");
  }
};

const handleCateEdit = (item: GiftCategory) => {
  item.edited = true;
};

const handleCateCancel = (item: GiftCategory, _idx: number) => {
  if (item.id === -1) {
    item.name = "";
  } else {
    item.edited = false;
  }
};
</script>

<style scoped></style>
