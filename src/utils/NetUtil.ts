import EventBus, { C_EVENT } from "@/modal/EventBus.ts";
import { UData, UserData } from "@/modal/UserData.ts";
import { clearLoginCache, getAccessToken, refreshToken } from "@/utils/Auth";
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";
import _ from "lodash";

/** TTS 任务分析结果，与 server/frontend TTS.vue 展示一致 */
export interface TtsTaskAnalysis {
  words?: string[];
  sentence?: string[];
  abstract?: string;
  doodle?: string;
  [key: string]: unknown;
}

/** TTS 任务项，与 server/core/services/tts_mgr TTSTask 及 list_tasks 返回字段一致 */
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
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const REMOTE = { url: "https://leo-zhao.natapp4.cc/api", available: false };
const LOCAL = { url: "http://192.168.50.171:8848/api", available: false };
// const LOCAL = { url: "http://localhost:8888", available: false };
let API_URL = "";
// const URL = "http://192.168.50.184:9527/api";

/** 带认证的 API 客户端：自动带 Authorization、withCredentials，401 时尝试 refresh 后重试一次 */
const apiClient = axios.create({
  timeout: 30000,
  withCredentials: true,
});

// 请求拦截器：附加 access_token
apiClient.interceptors.request.use(
  (cfg: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      if (!cfg.headers) cfg.headers = {} as InternalAxiosRequestConfig["headers"];
      (cfg.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
    return cfg;
  },
  (err) => Promise.reject(err)
);

// 401 时 refresh 后重试一次
let isRefreshing = false;
let refreshWaiters: Array<(token: string | null) => void> = [];
async function ensureRefreshed(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise((resolve) => {
      refreshWaiters.push(resolve);
    });
  }
  isRefreshing = true;
  try {
    const data = await refreshToken(API_URL);
    const token = data?.access_token || getAccessToken();
    refreshWaiters.forEach((cb) => cb(token));
    refreshWaiters = [];
    return token;
  } catch (e: any) {
    // 仅 refresh 返回 401 时清空本地登录缓存；422 等（如刚登录 cookie 未就绪）保留
    if (e?.response?.status === 401) {
      clearLoginCache();
    }
    refreshWaiters.forEach((cb) => cb(null));
    refreshWaiters = [];
    throw e;
  } finally {
    isRefreshing = false;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && cfg && !cfg._retry) {
      cfg._retry = true;
      try {
        const newToken = await ensureRefreshed();
        if (newToken) {
          if (!cfg.headers) cfg.headers = {} as AxiosRequestConfig["headers"];
          (cfg.headers as Record<string, string>)["Authorization"] = `Bearer ${newToken}`;
        }
        return apiClient.request(cfg);
      } catch (refreshErr: any) {
        // refresh 返回 401 才视为登录过期并跳转登录页；422 等（如刚登录时 refresh 未就绪）不踢出
        const status = refreshErr?.response?.status;
        if (status === 401) {
          clearLoginCache();
          EventBus.$emit(C_EVENT.AUTH_EXPIRED);
        }
      }
    }
    return Promise.reject(error);
  }
);

export function getApiUrl() {
  return API_URL;
}

async function checkAddress(url: string, timeout: number = 10000) {
  try {
    const response = await axios
      .create({
        timeout: timeout,
      })
      .head(url + "/");
    return response.status >= 200 && response.status < 300;
  } catch {
    return false;
  }
}

