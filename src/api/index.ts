export {
  apiClient,
  getApiUrl,
  initNet,
  checkLocalAddressAvailable,
  checkAndSwitchServer,
  switchToLocal,
  switchToRemote,
  isLocalIpAvailable,
} from "./api-client";

export { getSave, setSave, getScheduleList } from "./schedule";
export {
  getUserInfo,
  setUserData,
  getUserList,
  addScore,
  clearUserListCache,
} from "./user";
export {
  getConversationId,
  setConversationId,
  getChatSetting,
  setChatSetting,
  getChatMessages,
  getAiChatMessages,
  getChatMem,
  setChatMem,
} from "./chat";
export {
  getLotteryData,
  setLotteryData,
  getGiftData,
  doLottery,
} from "./lottery";
export {
  createTtsTask,
  getTtsTaskList,
  getTtsDownloadUrl,
  downloadTtsAudio,
  updateTtsTask,
  deleteTtsTask,
  startTtsAnalysis,
  ocrTtsTask,
} from "./tts";
export type { TtsTaskItem, TtsTaskAnalysis } from "./tts";
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
export { getPic, getPicList, setPic, delPic } from "./pic";
export { getColorList, setColor, delColor } from "./color";
export { getList, getRdsData, setRdsData } from "./data";
