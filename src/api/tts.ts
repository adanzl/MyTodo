import { apiClient, getApiUrl } from "./api-client";
import type {
  ApiResponse,
  CreateTtsTaskBody,
  CreateTtsTaskResponse,
  UpdateTtsTaskBody,
  TtsTaskIdBody,
  TtsTaskItem,
} from "./types";

export type { TtsTaskItem, TtsTaskAnalysis } from "./types";

export async function createTtsTask(
  opts: CreateTtsTaskBody
): Promise<CreateTtsTaskResponse> {
  const rsp = await apiClient.post<ApiResponse<CreateTtsTaskResponse>>(
    "/tts/create",
    opts
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "创建任务失败");
  }
  const data = rsp.data.data;
  return { task_id: data?.task_id ?? "" };
}

export async function getTtsTaskList(): Promise<TtsTaskItem[]> {
  const rsp = await apiClient.get<ApiResponse<TtsTaskItem[]>>("/tts/list");
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取 TTS 任务列表失败");
  }
  return rsp.data.data ?? [];
}

/** 获取单个 TTS 任务详情 */
export async function getTtsTask(taskId: string): Promise<TtsTaskItem> {
  const rsp = await apiClient.get<ApiResponse<TtsTaskItem>>("/tts/get", {
    params: { task_id: taskId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取任务失败");
  }
  const data = rsp.data.data;
  if (!data) throw new Error("任务不存在");
  return data;
}

export function getTtsDownloadUrl(taskId: string): string {
  const base = getApiUrl();
  if (!base) return "";
  const sep = base.endsWith("/") ? "" : "/";
  return `${base}${sep}tts/download?task_id=${encodeURIComponent(taskId)}`;
}

/** 直接链接下载：不经过 blob，兼容各类浏览器（依赖同源或 Cookie 鉴权） */
export function downloadTtsAudio(taskId: string, fileName?: string): void {
  const name = fileName ?? `tts_${taskId}.mp3`;
  const url = getTtsDownloadUrl(taskId);
  if (!url) throw new Error("无法生成下载地址");
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.rel = "noopener";
  a.target = "_blank";
  a.click();
}

export async function updateTtsTask(
  taskId: string,
  opts: Omit<UpdateTtsTaskBody, "task_id">
): Promise<void> {
  const body: UpdateTtsTaskBody = { task_id: taskId, ...opts };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/tts/update", body);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "更新任务失败");
  }
}

export async function deleteTtsTask(taskId: string): Promise<void> {
  const body: TtsTaskIdBody = { task_id: taskId };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/tts/delete", body);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "删除任务失败");
  }
}

/** 开始处理 TTS 任务（合成语音） */
export async function startTtsTask(taskId: string): Promise<void> {
  const body: TtsTaskIdBody = { task_id: taskId };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/tts/start", body);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "启动任务失败");
  }
}

export async function startTtsAnalysis(taskId: string): Promise<void> {
  const body: TtsTaskIdBody = { task_id: taskId };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/tts/analysis", body);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "发起分析失败");
  }
}

export async function ocrTtsTask(taskId: string, files: File[]): Promise<void> {
  const formData = new FormData();
  formData.append("task_id", taskId);
  files.forEach((f) => formData.append("file", f));
  const rsp = await apiClient.post<ApiResponse<unknown>>("/tts/ocr", formData, {
    timeout: 60000,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "OCR 识别失败");
  }
}
