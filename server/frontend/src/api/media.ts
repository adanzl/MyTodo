/**
 * 媒体相关 API
 */
import { api } from "./config";

/**
 * 媒体操作接口
 */
export async function mediaAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, any> = {}
): Promise<any> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/api/media/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/api/media/${action}`, params);
  }
  return rsp.data;
}

/**
 * 媒体任务相关 API
 */

/**
 * 获取媒体任务列表
 */
export async function getMediaTaskList() {
  const response = await api.get("/api/media/task/list");
  return response.data;
}

/**
 * 创建媒体任务
 */
export async function createMediaTask() {
  const response = await api.post("/api/media/task/create", {});
  return response.data;
}

/**
 * 获取媒体任务详情
 */
export async function getMediaTask(taskId: string) {
  const response = await api.post("/api/media/task/get", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 删除媒体任务
 */
export async function deleteMediaTask(taskId: string) {
  const response = await api.post("/api/media/task/delete", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 添加文件到媒体任务
 */
export async function addFileToMediaTask(taskId: string, filePath: string) {
  const response = await api.post("/api/media/task/addFileByPath", {
    task_id: taskId,
    file_path: filePath,
  });
  return response.data;
}

/**
 * 从媒体任务删除文件
 */
export async function deleteFileFromMediaTask(taskId: string, fileIndex: number) {
  const response = await api.post("/api/media/task/deleteFile", {
    task_id: taskId,
    file_index: fileIndex,
  });
  return response.data;
}

/**
 * 开始媒体任务合成
 */
export async function startMediaTask(taskId: string) {
  const response = await api.post("/api/media/task/start", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 重新排序媒体任务文件
 */
export async function reorderMediaTaskFiles(taskId: string, fileIndices: number[]) {
  const response = await api.post("/api/media/task/reorderFiles", {
    task_id: taskId,
    file_indices: fileIndices,
  });
  return response.data;
}

/**
 * 获取媒体任务下载 URL
 */
import { getApiUrl } from "./config";

export function getMediaTaskDownloadUrl(taskId: string): string {
  return `${getApiUrl()}/api/media/task/download?task_id=${taskId}`;
}

/**
 * 转存媒体任务结果文件
 */
export async function saveMediaTaskResult(taskId: string, targetPath: string) {
  const response = await api.post("/api/media/task/save", {
    task_id: taskId,
    target_path: targetPath,
  });
  return response.data;
}
