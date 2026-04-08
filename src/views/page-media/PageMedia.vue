<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>
            <div class="px-2">媒体播放列表</div>
        </ion-title>
        <ion-buttons slot="end">
          <ion-button @click="refreshPlaylists" :disabled="loading">
            <ion-icon :icon="refreshOutline" slot="icon-only" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      <div v-if="loading" class="flex justify-center items-center h-full">
        <ion-spinner name="crescent" />
      </div>

      <div v-else-if="playlists.length === 0" class="flex flex-col justify-center items-center h-full text-gray-400">
        <ion-icon :icon="musicalNotesOutline" class="text-6xl mb-4" />
        <p>暂无播放列表</p>
      </div>

      <div v-else class="space-y-3">
        <ion-card 
          v-for="playlist in playlists" 
          :key="playlist.id"
          class="hover:bg-gray-50 transition-colors cursor-pointer"
          @click="showPlaylistDetail(playlist)">
          <ion-card-content>
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <h2 class="text-lg font-semibold truncate">{{ playlist.name }}</h2>
                <div class="flex items-center gap-2 mt-2 text-[12px]!">
                    <p class=" text-gray-500 flex items-center w-12">
                      <ion-icon :icon="headsetOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                      {{ playlist.total}} 
                    </p>
                    <p class=" text-blue-600 flex items-center w-32">
                      <ion-icon :icon="playOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                       {{ getPlaylistNextCronTime(playlist) }}
                    </p>
                    <p class=" text-blue-600 flex items-center">
                      <ion-icon :icon="timeOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                       {{ playlist.schedule.duration }}
                    </p>
                </div>
              </div>
              <div class="flex items-center gap-2 ml-2">
                  <ion-button @click="playPlaylistItem(playlist)" :disabled="!isAdmin">
                   <ion-icon :icon="playlist.isPlaying ? pauseOutline : playOutline" class="inline-block w-5 h-5" />
                  </ion-button>
              </div>
            </div>
          </ion-card-content>
        </ion-card>
      </div>
    </ion-content>

    <!-- 播放列表详情对话框 -->
    <PlaylistDetail :playlist="selectedPlaylist" @close="closeDetailModal" />
  </ion-page>
</template>

<script setup lang="ts">
import { ref, onMounted, inject, computed } from 'vue';
import {
    IonPage,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonButton,
    IonContent,
    IonCard,
    IonCardContent,
    IonIcon,
    IonSpinner,
} from '@ionic/vue';
import {
    refreshOutline,
    musicalNotesOutline,
    headsetOutline,
    timeOutline,
    playOutline,
    pauseOutline,
} from 'ionicons/icons';
import { getPlaylists, playPlaylist, pausePlaylist, type Playlist } from '@/api/api-playlist';
import { getNextCronTime } from '@/utils/cron-util';
import PlaylistDetail from './dialogs/PlaylistDetail.vue';
import EventBus, { C_EVENT } from '@/types/event-bus';

const globalVar: any = inject('globalVar');
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const playlists = ref<Playlist[]>([]);
const selectedPlaylist = ref<Playlist | null>(null);
const loading = ref(false);

// 加载播放列表
const loadPlaylists = async () => {
    loading.value = true;
    try {
        const response = await getPlaylists();
        if (response.code === 0 && response.data) {
            // 服务器返回的是对象，key是id，value是playlist数据
            const playlistObj = response.data as unknown as Record<string, Playlist>;
            playlists.value = Object.values(playlistObj).map(playlist => ({
                ...playlist,
                // 对前置列表排序
                pre_lists: playlist.pre_lists?.map(preList => 
                    preList ? [...preList].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) : []
                ),
                // 对主列表排序
                playlist: playlist.playlist ? [...playlist.playlist].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) : []
            }));
        }
    } catch (error) {
        console.error('加载播放列表失败:', error);
    } finally {
        loading.value = false;
    }
};

// 刷新播放列表
const refreshPlaylists = async () => {
    await loadPlaylists();
};

// 获取下次播放时间
const getPlaylistNextCronTime = (playlist: Playlist): string | null => {
    if (!playlist.schedule?.enabled || !playlist.schedule?.cron) {
        return null;
    }

    return getNextCronTime(playlist.schedule.cron);
};

// 显示播放列表详情
const showPlaylistDetail = (playlist: Playlist) => {
    selectedPlaylist.value = playlist;
};

// 关闭详情对话框
const closeDetailModal = () => {
    selectedPlaylist.value = null;
};

// 播放播放列表
const playPlaylistItem = async (playlist: Playlist) => {
    try {
        const response = playlist.isPlaying 
            ? await pausePlaylist(playlist.id)
            : await playPlaylist(playlist.id);
        if (response.code === 0) {
            EventBus.$emit(C_EVENT.TOAST, playlist.isPlaying ? '已暂停' : '开始播放');
            // 刷新列表以更新状态
            await loadPlaylists();
        } else {
            EventBus.$emit(C_EVENT.TOAST, response.msg || '操作失败');
        }
    } catch (error) {
        console.error('操作失败:', error);
        EventBus.$emit(C_EVENT.TOAST, '操作失败');
    }
};

onMounted(() => {
    loadPlaylists();
});
</script>

<style scoped></style>
