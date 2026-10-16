<template>
    <div class="flex gap-4 h-[calc(100vh-220px)] min-w-0 overflow-hidden">
        <div class="w-64 shrink-0 border rounded p-3 flex flex-col">
            <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-semibold">任务列表</h3>
                <el-button type="info" v-bind="smallIconButtonProps" @click="loadTaskList" :loading="loading">
                    <el-icon v-if="!loading">
                        <Refresh />
                    </el-icon>
                </el-button>
            </div>
            <div v-if="taskList.length > 0" class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-100">
                <div v-for="task in taskList" :key="task.task_id"
                    class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 min-h-15 flex flex-col justify-between gap-1"
                    :class="{
                        'border-blue-500 bg-blue-50': currentTask && task.task_id === currentTask.task_id,
                    }" @click="handleViewTask(task.task_id)">
                    <div class="text-sm font-medium truncate" :title="task.name || task.source_url || task.task_id">
                        {{ task.name || task.source_url || task.task_id }}
                    </div>
                    <div class="flex items-center justify-between gap-2 min-h-5">
                        <div class="flex items-center gap-1 min-w-0">
                            <el-tag v-if="task.platform_label" size="small" type="info" class="h-5! text-xs!">
                                {{ task.platform_label }}
                            </el-tag>
                            <el-tag :type="getStatusTagType(task.status)" size="small"
                                class="h-5! text-xs! w-14 text-center">
                                {{ getStatusText(task.status) }}
                            </el-tag>
                        </div>
                        <el-button type="danger" v-bind="smallTextButtonProps"
                            @click.stop="handleDeleteTask(task.task_id)" :disabled="task.status === 'processing'">
                            <el-icon>
                                <Delete />
                            </el-icon>
                        </el-button>
                    </div>
                    <div v-if="task.status === 'processing' && task.stage" class="text-xs text-gray-500 truncate">
                        {{ task.stage }}
                    </div>
                </div>
            </div>
            <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400 min-h-100 text-center px-2">
                还没有任务。在右侧粘贴链接开始。
            </div>
            <div class="shrink-0 border-t mt-2 pt-2">
                <el-button type="danger" plain class="w-full" :disabled="!hasClearableTasks || loading"
                    @click="handleClearAllTasks">
                    删除所有任务
                </el-button>
            </div>
        </div>

        <div class="flex-1 min-w-0 border rounded p-3 flex flex-col min-h-0 gap-3">
            <div class="shrink-0">
                <div class="flex items-center gap-2">
                    <el-input ref="urlInputRef" v-model="sourceUrl" clearable class="flex-1 min-w-0"
                        placeholder="粘贴视频链接或分享文案，回车开始" @keyup.enter="handleExtract" />
                    <el-button plain :disabled="submitting" @click="openLogin">登录</el-button>
                    <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="handleExtract">
                        提取
                    </el-button>
                </div>
                <div class="mt-2 min-h-5 flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                    <el-tag v-if="urlHint.site" size="small" type="success" class="h-5! text-xs!">
                        {{ urlHint.site.label }}
                    </el-tag>
                    <span>{{ urlHint.text }}</span>
                    <el-tag size="small" :type="loginReady('bilibili') ? 'success' : 'info'" class="h-5! text-xs! cursor-pointer"
                        @click="openLogin">
                        哔哩哔哩 {{ loginReady('bilibili') ? '已登录' : '未登录' }}
                    </el-tag>
                    <el-tag size="small" :type="loginReady('douyin') ? 'success' : 'info'" class="h-5! text-xs! cursor-pointer"
                        @click="openLogin">
                        抖音 {{ loginReady('douyin') ? '已登录' : '未登录' }}
                    </el-tag>
                </div>
            </div>

            <template v-if="currentTask">
                <div class="shrink-0">
                    <h3 class="text-base font-semibold mb-2 truncate"
                        :title="currentTask.name || currentTask.source_url">
                        {{ currentTask.name || "未命名任务" }}
                    </h3>
                    <div class="flex items-center gap-2 mb-2 flex-wrap">
                        <el-tag :type="getStatusTagType(currentTask.status)" size="small" class="w-14 text-center">
                            {{ getStatusText(currentTask.status) }}
                        </el-tag>
                        <el-tag v-if="currentTask.platform_label" size="small" type="info">
                            {{ currentTask.platform_label }}
                        </el-tag>
                        <el-tag v-if="subtitleSourceLabel" size="small">
                            {{ subtitleSourceLabel }}
                        </el-tag>
                    </div>
                    <a v-if="currentTask.source_url" :href="currentTask.source_url" target="_blank"
                        rel="noopener noreferrer"
                        class="text-xs text-blue-600 hover:text-blue-800 wrap-anywhere block mb-2">
                        {{ currentTask.source_url }}
                    </a>
                    <div v-if="currentTask.status === 'processing'" class="mb-2">
                        <el-progress :percentage="50" indeterminate />
                        <div class="text-xs text-gray-500">{{ currentTask.stage || "正在处理" }}</div>
                    </div>
                    <div v-if="currentTask.error_message" class="text-xs text-red-500 wrap-anywhere mb-2">
                        {{ currentTask.error_message }}
                    </div>
                    <div class="flex gap-2">
                        <div class="border rounded p-2 flex-1 min-w-0">
                            <div class="flex items-center justify-between gap-2">
                                <h4 class="text-xs font-semibold">视频</h4>
                                <a v-if="currentTask.uploaded_info" class="text-xs text-blue-600 hover:text-blue-800"
                                    :href="downloadUrl('video')" target="_blank" rel="noopener noreferrer">下载</a>
                            </div>
                            <div v-if="currentTask.uploaded_info" class="text-xs text-gray-600 truncate"
                                :title="currentTask.uploaded_info.name">
                                {{ currentTask.uploaded_info.name }}
                                <span class="text-gray-400">{{ formatSize(currentTask.uploaded_info.size ?? 0) }}</span>
                            </div>
                            <div v-else class="text-xs text-gray-400">下载完成后显示</div>
                        </div>
                        <div class="border rounded p-2 flex-1 min-w-0">
                            <div class="flex items-center justify-between gap-2">
                                <h4 class="text-xs font-semibold">字幕</h4>
                                <a v-if="currentTask.subtitle_info" class="text-xs text-blue-600 hover:text-blue-800"
                                    :href="downloadUrl('subtitle')" target="_blank" rel="noopener noreferrer">下载</a>
                            </div>
                            <div v-if="currentTask.subtitle_info" class="text-xs text-gray-600 truncate">
                                {{ currentTask.subtitle_info.name }}
                            </div>
                            <div v-else class="text-xs text-gray-400">提取完成后显示</div>
                        </div>
                    </div>
                </div>

                <div class="flex-1 min-h-0 border rounded flex flex-col">
                    <div class="shrink-0 flex items-center justify-between px-3 py-2 border-b">
                        <span class="text-sm font-semibold">字幕文本</span>
                        <el-button size="small" plain :disabled="!currentTask.text" @click="copyText">复制</el-button>
                    </div>
                    <div v-if="currentTask.text" class="flex-1 overflow-y-auto p-3 text-sm leading-6 whitespace-pre-wrap wrap-break-word">
                        {{ currentTask.text }}
                    </div>
                    <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
                        {{ currentTask.status === 'processing' ? '字幕出来后会显示在这里' : '这个任务还没有字幕文本' }}
                    </div>
                </div>
            </template>

            <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
                粘贴链接并提取。完成后在这里看字幕。
            </div>
        </div>

        <el-dialog v-model="loginVisible" title="登录站点" width="520px" :close-on-click-modal="false" @closed="stopQrPoll()">
            <p class="text-xs text-gray-500 mb-3">用对应 App 扫码。登录态保存在服务器上，不用改配置文件。</p>
            <div class="space-y-3">
                <div v-for="site in qrSites" :key="site.id" class="border rounded p-3">
                    <div class="flex items-center justify-between gap-2 mb-2">
                        <h4 class="text-sm font-semibold">{{ site.label }}</h4>
                        <el-tag size="small" :type="loginReady(site.id) ? 'success' : 'info'">
                            {{ loginReady(site.id) ? '已登录' : '未登录' }}
                        </el-tag>
                    </div>
                    <p class="text-xs text-gray-500 mb-2">{{ site.hint }}</p>
                    <div v-if="site.image" class="flex justify-center mb-2">
                        <img :src="site.image" :alt="`${site.label}登录二维码`" class="w-48 h-48" />
                    </div>
                    <p v-if="site.message" class="text-xs text-gray-600 mb-2">{{ site.message }}</p>
                    <div class="flex gap-2">
                        <el-button size="small" type="primary" :loading="site.loading" @click="startQr(site.id)">
                            {{ site.image ? '重新生成' : '显示二维码' }}
                        </el-button>
                        <el-button v-if="loginReady(site.id)" size="small" plain :disabled="loginBusy"
                            @click="logoutSite(site.id)">
                            退出
                        </el-button>
                    </div>
                </div>
            </div>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Delete } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import { useControllableInterval } from "@/composables/useInterval";
