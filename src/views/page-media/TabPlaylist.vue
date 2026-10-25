<template>
  <ion-segment-content id="tabPlaylist">
    <ion-content :scroll-y="true" class="ion-padding">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content />
      </ion-refresher>

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
                <div class="flex items-center gap-2 mt-2 text-xs">
                  <p class="text-gray-500 flex items-center w-12">
                    <ion-icon :icon="headsetOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                    {{ playlist.total }}
                  </p>
                  <p class="text-blue-600 flex items-center w-32">
                    <ion-icon :icon="playOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                    {{ getPlaylistNextCronTime(playlist) }}
                  </p>
                  <p class="text-blue-600 flex items-center">
                    <ion-icon :icon="timeOutline" class="inline-block w-3.5 h-3.5 mr-1" />
                    {{ playlist.schedule?.duration }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2 ml-2">
                <ion-button @click.stop="playPlaylistItem(playlist)" :disabled="!isAdmin" fill="outline">
                  <ion-icon :icon="playlist.isPlaying ? pauseOutline : playOutline" class="inline-block w-5 h-5" />
                </ion-button>
              </div>
            </div>
          </ion-card-content>
        </ion-card>
      </div>
    </ion-content>

    <PlaylistDetail :playlist="selectedPlaylist" @close="closeDetailModal" />
  </ion-segment-content>
</template>

<script setup lang="ts">
import { ref, onMounted, inject, computed } from "vue";
import {
  IonCard,
  IonCardContent,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSpinner,
} from "@ionic/vue";
import {
  musicalNotesOutline,
  headsetOutline,
  timeOutline,
  playOutline,
  pauseOutline,
} from "ionicons/icons";
import { getPlaylists, playPlaylist, stopPlaylist, type Playlist } from "@/api/api-playlist";
import { getNextCronTime } from "@/utils/cron-util";
import PlaylistDetail from "./dialogs/PlaylistDetail.vue";
import EventBus, { C_EVENT } from "@/types/event-bus";

const globalVar: any = inject("globalVar");
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const playlists = ref<Playlist[]>([]);
const selectedPlaylist = ref<Playlist | null>(null);
const loading = ref(false);

const loadPlaylists = async (silent = false) => {
  if (!silent) loading.value = true;
  try {
    const response = await getPlaylists();
    if (response.code === 0 && response.data) {
      const playlistObj = response.data as unknown as Record<string, Playlist>;
      playlists.value = Object.values(playlistObj)
        .map((playlist) => ({
          ...playlist,
          pre_lists: playlist.pre_lists?.map((preList) =>
            preList ? [...preList].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) : []
          ),
          playlist: playlist.playlist
            ? [...playlist.playlist].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
            : [],
        }))
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    }
  } catch (error) {
    console.error("加载播放列表失败:", error);
  } finally {
    loading.value = false;
  }
};

const getPlaylistNextCronTime = (playlist: Playlist): string | null => {
  if (!playlist.schedule?.enabled || !playlist.schedule?.cron) {
    return null;
  }
  return getNextCronTime(playlist.schedule.cron);
};

const showPlaylistDetail = (playlist: Playlist) => {
  selectedPlaylist.value = playlist;
};

const closeDetailModal = () => {
  selectedPlaylist.value = null;
};

const playPlaylistItem = async (playlist: Playlist) => {
  try {
    const response = playlist.isPlaying
      ? await stopPlaylist(playlist.id)
      : await playPlaylist(playlist.id);
    if (response.code === 0) {
      EventBus.$emit(C_EVENT.TOAST, playlist.isPlaying ? "已停止" : "开始播放");
      await loadPlaylists(true);
    } else {
      EventBus.$emit(C_EVENT.TOAST, response.msg || "操作失败");
    }
  } catch (error) {
    console.error("操作失败:", error);
    EventBus.$emit(C_EVENT.TOAST, "操作失败");
  }
};

const onRefresh = (event: CustomEvent) => {
  loadPlaylists(true).finally(() => {
    (event.target as HTMLIonRefresherElement).complete();
  });
};

onMounted(() => {
  loadPlaylists();
});
</script>
