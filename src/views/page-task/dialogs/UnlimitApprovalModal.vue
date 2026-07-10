<template>
  <ion-modal
    :is-open="isOpen"
    @did-dismiss="handleDismiss"
    class="[--width:95vw] [--max-width:480px] [--height:60vh] [--border-radius:12px]"
  >
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="handleDismiss">
            <ion-icon :icon="closeOutline" />
          </ion-button>
        </ion-buttons>
        <ion-title>不限时审批</ion-title>
        <ion-buttons slot="end">
          <ion-button v-if="selectedIds.size > 0" color="success" @click="batchApprove">
            通过({{ selectedIds.size }})
          </ion-button>
          <ion-button v-if="selectedIds.size > 0" color="danger" @click="batchDeny">
            拒绝({{ selectedIds.size }})
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-content class="[--padding-bottom:8px]">
      <!-- 待审批 -->
      <div class="px-4 pt-3 pb-1 text-xs font-medium text-gray-400">待审批 ({{ applications.length }})</div>
      <div v-if="loading" class="flex justify-center items-center py-10">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <template v-else>
        <div v-if="applications.length === 0" class="text-center py-6 text-gray-400 text-sm">
          暂无待审批申请
        </div>

        <ion-list v-else class="[--ion-item-background:transparent]">
          <ion-item
            v-for="app in applications"
            :key="app.id"
            :button="false"
            :detail="false"
            lines="inset"
            class="px-2"
          >
            <ion-checkbox
              slot="start"
              :checked="selectedIds.has(app.id)"
              @ionChange="toggleSelect(app.id)"
            />
            <ion-label class="flex flex-col gap-1 py-2 ml-3">
              <div class="flex items-center gap-2">
                <span class="text-base font-medium">{{ getUserName(app.user_id) }}</span>
                <span class="text-xs text-gray-500">#{{ app.id }}</span>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
                <span>时长: {{ app.duration }}分钟</span>
                <span>{{ getLockTypeLabel(app.lock_code) }}</span>
                <span>{{ formatTime(app.created_at) }}</span>
              </div>
            </ion-label>
            <div class="flex gap-2 shrink-0" slot="end">
              <ion-button size="small" color="success" fill="outline" @click="approveOne(app.id)">
                通过
              </ion-button>
              <ion-button size="small" color="danger" fill="outline" @click="denyOne(app.id)">
                拒绝
              </ion-button>
            </div>
          </ion-item>
        </ion-list>
      </template>

      <!-- 生效中 -->
      <div class="border-t border-gray-200/60 mx-4 my-2"></div>
      <div class="px-4 pt-1 pb-1 text-xs font-medium text-gray-400">生效中 ({{ historyList.length }})</div>
      <div v-if="historyLoading" class="flex justify-center items-center py-6">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <template v-else>
        <div v-if="historyList.length === 0" class="text-center py-6 text-gray-400 text-sm">
          暂无生效中申请
        </div>

        <ion-list v-else class="[--ion-item-background:transparent]">
          <ion-item
            v-for="app in historyList"
            :key="app.id"
            :button="false"
            :detail="false"
            lines="inset"
            class="px-2"
          >
            <ion-label class="flex flex-col gap-1 py-2 ml-3">
              <div class="flex items-center gap-2">
                <span class="text-base font-medium">{{ getUserName(app.user_id) }}</span>
                <span class="text-xs text-gray-500">#{{ app.id }}</span>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
                <span>时长: {{ app.duration }}分钟</span>
                <span>{{ getLockTypeLabel(app.lock_code) }}</span>
                <span>{{ formatTime(app.created_at) }}</span>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                <span v-if="app.approved_at">审批: {{ formatTime(app.approved_at) }}</span>
                <span v-else-if="app.denied_at">拒绝: {{ formatTime(app.denied_at) }}</span>
                <span v-if="app.expires_at" :class="dayjs(app.expires_at).isBefore(dayjs()) ? 'text-red-500' : 'text-gray-500'">
                  过期: {{ formatTime(app.expires_at) }}
                </span>
              </div>
            </ion-label>
            <div class="flex gap-2 shrink-0" slot="end">
              <ion-button
                v-if="app.status === 'approved'"
                size="small"
                color="danger"
                fill="outline"
                @click="handleRevoke(app.id)"
              >
                失效
              </ion-button>
            </div>
          </ion-item>
        </ion-list>
      </template>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import dayjs from 'dayjs';
