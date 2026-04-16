<template>
  <div class="p-2">
    <div class="flex items-center justify-between mb-0">
      <el-button type="primary" @click="onAddPoolClk" class="h-9.5! mt-px">
        <el-icon>
          <Plus />
        </el-icon>
        添加奖池
      </el-button>
    </div>
    <el-table :data="poolList.data" v-loading="loading">
      <el-table-column property="id" label="ID" width="80" />
      <el-table-column property="name" label="奖池名称" width="200">
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
      <el-table-column property="cost" label="费用" width="100">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.cost" size="small" type="number" placeholder="0" clearable />
            </template>
            <template v-else>
              <span>{{ row.cost ?? '-' }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="count" label="数量" width="80">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.count" size="small" type="number" placeholder="0" clearable />
            </template>
            <template v-else>
              <span>{{ row.count ?? '-' }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="count_mx" label="最大数量" width="80">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.count_mx" size="small" type="number" placeholder="0" clearable />
            </template>
            <template v-else>
              <span>{{ row.count_mx ?? '-' }}</span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="cate_list" label="分类列表" min-width="250">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-select v-model="row.cate_ids" multiple collapse-tags collapse-tags-tooltip size="small"
                placeholder="选择分类" style="width: 100%">
                <el-option v-for="cate in categoryList" :key="cate.id" :label="cate.name" :value="cate.id" />
              </el-select>
            </template>
            <template v-else>
              <span>{{ row.cate_names || '-' }}</span>
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
            <el-button v-if="row.edited" size="small" @click="handlePoolCancel(row, poolList.data.indexOf(row))">
              取消
            </el-button>
            <el-button v-else size="small" @click="handlePoolEdit(row)">
              编辑
            </el-button>
            <el-button v-if="row.id !== -1" size="small" type="danger" @click="handlePoolDelete(row)">
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination layout="prev, pager, next" :total="poolList.totalCount" :page-size="PAGE_SIZE"
      :current-page="poolList.pageNum" class="mt-2" background
      @current-change="(page: number) => handlePageChange(page, PAGE_SIZE)" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import { getList, getData, setData, delData } from "@/api/api-common";
import * as _ from "lodash-es";

interface PoolItem {
  id: number;
  name: string;
  cost?: number;
  count?: number;
  count_mx?: number;
  cate_list?: string;
  cate_ids?: number[];
  cate_names?: string;
  edited?: boolean;
}

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
    const response = await getList<PoolItem>("t_gift_pool", undefined, pageNum, pageSize);
    if (response && response.data) {
      const d = response.data.data || [];
      poolList.value.data = [];
      poolList.value.pageNum = response.data.pageNum ?? pageNum;
      poolList.value.pageSize = response.data.pageSize ?? pageSize;
      poolList.value.totalCount = response.data.totalCount ?? 0;
      poolList.value.totalPage =
        response.data.totalPage ??
        Math.ceil((response.data.totalCount ?? 0) / (response.data.pageSize ?? pageSize));

      _.forEach(d, item => {
        // 解析分类 ID 列表
        const cateIds = item.cate_list ? item.cate_list.split(',').map(id => parseInt(id)).filter(id => !isNaN(id)) : [];
        // 获取对应的分类名称
        const cateNames = getCategoryNames(cateIds, categoryList.value);

        poolList.value.data.push({
          id: item.id,
          name: item.name,
          cost: item.cost,
          count: item.count ?? 0,
          count_mx: item.count_mx ?? 0,
          cate_list: item.cate_list || "",
          cate_ids: cateIds,
          cate_names: cateNames,
          edited: false,
        });
      });
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(JSON.stringify(err));
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
      const data = await getData<PoolItem>("t_gift_pool", item.id);
      console.log("取消编辑 - 获取到的数据:", data);
      // 恢复原始数据
      item.name = data.name || item.name;
      item.cost = data.cost || item.cost;
      item.count = data.count ?? item.count;
      item.count_mx = data.count_mx ?? item.count_mx;
      item.cate_list = data.cate_list ?? item.cate_list;
      // 重新解析分类
      const cateIds = item.cate_list ? item.cate_list.split(',').map(id => parseInt(id)).filter(id => !isNaN(id)) : [];
      item.cate_ids = cateIds;
      item.cate_names = getCategoryNames(cateIds, categoryList.value);
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

    // 将分类 ID 数组转换为逗号分隔的字符串
    const cateListStr = item.cate_ids && item.cate_ids.length > 0
      ? item.cate_ids.join(',')
      : '';

    const data = {
      id: item.id,
      name: item.name.trim(),
      cost: item.cost,
      count: item.count,
      count_mx: item.count_mx,
      cate_list: cateListStr,
    };
    await setData("t_gift_pool", data);
    await refreshPoolList(poolList.value.pageNum, poolList.value.pageSize);
    ElMessage.success("保存成功");
  } catch (error) {
    console.error("保存奖池失败:", error);
    ElMessage.error("保存奖池失败");
  }
};

const handlePoolDelete = async (item: PoolItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除奖池"${item.name}"吗？删除后无法恢复。`,
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    await delData("t_gift_pool", item.id);
    await refreshPoolList(poolList.value.pageNum, poolList.value.pageSize);
    ElMessage.success("删除成功");
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除奖池失败:", error);
      ElMessage.error("删除奖池失败");
    }
  }
};

const handlePageChange = (pageNum: number, pageSize: number) => {
  refreshPoolList(pageNum, pageSize);
};

// 辅助函数：根据分类 ID 列表获取分类名称
const getCategoryNames = (cateIds: number[], categories: Array<{ id: number; name: string }>): string => {
  if (!cateIds || cateIds.length === 0) return '';
  const names = cateIds
    .map(id => categories.find(c => c.id === id)?.name)
    .filter(name => name) as string[];
  return names.join('、');
};

// 加载所有分类
const refreshCategoryList = async () => {
  try {
    const response = await getList<{ id: number; name: string }>("t_gift_category");
    if (response && response.data) {
      categoryList.value = response.data.data || [];
    }
  } catch (error) {
    console.error("获取分类列表失败:", error);
  }
};

onMounted(() => {
  refreshCategoryList();
  refreshPoolList(1, PAGE_SIZE);
});
</script>

<style scoped></style>
