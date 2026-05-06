<template>
  <el-dialog
    v-model="visible"
    title="批量添加素材"
    width="1000px"
    :close-on-click-modal="false"
    :before-close="handleBeforeClose"
  >
    <div v-loading="submitting" element-loading-text="正在添加素材..." class="max-h-[80vh] min-h-100 overflow-y-auto">
      <!-- 配置区域 -->
      <div class="mb-4 p-4 bg-gray-50 rounded">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-2">分类</label>
            <el-select v-model="defaultCateId" placeholder="选择分类" class="w-full">
              <el-option
                v-for="cate in categoryList"
                :key="cate.id"
                :label="cate.name"
                :value="cate.id"
              />
            </el-select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">类型</label>
            <el-radio-group v-model="defaultType">
              <el-radio :value="0">PDF</el-radio>
              <el-radio :value="1">视频</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>

      <!-- 已添加列表 -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-sm font-medium flex-1">待添加素材 ({{ materialList.length }} 条)</h4>
          <el-button size="small" type="primary" @click="openFileBrowser">浏览文件</el-button>
          <el-button size="small" type="danger" @click="clearMaterialList">清空列表</el-button>
        </div>
        <el-table :data="materialList" border max-height="300" size="small">
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
          <el-table-column label="分类" width="100">
            <template #default="{ row }">
              <el-select v-model="row.cate_id" size="small" class="w-full">
                <el-option
                  v-for="cate in categoryList"
                  :key="cate.id"
                  :label="cate.name"
                  :value="cate.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag :type="row.type === 0 ? 'success' : 'primary'" size="small">
                {{ row.type === 0 ? 'PDF' : '视频' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ $index }">
              <el-button size="small" type="danger" @click="removeMaterial($index)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 错误信息 -->
      <div v-if="errors.length > 0" class="mt-4">
        <h4 class="text-sm font-medium mb-2 text-red-600">错误信息 ({{ errors.length }} 条)</h4>
        <el-alert
          v-for="(error, index) in errors"
          :key="index"
          :title="error"
          type="error"
          show-icon
          class="mb-2"
          :closable="false"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
        <div class="text-sm text-gray-600">
          已选择 {{ materialList.length }} 个素材
        </div>
        <div>
          <el-button @click="handleBeforeClose">取消</el-button>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="submitting"
            :disabled="materialList.length === 0"
          >
            确认添加 ({{ materialList.length }})
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>

  <!-- 文件选择对话框 -->
  <FileDialog
    v-model:visible="fileDialogVisible"
    title="批量选择文件"
    :extensions="getExtensionsByType(defaultType)"
    mode="file"
    :multiple="true"
    @confirm="handleFileConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { addMaterial } from "@/api/api-task";
import FileDialog from "@/views/dialogs/FileDialog.vue";

interface Props {
  modelValue: boolean;
  categoryList: Array<{ id: number; name: string }>;
}

interface MaterialItem {
  name: string;
  path: string;
  cate_id: number;
  type: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

// 配置
const defaultCateId = ref<number>();
const defaultType = ref<number>(0);
const fileDialogVisible = ref(false);
const materialList = ref<MaterialItem[]>([]);
const errors = ref<string[]>([]);
const submitting = ref(false);

// 初始化默认分类
watch(
  () => props.categoryList,
  (list) => {
    if (list.length > 0 && !defaultCateId.value) {
      defaultCateId.value = list[0].id;
    }
  },
  { immediate: true }
);

// 根据类型获取扩展名
const getExtensionsByType = (type: number): string => {
  if (type === 0) return ".pdf";
  if (type === 1) return ".mp4,.avi,.mkv,.mov,.wmv,.flv,.webm";
  return ".mp3,.wav,.aac,.ogg,.m4a,.flac,.wma";
};

// 打开文件浏览器
const openFileBrowser = () => {
  fileDialogVisible.value = true;
};

// 文件选择确认
const handleFileConfirm = (filePaths: string[]) => {
  if (!filePaths?.length) return;

  filePaths.forEach((filePath) => {
    const fileName = filePath.split('/').pop() || filePath;
    materialList.value.push({
      name: fileName.replace(/\.[^/.]+$/, ""),
      path: filePath,
      cate_id: defaultCateId.value || props.categoryList[0]?.id || 1,
      type: defaultType.value,
    });
  });

  ElMessage.success(`已添加 ${filePaths.length} 个文件`);
};

// 移除素材
const removeMaterial = (index: number) => {
  materialList.value.splice(index, 1);
};

// 清空素材列表
const clearMaterialList = async () => {
  if (materialList.value.length === 0) return;

  try {
    await ElMessageBox.confirm("确定要清空所有待添加素材吗？", "提示", { type: "warning" });
    materialList.value = [];
    errors.value = [];
  } catch {}
};

// 关闭前确认
const handleBeforeClose = async (done?: () => void) => {
  if (materialList.value.length > 0) {
    try {
      await ElMessageBox.confirm("确定要关闭并清空所有待添加素材吗？", "提示", { type: "warning" });
    } catch {
      return;
    }
  }
  clearMaterialList();
  done ? done() : (visible.value = false);
};

// 提交批量添加
const handleSubmit = async () => {
  if (!materialList.value.length) {
    ElMessage.warning("请至少添加一个素材");
    return;
  }

  submitting.value = true;
  errors.value = [];
  const failedItems: string[] = [];

  for (const material of materialList.value) {
    try {
      await addMaterial(material);
    } catch (error: any) {
      console.error(`添加素材 "${material.name}" 失败:`, error);
      failedItems.push(material.name);
    }
  }

  const successCount = materialList.value.length - failedItems.length;
  if (!failedItems.length) {
    ElMessage.success(`成功添加 ${successCount} 个素材`);
    emit("success");
    visible.value = false;
    materialList.value = [];
  } else {
    errors.value = failedItems.map((name) => `添加失败: ${name}`);
    ElMessage.warning(`添加完成：成功 ${successCount} 个，失败 ${failedItems.length} 个`);
    materialList.value = materialList.value.filter((m) => failedItems.includes(m.name));
  }
  submitting.value = false;
};

// 监听对话框打开，重置数据
watch(visible, (newVal) => {
  if (newVal) {
    materialList.value = [];
    errors.value = [];
  }
});
</script>


