<script setup lang="ts">
import { IonButton, IonIcon, IonRange } from "@ionic/vue";
import { playOutline, stopOutline } from "ionicons/icons";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { isUCOrQuarkBrowser } from "@/utils/browser-util";

const props = withDefaults(
  defineProps<{
    src: string | string[];
    /** 预知的时长（秒），用于在未加载时显示 */
    durationSeconds?: number | null;
    widthClass?: string;
    /** 是否显示播放按钮 */
    showPlayButton?: boolean;
    /** 是否显示播放进度条 */
    showProgress?: boolean;
    /** 是否显示时间标签 */
    showTimeLabel?: boolean;
    /** 是否循环播放 */
    loop?: boolean;
  }>(),
  { durationSeconds: null, widthClass: "w-full", showPlayButton: true, showProgress: true, showTimeLabel: true, loop: false }
);

const audioRef = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(props.durationSeconds ?? 0);
const progress = ref(0);
const currentAudioIndex = ref(0);
const isSeeking = ref(false);

const isLegacyAudioWebView = isUCOrQuarkBrowser();
const timeupdateMinIntervalMs = isLegacyAudioWebView ? 400 : 200;

/** 避免 :ref 回调每次渲染重复 addEventListener（多个 ended 会把索引误判进 else 分支） */
let audioBindAbort: AbortController | null = null;
let boundAudioEl: HTMLAudioElement | null = null;
/** 程序更新进度条时屏蔽 ion-range 误触发的 seek（UC/X5 常见） */
let suppressRangeSeek = false;
let lastTimeupdateAt = 0;

function teardownAudioBindings() {
  audioBindAbort?.abort();
  audioBindAbort = null;
  boundAudioEl = null;
}

const srcList = computed((): string[] => {
  const s = props.src;
  if (s == null || s === "") return [];
  return Array.isArray(s) ? s.filter(Boolean) : [s];
});

// 获取当前播放的音频 URL
const currentSrc = computed(() => srcList.value[currentAudioIndex.value] ?? "");

