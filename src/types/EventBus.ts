import { reactive } from "vue";

type EventCallback = (...args: any[]) => void;

const EventBus = reactive({
  events: {} as Record<string, EventCallback[]>,

  $on(event: string, callback: EventCallback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  },

  $emit(event: string, ...args: any[]) {
    const callbacks = this.events[event];
    if (callbacks) {
      callbacks.forEach((callback) => callback(...args));
    }
  },

  $off(event: string, callback: EventCallback) {
    const callbacks = this.events[event];
    if (callbacks) {
      this.events[event] = callbacks.filter((cb) => cb !== callback);
    }
  },
});

export const C_EVENT = {
  MENU_CLOSE: "menuClose",
  UPDATE_COLOR: "updateColor",
  UPDATE_SAVE: "updateSave",
  UPDATE_SCHEDULE_GROUP: "updateScheduleListId",
  UPDATE_USER_INFO: "updateUserInfo",
  REWARD: "reward",
  TOAST: "toast",
  /** 抽奖：从设置页跳转到指定奖品类别 */
  LOTTERY_NAV_TO_CATE: "lotteryNavToCate",
  /** 未登录或 token 失效，应显示登录页 */
  AUTH_EXPIRED: "authExpired",
  /** 登录缓存已清除（登出/401 等），用于取消 proactive refresh 定时器 */
  LOGIN_CACHE_CLEARED: "loginCacheCleared",
  /** 本地/远程地址切换（payload: boolean，true=使用远程） */
  SERVER_SWITCH: "serverSwitch",
};

export default EventBus;
