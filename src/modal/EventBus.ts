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
  /** 未登录或 token 失效，应显示登录页 */
  AUTH_EXPIRED: "authExpired",
};

export default EventBus;