import QRCode from "qrcode";
import {
    getVideoDumpSites,
    getVideoDumpLogin,
    getVideoDumpList,
    createVideoDump,
    getVideoDumpTaskStatus,
    getVideoDumpDownloadUrl,
    deleteVideoDump,
    startBilibiliQr,
    pollBilibiliQr,
    startDouyinQr,
    pollDouyinQr,
    logoutVideoDump,
} from "@/api/api-video-dump";
import type { VideoDumpLoginSite, VideoDumpQrStart, VideoDumpSite, VideoDumpTask } from "@/types/tools/video-dump";

const FALLBACK_SITES: VideoDumpSite[] = [
    { id: "bilibili", label: "哔哩哔哩", hosts: ["bilibili.com", "b23.tv"] },
    { id: "douyin", label: "抖音", hosts: ["douyin.com", "iesdouyin.com"] },
];

const STATUS_MAP: Record<string, { tag: "info" | "warning" | "success" | "danger"; text: string }> = {
    uploaded: { tag: "info", text: "已上传" },
    pending: { tag: "info", text: "等待" },
    processing: { tag: "warning", text: "处理" },
    success: { tag: "success", text: "完成" },
    failed: { tag: "danger", text: "失败" },
};

const SUBTITLE_SOURCE: Record<string, string> = {
    platform: "平台字幕",
    whisper: "语音识别",
};

