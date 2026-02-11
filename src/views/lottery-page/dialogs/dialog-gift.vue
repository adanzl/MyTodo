<template>
  <!-- 新建/详情奖品弹窗（复用） -->
  <ion-modal :is-open="isOpen" @willDismiss="onWillDismiss">
    <ion-header>
      <ion-toolbar>
        <ion-title>{{ editingGift ? "奖品详情" : "新建奖品" }}</ion-title>
        <ion-buttons slot="start">
          <ion-button @click="handleClose">
            <ion-icon :icon="closeOutline" />
          </ion-button>
        </ion-buttons>
        <ion-buttons slot="end" v-if="editingGift && isAdmin">
          <ion-button color="danger" fill="clear" class="mr-5" @click="handleDelete">删除</ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="p-4 space-y-2">
        <ion-item lines="full">
          <ion-label position="stacked">名称</ion-label>
          <div class="flex items-center gap-2 w-full">
            <ion-input
              :model-value="newGift.name"
              placeholder="请输入奖品名称"
              @ionInput="newGift.name = $event.detail.value"
              :readonly="!!editingGift && !isAdmin"
              :clear-input="true"
              class="flex-1 min-w-0" />
            <div class="origin-left shrink-0">
              <ion-checkbox
                :checked="!!newGift.enable"
                @ionChange="newGift.enable = $event.detail.checked ? 1 : 0"
                :disabled="!!editingGift && !isAdmin">
                启用
              </ion-checkbox>
            </div>
          </div>
        </ion-item>
        <div class="flex gap-2 w-full">
          <ion-item lines="full" class="flex-1">
            <ion-label position="stacked">类别</ion-label>
            <ion-select
              interface="popover"
              placeholder="选择类别"
              :model-value="newGift.cate_id"
              @ionChange="newGift.cate_id = $event.detail.value"
              :disabled="!!editingGift && !isAdmin">
              <ion-select-option
                v-for="cate in lotteryCatList.filter((c: any) => c.id !== 0)"
                :key="cate.id"
                :value="cate.id">
                {{ cate.name }}
              </ion-select-option>
            </ion-select>
          </ion-item>
          <ion-item lines="full" class="w-18 shrink-0">
            <ion-label position="stacked">积分</ion-label>
            <ion-input
              type="number"
              :model-value="newGift.cost"
              placeholder="消耗积分"
              @ionInput="newGift.cost = +$event.detail.value"
              :readonly="!!editingGift && !isAdmin" />
          </ion-item>
          <ion-item lines="full" class="w-18 shrink-0">
            <ion-label position="stacked">库存</ion-label>
            <ion-input
              type="number"
              :model-value="newGift.stock"
              placeholder="数量"
              @ionInput="newGift.stock = +$event.detail.value"
              :readonly="!!editingGift && !isAdmin" />
          </ion-item>
          <ion-item lines="full" class="w-18 shrink-0">
            <ion-label position="stacked">兑换</ion-label>
            <div class="flex items-center justify-center pt-1">
              <ion-checkbox
                class="scale-75 origin-center"
                :checked="!!newGift.exchange"
                @ionChange="newGift.exchange = $event.detail.checked ? 1 : 0"
                :disabled="!!editingGift && !isAdmin">
              </ion-checkbox>
            </div>
          </ion-item>
        </div>
        <ion-item lines="full">
          <ion-label position="stacked">图片</ion-label>
          <input
            type="file"
            accept="image/*"
            @change="onNewGiftImageChange"
            class="mt-1"
            v-if="!editingGift || isAdmin" />
        </ion-item>
        <div v-if="newGiftPreview" class="mt-2 flex justify-center">
          <img :src="newGiftPreview" class="w-full h-full object-cover rounded" />
        </div>
      </div>
    </ion-content>
    <ion-footer>
      <ion-toolbar class="ion-padding">
        <div class="flex gap-2 w-full">
          <ion-button v-if="!editingGift" fill="outline" class="w-20" @click="handleClose">取消</ion-button>
          <ion-button v-if="!editingGift" color="primary" class="flex-1" @click="saveGift">确定</ion-button>
          <template v-else>
            <ion-button v-if="isAdmin" fill="outline" class="w-20" @click="handleClose">取消</ion-button>
            <ion-button v-if="isAdmin" color="primary" class="flex-1" @click="saveGift">更新</ion-button>
            <ion-button v-else class="flex-1" @click="handleClose">关闭</ion-button>
          </template>
        </div>
      </ion-toolbar>
    </ion-footer>
  </ion-modal>
