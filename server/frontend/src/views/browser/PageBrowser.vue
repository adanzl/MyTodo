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
                <el-button type="success" @click="handlePublish" :loading="publishing">
                  发布新版本
                </el-button>
              </div>
            </div>
          </template>
          <!-- 版本信息 -->
          <el-descriptions :column="3" border class="mb-4">
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
              <div class="flex gap-2 items-center w-full">
                <el-input v-model="appForm.url" placeholder="https://example.com/app.apk" class="flex-1" />
                <el-button size="small" @click="setRemoteUrl" :type="urlMode === 'remote' ? 'primary' : ''">远程</el-button>
                <el-button size="small" @click="setLocalUrl" :type="urlMode === 'local' ? 'primary' : ''">本地</el-button>
              </div>
            </el-form-item>
          </el-form>
          <!-- PIN 码设置 -->
          <el-divider />
          <el-form :model="adminForm" label-width="100px">
            <el-form-item label="PIN 码">
              <div class="flex gap-2 items-center w-full">
                <el-input v-model="adminForm.pin" type="password" show-password placeholder="输入新 PIN 码" />
                <el-tag type="info" class="shrink-0">{{ config.admin?.pin || '未设置' }}</el-tag>
                <el-button type="primary" size="small" @click="handleSetPin" :loading="savingAdmin" :disabled="!adminForm.pin.trim()">
                  设置
                </el-button>
                <el-button size="small" @click="handleClearPin" :disabled="!config.admin?.pin">
                  清空
                </el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 白名单 + 书签 -->
        <div class="flex gap-4 mb-4">
          <!-- 白名单配置 -->
          <el-card class="flex-1 min-w-0">
            <template #header>
              <span class="font-bold">白名单配置</span>
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
                    v-for="(_, index) in whitelistForm.urls"
                    :key="index"
                    class="flex gap-2 mb-2"
                  >
                    <el-input v-model="whitelistForm.urls[index]" placeholder="example.com" :disabled="!editingUrls[index]" />
                    <el-button @click="toggleEditUrl(index)" :icon="editingUrls[index] ? Reading : Edit" circle />
                    <el-button type="danger" plain circle @click="removeUrl(index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button type="primary" plain @click="addUrl">添加</el-button>
                </div>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 书签配置 -->
          <el-card class="flex-1 min-w-0">
            <template #header>
              <span class="font-bold">书签配置</span>
            </template>
            <div class="w-full">
              <div
                v-for="(mark, index) in marksForm"
                :key="index"
                class="flex flex-col gap-1 mb-3 pb-3 border-b border-gray-100 last:border-b-0"
              >
                <div class="flex gap-2 items-center">
                  <el-tag type="info" size="small">#{{ mark.position }}</el-tag>
                  <span class="font-medium truncate">{{ mark.title || '未命名' }}</span>
                  <el-button :icon="ArrowUp" circle size="small" :disabled="index === 0" @click="moveMarkUp(index)" class="ml-auto shrink-0" />
                  <el-button :icon="ArrowDown" circle size="small" :disabled="index === marksForm.length - 1" @click="moveMarkDown(index)" />
                  <el-button :icon="Edit" circle size="small" @click="editMark(index)" />
                  <el-button type="danger" :icon="Delete" circle size="small" @click="removeMark(index)" />
                </div>
                <span class="text-xs text-blue-500 truncate">{{ mark.url || '-' }}</span>
              </div>
              <el-button type="primary" plain @click="showMarkDialog = true">添加书签</el-button>
            </div>
          </el-card>
        </div>

        <!-- 添加/编辑书签弹窗 -->
        <el-dialog v-model="showMarkDialog" :title="editingMarkIndex >= 0 ? '编辑书签' : '添加书签'" width="420px">
          <el-form :model="markForm" label-width="60px">
            <el-form-item label="标题">
              <el-input v-model="markForm.title" placeholder="书签名称" />
            </el-form-item>
            <el-form-item label="URL">
              <el-input v-model="markForm.url" placeholder="https://..." />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showMarkDialog = false">取消</el-button>
            <el-button type="primary" @click="confirmAddMark" :disabled="!markForm.title.trim()">
              确定
            </el-button>
          </template>
        </el-dialog>

      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowDown, ArrowUp, Delete, Edit, Reading, Refresh } from "@element-plus/icons-vue";
import { getBrowserConfig, setBrowserConfig, publishBrowserVersion } from "@/api/api-browser";
import type { BrowserConfig, BrowserMark } from "@/api/api-browser";
import { REMOTE, LOCAL_IP, LOCAL_HTTP_PORT } from "@/api/config";

