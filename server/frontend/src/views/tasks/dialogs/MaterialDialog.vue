<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑素材' : '新增素材'"
    width="500px"
    @close="handleClose"
  >
    <el-form :model="formData" label-width="100px">
      <el-form-item label="名称" required>
        <el-input v-model="formData.name" placeholder="请输入素材名称" />
      </el-form-item>
      <el-form-item label="类型" required>
        <el-radio-group v-model="formData.type">
          <el-radio :value="0">PDF</el-radio>
          <el-radio :value="1">Video</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="路径" required>
        <div class="flex gap-2">
          <el-input
            v-model="formData.path"
            placeholder="请输入素材路径"
            :title="formData.path"
            show-overflow-tooltip
          />
          <el-button @click="openFileBrowser">浏览</el-button>
        </div>
      </el-form-item>
      <el-form-item label="分类" required>
        <el-select v-model="formData.cate_id" placeholder="请选择分类">
          <el-option
            v-for="item in (categoryList || [])"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button v-if="isEdit" @click="handleViewDetail">详情</el-button>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
    </template>
  </el-dialog>

  <!-- 文件选择对话框 -->
  <FileDialog
    v-model:visible="fileDialogVisible"
    :title="formData.type === 0 ? '选择PDF文件' : '选择视频文件'"
    :extensions="formData.type === 0 ? '.pdf' : '.mp4,.avi,.mkv,.mov'"
    mode="file"
    @confirm="handleFileConfirm"
  />
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  addMaterial,
  updateMaterial,
  type Material,
} from "@/api/api-task";
import FileDialog from "@/views/dialogs/FileDialog.vue";

interface Props {
  modelValue: boolean;
  isEdit: boolean;
  materialData?: Partial<Material>;
  categoryList?: { id: number; name: string }[];
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
  (e: "view-detail", material: Material): void;
}

const props = withDefaults(defineProps<Props>(), {
  materialData: () => ({}),
});

const emit = defineEmits<Emits>();

const visible = ref(props.modelValue);
const submitting = ref(false);
const formData = ref<Partial<Material>>({
  name: "",
  type: 0,
  path: "",
  cate_id: 1,
});
const fileDialogVisible = ref(false);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val) {
      initForm();
    }
  }
);

// 监听 visible 变化
watch(visible, (val) => {
  emit("update:modelValue", val);
});

// 初始化表单
const initForm = async () => {
  // 使用外层传入的分类列表，如果没有则加载
  const categories = props.categoryList || [];

  if (props.isEdit && props.materialData?.id) {
    // 编辑模式，填充数据 - 确保类型一致
    formData.value = {
      name: props.materialData.name || "",
      type: props.materialData.type ?? 0,
      path: props.materialData.path || "",
      cate_id: Number(props.materialData.cate_id) ?? 0,
    };
    console.log('编辑模式 - cate_id:', formData.value.cate_id, '类型:', typeof formData.value.cate_id);
  } else {
    // 新增模式，重置表单
    formData.value = {
      name: "",
      type: 0,
      path: "",
      cate_id: categories.length > 0 ? categories[0].id : 0,
    };
  }
};


// 提交表单
const handleSubmit = async () => {
  if (!formData.value.name || !formData.value.path || !formData.value.cate_id) {
    ElMessage.warning("请填写必填项");
    return;
  }

  submitting.value = true;
  try {
    if (props.isEdit && props.materialData?.id) {
      await updateMaterial({
        id: props.materialData.id,
        name: formData.value.name,
        type: formData.value.type,
        path: formData.value.path,
        cate_id: formData.value.cate_id,
      } as Material);
      ElMessage.success("更新成功");
    } else {
      await addMaterial({
        name: formData.value.name,
        type: formData.value.type ?? 0,
        path: formData.value.path,
        cate_id: formData.value.cate_id,
      });
      ElMessage.success("添加成功");
    }
    emit("success");
    handleClose();
  } catch (error: any) {
    ElMessage.error(error.message || "操作失败");
  } finally {
    submitting.value = false;
  }
};

// 取消
const handleCancel = () => {
  handleClose();
};

// 关闭对话框
const handleClose = () => {
  visible.value = false;
};

// 打开详情
const handleViewDetail = () => {
  if (props.isEdit && props.materialData) {
    // 关闭当前弹窗
    handleClose();
    // 触发打开详情事件
    emit("view-detail", props.materialData as Material);
  }
};

// 打开文件浏览器
const openFileBrowser = () => {
  fileDialogVisible.value = true;
};

// 文件选择确认
const handleFileConfirm = (filePaths: string[]) => {
  if (filePaths && filePaths.length > 0) {
    const filePath = filePaths[0];
    formData.value.path = filePath;

    // 从路径中提取文件名（不含扩展名）
    const fileName = filePath.split('/').pop() || '';
    const nameWithoutExt = fileName.replace(/\.[^/.]+$/, '');

    // 如果名称为空，则自动填充
    if (!formData.value.name) {
      formData.value.name = nameWithoutExt;
    }
  }
  fileDialogVisible.value = false;
};
</script>
