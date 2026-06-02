<template>
  <el-popover
    v-model:visible="visible"
    placement="bottom-end"
    :width="440"
    trigger="click"
    @show="fetchTasks"
  >
    <template #reference>
      <slot name="reference">
        <el-button type="primary" plain size="small">识别任务</el-button>
      </slot>
    </template>
    <div class="flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium">字幕识别队列</span>
        <el-button type="primary" link size="small" :loading="loading" @click="fetchTasks">
          刷新
        </el-button>
      </div>
      <div v-loading="loading" class="min-h-12 max-h-72 overflow-y-auto">
        <div
          v-if="!loading && tasks.length === 0"
          class="text-sm text-gray-400 py-4 text-center"
        >
          暂无识别任务
        </div>
        <div
          v-for="task in tasks"
          :key="task.task_id"
          class="flex items-start gap-2 py-2 border-b border-gray-100 last:border-0"
        >
          <div class="flex-1 min-w-0">
            <div class="text-sm truncate" :title="task.video_path">
              {{ taskBasename(task.video_path) }}
            </div>
            <div class="text-xs text-gray-500 mt-0.5 flex items-center gap-2 flex-wrap">
              <el-tag :type="statusTag(task.status)" size="small">
                {{ statusText(task.status) }}
              </el-tag>
              <span v-if="task.language">语言 {{ task.language }}</span>
            </div>
            <div
              v-if="task.error_message"
              class="text-xs text-red-500 mt-0.5 truncate"
              :title="task.error_message"
            >
              {{ task.error_message }}
            </div>
          </div>
          <el-button
            v-if="canCancel(task)"
            type="danger"
            plain
            size="small"
            :loading="cancelingId === task.task_id"
            @click="handleCancel(task)"
          >
            取消
          </el-button>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  cancelRecognizeSubtitleTask,
  listRecognizeSubtitleTasks,
  type RecognizeSubtitleTask,
} from "@/utils/subtitle";

const visible = ref(false);
const loading = ref(false);
const tasks = ref<RecognizeSubtitleTask[]>([]);
const cancelingId = ref<string | null>(null);

const taskBasename = (path?: string) => {
  if (!path) return "—";
  const parts = path.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || path;
};

const statusText = (status?: string) => {
  const map: Record<string, string> = {
    pending: "等待中",
    processing: "识别中",
    success: "已完成",
    failed: "失败",
  };
  return map[status ?? ""] ?? status ?? "—";
};

const statusTag = (status?: string): "info" | "warning" | "success" | "danger" => {
  if (status === "processing") return "warning";
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  return "info";
};

const canCancel = (task: RecognizeSubtitleTask) =>
  task.status === "pending" || task.status === "processing";

const fetchTasks = async () => {
  loading.value = true;
  try {
    tasks.value = await listRecognizeSubtitleTasks();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "获取识别任务失败";
    ElMessage.error(msg);
    tasks.value = [];
  } finally {
    loading.value = false;
  }
};

const handleCancel = async (task: RecognizeSubtitleTask) => {
  const name = taskBasename(task.video_path);
  try {
    await ElMessageBox.confirm(
      `确定取消识别任务「${name}」吗？`,
      "取消识别",
      {
        confirmButtonText: "确定取消",
        cancelButtonText: "返回",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  cancelingId.value = task.task_id;
  try {
    await cancelRecognizeSubtitleTask(task.task_id);
    ElMessage.success("已取消");
    await fetchTasks();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "取消失败";
    ElMessage.error(msg);
  } finally {
    cancelingId.value = null;
  }
};
</script>
