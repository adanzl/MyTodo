<template>
  <div class="p-4">
    <el-skeleton :loading="loading" :rows="10" animated>
      <template #default>
        <!-- 版本信息 + App 配置 -->
        <el-card class="mb-4">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="text-lg font-bold">版本 & App 配置</span>
              <div class="flex gap-2 flex-1 justify-between items-center ml-3">
                <el-button @click="loadConfig" :icon="Refresh" type="primary" size="small" />
                <el-tooltip placement="bottom">
                  <template #content>
                    <pre class="m-0 text-xs">{{ configJson }}</pre>
                  </template>
                  <el-icon class="cursor-pointer">
                    <View />
                  </el-icon>
                </el-tooltip>
                <el-button type="success" @click="handlePublish" :loading="publishing">
                  发布新版本
                </el-button>
              </div>
            </div>
          </template>
          <!-- 版本信息 -->
          <el-descriptions :column="4" border class="mb-4">
            <el-descriptions-item label="版本号">
              <el-tag size="large" type="primary">{{ config.version || '-' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ config.timestamp || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ config.publishTime || '-' }}</el-descriptions-item>
            <el-descriptions-item label="环境">
              <el-tag :type="config.env === 'production' ? 'success' : 'warning'">
                {{ config.env || '未设置' }}
              </el-tag>
              <span class="ml-1 text-xs text-gray-400">(.env)</span>
            </el-descriptions-item>
          </el-descriptions>
          <!-- App 配置 + PIN 码 -->
          <div class="flex gap-4">
            <div class="flex-1 min-w-0">
              <el-form :model="appForm" label-width="100px">
                <el-form-item label="App 版本">
                  <div class="flex gap-2 items-center w-full">
                    <el-input v-model="appForm.version" placeholder="如 2.3.1" class="flex-1" />
                    <el-button type="warning" size="small" @click="handleLoadApkVersion" :loading="loadingApkVersion">
                      加载
                    </el-button>
                    <el-button type="primary" size="small" @click="handleSaveApp" :loading="savingApp">
                      保存
                    </el-button>
                  </div>
                </el-form-item>
                <el-form-item label="下载地址">
                  <div class="flex gap-2 items-center w-full">
                    <el-input v-model="appForm.url" placeholder="https://example.com/app.apk" class="flex-1" />
                    <el-button size="small" @click="setRemoteUrl"
                      :type="urlMode === 'remote' ? 'primary' : ''">远程</el-button>
                    <el-button size="small" @click="setLocalUrl"
                      :type="urlMode === 'local' ? 'primary' : ''">本地</el-button>
                  </div>
                </el-form-item>
                <el-form-item label="构建地址">
                  <div class="flex gap-2 items-center w-full">
                    <el-input v-model="buildPath" placeholder="/mnt/data/project/linxi-browser" class="flex-1" />
                    <el-button type="warning" @click="handleBuild" :loading="building">构建</el-button>
                  </div>
                  <div class="flex gap-2 items-center mt-1 text-xs">
                    <el-tag
                      :type="buildStatus?.status === 'success' ? 'success' : buildStatus?.status === 'failed' ? 'danger' : 'warning'"
                      size="small">
                      {{ buildStatus?.status === 'building' && buildStatus?.alive ? '构建中' : buildStatus?.status ===
                        'success' ?
                        '构建成功' : buildStatus?.status === 'failed' ? '构建失败' : buildStatus?.status || '未构建' }}
                    </el-tag>
                    <span class="text-gray-400">{{ buildStatus?.time }}</span>
                    <span v-if="buildStatus?.pid" class="text-gray-400">pid={{ buildStatus?.pid }}</span>
                    <el-button link type="primary" size="small" @click="loadBuildStatus">刷新</el-button>
                    <el-button link type="primary" size="small" @click="handleShowLog">log</el-button>
                  </div>
                </el-form-item>
              </el-form>
            </div>
            <div class="flex-1 min-w-0">
              <el-form :model="adminForm" label-width="100px">
                <el-form-item label="PIN 码">
                  <div class="flex gap-2 items-center w-full">
                    <el-input v-model="adminForm.pin" type="password" show-password placeholder="输入新 PIN 码" />
                    <el-tag type="info" class="shrink-0">{{ config.admin?.pin || '未设置' }}</el-tag>
                    <el-button type="primary" size="small" @click="handleSetPin" :loading="savingAdmin"
                      :disabled="!adminForm.pin.trim()">
                      设置
                    </el-button>
                    <el-button size="small" @click="handleClearPin" :disabled="!config.admin?.pin">
                      清空
                    </el-button>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-card>

        <!-- 白名单 -->
        <div class="mb-4">
          <el-card>
            <template #header>
              <span class="font-bold">白名单配置</span>
            </template>
            <div class="flex divide-x divide-gray-200">
              <div v-for="col in USER_COLUMNS" :key="col.key" class="flex-1 min-w-0 px-4 first:pl-0 last:pr-0">
                <div class="text-left font-medium mb-2 pl-2">{{ col.label }}</div>
                <el-form label-width="80px" size="small">
                  <el-form-item label="开启">
                    <el-switch v-model="whitelistForm[col.key].open" active-value="true" inactive-value="false" @change="handleSaveWhitelist(col.key)" />
                  </el-form-item>
                  <el-form-item label="URL 列表">
                    <div class="w-full">
                      <div v-for="(_, index) in whitelistForm[col.key].urls" :key="index" class="flex gap-1 mb-2">
                        <el-input v-model="whitelistForm[col.key].urls[index]" placeholder="example.com"
                          :disabled="!editingUrls[col.key][index]" size="small" />
                        <el-button @click="toggleEditUrl(col.key, index)"
                          :icon="editingUrls[col.key][index] ? Reading : Edit" circle size="small" />
                        <el-button type="danger" plain circle @click="removeUrl(col.key, index)" size="small">
                          <el-icon>
                            <Delete />
                          </el-icon>
                        </el-button>
                      </div>
                      <el-button type="primary" plain @click="addUrl(col.key)" size="small">添加</el-button>
                    </div>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 书签配置 -->
        <div class="mb-4">
          <el-card>
            <template #header>
              <span class="font-bold">书签配置</span>
            </template>
            <div class="flex divide-x divide-gray-200">
              <div v-for="col in USER_COLUMNS" :key="col.key" class="flex-1 min-w-0 px-4 first:pl-0 last:pr-0">
                <div class="text-left font-medium mb-2 pl-2">{{ col.label }}</div>
                <div class="w-full">
                  <div v-for="(mark, index) in marksForm[col.key]" :key="index"
                    class="flex flex-col gap-1 mb-3 pb-3 border-b border-gray-100 last:border-b-0">
                    <div class="flex gap-2 items-center">
                      <el-tag type="info" size="small">#{{ mark.position }}</el-tag>
                      <span class="font-medium truncate">{{ mark.title || '未命名' }}</span>
                      <el-button :icon="ArrowUp" circle size="small" :disabled="index === 0"
                        @click="moveMarkUp(col.key, index)" class="ml-auto shrink-0" />
                      <el-button :icon="ArrowDown" circle size="small"
                        :disabled="index === marksForm[col.key].length - 1" @click="moveMarkDown(col.key, index)" />
                      <el-button :icon="Edit" circle size="small" @click="editMark(col.key, index)" />
                      <el-button type="danger" :icon="Delete" circle size="small" @click="removeMark(col.key, index)" />
                    </div>
                    <span class="text-xs text-blue-500 truncate">{{ mark.url || '-' }}</span>
                  </div>
                  <el-button type="primary" plain
                    @click="currentMarkUser = col.key; editingMarkIndex = -1; showMarkDialog = true"
                    size="small">添加书签</el-button>
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <BookmarkDialog
          v-model="showMarkDialog"
          :editing-mark="editingMarkIndex >= 0 ? marksForm[currentMarkUser][editingMarkIndex] : null"
          @confirm="onBookmarkConfirm"
        />

        <BuildLogDialog v-model="showLogDialog" />

      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowDown, ArrowUp, Delete, Edit, Reading, Refresh, View } from "@element-plus/icons-vue";
