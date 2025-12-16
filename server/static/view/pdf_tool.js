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
      const loading = ref(false);
      const fileList = ref([]);
      const uploadFile = ref(null);
      const uploadFilePath = ref("");

      // 获取文件列表
      const loadFileList = async () => {
        try {
          loading.value = true;
          const response = await axios.get(`${getApiUrl()}/pdf/list`);
          if (response.data.code === 0) {
            const mapping = response.data.data.mapping || [];
            // 为每个文件项添加处理状态标记和密码字段
            fileList.value = mapping.map(item => ({
              ...item,
              _decrypting: item._decrypting || false,
              _password: item._password !== undefined ? item._password : ""
            }));
          } else {
            ElMessage.error(response.data.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 处理文件选择
      const handleFileChange = (file) => {
        uploadFile.value = file.raw;
        // 只显示文件名，不显示路径
        uploadFilePath.value = file.raw.name;
      };

      // 上传文件
      const handleUpload = async () => {
        if (!uploadFile.value) {
          ElMessage.warning("请选择要上传的文件");
          return;
        }

        const file = uploadFile.value;
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          ElMessage.error("只支持 PDF 文件");
          return;
        }

        try {
          loading.value = true;
          const formData = new FormData();
          formData.append('file', file);

          const response = await axios.post(`${getApiUrl()}/pdf/upload`, formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });

          if (response.data.code === 0) {
            ElMessage.success("文件上传成功");
            uploadFile.value = null;
            uploadFilePath.value = "";
            await loadFileList();
          } else {
            ElMessage.error(response.data.msg || "文件上传失败");
          }
        } catch (error) {
          console.error("文件上传失败:", error);
          ElMessage.error("文件上传失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 解密文件
      const handleDecrypt = async (item) => {
        if (!item.uploaded) {
          ElMessage.warning("请先上传文件");
          return;
        }

        // 如果正在处理中，不允许重复操作
        if (item._decrypting) {
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
          // 设置该文件为处理中状态
          item._decrypting = true;
          
          // 构建请求数据
          const requestData = {
            filename: item.uploaded.name,
          };
          
          // 从输入框获取密码
          // 如果输入框有值（包括空字符串），添加到请求中
          // 后端会处理：空字符串会先尝试无密码，非空字符串会使用该密码
          if (item._password !== undefined && item._password !== null) {
            requestData.password = item._password;
          }

          const response = await axios.post(`${getApiUrl()}/pdf/decrypt`, requestData);

          if (response.data.code === 0) {
            ElMessage.success("文件解密成功");
            // 解密成功后清空密码输入框
            item._password = "";
            await loadFileList();
          } else {
            // 如果密码错误，提示用户
            if (response.data.msg && response.data.msg.includes("密码")) {
              ElMessage.error(response.data.msg || "密码错误，请重试");
            } else {
              ElMessage.error(response.data.msg || "文件解密失败");
            }
          }
        } catch (error) {
          console.error("文件解密失败:", error);
          ElMessage.error("文件解密失败: " + (error.message || "未知错误"));
        } finally {
          // 清除处理中状态
          item._decrypting = false;
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
          loading.value = true;
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
          loading.value = false;
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
        loading,
        fileList,
        uploadFile,
        uploadFilePath,
        loadFileList,
        handleFileChange,
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

