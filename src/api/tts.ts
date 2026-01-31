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

export function getTtsDownloadUrl(taskId: string): string {
  const base = getApiUrl();
  if (!base) return "";
  const sep = base.endsWith("/") ? "" : "/";
  return `${base}${sep}tts/download?task_id=${encodeURIComponent(taskId)}`;
}

export async function downloadTtsAudio(
  taskId: string,
  fileName?: string
): Promise<void> {
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
