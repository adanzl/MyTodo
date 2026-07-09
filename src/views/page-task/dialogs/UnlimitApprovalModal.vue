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

    <ion-content>
      <div v-if="loading" class="flex justify-center items-center py-10">
        <ion-spinner name="crescent"></ion-spinner>
      </div>

      <div v-else-if="applications.length === 0" class="text-center py-10 text-gray-400 text-sm">
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
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
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

// 用户名称映射
const userNames: Record<number, string> = {
  3: '灿灿',
  4: '昭昭',
};

const getUserName = (userId: number): string => {
  return userNames[userId] || `用户${userId}`;
};

const formatTime = (isoStr: string): string => {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  } catch {
    return isoStr;
  }
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

const handleDismiss = () => {
  emit('update:isOpen', false);
};

// 单条通过
const approveOne = async (id: number) => {
  await doApprove([id]);
};

// 单条拒绝
const denyOne = async (id: number) => {
  await doDeny([id]);
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

const doApprove = async (ids: number[]) => {
  try {
    await approveUnlimitApplications(ids);
    emit('approved');
    await fetchList();
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
    await fetchList();
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
  }
});
</script>
