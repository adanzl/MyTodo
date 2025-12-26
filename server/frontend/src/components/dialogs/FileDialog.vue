<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="title"
    width="800"
    :before-close="handleClose"
  >
    <div class="m-4">
      <div class="flex items-center gap-2 mb-2">
        <el-input :model-value="fileBrowserPath" placeholder="当前路径" readonly> </el-input>
        <el-button type="primary" @click="refreshFileBrowser" :loading="fileBrowserLoading">
          刷新
        </el-button>
      </div>
      <div class="flex items-center gap-2 mb-2">
        <el-button size="small" @click="handleNavigateUp" :disabled="!fileBrowserCanNavigateUp">
          上一级
        </el-button>
        <el-button size="small" @click="handleGoToHome"> 首页 </el-button>
        <el-button size="small" @click="handleSelectAll"> 全选 </el-button>
        <el-button size="small" @click="handleDeselectAll"> 取消全选 </el-button>
        <span v-if="selectedFiles.length > 0" class="text-sm text-blue-600 ml-2">
          已选择 {{ selectedFiles.length }} 个文件
        </span>
      </div>
    </div>
    <el-table
      :data="fileBrowserList"
      stripe
      class="w-full"
      v-loading="fileBrowserLoading"
      :height="400"
      @row-click="handleRowClick"
    >
      <el-table-column width="55">
        <template #default="{ row }">
          <el-checkbox
            v-if="!row.isDirectory"
            :model-value="isFileSelected(row)"
            @change="handleToggleSelection(row)"
            @click.stop
          >
          </el-checkbox>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="200">
        <template #default="{ row }">
          <div class="flex items-center gap-2">
            <span v-if="row.isDirectory">📁</span>
            <span v-else>📄</span>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="100">
        <template #default="{ row }">
          <span v-if="!row.isDirectory">{{ formatSize(row.size) }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="!row.isDirectory && isFileSelected(row)" type="success" size="small">
            已选择
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <slot name="footer">
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-500">
            <span v-if="mode === 'file'">提示：点击文件可切换选择状态，双击目录可进入</span>
            <span v-else>提示：选择目录作为转存目标，双击目录可进入</span>
          </span>
          <div class="flex gap-2 items-center">
            <slot name="footer-prepend"></slot>
            <el-button @click="handleClose">取消</el-button>
            <el-button
              type="primary"
              @click="handleConfirm"
              :loading="confirmLoading"
              :disabled="isConfirmDisabled"
            >
              {{ confirmButtonText
              }}<span v-if="mode === 'file'"> ({{ selectedFiles.length }})</span>
            </el-button>
          </div>
        </div>
      </slot>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import { api } from "@/api/config";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils";

interface FileBrowserItem {
  name: string;
  size?: number;
  isDirectory: boolean;
}

interface Props {
  visible?: boolean;
  title?: string;
  defaultPath?: string;
  extensions?: string;
  confirmButtonText?: string;
  confirmLoading?: boolean;
  mode?: "file" | "directory";
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  title: "选择文件",
  defaultPath: "/mnt/ext_base",
  extensions: "audio",
  confirmButtonText: "确定",
  confirmLoading: false,
  mode: "file",
});

const emit = defineEmits<{
  "update:visible": [value: boolean];
  confirm: [filePaths: string[]];
  close: [];
}>();

// 状态
const fileBrowserPath = ref<string>(props.defaultPath);
const fileBrowserList = ref<FileBrowserItem[]>([]);
const fileBrowserLoading = ref(false);
const selectedFiles = ref<string[]>([]);
const fileBrowserCanNavigateUp = ref(false);
let lastFileBrowserPath = props.defaultPath;

// 更新是否可以向上导航
const updateFileBrowserCanNavigateUp = () => {
  const path = fileBrowserPath.value;
  fileBrowserCanNavigateUp.value = !!(path && path !== "/mnt/ext_base" && path !== "/");
};

