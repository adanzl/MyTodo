/**
 * API 层与后端约定的请求/响应类型
 * 与 src/types/ 中的领域类型区分：此处仅描述 HTTP 接口的入参与返回结构
 */

/** 后端统一响应壳：code=0 表示成功，data 为业务数据 */
export interface ApiResponse<T = unknown> {
  code: number;
  msg?: string;
  data?: T;
}

// ----- 通用 / getData・setData -----

/** getData 通用查询参数 */
export interface GetDataParams {
  table: string;
  id: number;
  fields?: string;
}

/** setData 通用请求体 */
export interface SetDataBody<T = unknown> {
  table: string;
  data: T;
}

/** getAll 通用列表响应（部分接口返回 { data: T[] }） */
export interface ApiListResponse<T> {
  data: T[];
}

// ----- user -----

/** 用户基础信息（getData t_user 等返回） */
export interface UserInfo {
  id: number;
  score?: number;
  [key: string]: unknown;
}

/** 用户列表项（getAllUser 单条，含 wish_list 等） */
export interface UserListItem {
  id: number;
  name?: string;
  score?: number;
  wish_list?: unknown;
  [key: string]: unknown;
}

/** getAllUser 响应：后端返回 data.data 为列表 */
export interface GetUserListResponse {
  data: UserListItem[];
}

/** setUserData 入参：可部分字段 */
export type SetUserDataPayload = Partial<Record<string, unknown>>;

/** addScore 请求体 */
export interface AddScoreBody {
  user: number;
  action: string;
  value: number;
  msg: string;
}

// ----- schedule -----

/** getSave 接口返回的原始 data 结构 */
export interface GetSaveResponseData {
  data: string;
  user_id: number;
}

/** getScheduleList 单条：id, name, user_id */
export interface ScheduleListItem {
  id: number;
  name?: string;
  user_id?: number;
  [key: string]: unknown;
}

/** setSave 请求体中的 data 字段 */
export interface SetSaveDataBody {
  id: number;
  data: string;
}

// ----- chat -----

/** getRdsData / setRdsData 用于 chatSetting、mem、conversation:id 等 */
export interface RdsKeyValueBody {
  id: number;
  value: string;
}

/** getRdsList 聊天消息列表等 */
export interface GetRdsListParams {
  key: string;
  pageSize: number;
  startId?: number | string;
}

/** getChatMessages 返回结构按实际列表使用，此处仅约束为数组或列表形态 */
export type ChatMessagesData = unknown;

/** getAiChatMessages 参数 */
export interface GetAiChatMessagesParams {
  conversation_id: string;
  limit: number;
  user: string;
  first_id?: string | number;
}

// ----- lottery -----

/** getGiftData 单条礼品 */
export interface GiftItem {
  id?: number;
  name?: string;
  image?: string;
  [key: string]: unknown;
}

/** doLottery 请求体 */
export interface DoLotteryBody {
  user_id: number;
  cate_id: number;
}

/** doLottery 返回：含 gift 信息 */
export interface DoLotteryResult {
  gift: { name?: string; image?: string; [key: string]: unknown };
  [key: string]: unknown;
}

/** 礼品分类（getList t_gift_category） */
export interface GiftCategoryItem {
  id?: number;
  name?: string;
  cost?: number;
  [key: string]: unknown;
}

/** 礼品列表项（getList t_gift） */
export interface GiftListItem {
  id?: number;
  name?: string;
  image?: string;
  cate_id?: number;
  cost?: number;
  [key: string]: unknown;
}

/** getAll 分页列表响应（部分接口返回 data + pageNum/pageSize/totalCount/totalPage） */
export interface ApiPagedResponse<T> {
  data: T[];
  pageNum?: number;
  pageSize?: number;
  totalCount?: number;
  totalPage?: number;
}

// ----- pic -----

/** getPicList / getAll 图片列表单条 */
export interface PicListItem {
  id: number;
  data: string;
  [key: string]: unknown;
}

/** setData 图片：id + data */
export interface SetPicDataBody {
  id?: number;
  data: string;
}

// ----- color -----

/** 颜色列表单条（getAll t_colors） */
export interface ColorListItem {
  id: number;
  name?: string;
  color?: string;
  [key: string]: unknown;
}

/** setData 颜色 */
export interface SetColorDataBody {
  id?: number;
  name: string;
  color: string;
}

// ----- data（通用 getList / getRdsData / setRdsData） -----

export interface GetListParams {
  table: string;
  conditions?: string;
  pageNum?: number;
  pageSize?: number;
}

export interface SetRdsDataBody {
  table: string;
  data: { id: number; value: unknown };
}

/** delData 请求体（/delData） */
export interface DelDataBody {
  id: number;
  table: string;
}

/** addScore 成功返回（后端通常返回 data 或空，无业务数据时可视为 void） */
export type AddScoreResponse = unknown;

/** 抽奖配置（getLotteryData / setLotteryData 为 Redis 存取的字符串） */
export type LotteryConfig = string;

/** getRdsList 通用列表响应（如 getChatMessages 返回的列表结构，具体字段以实际接口为准） */
export interface GetRdsListResponse<T = unknown> {
  list?: T[];
  [key: string]: unknown;
}

// ----- tts -----

/** TTS 任务分析结果，与 server 端 list_tasks 返回的 analysis 一致 */
export interface TtsTaskAnalysis {
  words?: string[];
  sentence?: string[];
  abstract?: string;
  doodle?: string;
  [key: string]: unknown;
}

/** TTS 任务项，与 server/core/services/tts_mgr TTSTask 及 GET /tts/list 返回一致 */
export interface TtsTaskItem {
  task_id: string;
  name: string;
  status: string;
  error_message?: string | null;
  create_time: number;
  update_time: number;
  text?: string;
  role?: string | null;
  model?: string | null;
  speed?: number;
  vol?: number;
  generated_chars?: number;
  total_chars?: number;
  duration?: number | null;
  ocr_running?: boolean;
  analysis_running?: boolean;
  analysis?: TtsTaskAnalysis | null;
}

/** POST /tts/create 请求体 */
export interface CreateTtsTaskBody {
  text: string;
  name?: string;
  role?: string;
  model?: string;
  speed?: number;
  vol?: number;
}

/** POST /tts/create 响应 data */
export interface CreateTtsTaskResponse {
  task_id: string;
}

/** POST /tts/update 请求体 */
export interface UpdateTtsTaskBody {
  task_id: string;
  name?: string;
  text?: string;
  role?: string;
  model?: string;
  speed?: number;
  vol?: number;
}

/** POST /tts/delete、/tts/analysis 请求体 */
export interface TtsTaskIdBody {
  task_id: string;
}
