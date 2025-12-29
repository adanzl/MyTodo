/**
 * 用户 Store
 * 管理用户列表和当前用户状态
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getList } from "@/api/common";
import { ElMessage } from "element-plus";
import type { User } from "@/types/user";

export interface UserWithExtras extends User {
  wish_progress?: number;
  wish_list?: string;
}

export const useUserStore = defineStore("user", () => {
  // 状态
  const userList = ref<UserWithExtras[]>([]);
  const loading = ref(false);
  const lastFetchTime = ref<number | null>(null);

  // 缓存时间（毫秒），5分钟内不重复请求
  const CACHE_DURATION = 5 * 60 * 1000;

  // Getters
  const getUserById = (id: number | string) => {
      return userList.value.find(user => String(user.id) === String(id));
    };

  const isDataFresh = computed(() => {
    if (!lastFetchTime.value) return false;
    return Date.now() - lastFetchTime.value < CACHE_DURATION;
  });

  // Actions
  /**
   * 刷新用户列表
   * @param force 是否强制刷新（忽略缓存）
   */
  const refreshUserList = async (force = false) => {
    // 如果数据新鲜且不强制刷新，直接返回
    if (!force && isDataFresh.value && userList.value.length > 0) {
      return;
    }

    loading.value = true;
    try {
      const response = await getList<UserWithExtras>("t_user");
      if (response && response.data) {
        // API 返回的是分页格式，用户数组在 response.data 中（PaginatedResponse 的 data 就是数组）
        // 但实际 API 可能返回 { data: { data: [...] } } 格式，需要兼容处理
        const data = response.data as unknown as { data?: UserWithExtras[] } | UserWithExtras[];
        const users = Array.isArray(data) ? data : (data as { data?: UserWithExtras[] }).data || [];
        userList.value = Array.isArray(users) ? users : [];
        lastFetchTime.value = Date.now();
      } else {
        userList.value = [];
      }
    } catch (error) {
      console.error("获取用户列表失败:", error);
      ElMessage.error("获取用户列表失败");
      userList.value = [];
    } finally {
      loading.value = false;
    }
  };

  /**
   * 清除用户列表缓存
   */
  const clearCache = () => {
    lastFetchTime.value = null;
  };

  return {
    // 状态
    userList,
    loading,
    lastFetchTime,
    // Getters
    getUserById,
    isDataFresh,
    // Actions
    refreshUserList,
    clearCache,
  };
});