import { getBrowserConfig, setBrowserConfig, publishBrowserVersion, buildBrowser, getBuildStatus, getLatestApkVersion } from "@/api/api-browser";
import BookmarkDialog from "./dialogs/BookmarkDialog.vue";
import BuildLogDialog from "./dialogs/BuildLogDialog.vue";
import type { BrowserConfig, BrowserMark } from "@/api/api-browser";
import { REMOTE, LOCAL_IP, LOCAL_HTTP_PORT } from "@/api/config";

// 用户列定义
const USER_COLUMNS = [
  { key: "3", label: "灿灿" },
  { key: "4", label: "昭昭" },
];

const loading = ref(false);
const savingApp = ref(false);
const savingWhitelist = ref(false);
const savingAdmin = ref(false);
const savingMarks = ref(false);
const publishing = ref(false);
const building = ref(false);
const loadingApkVersion = ref(false);
const buildPath = ref('/mnt/data/project/linxi-browser');
const buildStatus = ref<{ status: string; time: string; path: string; pid: number; log: string; alive: boolean } | null>(null);

const showLogDialog = ref(false);

// 下载地址域名切换
const REMOTE_DOWNLOAD_DOMAIN = REMOTE.url.replace(/\/+$/, "");
const LOCAL_DOWNLOAD_DOMAIN = `http://${LOCAL_IP}:${LOCAL_HTTP_PORT}`;
const urlMode = ref<"remote" | "local" | null>(null);

