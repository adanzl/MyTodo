<script setup lang="ts">
import { IonButton, IonIcon, IonRange } from "@ionic/vue";
import { playOutline, stopOutline } from "ionicons/icons";
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    src: string;
    /** 预知的时长（秒），用于在未加载时显示 */
    durationSeconds?: number | null;
    widthClass?: string;
  }>(),
  { durationSeconds: null, widthClass: "w-full" }
);

const audioRef = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(props.durationSeconds ?? 0);
const progress = ref(0);

function formatSeconds(s: number): string {
  if (!s || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

const formattedCurrent = computed(() => formatSeconds(currentTime.value));
const formattedDuration = computed(() => formatSeconds(duration.value));

function togglePlay() {
  if (!props.src) return;
  const audio = audioRef.value;
  if (!audio) return;
  if (isPlaying.value) {
    audio.pause();
    audio.currentTime = 0;
    return;
  }
  audio.play().catch((e) => console.warn("Audio play failed", e));
}

function onSeek(e: CustomEvent) {
  const v = (e.detail?.value as number) ?? 0;
  const audio = audioRef.value;
  if (!audio || !(duration.value > 0)) return;
  const target = (v / 100) * duration.value;
  audio.currentTime = target;
  currentTime.value = target;
  progress.value = v;
}

function bindAudio(el: HTMLAudioElement | null) {
  if (!el) {
    unbindAudio();
    return;
  }
  audioRef.value = el;
  el.addEventListener("loadedmetadata", () => {
    if (el.duration > 0 && isFinite(el.duration)) {
      duration.value = el.duration;
    }
  });
  el.addEventListener("timeupdate", () => {
    currentTime.value = el.currentTime;
    const d = duration.value || el.duration;
    if (d > 0) {
      progress.value = (el.currentTime / d) * 100;
    }
  });
  el.addEventListener("play", () => {
    isPlaying.value = true;
  });
  el.addEventListener("pause", () => {
    isPlaying.value = false;
  });
  el.addEventListener("ended", () => {
    isPlaying.value = false;
    currentTime.value = 0;
    progress.value = 0;
  });
  el.addEventListener("error", () => {
    isPlaying.value = false;
  });
}

function unbindAudio() {
  const audio = audioRef.value;
  if (audio) {
    audio.pause();
    audio.src = "";
  }
  audioRef.value = null;
}

watch(
  () => props.src,
  (url) => {
    if (!url) {
      unbindAudio();
      duration.value = props.durationSeconds ?? 0;
      currentTime.value = 0;
      progress.value = 0;
      isPlaying.value = false;
      return;
    }
    duration.value = props.durationSeconds ?? 0;
    currentTime.value = 0;
    progress.value = 0;
  },
  { immediate: true }
);

watch(
  () => props.durationSeconds,
  (v) => {
    if (v != null && v > 0 && duration.value <= 0) {
      duration.value = v;
    }
  }
);

onBeforeUnmount(() => {
  unbindAudio();
});
</script>

<template>
  <div
    class="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 py-0 px-2"
    :class="widthClass">
    <audio
      v-if="src"
      :ref="(el) => bindAudio(el as HTMLAudioElement | null)"
      :src="src"
      preload="metadata"
      class="hidden" />
    <ion-button
      fill="clear"
      size="small"
      class="!min-w-9 !w-10 !h-10 !m-0"
      :disabled="!src"
      @click="togglePlay">
      <ion-icon v-if="isPlaying" :icon="stopOutline" />
      <ion-icon v-else :icon="playOutline" />
    </ion-button>
    <ion-range
      :value="progress"
      :min="0"
      :max="100"
      :step="1"
      class="flex-1 min-w-0"
      :disabled="!src || !isPlaying"
      @ionInput="onSeek($event)"
      @ionChange="onSeek($event)">
    </ion-range>
    <span class="text-xs text-gray-600 shrink-0 min-w-[4rem] tabular-nums">
      {{ formattedCurrent }} / {{ formattedDuration }}
    </span>
  </div>
</template>