const loading = ref(false);
const savingApp = ref(false);
const savingWhitelist = ref(false);
const savingAdmin = ref(false);
const savingMarks = ref(false);
const publishing = ref(false);

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
  whitelist: { open: "false", urls: [] },
  marks: [],
});

const appForm = reactive({ version: "", url: "" });
const whitelistForm = reactive({ open: "false", urls: [] as string[] });
const originalUrls = ref<string[]>([]);
const editingUrls = reactive<Record<number, boolean>>({});
const adminForm = reactive({ pin: "" });
const marksForm = reactive<BrowserMark[]>([]);
const showMarkDialog = ref(false);
const editingMarkIndex = ref(-1);
const markForm = reactive({ title: "", url: "", position: 1 });

const loadConfig = async () => {
  loading.value = true;
  try {
    const data = await getBrowserConfig();
    config.value = data;
    appForm.version = data.app?.version || "";
    appForm.url = data.app?.url || "";
    whitelistForm.open = data.whitelist?.open || "false";
    whitelistForm.urls = [...(data.whitelist?.urls || [])];
    originalUrls.value = [...(data.whitelist?.urls || [])];
    marksForm.length = 0;
    marksForm.push(...(data.marks || []));
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
    const urls = whitelistForm.urls.map((url, i) =>
      editingUrls[i] ? originalUrls.value[i] ?? url : url
    ).filter((u) => u.trim() !== "");
    const result = await setBrowserConfig({ whitelist: { open: whitelistForm.open, urls } });
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

const addUrl = () => {
  whitelistForm.urls.push("");
  editingUrls[whitelistForm.urls.length - 1] = true;
};

const removeUrl = (index: number) => {
  whitelistForm.urls.splice(index, 1);
};

const handleSaveMarks = async () => {
  savingMarks.value = true;
  try {
    const marks = [...marksForm];
    const result = await setBrowserConfig({ marks });
    config.value = result;
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || "保存失败");
  } finally {
    savingMarks.value = false;
  }
};

const editMark = (index: number) => {
  editingMarkIndex.value = index;
  const mark = marksForm[index];
  markForm.title = mark.title;
  markForm.url = mark.url;
  showMarkDialog.value = true;
};

const confirmAddMark = () => {
  if (!markForm.title.trim()) return;
  if (editingMarkIndex.value >= 0) {
    marksForm[editingMarkIndex.value].title = markForm.title.trim();
    marksForm[editingMarkIndex.value].url = markForm.url.trim();
  } else {
    const nextPos = marksForm.length > 0 ? marksForm.length + 1 : 1;
    marksForm.push({ title: markForm.title.trim(), url: markForm.url.trim(), position: nextPos });
  }
  showMarkDialog.value = false;
};

const removeMark = (index: number) => {
  marksForm.splice(index, 1);
};

const reorderMarks = (fn: (arr: BrowserMark[]) => BrowserMark[]) => {
  const arr = fn([...marksForm]);
  arr.forEach((m, i) => (m.position = i + 1));
  marksForm.length = 0;
  marksForm.push(...arr);
};

const moveMarkUp = (index: number) => {
  if (index <= 0) return;
  reorderMarks((arr) => {
    [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
    return arr;
  });
};

const moveMarkDown = (index: number) => {
  if (index >= marksForm.length - 1) return;
  reorderMarks((arr) => {
    [arr[index + 1], arr[index]] = [arr[index], arr[index + 1]];
    return arr;
  });
};

const toggleEditUrl = (index: number) => {
  if (editingUrls[index]) {
    // 退出编辑时处理 URL：去掉协议和端口
    const raw = whitelistForm.urls[index];
    whitelistForm.urls[index] = raw.replace(/^https?:\/\//, "").replace(/:\d+/, "");
  }
  editingUrls[index] = !editingUrls[index];
};

// 自动保存
let whitelistLoaded = false;
let marksLoaded = false;

watch(
  () => ({ open: whitelistForm.open, urls: [...whitelistForm.urls] }),
  () => {
    if (!whitelistLoaded || savingWhitelist.value) return;
    handleSaveWhitelist();
  },
  { deep: true }
);

watch(
  marksForm,
  () => {
    if (!marksLoaded || savingMarks.value) return;
    handleSaveMarks();
  },
  { deep: true }
);

onMounted(async () => {
  await loadConfig();
  whitelistLoaded = true;
  marksLoaded = true;
});
</script>
