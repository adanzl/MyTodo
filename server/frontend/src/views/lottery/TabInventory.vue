<template>
  <div class="p-2">
    <div class="flex items-center gap-2 h-10 mb-2">
      <el-button
        size="small"
        type="primary"
        plain
        @click="handleRefresh"
        :icon="Refresh"
        :loading="loading"
      />
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :span="12" v-for="user in displayUsers" :key="user.id">
        <h2
          class="text-xs font-bold text-white mb-3 text-center py-2 rounded-lg"
          :class="user.id === USER_CANCAN_ID ? 'bg-linear-to-br from-[#f093fb] to-[#f5576c]' : 'bg-linear-to-br from-[#667eea] to-[#764ba2]'"
        >
          {{ user.name }}
        </h2>
        <el-table
          :data="getInventoryRows(user.inventory)"
          stripe
          :max-height="tableMaxHeight"
          empty-text="暂无库存"
        >
          <el-table-column label="类别" prop="cateName" min-width="120" show-overflow-tooltip />
          <el-table-column label="数量" prop="quantity" width="80" align="center" />
        </el-table>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { getGiftCategoryList } from "@/api/api-lottery";
import type { GiftCategory } from "@/types/lottery";
import { useUserStore } from "@/stores/user";

const USER_CANCAN_ID = 3;
const USER_ZHAOZHAO_ID = 4;

interface InventoryRow {
  cateId: number;
  cateName: string;
  quantity: number;
}

const userStore = useUserStore();
const loading = ref(false);
const cateMap = ref<Map<number, string>>(new Map());
const tableMaxHeight = ref(400);

const displayUsers = computed(() => {
  const ids = [USER_CANCAN_ID, USER_ZHAOZHAO_ID];
  return ids.map(id => {
    const user = userStore.getUserById(id);
    return {
      id,
      name: id === USER_CANCAN_ID ? "灿灿" : "昭昭",
      inventory: user?.inventory,
    };
  });
});

const parseInventory = (inventory?: string): Record<string, number> => {
  if (!inventory || inventory.trim() === "") return {};
  try {
    const parsed = JSON.parse(inventory);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, number>;
    }
  } catch {
    // ignore invalid json
  }
  return {};
};

const getCateLabel = (cateId: number) => cateMap.value.get(cateId) ?? `分类${cateId}`;

const getInventoryRows = (inventory?: string): InventoryRow[] => {
  const data = parseInventory(inventory);
  return Object.entries(data)
    .map(([cateIdStr, quantity]) => {
      const cateId = Number(cateIdStr);
      return {
        cateId,
        cateName: getCateLabel(cateId),
        quantity: Number(quantity) || 0,
      };
    })
    .filter(row => row.quantity > 0)
    .sort((a, b) => a.cateId - b.cateId);
};

const calculateTableHeight = () => {
  nextTick(() => {
    tableMaxHeight.value = window.innerHeight - 320;
  });
};

const loadCateMap = async () => {
  try {
    const response = await getGiftCategoryList<GiftCategory>(undefined, 1, 500);
    const categories = response.data?.data || [];
    cateMap.value = new Map(categories.map(item => [item.id, item.name]));
  } catch (error) {
    console.error("获取礼物分类失败:", error);
  }
};

const loadData = async () => {
  loading.value = true;
  try {
    await userStore.refreshUserList(true);
    await loadCateMap();
  } finally {
    loading.value = false;
  }
};

const handleRefresh = () => {
  loadData();
};

onMounted(async () => {
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);
  window.addEventListener("refresh-lottery-inventory-tab", handleRefresh);
  await loadData();
});

onUnmounted(() => {
  window.removeEventListener("resize", calculateTableHeight);
  window.removeEventListener("refresh-lottery-inventory-tab", handleRefresh);
});
</script>
