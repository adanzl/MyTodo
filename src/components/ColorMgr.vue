<template>
  <ion-modal ref="modal" id="colorMgr" aria-hidden="false" class="backdrop">
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <h3>颜色编辑</h3>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="flex items-center p-2 h-16">
        <span class="flex w-8 justify-center items-center">-</span>
        <span
          class="v-dot w-in"
          :style="{
            'background-color': n_color.tag,
          }" />
        <ion-input
          class="ml-4 w-20 text-xs h-8 min-h-0 color-name"
          fill="solid"
          mode="md"
          placeholder="新建颜色"
          :value="n_color.label"
          @ionChange="inputChange($event, n_color, 0)" />
        <button class="ml-2 text-xl" @click="openColorPicker($event, n_color)">
          <ion-icon :icon="colorPaletteOutline" />
        </button>
        <ion-input
          mode="md"
          class="ml-1 w-28 grow h-8 min-h-0"
          fill="outline"
          :value="n_color.tag"
          @ionChange="inputChange($event, n_color, 1)" />
        <button class="w-16 h-full" @click="btnSaveClk($event, n_color)">
          <ion-icon :icon="saveOutline" />
        </button>
      </div>
      <div class="flex items-center p-2 h-16" v-for="(color, idx) in colorOptions" :key="idx">
        <span class="flex w-8 justify-center items-center">{{ color.id }}</span>
        <span
          class="v-dot w-in"
          :style="{
            'background-color': color.tag,
          }" />
        <ion-input
          class="ml-4 w-20 text-xs h-8 min-h-0 color-name"
          fill="solid"
          mode="md"
          :value="color.label"
          @ionChange="inputChange($event, color, 0)" />
        <button class="ml-2 text-xl" @click="openColorPicker($event, color)">
          <ion-icon :icon="colorPaletteOutline" />
        </button>
        <ion-input
          mode="md"
          class="ml-1 w-28 grow h-8 min-h-0"
          fill="outline"
          :value="color.tag"
          @ionChange="inputChange($event, color, 1)" />
        <button class="w-8 h-full" @click="btnSaveClk($event, color)">
          <ion-icon :icon="saveOutline" />
        </button>
        <button class="w-8 h-full" @click="btnRemoveClk($event, color)">
          <ion-icon :icon="removeCircleOutline" />
        </button>
      </div>
    </ion-content>
    <ion-footer class="flex">
      <ion-toolbar>
        <ion-button expand="full" fill="clear" @click="confirm()"> 确定 </ion-button>
      </ion-toolbar>
    </ion-footer>
    <ColorPicker
      :isOpen="bOpenColorPicker"
      :hexColor="curColor.tag"
      @colorChanged="onSetColor"
      @willDismiss="() => (bOpenColorPicker = false)" />
  </ion-modal>
</template>
<style lang="css" scoped>
.color-name {
  --background: rgba(0, 0, 0, 0);
  --padding-start: 5px;
  --padding-end: 5px;
}
</style>
<script lang="ts" setup>
import ColorPicker from "@/components/ColorPicker.vue";
import { LoadColorData } from "@/modal/ColorType";
import { delColor, setColor } from "@/utils/NetUtil";
import { createTriggerController } from "@/utils/Overlay";
import { alertController } from "@ionic/vue";
import { colorPaletteOutline, removeCircleOutline, saveOutline } from "ionicons/icons";
import { forEach } from "lodash-es";
import { inject, onMounted, ref, watch } from "vue";
const props = defineProps({
  trigger: {
    type: String,
    default: "",
  },
});

const triggerController = createTriggerController();
const modal = ref();
const valueRef = ref<any>();
const n_color = ref({ tag: "#000000", label: "" });
const eventBus: any = inject("eventBus");
const colorOptions = ref<any[]>([]);
const bOpenColorPicker = ref(false);
const curColor = ref<any>({});
eventBus.$on("updateColor", (params: any[]) => {
  colorOptions.value = [];
  forEach(params, (v: any) => colorOptions.value.push(v));
});

const emits = defineEmits(["update:value"]);
onMounted(() => {
  watch(
    () => props.trigger,
    (nv) => {
      if (nv) {
        triggerController.addClickListener(modal.value!.$el!, nv);
      }
    },
    { immediate: true } // 立即执行一次 watcher
  );
});

function inputChange(event: any, color: any, type: number) {
  console.log("inputChange", event.detail.value, color.id, type);
  if (type === 0) {
    color.label = event.detail.value;
  } else {
    color.tag = event.detail.value;
  }
}

async function openColorPicker(_event: Event, color: any) {
  curColor.value = color;
  bOpenColorPicker.value = true;
}

async function btnRemoveClk(_event: any, color: any) {
  const alert = await alertController.create({
    header: "Confirm",
    message: "确认删除 [" + color.label + "]",
    buttons: [
      {
        text: "OK",
        handler: () => {
          console.log("btnRemoveClk", color.id);
          delColor(color.id).then(async () => {
            LoadColorData();
          });
        },
      },
      "Cancel",
    ],
  });
  await alert.present();
}

async function btnSaveClk(_event: any, color: any) {
  console.log("btnSaveClk", color);
  setColor(color.id, color.label, color.tag).then(async () => {
    n_color.value = { tag: "#000000", label: "" };
    await LoadColorData();
  });
}

const confirm = () => {
  emits("update:value", valueRef.value);
  modal.value.$el!.dismiss();
};

function onSetColor(color: any) {
  console.log("onSetColor", curColor.value, color);
  curColor.value.tag = color;
}
</script>