function formatSeconds(s: number): string {
  if (!s || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

const formattedCurrent = computed(() => formatSeconds(currentTime.value));
const formattedDuration = computed(() => formatSeconds(duration.value));

const hasAudioSource = computed(() => {
  const s = props.src;
  if (s == null || s === "") return false;
  return Array.isArray(s) ? s.length > 0 : true;
});

function togglePlay() {
  if (!hasAudioSource.value) return;
  const audio = audioRef.value;
  if (!audio) return;
  if (isPlaying.value) {
    audio.pause();
    audio.currentTime = 0;
    return;
  }
  audio.play().catch((e) => console.warn("Audio play failed", e));
}

function setProgressFromAudio(pct: number, time: number) {
  suppressRangeSeek = true;
  progress.value = pct;
  currentTime.value = time;
  queueMicrotask(() => {
    suppressRangeSeek = false;
  });
}

function onSeek(e: CustomEvent) {
  if (suppressRangeSeek) return;
  const v = (e.detail?.value as number) ?? 0;
  const audio = audioRef.value;
  if (!audio || !(duration.value > 0)) return;
  const target = (v / 100) * duration.value;
  audio.currentTime = target;
  currentTime.value = target;
  progress.value = v;
}

/** X5/UC 会误触发 ended，导致短片段循环重播 */
function isAudioActuallyEnded(el: HTMLAudioElement): boolean {
  const d = el.duration;
  if (!(d > 0) || !isFinite(d)) return true;
  return el.currentTime >= d - 0.35 || el.ended;
}

function playNextInList(el: HTMLAudioElement, nextUrl: string, nextIdx: number) {
  el.pause();
  el.src = nextUrl;
  currentAudioIndex.value = nextIdx;
  isPlaying.value = true;
  currentTime.value = 0;
  setProgressFromAudio(0, 0);

  el.addEventListener(
    "canplay",
    function playWhenReady() {
      el.removeEventListener("canplay", playWhenReady);
      el.play().catch((e) => console.warn("Audio play failed", e));
    },
    { once: true }
  );
}

function bindAudio(el: HTMLAudioElement | null) {
  if (!el) {
    unbindAudio();
    return;
  }
  if (el === boundAudioEl) {
    audioRef.value = el;
    return;
  }

  teardownAudioBindings();
  audioBindAbort = new AbortController();
  const { signal } = audioBindAbort;
  boundAudioEl = el;
  audioRef.value = el;

  el.addEventListener(
    "ended",
    () => {
      if (!isAudioActuallyEnded(el)) return;

      const list = srcList.value;
      if (currentAudioIndex.value < list.length - 1) {
        const nextIdx = currentAudioIndex.value + 1;
        const nextUrl = list[nextIdx];
        if (nextUrl) playNextInList(el, nextUrl, nextIdx);
        return;
      }
      if (props.loop && list.length > 0) {
        playNextInList(el, list[0], 0);
        return;
      }
      isPlaying.value = false;
      currentTime.value = 0;
      setProgressFromAudio(0, 0);
      currentAudioIndex.value = 0;
    },
    { signal }
  );
  el.addEventListener(
    "loadedmetadata",
    () => {
      if (el.duration > 0 && isFinite(el.duration)) {
        duration.value = el.duration;
      }
    },
    { signal }
  );
  el.addEventListener(
    "timeupdate",
    () => {
      if (isSeeking.value) return;
      const now = performance.now();
      if (now - lastTimeupdateAt < timeupdateMinIntervalMs) return;
      lastTimeupdateAt = now;

      const d = duration.value || el.duration;
      if (d > 0) {
        setProgressFromAudio((el.currentTime / d) * 100, el.currentTime);
      } else {
        currentTime.value = el.currentTime;
      }
    },
    { signal }
  );
  el.addEventListener("play", () => {
    isPlaying.value = true;
  }, { signal });
  el.addEventListener("pause", () => {
    isPlaying.value = false;
  }, { signal });
  el.addEventListener("error", () => {
    isPlaying.value = false;
  }, { signal });
}

function unbindAudio() {
  teardownAudioBindings();
  const audio = audioRef.value;
  if (audio) {
    audio.pause();
    audio.src = "";
  }
  audioRef.value = null;
}

watch(
  () => props.src,
  (newSrc) => {
    if (!newSrc || (Array.isArray(newSrc) && newSrc.length === 0)) {
      unbindAudio();
      duration.value = props.durationSeconds ?? 0;
      currentTime.value = 0;
      progress.value = 0;
      isPlaying.value = false;
      currentAudioIndex.value = 0;
      return;
    }
    duration.value = props.durationSeconds ?? 0;
    currentTime.value = 0;
    progress.value = 0;
    currentAudioIndex.value = 0;
  },
  { immediate: true }
);

// 暴露方法给父组件
defineExpose({
  togglePlay,
  isPlaying,
  currentTime,
  duration,
  playIdx: currentAudioIndex,
});

onBeforeUnmount(() => {
  unbindAudio();
});
</script>

<template>
  <div
    class="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 py-0 px-2 h-10"
    :class="widthClass">
    <audio
      v-if="currentSrc"
      :ref="(el) => bindAudio(el as HTMLAudioElement | null)"
      :src="currentSrc"
      preload="metadata"
      playsinline
      webkit-playsinline
      x5-playsinline
      class="hidden" />
    <ion-button
      v-if="showPlayButton"
      fill="clear"
      size="small"
      class="min-w-0! w-5! h-10! m-0! [&::part(native)]:p-0"
      :disabled="!hasAudioSource"
      @click="togglePlay">
      <ion-icon v-if="isPlaying" :icon="stopOutline" />
      <ion-icon v-else :icon="playOutline" />
    </ion-button>
    <ion-range
      v-if="showProgress"
      :value="progress"
      :min="0"
      :max="100"
      :step="1"
      class="flex-1 min-w-0"
      :disabled="!hasAudioSource || !isPlaying"
      @ionKnobMoveStart="isSeeking = true"
      @ionKnobMoveEnd="isSeeking = false"
      @ionInput="onSeek($event)"
      @ionChange="onSeek($event)">
    </ion-range>
    <span v-if="showTimeLabel" class="text-xs text-gray-600 tabular-nums whitespace-nowrap">
      {{ formattedCurrent }} / {{ formattedDuration }}
    </span>
  </div>
</template>
