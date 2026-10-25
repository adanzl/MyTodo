<template>
  <ion-page class="main-bg">
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <div class="px-2">媒体</div>
        </ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-segment :value="segmentValue" @ionChange="handleSegmentChange">
      <ion-segment-button
        value="playlist"
        content-id="tabPlaylist"
        layout="icon-start"
        class="text-blue-500 [&::part(native)]:px-0">
        <ion-icon :icon="musicalNotesOutline" class="w-4 h-4" />
        <ion-label class="ml-1">播放列表</ion-label>
      </ion-segment-button>
      <ion-segment-button
        value="mi"
        content-id="tabMiDevices"
        layout="icon-start"
        :disabled="!isAdmin"
        class="text-blue-500 [&::part(native)]:px-0">
        <ion-icon :icon="radioOutline" class="w-4 h-4" />
        <ion-label class="ml-1">小米设备</ion-label>
      </ion-segment-button>
    </ion-segment>

    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <TabPlaylist />
      <TabMiDevices :active="segmentValue === 'mi'" :enabled="isAdmin" />
    </ion-segment-view>
  </ion-page>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import { IonSegment, IonSegmentButton, IonSegmentView } from "@ionic/vue";
import { musicalNotesOutline, radioOutline } from "ionicons/icons";
import TabPlaylist from "./TabPlaylist.vue";
import TabMiDevices from "./TabMiDevices.vue";

const globalVar: any = inject("globalVar");
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const segmentValue = ref("playlist");
const tabsHeight = ref(0);

let observer: MutationObserver | null = null;

const updateTabsHeight = () => {
  const tabs = document.querySelector("ion-tab-bar");
  if (tabs) {
    tabsHeight.value = tabs.clientHeight;
  }
};

const handleSegmentChange = (event: CustomEvent) => {
  const value = event.detail.value as string;
  if (value === "mi" && !isAdmin.value) {
    segmentValue.value = "playlist";
    return;
  }
  segmentValue.value = value;
};

onMounted(() => {
  observer = new MutationObserver(() => {
    updateTabsHeight();
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
  updateTabsHeight();
  window.addEventListener("resize", updateTabsHeight);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTabsHeight);
  if (observer) {
    observer.disconnect();
    observer = null;
  }
});
</script>
