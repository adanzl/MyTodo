export {
  apiClient,
  getApiUrl,
  initNet,
  scheduleProactiveRefresh,
  checkLocalAddressAvailable,
  checkAndSwitchServer,
  switchToLocal,
  switchToRemote,
  isLocalIpAvailable,
} from "./api-client";

export { getSave, setSave, getScheduleList } from "./api-schedule";
export {
  getUserInfo,
  setUserData,
  getUserList,
  addScore,
  clearUserListCache,
} from "./api-user";
export {
  getConversationId,
  setConversationId,
  getChatSetting,
  setChatSetting,
  getChatMessages,
  getAiChatMessages,
  getChatMem,
  setChatMem,
} from "./api-chat";
export {
  getLotteryData,
  setLotteryData,
  getGiftData,
  doLottery,
  doExchange,
} from "./api-lottery";
export {
  createTtsTask,
  getTtsTaskList,
  getTtsDownloadUrl,
  downloadTtsAudio,
  updateTtsTask,
  deleteTtsTask,
  startTtsAnalysis,
  ocrTtsTask,
} from "./api-tts";
export type { TtsTaskItem, TtsTaskAnalysis } from "./api-tts";
export type {
  ApiResponse,
  ApiListResponse,
  ApiPagedResponse,
  GetRdsListResponse,
  UserInfo,
  UserListItem,
  GetUserListResponse,
  ScheduleListItem,
  GiftItem,
  GiftListItem,
  GiftCategoryItem,
  DoLotteryResult,
  ColorListItem,
  PicListItem,
  LotteryConfig,
  CreateTtsTaskResponse,
  CreateTtsTaskBody,
  UpdateTtsTaskBody,
  TtsTaskIdBody,
} from "./types";
export { getPic, getPicList, setPic, delPic } from "./api-pic";
export { getColorList, setColor, delColor } from "./api-color";
export { getList, getRdsData, setRdsData, setData, delData } from "./data";
