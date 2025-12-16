import { getApiUrl } from "../js/net_util.js";
const axios = window.axios;

const { ref, onMounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
let component = null;

async function loadTemplate() {
  const response = await fetch(`./view/pdf_tool-template.html?t=${Date.now()}`);
  return await response.text();
}

async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  
  component = {
    setup() {
      const refData = {
        loading: ref(false),
        fileList: ref([]),
        uploadFile: ref(null),
        password: ref(""),
        decrypting: ref(false),
      };

      // 获取文件列表
      const loadFileList = async () => {
        try {
          refData.loading.value = true;
          const response = await axios.get(`${getApiUrl()}/pdf/list`);
          if (response.data.code === 0) {
            refData.fileList.value = response.data.data.mapping || [];
          } else {
            ElMessage.error(response.data.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.loading.value = false;
        }
      };

      // 上传文件
      const handleUpload = async () => {
        if (!refData.uploadFile.value) {
          ElMessage.warning("请选择要上传的文件");
          return;
        }

        const file = refData.uploadFile.value;
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          ElMessage.error("只支持 PDF 文件");
          return;
        }

        try {
          refData.loading.value = true;
          const formData = new FormData();
          formData.append('file', file);

          const response = await axios.post(`${getApiUrl()}/pdf/upload`, formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });

          if (response.data.code === 0) {
            ElMessage.success("文件上传成功");
            refData.uploadFile.value = null;
            await loadFileList();
          } else {
            ElMessage.error(response.data.msg || "文件上传失败");
          }
        } catch (error) {
          console.error("文件上传失败:", error);
          ElMessage.error("文件上传失败: " + (error.message || "未知错误"));
        } finally {
          refData.loading.value = false;
        }
      };

      // 解密文件
      const handleDecrypt = async (item) => {
        if (!item.uploaded) {
          ElMessage.warning("请先上传文件");
          return;
        }

        if (item.has_unlocked) {
          const confirmed = await ElMessageBox.confirm(
            "已解密的文件已存在，是否重新解密？",
            "提示",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          ).catch(() => false);
          if (!confirmed) return;
        }

        try {
          refData.decrypting.value = true;
          const response = await axios.post(`${getApiUrl()}/pdf/decrypt`, {
            filename: item.uploaded.name,
            password: refData.password.value || undefined,
          });

          if (response.data.code === 0) {
            ElMessage.success("文件解密成功");
            refData.password.value = "";
            await loadFileList();
          } else {
            ElMessage.error(response.data.msg || "文件解密失败");
          }
        } catch (error) {
          console.error("文件解密失败:", error);
          ElMessage.error("文件解密失败: " + (error.message || "未知错误"));
        } finally {
          refData.decrypting.value = false;
        }
      };

      // 下载文件
      const handleDownload = async (item, type) => {
        if (!item[type]) {
          ElMessage.warning("文件不存在");
          return;
        }

        try {
          const url = `${getApiUrl()}/pdf/download/${encodeURIComponent(item[type].name)}?type=${type}`;
          window.open(url, '_blank');
        } catch (error) {
          console.error("下载文件失败:", error);
          ElMessage.error("下载文件失败: " + (error.message || "未知错误"));
        }
      };

      // 删除文件
      const handleDelete = async (item) => {
        if (!item.uploaded) {
          ElMessage.warning("请先上传文件");
          return;
        }

        const confirmed = await ElMessageBox.confirm(
          "确定要删除该文件吗？",
          "提示",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        ).catch(() => false);

        if (!confirmed) return;

        try {
          refData.loading.value = true;
          const response = await axios.post(`${getApiUrl()}/pdf/delete`, {
            filename: item.uploaded.name,
            type: 'both',
          });

          if (response.data.code === 0) {
            ElMessage.success("文件删除成功");
            await loadFileList();
          } else {
            ElMessage.error(response.data.msg || "文件删除失败");
          }
        } catch (error) {
          console.error("删除文件失败:", error);
          ElMessage.error("删除文件失败: " + (error.message || "未知错误"));
        } finally {
          refData.loading.value = false;
        }
      };

      // 格式化文件大小
      const formatFileSize = (bytes) => {
        if (!bytes) return '-';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      };

      // 格式化时间
      const formatTime = (timestamp) => {
        if (!timestamp) return '-';
        return new Date(timestamp * 1000).toLocaleString();
      };

      onMounted(() => {
        loadFileList();
      });

      return {
        ...refData,
        loadFileList,
        handleUpload,
        handleDecrypt,
        handleDownload,
        handleDelete,
        formatFileSize,
        formatTime,
      };
    },
    template,
  };
  return component;
}

export default createComponent();