const smallIconButtonProps = { size: "small" as const, plain: true, class: "w-8! h-6! p-0!" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "h-5! text-xs! px-2!" };

const loading = ref(false);
const submitting = ref(false);
const sourceUrl = ref("");
const sites = ref<VideoDumpSite[]>(FALLBACK_SITES);
const loginSites = ref<VideoDumpLoginSite[]>([]);
const taskList = ref<VideoDumpTask[]>([]);
const currentTask = ref<VideoDumpTask | null>(null);
const urlInputRef = ref<{ focus: () => void } | null>(null);
const loginVisible = ref(false);
const loginBusy = ref(false);

type QrSiteId = "bilibili" | "douyin";
interface QrSite {
    id: QrSiteId;
    label: string;
    hint: string;
    image: string;
    message: string;
    loginId: string;
    loading: boolean;
    timer: number;
}
const qrSites = reactive<QrSite[]>([
    {
        id: "bilibili",
        label: "哔哩哔哩",
        hint: "用哔哩哔哩 App 扫码。扫码后才能稳定拿到平台字幕。",
        image: "",
        message: "",
        loginId: "",
        loading: false,
        timer: 0,
    },
    {
        id: "douyin",
        label: "抖音",
        hint: "用抖音 App 扫码。扫码后部分视频才能下载。",
        image: "",
        message: "",
        loginId: "",
        loading: false,
        timer: 0,
    },
]);
const qrStart = { bilibili: startBilibiliQr, douyin: startDouyinQr };
const qrPoll = { bilibili: pollBilibiliQr, douyin: pollDouyinQr };

