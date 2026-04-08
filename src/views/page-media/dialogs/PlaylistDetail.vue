<template>
  <ion-modal ref="modal" aria-hidden="false" id="main" :is-open="!!playlist" @willDismiss="onModalWillDismiss">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button fill="clear" @click="close()">
            <ion-icon :icon="closeOutline" />
          </ion-button>
        </ion-buttons>
        <ion-title>{{ playlist?.name }}</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <div v-if="playlist" class="space-y-4">
        <!-- 前置列表 -->
        <div class="">
          <h4 class="text-base font-semibold mb-2">前置列表</h4>
          <!-- 星期选择器 -->
          <div class="flex gap-1 mb-3 overflow-x-auto">
            <ion-button
              v-for="(name, index) in weekdays"
              :key="index"
              size="small"
              :fill="selectedWeekday === index ? 'solid' : 'outline'"
              @click="selectedWeekday = index"
              class="p-0! text-[11px]! flex-1!"
              >
              {{ name }}
            </ion-button>
          </div>
          <!-- 当前选中的星期列表 -->
          <div v-if="playlist.pre_lists[selectedWeekday] && playlist.pre_lists[selectedWeekday].length > 0" class="space-y-1 pl-2">
            <div
              v-for="(item, idx) in playlist.pre_lists[selectedWeekday]"
              :key="idx"
              :class="[
                'text-sm truncate cursor-pointer p-1 hover:bg-gray-50 rounded flex',
                isCurrentItem(selectedWeekday, idx) ? 'bg-blue-100 text-blue-600 font-semibold' : 'text-gray-700'
              ]"
              @click="showFullPath(item)">
              <div class="flex items-center gap-2">{{ idx + 1 }}.</div> 
              <div class="flex-1 truncate">{{ getFileName(item) }}</div>
              <div class="w-13">{{ formatDuration(item.duration) }}</div>
            </div>
          </div>
          <div v-else class="text-center text-gray-400 py-4">暂无曲目</div>
        </div>

        <!-- 主列表 -->
        <div >
          <h4 class="text-base font-semibold mb-2">播放列表 ({{ playlist.playlist.length }})</h4>
          <div class="space-y-1" v-if="playlist.playlist && playlist.playlist.length > 0">
            <div
              v-for="(item, idx) in playlist.playlist"
              :key="idx"
              :class="[
                'text-sm truncate p-2 hover:bg-gray-50 rounded cursor-pointer flex',
                isCurrentItem(-1, idx) ? 'bg-blue-100 text-blue-600 font-semibold' : 'bg-gray-100 text-gray-700'
              ]"
              @click="showFullPath(item)">
              <div class="flex items-center gap-2">{{ idx + 1 }}.</div> 
              <div class="flex-1 truncate">{{ getFileName(item) }}</div>
              <div class="w-13">{{ formatDuration(item.duration) }}</div>
            </div>
          </div>
          <div v-else class="text-center text-gray-400 py-8">暂无曲目</div>
        </div>

      </div>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { IonModal, IonHeader, IonToolbar, IonTitle, IonButtons, IonButton, IonContent, IonIcon } from '@ionic/vue';
import { closeOutline } from 'ionicons/icons';
import type { Playlist, PlaylistItem } from '@/api/api-playlist';
import EventBus, { C_EVENT } from '@/types/event-bus';

interface Props {
  playlist: Playlist | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
}>();

const modal = ref<any>(null);
const selectedWeekday = ref(new Date().getDay());
const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

// 监听 playlist 变化，重置 selectedWeekday
watch(() => props.playlist, () => {
  selectedWeekday.value = new Date().getDay();
});

const close = () => {
  modal.value?.$el.dismiss();
};

const onModalWillDismiss = () => {
  emit('close');
};

// 获取文件名
const getFileName = (item: PlaylistItem): string => {
  const uri = item.uri || item.name || '未知文件';
  const parts = uri.split('/');
  return parts[parts.length - 1] || uri;
};

// 格式化时长为 HH:MM:SS
const formatDuration = (seconds?: number): string => {
  if (!seconds && seconds !== 0) return '--:--:--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

// 显示完整路径
const showFullPath = (item: PlaylistItem) => {
  const fullPath = item.uri || item.name || '未知文件';
  EventBus.$emit(C_EVENT.TOAST, fullPath);
};

// 判断是否为当前播放项
const isCurrentItem = (weekdayIndex: number, itemIndex: number): boolean => {
  if (!props.playlist?.isPlaying || props.playlist.current_index === undefined) {
    return false;
  }
  
  // 如果正在播放前置列表
  if (props.playlist.in_pre_files) {
    return weekdayIndex !== -1 && itemIndex === props.playlist.current_index;
  }
  // 如果正在播放主列表
  else {
    return weekdayIndex === -1 && itemIndex === props.playlist.current_index;
  }
};
</script>
