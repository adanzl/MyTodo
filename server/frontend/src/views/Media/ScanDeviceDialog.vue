<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleUpdateVisible"
    title="扫描到的设备"
    width="800"
  >
    <div class="mb-4">
      <el-button type="primary" @click="handleRefresh" :loading="loading">刷新扫描</el-button>
    </div>
    <el-table :data="deviceList" stripe class="w-full" v-loading="loading" :height="400">
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="address" label="地址" min-width="120" />
      <el-table-column prop="rssi" label="信号强度" width="100">
        <template #default="{ row }">
          <span>{{ row.rssi }} dBm</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button
            size="small"
            type="primary"
            @click="handleConnect(row)"
            :loading="row.connecting"
            :disabled="row.connecting"
          >
            连接
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="deviceList.length === 0 && !loading" class="text-center text-gray-400 mt-4 py-8">
      暂无扫描到的设备，点击"刷新扫描"按钮开始扫描
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean;
  deviceList: any[];
  loading: boolean;
}

interface Emits {
  (e: "update:visible", value: boolean): void;
  (e: "refresh"): void;
  (e: "connect", device: any): void;
  (e: "close"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const handleUpdateVisible = (value: boolean) => {
  emit("update:visible", value);
  if (!value) {
    emit("close");
  }
};

const handleRefresh = () => {
  emit("refresh");
};

const handleConnect = (device: any) => {
  emit("connect", device);
};
</script>
