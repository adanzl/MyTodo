<template>
  <div class="p-4">
    <el-skeleton :loading="loading" :rows="10" animated>
      <template #default>
        <!-- 版本信息 + App 配置 -->
        <el-card class="mb-4">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="text-lg font-bold">版本 & App 配置</span>
              <div class="flex gap-2">
                <el-button type="success" @click="handlePublish" :loading="publishing">
                  发布新版本
                </el-button>
                <el-button @click="loadConfig" :icon="Refresh" />
              </div>
            </div>
          </template>
          <!-- 版本信息 -->
          <el-descriptions :column="3" border class="mb-4">
            <el-descriptions-item label="版本号">
              <el-tag size="large" type="primary">{{ config.version || '-' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ config.timestamp || '-' }}</el-descriptions-item>
            <el-descriptions-item label="环境">
              <el-tag :type="config.env === 'production' ? 'success' : 'warning'">
                {{ config.env || '未设置' }}
              </el-tag>
              <span class="ml-1 text-xs text-gray-400">(.env)</span>
            </el-descriptions-item>
          </el-descriptions>
          <!-- App 配置 -->
          <el-form :model="appForm" label-width="100px" class="mt-2">
            <div class="flex justify-end mb-2">
              <el-button type="primary" size="small" @click="handleSaveApp" :loading="savingApp">
                保存
              </el-button>
            </div>
            <el-form-item label="App 版本">
              <el-input v-model="appForm.version" placeholder="如 2.3.1" />
            </el-form-item>
            <el-form-item label="下载地址">
              <el-input v-model="appForm.url" placeholder="https://example.com/app.apk" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 白名单配置 -->
        <el-card class="mb-4">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">白名单配置</span>
              <el-button type="primary" size="small" @click="handleSaveWhitelist" :loading="savingWhitelist">
                保存
              </el-button>
            </div>
          </template>
          <el-form label-width="100px">
            <el-form-item label="开启白名单">
              <el-switch
                v-model="whitelistForm.open"
                active-value="true"
                inactive-value="false"
              />
            </el-form-item>
            <el-form-item label="URL 列表">
              <div class="w-full">
                <div
                  v-for="(url, index) in whitelistForm.urls"
                  :key="index"
                  class="flex gap-2 mb-2"
                >
                  <el-input v-model="whitelistForm.urls[index]" placeholder="example.com" />
                  <el-button type="danger" plain circle @click="removeUrl(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <el-button type="primary" plain @click="addUrl">添加 URL</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Admin 配置 -->
        <el-card>
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold">Admin 配置</span>
              <el-button type="primary" size="small" @click="handleSaveAdmin" :loading="savingAdmin">
                保存
              </el-button>
            </div>
          </template>
          <el-form :model="adminForm" label-width="100px">
            <el-form-item label="PIN 码">
              <el-input v-model="adminForm.pin" type="password" show-password placeholder="输入新 PIN 码（保存时自动 MD5）" />
            </el-form-item>
          </el-form>
        </el-card>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Refresh } from "@element-plus/icons-vue";
import { getBrowserConfig, setBrowserConfig, publishBrowserVersion } from "@/api/api-browser";
import type { BrowserConfig } from "@/api/api-browser";

const loading = ref(false);
const savingApp = ref(false);
const savingWhitelist = ref(false);
const savingAdmin = ref(false);
const publishing = ref(false);

const config = ref<BrowserConfig>({
  version: "",
  timestamp: "",
  env: "",
  app: { version: "", url: "" },
  admin: { pin: "" },
  whitelist: { open: "false", urls: [] },
});

const appForm = reactive({ version: "", url: "" });
const whitelistForm = reactive({ open: "false", urls: [] as string[] });
const adminForm = reactive({ pin: "" });

const loadConfig = async () => {
  loading.value = true;
  try {
    const data = await getBrowserConfig();
    config.value = data;
    appForm.version = data.app?.version || "";
    appForm.url = data.app?.url || "";
    whitelistForm.open = data.whitelist?.open || "false";
    whitelistForm.urls = [...(data.whitelist?.urls || [])];
    adminForm.pin = "";
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "加载配置失败");
  } finally {
    loading.value = false;
  }
};

const handleSaveApp = async () => {
  savingApp.value = true;
  try {
    await setBrowserConfig({ app: { ...appForm } });
    ElMessage.success("App 配置已保存");
    await loadConfig();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingApp.value = false;
  }
};

const handleSaveWhitelist = async () => {
  savingWhitelist.value = true;
  try {
    const urls = whitelistForm.urls.filter((u) => u.trim() !== "");
    await setBrowserConfig({ whitelist: { open: whitelistForm.open, urls } });
    ElMessage.success("白名单配置已保存");
    await loadConfig();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingWhitelist.value = false;
  }
};

const handleSaveAdmin = async () => {
  if (!adminForm.pin.trim()) {
    ElMessage.warning("请输入 PIN 码");
    return;
  }
  savingAdmin.value = true;
  try {
    await setBrowserConfig({ admin: { pin: adminForm.pin } });
    ElMessage.success("Admin 配置已保存");
    adminForm.pin = "";
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingAdmin.value = false;
  }
};

const handlePublish = async () => {
  try {
    await ElMessageBox.confirm("确认发布新版本？版本号将自动递增。", "提示", { type: "warning" });
    publishing.value = true;
    const result = await publishBrowserVersion();
    ElMessage.success(`版本 ${result.version} 已发布`);
    await loadConfig();
  } catch (e: unknown) {
    if ((e as Error).message !== "cancel") {
      ElMessage.error((e as Error).message || "发布失败");
    }
  } finally {
    publishing.value = false;
  }
};

const addUrl = () => {
  whitelistForm.urls.push("");
};

const removeUrl = (index: number) => {
  whitelistForm.urls.splice(index, 1);
};

onMounted(() => {
  loadConfig();
});
</script>
