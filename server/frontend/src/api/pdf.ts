/**
 * PDF 相关 API
 */
import { api } from "./config";

/**
 * 获取 PDF 文件列表
 */
export async function getPdfList() {
  const response = await api.get("/pdf/list");
  return response.data;
}

/**
 * 上传 PDF 文件
 */
export async function uploadPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/pdf/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

/**
 * 解密 PDF 文件
 */
export async function decryptPdf(filename: string, password?: string) {
  const data: { filename: string; password?: string } = { filename };
  if (password !== undefined && password !== null) {
    data.password = password;
  }
  const response = await api.post("/pdf/decrypt", data);
  return response.data;
}

/**
 * 下载 PDF 文件
 */
export function getPdfDownloadUrl(filename: string, type: "uploaded" | "unlocked"): string {
  // 使用 api 实例的 baseURL，然后拼接路径
  const baseURL = api.defaults.baseURL || "";
  return `${baseURL}/pdf/download/${encodeURIComponent(filename)}?type=${type}`;
}

/**
 * 删除 PDF 文件
 */
export async function deletePdf(filename: string, type: "both" | "uploaded" | "unlocked" = "both") {
  const response = await api.post("/pdf/delete", {
    filename,
    type,
  });
  return response.data;
}