</template>

<script setup lang="ts">
import {
  IonButtons,
  IonCheckbox,
  IonContent,
  IonFooter,
  IonHeader,
  IonInput,
  IonItem,
  IonLabel,
  IonModal,
  IonSelect,
  IonSelectOption,
  IonTitle,
  IonToolbar,
  loadingController,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { uploadPic, getPicDisplayUrl } from "@/api/pic";
import { resizeImageToFile } from "@/utils/ImgMgr";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import { ref, watch } from "vue";
import { closeOutline } from "ionicons/icons";
import { setData } from "@/api/data";

const props = defineProps<{
  isOpen: boolean;
  editingGift: any | null;
  lotteryCatList: any[];
  selectedCate: any;
  isAdmin: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "delete", gift: any): void;
  (e: "saved", payload: { isUpdate: boolean }): void;
}>();

const newGift = ref<{
  name: string;
  cost: number;
  cate_id?: number;
  image?: string;
  enable?: number;
  exchange?: number;
  stock?: number;
}>({
  name: "",
  cost: 0,
  image: "",
  enable: 1,
  exchange: 1,
  stock: 1,
});
const newGiftPreview = ref<string>("");
const newGiftFile = ref<File | null>(null);

watch(
  () => [props.isOpen, props.editingGift, props.selectedCate],
  () => {
    if (!props.isOpen) return;

    if (props.editingGift) {
      const item = props.editingGift;
      newGift.value = {
        name: item.name ?? "",
        cost: item.cost ?? 0,
        cate_id: item.cate_id,
        image: item.img ?? item.image ?? "",
        enable: item.enable ?? 1,
        exchange: item.exchange ?? 1,
        stock: item.stock ?? 0,
      };
      newGiftPreview.value = newGift.value.image
        ? getPicDisplayUrl(newGift.value.image)
        : "";
      newGiftFile.value = null;
    } else {
      const rand = Math.floor(10000 + Math.random() * 90000); // 5 位随机数
      newGift.value = {
        name: `gift_${rand}`,
        cost: 0,
        cate_id: props.selectedCate && props.selectedCate.id !== 0 ? props.selectedCate.id : undefined,
        image: "",
        enable: 1,
        exchange: 1,
        stock: 1,
      };
      newGiftPreview.value = "";
      newGiftFile.value = null;
    }
  },
  { immediate: true }
);

function handleClose() {
  emit("close");
}

function onWillDismiss() {
  emit("close");
}

function handleDelete() {
  if (props.editingGift) {
    emit("delete", props.editingGift);
  }
}

async function saveGift() {
  if (!newGift.value.name?.trim()) {
    EventBus.$emit(C_EVENT.TOAST, "请输入奖品名称");
    return;
  }
  const loading = await loadingController.create({ message: "保存中..." });
  await loading.present();
  try {
    let imageName = newGift.value.image;
    if (newGiftFile.value) {
      const resized = await resizeImageToFile(newGiftFile.value);
      const resp = await uploadPic(resized);
      imageName = resp.filename;
    }

    const isUpdate = !!props.editingGift;
    await setData("t_gift", {
      id: isUpdate ? props.editingGift.id : undefined,
      name: newGift.value.name.trim(),
      cate_id:
        newGift.value.cate_id ??
        (props.selectedCate && props.selectedCate.id !== 0 ? props.selectedCate.id : undefined),
      cost: Number(newGift.value.cost) || 0,
      enable: newGift.value.enable ?? 1,
      exchange: newGift.value.exchange ?? 1,
      stock: Number(newGift.value.stock) || 0,
      image: imageName,
    });
    EventBus.$emit(C_EVENT.TOAST, isUpdate ? "更新成功" : "添加奖品成功");
    newGiftFile.value = null;
    newGiftPreview.value = "";
    emit("saved", { isUpdate });
    emit("close");
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    await loading.dismiss();
  }
}

async function onNewGiftImageChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  newGiftPreview.value = URL.createObjectURL(file);
  newGiftFile.value = file;

  target.value = "";
}
</script>

