<template>
  <span v-if="isRemote" class="server-remote-badge">远</span>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { isLocalIpAvailable } from "@/utils/NetUtil";

const isRemote = ref(isLocalIpAvailable() === false);

function onServerSwitch(usingRemote: boolean) {
  isRemote.value = usingRemote;
}

onMounted(() => {
  isRemote.value = isLocalIpAvailable() === false;
  EventBus.$on(C_EVENT.SERVER_SWITCH, onServerSwitch);
});

onBeforeUnmount(() => {
  EventBus.$off(C_EVENT.SERVER_SWITCH, onServerSwitch);
});
</script>

<style scoped>
.server-remote-badge {
  font-size: 12px;
  color: var(--ion-color-medium);
  margin-left: 4px;
  padding: 0 6px;
}
</style>