// 刷新文件浏览器
const refreshFileBrowser = async () => {
  try {
    fileBrowserLoading.value = true;
    const path = fileBrowserPath.value || props.defaultPath;
    const response = await api.get("/listDirectory", {
      params: { path: path, extensions: props.extensions },
    });
    if (response.data.code === 0) {
      fileBrowserList.value = response.data.data || [];
      updateFileBrowserCanNavigateUp();
    } else {
      ElMessage.error(response.data.msg || "获取文件列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取文件列表失败");
  } finally {
    fileBrowserLoading.value = false;
  }
};

// 向上导航
const handleNavigateUp = () => {
  const path = fileBrowserPath.value;
  if (path && path !== "/mnt/ext_base" && path !== "/") {
    const parts = String(path)
      .split("/")
      .filter(p => p);
    parts.pop();
    fileBrowserPath.value = parts.length > 0 ? "/" + parts.join("/") : "/mnt/ext_base";
    updateFileBrowserCanNavigateUp();
    refreshFileBrowser();
  }
};

// 回到首页
const handleGoToHome = () => {
  fileBrowserPath.value = props.defaultPath;
  updateFileBrowserCanNavigateUp();
  refreshFileBrowser();
};

// 行点击处理
const handleRowClick = (row: FileBrowserItem) => {
  if (row.isDirectory) {
    const newPath =
      fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
    fileBrowserPath.value = newPath;
    updateFileBrowserCanNavigateUp();
    refreshFileBrowser();
  } else {
    handleToggleSelection(row);
  }
};

// 切换文件选择状态
const handleToggleSelection = (row: FileBrowserItem) => {
  if (row.isDirectory) return;
  const filePath =
    fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
  const index = selectedFiles.value.indexOf(filePath);
  if (index > -1) {
    selectedFiles.value.splice(index, 1);
  } else {
    selectedFiles.value.push(filePath);
  }
};

// 检查文件是否被选中
const isFileSelected = (row: FileBrowserItem): boolean => {
  if (row.isDirectory) return false;
  const filePath =
    fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
  return selectedFiles.value.includes(filePath);
};

// 全选当前目录下的所有文件
const handleSelectAll = () => {
  const currentPath = fileBrowserPath.value;
  fileBrowserList.value.forEach(row => {
    if (!row.isDirectory) {
      const filePath = currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
      if (!selectedFiles.value.includes(filePath)) {
        selectedFiles.value.push(filePath);
      }
    }
  });
};

// 取消全选当前目录下的所有文件
const handleDeselectAll = () => {
  const currentPath = fileBrowserPath.value;
  const currentFiles = fileBrowserList.value
    .filter(row => !row.isDirectory)
    .map(row => {
      return currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
    });

  // 只移除当前目录下的文件，保留其他目录的文件
  selectedFiles.value = selectedFiles.value.filter(filePath => {
    return !currentFiles.includes(filePath);
  });
};

// 确认选择文件
const handleConfirm = () => {
  const modeValue = String(props.mode || "file")
    .toLowerCase()
    .trim();

  if (modeValue === "directory") {
    // 目录模式：传递当前路径
    const currentPath = fileBrowserPath.value || props.defaultPath || "/mnt/ext_base";
    if (!currentPath || String(currentPath).trim() === "") {
      ElMessage.warning("请先选择一个目录");
      return;
    }
    emit("confirm", [String(currentPath)]);
  } else {
    // 文件模式：传递选中的文件
    if (selectedFiles.value.length === 0) {
      ElMessage.warning("请先选择要添加的文件");
      return;
    }
    emit("confirm", [...selectedFiles.value]);
  }

  lastFileBrowserPath = fileBrowserPath.value;
  handleClose();
};

// 处理关闭
const handleClose = () => {
  selectedFiles.value = [];
  emit("close");
};

// 计算按钮是否禁用
const isConfirmDisabled = computed(() => {
  const modeValue = String(props.mode || "file")
    .toLowerCase()
    .trim();
  // 目录模式下，按钮始终可用
  if (modeValue === "directory") {
    return false;
  }
  // 文件模式下，没有选中文件时禁用
  return selectedFiles.value.length === 0;
});

// 监听 visible 变化
watch(
  () => props.visible,
  newVal => {
    if (newVal) {
      fileBrowserPath.value = lastFileBrowserPath;
      selectedFiles.value = [];
      refreshFileBrowser();
    } else {
      selectedFiles.value = [];
    }
  }
);

// 监听路径变化
watch(fileBrowserPath, () => {
  refreshFileBrowser();
});
</script>