export async function initNet(): Promise<void> {
  await checkAddress(REMOTE.url).then((ret) => {
    if (ret && !LOCAL.available) {
      REMOTE.available = true;
      console.log("use url:", REMOTE.url);
      API_URL = REMOTE.url;
    }
    return ret;
  });
  const protocol = window.location.protocol;
  if (protocol !== "https:") {
    await checkAddress(LOCAL.url, 100).then((ret) => {
      if (ret) {
        LOCAL.available = true;
        console.log("use url:", LOCAL.url, ret);
        API_URL = LOCAL.url;
      }
      return ret;
    });
  }
  apiClient.defaults.baseURL = API_URL;
  console.log("init net ");
}
export async function getSave(id: number) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp: any = await apiClient.get("/getData", {
    params: { id: id, table: "t_schedule", fields: "data,user_id" },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const ret: UserData = UData.parseUserData(rsp.data.data.data);
  ret.userId = rsp.data.data.user_id;
  EventBus.$emit(C_EVENT.UPDATE_SAVE, ret);
  return ret;
}

export function setSave(id: number | undefined, data: any) {
  // console.log(data);
  return new Promise((resolve, reject) => {
    if (id === undefined) {
      reject(new Error("id is undefined"));
      return;
    }
    apiClient
      .post("/setData", {
        table: "t_schedule",
        data: {
          id: id,
          data: JSON.stringify(data),
        },
      })
      .then((res: any) => {
        if (res.data.code === 0) {
          resolve(res);
          EventBus.$emit(C_EVENT.UPDATE_SAVE, data);
        } else {
          reject(new Error(res.data.msg));
        }
      })
      .catch((err: any) => {
        reject(err);
      });
  });
}

export async function getGiftData(id: number) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp: any = await apiClient.get("/getData", {
    params: { id: id, table: "t_gift", fields: "*" },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

// export async function setUserInfo(id: number | undefined, score: number) {
//   const rsp: any = await apiClient.post("/setData", {
//     table: "t_user",
//     data: {
//       id: id,
//       score: score,
//     },
//   });
//   console.log("setUserInfo", rsp.data);
//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }
//   return rsp.data.data;
// }
/**
 * 变更积分
 * @param {*} user id
 * @param {*} action 行为
 * @param {*} value 分值
 * @param {*} msg 备注
 * @returns
 */
export async function addScore(user: number, action: string, value: number, msg: string) {
  const rsp = await apiClient.post("/addScore", {
    user,
    action,
    value,
    msg,
  });

  console.log("addScore", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

export async function getConversationId(id: number) {
  const rsp: any = await apiClient.get("/getRdsData", {
    params: { table: "conversation:id", id: id },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setConversationId(id: number, cId: string) {
  const rsp: any = await apiClient.post("/setRdsData", {
    table: "conversation:id",
    data: {
      id: id,
      value: cId,
    },
  });
  console.log("setConversationId", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getChatSetting(id: number) {
  const rsp: any = await apiClient.get("/getRdsData", {
    params: { table: "chatSetting", id: id },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setChatSetting(id: number, cId: string) {
  const rsp: any = await apiClient.post("/setRdsData", {
    table: "chatSetting",
    data: {
      id: id,
      value: cId,
    },
  });
  console.log("setChatSetting", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getLotteryData() {
  const rsp: any = await apiClient.get("/getRdsData", {
    params: { table: "lottery", id: 2 },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setLotteryData(value: string) {
  const rsp: any = await apiClient.post("/setRdsData", {
    table: "lottery",
    data: {
      id: 2,
      value: value,
    },
  });
  // console.log("setChatSetting", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getAiChatMessages(
  conversation_id: string,
  limit: number,
  user: string,
  first_id?: string | number
) {
  const rsp: any = await apiClient.get("/chatMessages", {
    params: { conversation_id: conversation_id, limit: limit, user: user, first_id: first_id },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getChatMessages(
  key: string,
  startId: number | string | undefined,
  pageSize: number
) {
  const rsp: any = await apiClient.get("/getRdsList", {
    params: { key: "chat:" + key, pageSize: pageSize, startId: startId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/** TTS 任务创建，参考 server/core/api/tts_routes.py POST /tts/create，返回 task_id */
export async function createTtsTask(opts: {
  text: string;
  name?: string;
  role?: string;
  model?: string;
  speed?: number;
  vol?: number;
}): Promise<{ task_id: string }> {
  const rsp: any = await apiClient.post("/tts/create", opts);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "创建任务失败");
  }
  return { task_id: rsp.data.data?.task_id ?? "" };
}

/** TTS 任务列表，参考 server/core/api/tts_routes.py GET /tts/list */
export async function getTtsTaskList(): Promise<TtsTaskItem[]> {
  const rsp: any = await apiClient.get("/tts/list");
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取 TTS 任务列表失败");
  }
  return rsp.data.data ?? [];
}

/** TTS 任务音频下载 URL，参考 server/core/api/tts_routes.py GET /tts/download */
export function getTtsDownloadUrl(taskId: string): string {
  const base = getApiUrl();
  if (!base) return "";
  const sep = base.endsWith("/") ? "" : "/";
  return `${base}${sep}tts/download?task_id=${encodeURIComponent(taskId)}`;
}

/** 下载 TTS 任务音频到本地：请求 blob 后触发浏览器下载 */
export async function downloadTtsAudio(taskId: string, fileName?: string): Promise<void> {
  const rsp = await apiClient.get("/tts/download", {
    params: { task_id: taskId },
    responseType: "blob",
  });
  const blob = rsp.data as Blob;
  if (blob.type === "application/json" || blob.size < 200) {
    const text = await blob.text();
    try {
      const json = JSON.parse(text) as { code?: number; msg?: string };
      if (json?.code !== 0) throw new Error(json?.msg || "下载失败");
    } catch (e) {
      if (e instanceof Error && e.message !== "下载失败") throw e;
      throw new Error((e as Error)?.message ?? text ?? "下载失败");
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName ?? `tts_${taskId}.mp3`;
  a.click();
  URL.revokeObjectURL(url);
}

/** TTS 任务更新，参考 server/core/api/tts_routes.py POST /tts/update */
export async function updateTtsTask(
  taskId: string,
  opts: { name?: string; text?: string; role?: string; model?: string; speed?: number; vol?: number }
): Promise<void> {
  const rsp: any = await apiClient.post("/tts/update", { task_id: taskId, ...opts });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "更新任务失败");
  }
}

/** TTS 任务删除，参考 server/core/api/tts_routes.py POST /tts/delete */
export async function deleteTtsTask(taskId: string): Promise<void> {
  const rsp: any = await apiClient.post("/tts/delete", { task_id: taskId });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "删除任务失败");
  }
}

/** TTS 任务发起分析，参考 server/core/api/tts_routes.py POST /tts/analysis */
export async function startTtsAnalysis(taskId: string): Promise<void> {
  const rsp: any = await apiClient.post("/tts/analysis", { task_id: taskId });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "发起分析失败");
  }
}

/** TTS 任务 OCR 图片识别，参考 server/core/api/tts_routes.py POST /tts/ocr，结果追加到任务文本末尾 */
export async function ocrTtsTask(taskId: string, files: File[]): Promise<void> {
  const formData = new FormData();
  formData.append("task_id", taskId);
  files.forEach((f) => formData.append("file", f));
  const rsp: any = await apiClient.post("/tts/ocr", formData, { timeout: 60000 });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "OCR 识别失败");
  }
}

export async function getChatMem(id: number) {
  const rsp: any = await apiClient.get("/getRdsData", {
    params: { table: "mem", id: id },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setChatMem(id: number, cId: string) {
  const rsp: any = await apiClient.post("/setRdsData", {
    table: "mem",
    data: {
      id: id,
      value: cId,
    },
  });
  console.log("setChatMem", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getUserInfo(id: number) {
  const rsp: any = await apiClient.get("/getData", {
    params: { table: "t_user", id: id, fields: "id,score" },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setPic(id: number | undefined, data: string): Promise<string> {
  const rsp: any = await apiClient.post("/setData", {
    table: "t_user_pic",
    data: {
      id: id,
      data: data,
    },
  });
  console.log("setPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function delPic(id: number) {
  const rsp: any = await apiClient.post("/delData", {
    id: id,
    table: "t_user_pic",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getScheduleList() {
  const rsp: any = await apiClient.get("/getAll", {
    params: { table: "t_schedule", fields: "id,name,user_id" },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getUserList() {
  const rsp: any = await apiClient.get("/getAllUser");
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  _.forEach(rsp.data.data.data, (item: any) => {
    if (item.wish_list) {
      item.wish_list = JSON.parse(item.wish_list);
    }
  });
  return rsp.data.data;
}

export async function setUserData(data: any) {
  const rsp: any = await apiClient.post("/setData", {
    table: "t_user",
    data: data,
  });
  console.log("setUser", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getPicList(pageNum?: number, pageSize?: number) {
  const rsp: any = await apiClient.get("/getAll", {
    params: { table: "t_user_pic", pageNum: pageNum, pageSize: pageSize },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getPic(id: number): Promise<string> {
  const rsp: any = await apiClient.get("/getData", {
    params: { table: "t_user_pic", id: id, idx: 1 },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getColorList(pageNum?: number, pageSize?: number) {
  const rsp: any = await apiClient.get("/getAll", {
    params: { table: "t_colors", pageNum: pageNum, pageSize: pageSize },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setColor(
  id: number | undefined,
  name: string,
  color: string
): Promise<string> {
  const rsp: any = await apiClient.post("/setData", {
    table: "t_colors",
    data: { id: id, name: name, color: color },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function delColor(id: number) {
  const rsp: any = await apiClient.post("/delData", {
    id: id,
    table: "t_colors",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 获取数据列表
 */
export async function getList(
  table: string,
  conditions: any = undefined,
  pageNum: number = 1,
  pageSize: number = 10
) {
  const rsp = await apiClient.get("/getAll", {
    params: {
      table: table,
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

/**
 * 获取rds数据
 */
export async function getRdsData(table: string, id: number) {
  const rsp = await apiClient.get("/getRdsData", {
    params: { table: table, id: id },
  });
  // console.log("getRdsData", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
/**
 * 设置rds数据
 */
export async function setRdsData(table: string, id: number, value: any) {
  const rsp = await apiClient.post("/setRdsData", {
    table: table,
    data: {
      id: id,
      value: value,
    },
  });
  // console.log("setRdsData", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function doLottery(userId: number, cateId: number) {
  const rsp = await apiClient.post("/doLottery", {
    user_id: userId,
    cate_id: cateId,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export default {};
