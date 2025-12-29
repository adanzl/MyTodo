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

export interface CurUser {
  bLogin: boolean;
  id: number | null;
  name: string | null;
  ico: string | null;
}

export const useUserStore = defineStore("user", () => {
  // 状态
  const userList = ref<UserWithExtras[]>([]);
  const loading = ref(false);
  const lastFetchTime = ref<number | null>(null);
  const curUser = ref<CurUser>({ bLogin: false, id: null, name: null, ico: null });

  // 缓存时间（毫秒），5分钟内不重复请求
  const CACHE_DURATION = 5 * 60 * 1000;

  // localStorage key
  const KEY_USER_ID = "user_id";

  // Getters
  const getUserById = (id: number | string) => {
    return userList.value.find(user => String(user.id) === String(id));
  };

  const isDataFresh = computed(() => {
    if (!lastFetchTime.value) return false;
    return Date.now() - lastFetchTime.value < CACHE_DURATION;
  });

  // 当前用户是否已登录
  const isLoggedIn = computed(() => curUser.value.bLogin);

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
        userList.value = response.data.data || [];
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

  /**
   * 设置当前用户（登录）
   */
  const setCurUser = (user: UserWithExtras) => {
    curUser.value = {
      bLogin: true,
      id: user.id,
      name: user.name,
      ico: user.icon || null,
    };
    localStorage.setItem(KEY_USER_ID, String(user.id));
  };

  /**
   * 清除当前用户（登出）
   */
  const clearCurUser = () => {
    curUser.value = { bLogin: false, id: null, name: null, ico: null };
    localStorage.removeItem(KEY_USER_ID);
  };

  /**
   * 从 localStorage 恢复当前用户
   */
  const restoreCurUser = async () => {
    const uId = localStorage.getItem(KEY_USER_ID);
    if (uId) {
      // 确保用户列表已加载
      if (userList.value.length === 0) {
        await refreshUserList();
      }
      const u = getUserById(uId);
      if (u) {
        setCurUser(u);
      }
    }
  };

  /**
   * 获取当前用户的完整信息
   */
  const getCurUserFullInfo = (): UserWithExtras | null => {
    if (!curUser.value.id) return null;
    return getUserById(curUser.value.id) || null;
  };

  return {
    // 状态
    userList,
    loading,
    lastFetchTime,
    curUser,
    // Getters
    getUserById,
    isDataFresh,
    isLoggedIn,
    // Actions
    refreshUserList,
    clearCache,
    setCurUser,
    clearCurUser,
    restoreCurUser,
    getCurUserFullInfo,
  };
});