const siteLabels = computed(() => sites.value.map((site) => site.label).join("、"));
const hasProcessing = computed(() => taskList.value.some((task) => task.status === "processing"));

const extractUrl = (text: string) => {
    const match = text.match(/https?:\/\/[^\s<>"']+/i);
    if (!match) return "";
    return match[0].replace(/[，。、,.;:!?）)】」』"']+$/u, "");
};

const urlHint = computed(() => {
    const raw = sourceUrl.value.trim();
    const busy = hasProcessing.value ? "有任务正在处理，完成后再提交。" : "";
    if (!raw) {
        return { site: null as VideoDumpSite | null, text: `${busy}支持${siteLabels.value}。可以粘贴分享文案。` };
    }
    const url = extractUrl(raw);
    if (!url) {
        return { site: null, text: "没有找到链接" };
    }
    const site = matchSite(url);
    if (site?.id === "bilibili" && !loginReady("bilibili")) {
        return { site, text: busy || "未登录。点登录，用 App 扫码后才能稳定拿到平台字幕" };
    }
    if (site?.id === "douyin" && !loginReady("douyin")) {
        return { site, text: busy || "未登录。点登录，用抖音 App 扫码后部分视频才能下载" };
    }
    if (site) return { site, text: busy || "回车或点提取" };
    return { site: null, text: busy || "这个站点还没单独登记，仍会尝试下载" };
});

const canSubmit = computed(() => {
    return !!extractUrl(sourceUrl.value.trim()) && !hasProcessing.value;
});
const hasClearableTasks = computed(() => taskList.value.some((task) => task.status !== "processing"));
const subtitleSourceLabel = computed(() => SUBTITLE_SOURCE[currentTask.value?.subtitle_source || ""] || "");

const getStatusTagType = (status: string) => STATUS_MAP[status]?.tag ?? "info";
const getStatusText = (status: string) => STATUS_MAP[status]?.text ?? status;
const loginReady = (id: string) => loginSites.value.find((item) => item.id === id)?.ready ?? false;

const loadLoginStatus = async () => {
    try {
        const response = await getVideoDumpLogin();
        if (response.code === 0 && response.data) loginSites.value = response.data;
    } catch (error) {
        logAndNoticeError(error as Error, "获取登录状态失败");
    }
};

const qrSite = (id: QrSiteId) => qrSites.find((item) => item.id === id)!;

const stopQrPoll = (id?: QrSiteId) => {
    for (const site of qrSites) {
        if (id && site.id !== id) continue;
        if (!site.timer) continue;
        window.clearInterval(site.timer);
        site.timer = 0;
    }
};

const qrPicture = async (data: VideoDumpQrStart) => {
    if (data.image?.startsWith("data:image/")) return data.image;
    if (data.url?.startsWith("https://")) {
        return QRCode.toDataURL(data.url, { margin: 1, width: 192 });
    }
    return "";
};

const pollQr = async (id: QrSiteId) => {
    const site = qrSite(id);
    if (!site.loginId) return;
    try {
        const response = await qrPoll[id](site.loginId);
        if (response.code !== 0) {
            stopQrPoll(id);
            site.message = response.msg || "查询扫码状态失败";
            return;
        }
        const status = response.data?.status;
        if (status === "success") {
            stopQrPoll(id);
            site.image = "";
            site.message = "已登录";
            await loadLoginStatus();
            ElMessage.success(`${site.label}已登录`);
            return;
        }
        if (status === "scanned") {
            site.message = "已扫码，请在手机上确认";
            return;
        }
        if (status === "expired" || status === "missing") {
            stopQrPoll(id);
            site.message = "二维码已过期，请重新生成";
            return;
        }
        site.message = `请用${site.label} App 扫码`;
    } catch (error) {
        stopQrPoll(id);
        logAndNoticeError(error as Error, "查询扫码状态失败");
    }
};

const startQr = async (id: QrSiteId) => {
    const site = qrSite(id);
    stopQrPoll(id);
    site.loading = true;
    site.image = "";
    site.message = "正在获取二维码";
    try {
        const response = await qrStart[id]();
        if (response.code !== 0 || !response.data?.login_id) {
            site.message = response.msg || "申请二维码失败";
            return;
        }
        const image = await qrPicture(response.data);
        if (!image) {
            site.message = "申请二维码失败";
            return;
        }
        site.loginId = response.data.login_id;
        site.image = image;
        site.message = `请用${site.label} App 扫码`;
        site.timer = window.setInterval(() => {
            void pollQr(id);
        }, 2000);
    } catch (error) {
        site.message = "申请二维码失败";
        logAndNoticeError(error as Error, "申请二维码失败");
    } finally {
        site.loading = false;
    }
};

const openLogin = async () => {
    loginVisible.value = true;
    await loadLoginStatus();
    for (const site of qrSites) {
        if (loginReady(site.id)) continue;
        if (site.image && site.loginId) {
            if (!site.timer) {
                site.timer = window.setInterval(() => {
                    void pollQr(site.id);
                }, 2000);
            }
            continue;
        }
        void startQr(site.id);
    }
};

const logoutSite = async (id: QrSiteId) => {
    loginBusy.value = true;
    try {
        const response = await logoutVideoDump(id);
        if (response.code !== 0) {
            ElMessage.error(response.msg || "退出失败");
            return;
        }
        const site = qrSite(id);
        stopQrPoll(id);
        site.image = "";
        site.message = "";
        site.loginId = "";
        await loadLoginStatus();
        ElMessage.success("已退出");
    } catch (error) {
        logAndNoticeError(error as Error, "退出登录失败");
    } finally {
        loginBusy.value = false;
    }
};

function matchSite(url: string): VideoDumpSite | null {
    let host = "";
    try {
        host = new URL(url).hostname.toLowerCase();
    } catch {
        return null;
    }
    if (host.startsWith("www.")) host = host.slice(4);
    return (
        sites.value.find((site) => site.hosts.some((item) => host === item || host.endsWith(`.${item}`))) || null
    );
}

const confirmAction = (message: string, title = "提示") =>
    ElMessageBox.confirm(message, title, {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
    })
        .then(() => true)
        .catch(() => false);

const withLoading = async (action: () => Promise<void>, errorMessage: string) => {
    try {
        loading.value = true;
        await action();
    } catch (error) {
        logAndNoticeError(error as Error, errorMessage);
    } finally {
        loading.value = false;
    }
};

const applyTask = (task: VideoDumpTask) => {
    currentTask.value = task;
    const index = taskList.value.findIndex((item) => item.task_id === task.task_id);
    if (index >= 0) taskList.value[index] = { ...taskList.value[index], ...task };
};

const loadSites = async () => {
    try {
        const response = await getVideoDumpSites();
        if (response.code === 0 && response.data?.length) sites.value = response.data;
    } catch (error) {
        logAndNoticeError(error as Error, "获取站点列表失败");
    }
};

const loadTaskList = () =>
    withLoading(async () => {
        const response = await getVideoDumpList();
        if (response.code !== 0) {
            ElMessage.error(response.msg || "获取任务列表失败");
            return;
        }
        taskList.value = response.data || [];
        if (!currentTask.value && taskList.value.length) await syncTask(taskList.value[0].task_id);
        watchProcessing();
    }, "获取任务列表失败");

const syncTask = async (taskId?: string) => {
    const id = taskId ?? currentTask.value?.task_id;
    if (!id) return;
    const response = await getVideoDumpTaskStatus(id);
    if (response.code === 0 && response.data) applyTask(response.data);
};

const handleViewTask = async (taskId: string) => {
    try {
        await syncTask(taskId);
        watchProcessing();
    } catch (error) {
        logAndNoticeError(error as Error, "获取任务信息失败");
    }
};

const handleExtract = async () => {
    const url = extractUrl(sourceUrl.value.trim());
    if (!url || submitting.value) return;
    if (hasProcessing.value) {
        ElMessage.warning("已有任务正在处理");
        return;
    }
    submitting.value = true;
    try {
        const response = await createVideoDump(url);
        if (response.code !== 0 || !response.data?.task_id) {
            ElMessage.error(response.msg || "创建任务失败");
            return;
        }
        sourceUrl.value = "";
        ElMessage.success("已开始提取");
        taskList.value = ((await getVideoDumpList()).data as VideoDumpTask[]) || [];
        applyTask(response.data);
        startPolling();
    } catch (error) {
        logAndNoticeError(error as Error, "创建任务失败");
    } finally {
        submitting.value = false;
    }
};

const handleClearAllTasks = async () => {
    const deletable = taskList.value.filter((task) => task.status !== "processing");
    if (!deletable.length) return;
    const skipped = taskList.value.length - deletable.length;
    const message = skipped
        ? `将删除 ${deletable.length} 个任务，${skipped} 个处理中的任务会保留。`
        : "确定删除所有任务吗？视频和字幕文件会一起删除。";
    if (!(await confirmAction(message, "删除所有任务"))) return;
    await withLoading(async () => {
        const response = await deleteVideoDump(undefined, true);
        if (response.code !== 0) {
            ElMessage.error(response.msg || "删除所有任务失败");
            return;
        }
        taskList.value = ((await getVideoDumpList()).data as VideoDumpTask[]) || [];
        const still = currentTask.value && taskList.value.some((task) => task.task_id === currentTask.value?.task_id);
        if (!still) {
            if (taskList.value.length) await syncTask(taskList.value[0].task_id);
            else currentTask.value = null;
        }
        ElMessage.success("已删除");
    }, "删除所有任务失败");
};

const handleDeleteTask = async (taskId: string) => {
    if (!(await confirmAction("确定删除该任务吗？视频和字幕会一起删除。"))) return;
    await withLoading(async () => {
        const response = await deleteVideoDump(taskId);
        if (response.code !== 0) {
            ElMessage.error(response.msg || "删除任务失败");
            return;
        }
        ElMessage.success("任务已删除");
        taskList.value = ((await getVideoDumpList()).data as VideoDumpTask[]) || [];
        if (currentTask.value?.task_id !== taskId) return;
        if (taskList.value.length) await syncTask(taskList.value[0].task_id);
        else currentTask.value = null;
    }, "删除任务失败");
};

const downloadUrl = (type: "video" | "text" | "subtitle") => {
    return getVideoDumpDownloadUrl(currentTask.value?.task_id || "", type);
};

const copyText = async () => {
    const text = currentTask.value?.text || "";
    if (!text) return;
    try {
        await navigator.clipboard.writeText(text);
        ElMessage.success("已复制");
    } catch (error) {
        logAndNoticeError(error as Error, "复制失败");
    }
};

const { start: startPolling, stop: stopPolling } = useControllableInterval(async () => {
    if (!taskList.value.some((task) => task.status === "processing") && currentTask.value?.status !== "processing") {
        stopPolling();
        return;
    }
    try {
        const list = await getVideoDumpList();
        if (list.code === 0) taskList.value = list.data || [];
        const currentId = currentTask.value?.task_id;
        if (currentId) {
            const response = await getVideoDumpTaskStatus(currentId);
            if (response.code === 0 && response.data) applyTask(response.data);
        }
        if (!taskList.value.some((task) => task.status === "processing")) stopPolling();
    } catch (error) {
        logAndNoticeError(error as Error, "刷新任务状态失败");
    }
}, 2000);

function watchProcessing() {
    if (currentTask.value?.status === "processing" || hasProcessing.value) startPolling();
}

onMounted(() => {
    urlInputRef.value?.focus();
    loadSites();
    loadLoginStatus();
    loadTaskList();
});
onBeforeUnmount(() => {
    stopPolling();
    stopQrPoll();
});
</script>
