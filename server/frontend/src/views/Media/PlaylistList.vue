<template>
  <div class="w-64 border rounded p-3 flex flex-col">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-base font-semibold">播放列表</h3>
      <div class="flex items-center gap-1">
        <el-button
          type="info"
          size="small"
          plain
          @click="$emit('open-device-list')"
          title="设备列表"
          class="!w-8 !h-6 !p-0"
        >
          <el-icon><Monitor /></el-icon>
        </el-button>
        <el-button
          type="primary"
          size="small"
          plain
          @click="$emit('refresh')"
          :loading="refreshing"
          title="刷新播放列表"
          class="!w-8 !h-6 !p-0"
        >
          <el-icon v-if="!refreshing"><Refresh /></el-icon>
        </el-button>
        <el-button
          type="success"
          size="small"
          @click="$emit('create')"
          title="新建播放列表"
          class="!w-8 !h-6 !p-0"
        >
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
    </div>
    <div
      v-if="playlistCollection && playlistCollection.length > 0"
      class="flex-1 overflow-y-auto space-y-2 pr-1"
    >
      <div
        v-for="playlist in playlistCollection"
        :key="playlist.id"
        class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
        :class="{ 'border-blue-500 bg-blue-50': playlist.id === activePlaylistId }"
        @click="$emit('select', playlist.id)"
      >
        <!-- 第一行：名称、曲目数量、功能按钮 -->
        <div class="flex items-center justify-between gap-2">
          <div class="text-sm font-medium truncate flex-1 min-w-0">{{ playlist.name }}</div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-xs text-gray-500 whitespace-nowrap flex items-center gap-1">
              <el-icon><Headset class="!w-3 !h-3" /></el-icon>
              <span class="whitespace-nowrap w-5 flex items-center justify-center">
                {{
                  ((playlist.pre_lists &&
                    playlist.pre_lists[getWeekdayIndex()] &&
                    playlist.pre_lists[getWeekdayIndex()].length) ||
                    0) + ((playlist.playlist && playlist.playlist.length) || 0)
                }}
              </span>
            </span>
            <div class="flex items-center justify-center">
              <el-dropdown
                trigger="click"
                @command="(command: string) => $emit('menu-command', command, playlist.id)"
                @click.stop
              >
                <el-button
                  type="default"
                  size="small"
                  plain
                  circle
                  class="!w-5 !h-5 !min-w-5 !p-0 text-xs"
                  title="更多"
                >
                  <span class="text-base leading-none mb-1">»</span>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="copy">
                      <span>复制</span>
                    </el-dropdown-item>
                    <el-dropdown-item v-if="playlistCollection.length > 1" command="delete" divided>
                      <span class="text-[#f56c6c]">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
        <!-- 第二行：下次运行时间（始终存在，保持固定高度） -->
        <div class="text-[10px] text-blue-600 min-h-[14px] flex items-center justify-between">
          <span v-if="getPlaylistNextCronTime(playlist)" class="flex items-center gap-1">
            <el-icon class="!w-3 !h-4"><VideoPlay /></el-icon>
            {{ getPlaylistNextCronTime(playlist) }}
          </span>
          <span v-else class="invisible">占位</span>
          <span v-if="playlist.trigger_button" class="text-gray-500 flex items-center gap-1">
            <el-icon class="!w-3 !h-4"><Cpu /></el-icon> {{ playlist.trigger_button }}
          </span>
        </div>
      </div>
    </div>
    <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
      暂无播放列表，请点击"新建"创建
    </div>
  </div>
</template>

<script setup lang="ts">
import { Monitor, Refresh, Plus, Headset, VideoPlay, Cpu } from "@element-plus/icons-vue";
import { getWeekdayIndex } from "@/utils/date";
import { calculateNextCronTimes } from "@/utils/cron";
import { formatDateTimeWithWeekday } from "@/utils/date";
import type { Playlist } from "@/types/playlist";

interface Props {
  playlistCollection: Playlist[];
  activePlaylistId: string;
  refreshing: boolean;
}

defineProps<Props>();

defineEmits<{
  select: [playlistId: string];
  create: [];
  refresh: [];
  "open-device-list": [];
  "menu-command": [command: string, playlistId: string];
}>();

const getPlaylistNextCronTime = (playlist: Playlist) => {
  if (
    !playlist ||
    !playlist.schedule ||
    playlist.schedule.enabled !== 1 ||
    !playlist.schedule.cron ||
    typeof playlist.schedule.cron !== "string"
  ) {
    return null;
  }
  try {
    const cronExpr = String(playlist.schedule.cron).trim();
    if (!cronExpr) {
      return null;
    }
    const times = calculateNextCronTimes(cronExpr, 1);
    if (times && times.length > 0) {
      return formatDateTimeWithWeekday(times[0]);
    }
    return null;
  } catch (error) {
    return null;
  }
};
</script>
