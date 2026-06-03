<template>
  <div class="p-2">
    <div class="flex items-center h-10">
      <el-button
        @click="refreshPoolList(poolList.pageNum, poolList.pageSize)"
        size="small"
        type="primary"
        plain
      >
        <el-icon>
          <Refresh />
        </el-icon>
      </el-button>
      <el-button type="primary" @click="onAddPoolClk" class="mt-px" size="small">
        <el-icon>
          <Plus />
        </el-icon>
        添加奖池
      </el-button>
    </div>
    <el-table :data="poolList.data" v-loading="loading">
      <el-table-column property="id" label="ID" width="60" />
      <el-table-column property="name" label="奖池名称" min-width="120">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.name" size="small" placeholder="请输入奖池名称" />
            </template>
            <template v-else>
              <span>{{ row.name }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="cost" label="费用" width="80" align="center">
        <template #default="{ row }">
          <template v-if="row.edited">
            <el-input v-model="row.cost" size="small" type="number" placeholder="0" clearable />
          </template>
          <template v-else>
            <span>{{ row.cost ?? "-" }}</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column property="count" label="数量" width="80" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <template v-if="row.edited">
              <el-input v-model="row.count" size="small" type="number" placeholder="0" clearable />
            </template>
            <template v-else>
              <span>{{ row.count ?? "-" }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="count_mx" label="最大数量" width="80" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <template v-if="row.edited">
              <el-input
                v-model="row.count_mx"
                size="small"
                type="number"
                placeholder="0"
                clearable
              />
            </template>
            <template v-else>
              <span>{{ row.count_mx ?? "-" }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="cate_list" label="分类列表" min-width="250">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-select
                v-model="row.cate_ids"
                multiple
                collapse-tags
                collapse-tags-tooltip
                size="small"
                placeholder="选择分类"
                style="width: 100%"
                :max-collapse-tags="5"
              >
                <el-option
                  v-for="cate in categoryList"
                  :key="cate.id"
                  :label="cate.name"
                  :value="cate.id"
                />
              </el-select>
            </template>
            <template v-else>
              <span>{{ row.cate_names && row.cate_names.length > 0 ? row.cate_names : "-" }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Operations" width="300">
        <template #default="{ row }">
          <div class="flex gap-2">
            <el-button v-if="row.edited" size="small" type="primary" @click="handlePoolSave(row)">
              保存
            </el-button>
            <el-button
              v-if="row.edited"
              size="small"
              @click="handlePoolCancel(row, poolList.data.indexOf(row))"
            >
              取消
            </el-button>
            <el-button v-else size="small" @click="handlePoolEdit(row)"> 编辑 </el-button>
            <el-button
              v-if="row.id !== -1"
              size="small"
              type="danger"
              @click="handlePoolDelete(row)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      layout="prev, pager, next"
      :total="poolList.totalCount"
      :page-size="PAGE_SIZE"
      :current-page="poolList.pageNum"
      class="mt-2"
      background
      @current-change="(page: number) => handlePageChange(page, PAGE_SIZE)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Refresh } from "@element-plus/icons-vue";
import {
  getGiftPoolList,
  getGiftPool,
  setGiftPool,
  deleteGiftPool,
  getGiftCategoryList,
  type GiftPoolData,
} from "@/api/api-lottery";

interface PoolItem extends GiftPoolData {
  cate_ids?: number[];
  cate_names?: string;
  edited?: boolean;
}

const parseCateIds = (cateList?: string) =>
  cateList
    ? cateList
        .split(",")
        .map(id => parseInt(id, 10))
        .filter(id => !Number.isNaN(id))
    : [];

const getCategoryNames = (cateIds: number[], categories: Array<{ id: number; name: string }>) => {
  if (!cateIds.length) return "";
  return cateIds
    .map(id => categories.find(c => c.id === id)?.name)
    .filter(Boolean)
    .join("、");
};

const toPoolItem = (item: GiftPoolData, categories: Array<{ id: number; name: string }>): PoolItem => {
  const cateIds = parseCateIds(item.cate_list);
  return {
    ...item,
    count: item.count ?? 0,
    count_mx: item.count_mx ?? 0,
    cate_list: item.cate_list || "",
    cate_ids: cateIds,
    cate_names: getCategoryNames(cateIds, categories),
    edited: false,
  };
};

const PAGE_SIZE = 10;
const poolList = ref<{
  data: PoolItem[];
  pageNum: number;
  pageSize: number;
  totalCount: number;
  totalPage: number;
}>({
  data: [],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});
const loading = ref(false);
const categoryList = ref<Array<{ id: number; name: string }>>([]);

const refreshPoolList = async (pageNum: number, pageSize: number) => {
  loading.value = true;
  try {
    const response = await getGiftPoolList<GiftPoolData>(undefined, pageNum, pageSize);
    if (response?.data) {
      poolList.value.pageNum = response.data.pageNum ?? pageNum;
      poolList.value.pageSize = response.data.pageSize ?? pageSize;
      poolList.value.totalCount = response.data.totalCount ?? 0;
      poolList.value.totalPage =
        response.data.totalPage ??
        Math.ceil((response.data.totalCount ?? 0) / (response.data.pageSize ?? pageSize));
      poolList.value.data = (response.data.data || []).map(item =>
        toPoolItem(item, categoryList.value)
      );
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("获取奖池列表失败");
  } finally {
    loading.value = false;
  }
};

const onAddPoolClk = () => {
  poolList.value.data.unshift({
    id: -1,
    name: "",
    cost: 0,
    count: 0,
    count_mx: 0,
    cate_list: "",
    cate_ids: [],
    cate_names: "",
    edited: true,
  });
};

const handlePoolEdit = (item: PoolItem) => {
  item.edited = true;
};

const handlePoolCancel = async (item: PoolItem, idx: number) => {
  if (item.id === -1) {
    poolList.value.data.splice(idx, 1);
  } else {
    try {
      const data = await getGiftPool<GiftPoolData>(item.id);
      Object.assign(item, toPoolItem(data, categoryList.value));
      item.edited = false;
    } catch (error) {
      console.error("获取奖池数据失败:", error);
      ElMessage.error("恢复数据失败");
    }
  }
};

const handlePoolSave = async (item: PoolItem) => {
  try {
    if (!item.name || !item.name.trim()) {
      ElMessage.warning("请输入奖池名称");
      return;
    }

    const cateListStr = item.cate_ids?.length ? item.cate_ids.join(",") : "";

    const data = {
      id: item.id,
      name: item.name.trim(),
      cost: item.cost,
      count: item.count,
      count_mx: item.count_mx,
      cate_list: cateListStr,
    };
    await setGiftPool(data);
    await refreshPoolList(poolList.value.pageNum, poolList.value.pageSize);
    ElMessage.success("保存成功");
  } catch (error) {
    console.error("保存奖池失败:", error);
    ElMessage.error("保存奖池失败");
  }
};

const handlePoolDelete = async (item: PoolItem) => {
  try {
    await ElMessageBox.confirm(`确定要删除奖池"${item.name}"吗？删除后无法恢复。`, "确认删除", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteGiftPool(item.id);
    await refreshPoolList(poolList.value.pageNum, poolList.value.pageSize);
    ElMessage.success("删除成功");
  } catch (error: unknown) {
    if (error !== "cancel") {
      console.error("删除奖池失败:", error);
      ElMessage.error("删除奖池失败");
    }
  }
};

const handlePageChange = (pageNum: number, pageSize: number) => {
  refreshPoolList(pageNum, pageSize);
};

const refreshCategoryList = async () => {
  try {
    const response = await getGiftCategoryList<{ id: number; name: string }>();
    categoryList.value = response.data?.data ?? [];
  } catch (error) {
    console.error("获取分类列表失败:", error);
  }
};

const handleRefresh = () => refreshPoolList(poolList.value.pageNum, poolList.value.pageSize);

onMounted(() => {
  refreshCategoryList();
  refreshPoolList(1, PAGE_SIZE);
  window.addEventListener("refresh-pool-tab", handleRefresh);
});

onUnmounted(() => {
  window.removeEventListener("refresh-pool-tab", handleRefresh);
});
</script>
<style scoped></style>