const config = ref<BrowserConfig>({
  version: "",
  timestamp: "",
  publishTime: "",
  env: "",
  app: { version: "", url: "" },
  admin: { pin: "" },
  whitelist: { "3": { open: "false", urls: [] }, "4": { open: "false", urls: [] } },
  marks: { "3": [], "4": [] },
});

const configJson = computed(() => JSON.stringify(config.value, null, 2));

const appForm = reactive({ version: "", url: "" });
// 白名单：按用户分组
const whitelistForm = reactive<Record<string, { open: string; urls: string[] }>>({
  "3": { open: "false", urls: [] },
  "4": { open: "false", urls: [] },
});
const editingUrls = reactive<Record<string, Record<number, boolean>>>({ "3": {}, "4": {} });
const adminForm = reactive({ pin: "" });
// 书签：按用户分组
const marksForm = reactive<Record<string, BrowserMark[]>>({ "3": [], "4": [] });
const showMarkDialog = ref(false);
const editingMarkIndex = ref(-1);
const currentMarkUser = ref("3");

const loadConfig = async () => {
  loading.value = true;
  try {
    const data = await getBrowserConfig();
    config.value = data;
    appForm.version = data.app?.version || "";
    appForm.url = data.app?.url || "";
    // 白名单：按用户分组加载
    for (const col of USER_COLUMNS) {
      const w = data.whitelist?.[col.key];
      whitelistForm[col.key] = { open: w?.open || "false", urls: [...(w?.urls || [])] };
      editingUrls[col.key] = {};
    }
    // 书签：按用户分组加载
    for (const col of USER_COLUMNS) {
      marksForm[col.key] = [...(data.marks?.[col.key] || [])];
    }
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

const handleSaveWhitelist = async (userKey: string) => {
  savingWhitelist.value = true;
  try {
    const form = whitelistForm[userKey];
    const urls = form.urls.filter((u: string) => u.trim() !== "");
    const whitelist = { ...config.value.whitelist, [userKey]: { open: form.open, urls } };
    const result = await setBrowserConfig({ whitelist });
    config.value = result;
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingWhitelist.value = false;
  }
};

const handleSetPin = async () => {
  if (!adminForm.pin.trim()) return;
  savingAdmin.value = true;
  try {
    await setBrowserConfig({ admin: { pin: adminForm.pin } });
    ElMessage.success("PIN 码已更新");
    adminForm.pin = "";
    await loadConfig();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "设置失败");
  } finally {
    savingAdmin.value = false;
  }
};

const handleClearPin = async () => {
  try {
    await ElMessageBox.confirm("确认清空 PIN 码？", "提示", { type: "warning" });
  } catch {
    return;
  }
  savingAdmin.value = true;
  try {
    await setBrowserConfig({ admin: { pin: "" } });
    ElMessage.success("PIN 码已清空");
    await loadConfig();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "清空失败");
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

const handleLoadApkVersion = async () => {
  if (!buildPath.value.trim()) {
    ElMessage.warning("请先填写构建地址");
    return;
  }
  loadingApkVersion.value = true;
  try {
    const result = await getLatestApkVersion(buildPath.value);
    appForm.version = result.version;
    ElMessage.success(`已加载版本: ${result.version}`);
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "加载版本失败");
  } finally {
    loadingApkVersion.value = false;
  }
};

const handleBuild = async () => {
  if (!buildPath.value.trim()) {
    ElMessage.warning("请填写构建地址");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `将在 ${buildPath.value} 目录执行：sh deploy/package.sh（后台执行构建脚本）\n\n确认继续？`,
      "构建确认",
      { type: "warning" }
    );
  } catch {
    return;
  }
  building.value = true;
  try {
    const result = await buildBrowser(buildPath.value);
    ElMessage.success(`构建已启动 (pid=${result.pid})，日志: ${result.log}`);
    await loadBuildStatus();
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "构建失败");
  } finally {
    building.value = false;
  }
};

