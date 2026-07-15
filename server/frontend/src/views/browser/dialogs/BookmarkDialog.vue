<template>
  <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑书签' : '添加书签'" width="420px">
    <el-form :model="form" label-width="60px">
      <el-form-item label="标题">
        <el-input v-model="form.title" placeholder="书签名称" />
      </el-form-item>
      <el-form-item label="URL">
        <el-input v-model="form.url" placeholder="https://..." />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleConfirm" :disabled="!form.title.trim()">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";

const props = defineProps<{ modelValue: boolean; editingMark: { title: string; url: string } | null }>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "confirm", data: { title: string; url: string }): void;
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const isEditing = computed(() => !!props.editingMark);

const form = reactive({ title: "", url: "" });

watch(dialogVisible, (v) => {
  if (!v) return;
  if (props.editingMark) {
    form.title = props.editingMark.title;
    form.url = props.editingMark.url;
  } else {
    form.title = "";
    form.url = "https://";
  }
});

const handleConfirm = () => {
  if (!form.title.trim()) return;
  emit("confirm", { title: form.title.trim(), url: form.url.trim() });
  dialogVisible.value = false;
};
</script>