import {
  IonModal,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonButtons,
  IonButton,
  IonIcon,
  IonContent,
  IonSpinner,
  IonList,
  IonItem,
  IonLabel,
  IonCheckbox,
  alertController,
} from '@ionic/vue';
import { closeOutline } from 'ionicons/icons';
import {
  listUnlimitApplications,
  approveUnlimitApplications,
  denyUnlimitApplications,
  revokeUnlimitApplication,
  type UnlimitApplication,
} from '@/api/api-task';

interface Props {
  isOpen: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
  (e: 'approved'): void;
}>();

const loading = ref(false);
const applications = ref<UnlimitApplication[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const historyLoading = ref(false);
const historyList = ref<UnlimitApplication[]>([]);

// 用户名称映射
const userNames: Record<number, string> = {
  3: '灿灿',
  4: '昭昭',
};

const getUserName = (userId: number): string => {
  return userNames[userId] || `用户${userId}`;
};

const getLockTypeLabel = (lockCode: number): string => {
  if (lockCode === 1) return '任务禁用';
  if (lockCode === 2) return '全局禁用';
  if (lockCode === 3) return '时长超限';
  return `未知(${lockCode})`;
};

const formatTime = (isoStr: string): string => {
  if (!isoStr) return '';
  const d = dayjs(isoStr);
  if (!d.isValid()) return isoStr;
  return d.format('MM-DD HH:mm');
};

const toggleSelect = (id: number) => {
  const next = new Set(selectedIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selectedIds.value = next;
};

const fetchList = async () => {
  loading.value = true;
  try {
    const res = await listUnlimitApplications('pending');
    applications.value = res.applications;
    selectedIds.value = new Set();
  } catch (e: any) {
    console.error('获取审批列表失败:', e);
  } finally {
    loading.value = false;
  }
};

const fetchHistoryList = async () => {
  historyLoading.value = true;
  try {
    const res = await listUnlimitApplications('approved,denied', dayjs().format());
    historyList.value = res.applications;
  } catch (e: any) {
    console.error('获取已处理列表失败:', e);
  } finally {
    historyLoading.value = false;
  }
};

const handleDismiss = () => {
  emit('update:isOpen', false);
};

// 单条通过
const approveOne = async (id: number) => {
  // 查找当前申请记录获取 duration
  const app = applications.value.find((a) => a.id === id);
  const defaultDuration = app?.duration ?? 60;

  const alert = await alertController.create({
    header: '审批通过',
    message: '请输入认证分钟数：',
    inputs: [
      {
        name: 'duration',
        type: 'number',
        value: String(defaultDuration),
        placeholder: '认证分钟数',
      },
    ],
    buttons: [
      { text: '取消', role: 'cancel' },
      {
        text: '确定',
        handler: (data) => {
          const num = Number(data.duration);
          if (!Number.isInteger(num) || num <= 0) {
            return false;
          }
          doApprove([id], num);
          return true;
        },
      },
    ],
  });
  await alert.present();
};

// 单条拒绝
const denyOne = async (id: number) => {
  await doDeny([id]);
};

// 失效
const handleRevoke = async (id: number) => {
  try {
    await revokeUnlimitApplication(id);
    await Promise.all([fetchList(), fetchHistoryList()]);
  } catch (e: any) {
    const alert = await alertController.create({
      header: '操作失败',
      message: e?.message || '请稍后重试',
      buttons: ['确定'],
    });
    await alert.present();
  }
};

// 批量通过
const batchApprove = async () => {
  if (selectedIds.value.size === 0) return;
  await doApprove(Array.from(selectedIds.value));
};

// 批量拒绝
const batchDeny = async () => {
  if (selectedIds.value.size === 0) return;
  await doDeny(Array.from(selectedIds.value));
};

const doApprove = async (ids: number[], duration?: number) => {
  try {
    await approveUnlimitApplications(ids, duration);
    emit('approved');
    await Promise.all([fetchList(), fetchHistoryList()]);
  } catch (e: any) {
    const alert = await alertController.create({
      header: '审批失败',
      message: e?.message || '请稍后重试',
      buttons: ['确定'],
    });
    await alert.present();
  }
};

const doDeny = async (ids: number[]) => {
  try {
    await denyUnlimitApplications(ids);
    await Promise.all([fetchList(), fetchHistoryList()]);
  } catch (e: any) {
    const alert = await alertController.create({
      header: '操作失败',
      message: e?.message || '请稍后重试',
      buttons: ['确定'],
    });
    await alert.present();
  }
};

// 打开时自动拉取
watch(() => props.isOpen, (val) => {
  if (val) {
    fetchList();
    fetchHistoryList();
  }
});
</script>