const loadBuildStatus = async () => {
  try {
    buildStatus.value = await getBuildStatus();
  } catch {
    // 忽略，可能还没有构建过
  }
};

const handleShowLog = () => {
  showLogDialog.value = true;
};

/** 替换 URL 的域名部分，保留路径和查询参数 */
function switchUrlDomain(url: string, targetDomain: string): string {
  if (!url || !url.trim()) return targetDomain + "/";
  try {
    const u = new URL(url.trim());
    const t = new URL(targetDomain);
    u.protocol = t.protocol;
    u.host = t.host;
    u.port = t.port;
    return u.toString();
  } catch {
    return url;
  }
}

function setRemoteUrl() {
  urlMode.value = "remote";
  appForm.url = switchUrlDomain(appForm.url, REMOTE_DOWNLOAD_DOMAIN);
}

function setLocalUrl() {
  urlMode.value = "local";
  appForm.url = switchUrlDomain(appForm.url, LOCAL_DOWNLOAD_DOMAIN);
}

const addUrl = (userKey: string) => {
  whitelistForm[userKey].urls.push("");
  editingUrls[userKey][whitelistForm[userKey].urls.length - 1] = true;
  handleSaveWhitelist(userKey);
};

const removeUrl = (userKey: string, index: number) => {
  whitelistForm[userKey].urls.splice(index, 1);
  handleSaveWhitelist(userKey);
};

const handleSaveMarks = async (userKey: string) => {
  savingMarks.value = true;
  try {
    const marks = { ...config.value.marks, [userKey]: [...marksForm[userKey]] };
    const result = await setBrowserConfig({ marks });
    config.value = result;
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingMarks.value = false;
  }
};

const editMark = (userKey: string, index: number) => {
  editingMarkIndex.value = index;
  currentMarkUser.value = userKey;
  showMarkDialog.value = true;
};

const onBookmarkConfirm = (data: { title: string; url: string }) => {
  const userKey = currentMarkUser.value;
  const userMarks = marksForm[userKey];
  if (editingMarkIndex.value >= 0) {
    userMarks[editingMarkIndex.value].title = data.title;
    userMarks[editingMarkIndex.value].url = data.url;
  } else {
    const nextPos = userMarks.length > 0 ? userMarks.length + 1 : 1;
    userMarks.push({ title: data.title, url: data.url, position: nextPos });
  }
  handleSaveMarks(userKey);
};

const removeMark = (userKey: string, index: number) => {
  marksForm[userKey].splice(index, 1);
  handleSaveMarks(userKey);
};

const reorderMarks = (userKey: string, fn: (arr: BrowserMark[]) => BrowserMark[]) => {
  const arr = fn([...marksForm[userKey]]);
  arr.forEach((m, i) => (m.position = i + 1));
  marksForm[userKey] = arr;
  handleSaveMarks(userKey);
};

const moveMarkUp = (userKey: string, index: number) => {
  if (index <= 0) return;
  reorderMarks(userKey, (arr) => {
    [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
    return arr;
  });
};

const moveMarkDown = (userKey: string, index: number) => {
  if (index >= marksForm[userKey].length - 1) return;
  reorderMarks(userKey, (arr) => {
    [arr[index + 1], arr[index]] = [arr[index], arr[index + 1]];
    return arr;
  });
};

const toggleEditUrl = (userKey: string, index: number) => {
  if (editingUrls[userKey][index]) {
    // 退出编辑时处理 URL：去掉协议和端口
    const raw = whitelistForm[userKey].urls[index];
    whitelistForm[userKey].urls[index] = raw.replace(/^https?:\/\//, "").replace(/:\d+$/, "");
    editingUrls[userKey][index] = false;
    if (!savingWhitelist.value) {
      handleSaveWhitelist(userKey);
    }
  } else {
    editingUrls[userKey][index] = true;
  }
};

onMounted(async () => {
  await loadConfig();
  await loadBuildStatus();
});
</script>
