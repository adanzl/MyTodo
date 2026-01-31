/**
 * 网络与 API 工具：统一从 @/api 再导出，保持对 @/utils/NetUtil 的兼容。
 * 新代码建议直接从 @/api 或 @/api/schedule、@/api/chat 等按模块引用。
 */

const AXIOS_ERR_NETWORK = "ERR_NETWORK";
const AXIOS_ERR_TIMEOUT = "ECONNABORTED";

/** 将接口/网络错误转为用户可读的提示文案，用于聊天、抽奖等强依赖后端的场景。 */
export function getNetworkErrorMessage(err: unknown): string {
  if (err == null) return "请求失败，请稍后重试";

  const ax = err as {
    code?: string;
    response?: { status?: number; data?: { msg?: string } };
    message?: string;
  };
  if (ax.code === AXIOS_ERR_NETWORK || ax.response?.status === 0) {
    return "网络异常，请检查网络后重试";
  }
  if (ax.code === AXIOS_ERR_TIMEOUT) {
    return "请求超时，请稍后重试";
  }
  if (ax.response?.status != null && ax.response.status >= 500) {
    return "服务暂时不可用，请稍后重试";
  }
  const msg = ax.response?.data?.msg;
  if (typeof msg === "string" && msg.trim()) return msg;

  if (err instanceof Error && err.message) return err.message;
  if (typeof (err as { message?: string }).message === "string") {
    return (err as { message: string }).message;
  }
  return "请求失败，请稍后重试";
}

export {
  getApiUrl,
  initNet,
  checkLocalAddressAvailable,
  checkAndSwitchServer,
  switchToLocal,
  switchToRemote,
  isLocalIpAvailable,
} from "@/api/api-client";

export { getSave, setSave, getScheduleList } from "@/api/schedule";
export { getUserInfo, setUserData, getUserList, addScore } from "@/api/user";
export {
  getConversationId,
  setConversationId,
  getChatSetting,
  setChatSetting,
  getChatMessages,
  getAiChatMessages,
  getChatMem,
  setChatMem,
} from "@/api/chat";
export {
  getLotteryData,
  setLotteryData,
  getGiftData,
  doLottery,
} from "@/api/lottery";
export {
  createTtsTask,
  getTtsTaskList,
  getTtsDownloadUrl,
  downloadTtsAudio,
  updateTtsTask,
  deleteTtsTask,
  startTtsTask,
  startTtsAnalysis,
  ocrTtsTask,
} from "@/api/tts";
export type { TtsTaskItem, TtsTaskAnalysis } from "@/api/tts";
export { getPic, getPicList, setPic, delPic } from "@/api/pic";
export { getColorList, setColor, delColor } from "@/api/color";
export { getList, getRdsData, setRdsData } from "@/api/data";

export default {};
