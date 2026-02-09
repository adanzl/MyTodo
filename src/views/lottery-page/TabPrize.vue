<template>
  <ion-segment-content id="tabPrize">
    <ion-item>
      <ion-select label="类别" placeholder="选择类别" justify="start" :model-value="selectedCate" @ionChange="onCateChange">
        <ion-select-option :value="cate" v-for="cate in lotteryCatList" :key="cate.id">
          {{ cate.name }}
        </ion-select-option>
      </ion-select>
      <ion-button class="ml-2" size="small" @click="isManageOpen = true">管理</ion-button>
      <div class="flex w-1/3 items-center justify-center">
        <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
        <div class="text-left pl-1 font-bold w-12">{{ userScore }}</div>
      </div>
    </ion-item>
    <ion-content :scrollY="true" class="h-[calc(100%-56px)]">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-item v-for="item in giftList.data" :key="item.id" button @click="openGiftDetail(item)">
        <ion-thumbnail slot="start">
          <img :src="getGiftImgUrl(item)" alt="" />
        </ion-thumbnail>
        <div class="w-full m-2">
          <ion-label>
            <h2 class="flex">
              <div class="w-8">[{{ item.id }}]</div>
              {{ item.name }}
            </h2>
          </ion-label>
          <div class="flex items-center">
            <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
            <div class="text-left pl-1 pt-1 font-bold w-12">{{ item.cost }}</div>
            <p class="text-sm ml-2 pt-1">{{ getCateName(item.cate_id) }}</p>
          </div>
        </div>
        <div class="flex gap-2" @click.stop>
        <ion-button class="w-14 h-10" @click="$emit('exchange', item)" :disabled="userScore < item.cost">
          兑
        </ion-button>
        <ion-button class="w-14 h-10" color="warning" @click="$emit('add-wish', item)"
          :disabled="wishList.ids.includes(item.id)">
          愿
        </ion-button>
        </div>
      </ion-item>
    </ion-content>

    <FabButton v-if="isAdmin" @click="openNewGift" class="right-[5%] bottom-[1%]" bottom="1%" right="5%" :hasBar="true">
      <Icon icon="mdi:plus" class="w-8 h-8" />
    </FabButton>

    <!-- 新建/详情奖品弹窗（复用） -->
    <ion-modal :is-open="isGiftModalOpen" @willDismiss="closeGiftModal">
      <ion-header>
        <ion-toolbar>
          <ion-title>{{ editingGift ? "奖品详情" : "新建奖品" }}</ion-title>
          <ion-buttons slot="start">
            <ion-button @click="closeGiftModal">
              <ion-icon :icon="closeOutline" />
            </ion-button>
          </ion-buttons>
          <ion-buttons slot="end" v-if="editingGift && isAdmin">
            <ion-button color="danger" fill="clear" class="mr-3" @click="onDeleteGiftInModal">删除</ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content>
        <div class="p-4 space-y-4">
          <ion-item lines="full">
            <ion-label position="stacked">名称</ion-label>
            <ion-input :model-value="newGift.name" placeholder="请输入奖品名称"
              @ionInput="newGift.name = $event.detail.value" :readonly="!!editingGift && !isAdmin" />
          </ion-item>
          <div class="flex gap-2 w-full">
            <ion-item lines="full" class="flex-1">
              <ion-label position="stacked">类别</ion-label>
              <ion-select interface="popover" placeholder="选择类别" :model-value="newGift.cate_id"
                @ionChange="newGift.cate_id = $event.detail.value" :disabled="!!editingGift && !isAdmin">
                <ion-select-option v-for="cate in lotteryCatList.filter((c: any) => c.id !== 0)" :key="cate.id"
                  :value="cate.id">
                  {{ cate.name }}
                </ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item lines="full" class="flex-1">
              <ion-label position="stacked">积分</ion-label>
              <ion-input type="number" :model-value="newGift.cost" placeholder="消耗积分"
                @ionInput="newGift.cost = +$event.detail.value" :readonly="!!editingGift && !isAdmin" />
            </ion-item>
          </div>
          <ion-item lines="full">
            <ion-label position="stacked">图片</ion-label>
            <input type="file" accept="image/*" @change="onNewGiftImageChange" class="mt-1"
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
            <ion-button v-if="!editingGift" fill="outline" class="w-20" @click="closeGiftModal">取消</ion-button>
            <ion-button v-if="!editingGift" color="primary" class="flex-1" @click="saveGift">确定</ion-button>
            <template v-else>
              <ion-button v-if="isAdmin" fill="outline" class="w-20" @click="closeGiftModal">取消</ion-button>
              <ion-button v-if="isAdmin" color="primary" class="flex-1" @click="saveGift">更新</ion-button>
              <ion-button v-else class="flex-1" @click="closeGiftModal">关闭</ion-button>
            </template>
          </div>
        </ion-toolbar>
      </ion-footer>
    </ion-modal>

    <ion-modal :is-open="isManageOpen"
      class="[--width:100%] [--height:100%] [--max-width:100%] [--max-height:100%] [--border-radius:0]"
      @willDismiss="onManageDismiss">
      <ion-header>
        <ion-toolbar>
          <ion-title>类别管理</ion-title>
          <ion-buttons slot="start">
            <ion-button @click="closeManage">
              <ion-icon :icon="closeOutline" />
            </ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content>
        <div class="p-4">
          <ion-button size="small" fill="outline" @click="addCate">添加类别</ion-button>
          <ion-list lines="full" class="mt-2 w-full">
            <ion-item v-for="(cate, idx) in manageCatList" :key="cate.id ?? 'new-' + idx" mode="ios">
              <div class="flex flex-col items-stretch w-full ">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-sm text-gray-500 w-12">ID: {{ cate.id ?? -1 }}</span>
                  <ion-input :model-value="cate.name" @ionInput="cate.name = $event.detail.value" placeholder="类别名称"
                    class="flex-1 min-w-0 flex-1 " fill="outline" />
                </div>
                <div class="flex flex-wrap items-center gap-2 w-full">
                  <span class="text-sm text-gray-500 w-12">积分:</span>
                  <ion-input type="number" :model-value="cate.cost" @ionInput="cate.cost = +$event.detail.value"
                    placeholder="消耗积分" class="w-24! " fill="outline" />
                  <div class="ml-auto flex gap-2">
                    <ion-button size="small" color="primary" @click="saveCate(cate, idx)">更新</ion-button>
                    <ion-button v-if="cate.id === -1 || cate.id == null" size="small" fill="outline"
                      @click="cancelAddCate(idx)">
                      取消
                    </ion-button>
                    <ion-button v-if="cate.id !== -1 && cate.id != null" size="small" color="danger" fill="outline"
                      @click="deleteCate(cate)">
                      删除
                    </ion-button>
                  </div>
                </div>
              </div>
            </ion-item>
          </ion-list>
        </div>
      </ion-content>
    </ion-modal>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonButtons,
  IonHeader,
  IonInput,
  IonList,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonThumbnail,
  IonTitle,
  IonToolbar,
  loadingController,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { setData, delData } from "@/api/data";
import { uploadPic, getPicDisplayUrl } from "@/api/pic";
import { PicDisplaySize, resizeImageToFile } from "@/utils/ImgMgr";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import _ from "lodash";
import { computed, inject, ref, watch } from "vue";
import { closeOutline } from "ionicons/icons";

const props = defineProps<{
  lotteryCatList: any[];
  selectedCate: any;
  giftList: { data: any[] };
  wishList: { ids: number[] };
  userScore: number;
}>();

const emit = defineEmits<{
  (e: "refresh", event: any): void;
  (e: "cate-change", value: any): void;
  (e: "exchange", item: any): void;
  (e: "add-wish", item: any): void;
  (e: "delete", item: any): void;
}>();

const globalVar: any = inject("globalVar");
const isManageOpen = ref(false);
const manageCatList = ref<Array<{ id?: number; name?: string; cost?: number }>>([]);
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const isGiftModalOpen = ref(false);
const editingGift = ref<any>(null);
const newGift = ref<{ name: string; cost: number; cate_id?: number; image?: string }>({
  name: "",
  cost: 0,
  image: "",
});
const newGiftPreview = ref<string>("");
const newGiftFile = ref<File | null>(null);

watch(
  () => [isManageOpen.value, props.lotteryCatList],
  () => {
    if (isManageOpen.value) {
      const list = props.lotteryCatList.filter((c: any) => c.id !== 0);
      manageCatList.value = list.map((c: any) => ({
        id: c.id,
        name: c.name,
        cost: c.cost ?? 0,
      }));
    }
  },
  { immediate: true }
);

function closeManage() {
  isManageOpen.value = false;
}
function onManageDismiss(event: any) {
  isManageOpen.value = false;
  if (event.detail?.role) return;
}

function addCate() {
  manageCatList.value.push({ id: -1, name: "", cost: 0 });
}
function cancelAddCate(idx: number) {
  manageCatList.value.splice(idx, 1);
}
async function saveCate(cate: any, _idx: number) {
  if (!cate.name?.trim()) {
    EventBus.$emit(C_EVENT.TOAST, "请输入类别名称");
    return;
  }
  try {
    await setData("t_gift_category", {
      id: cate.id === -1 ? undefined : cate.id,
      name: cate.name.trim(),
      cost: Number(cate.cost) || 0,
    });
    EventBus.$emit(C_EVENT.TOAST, "更新成功");
    emit("refresh", { target: { complete: () => { } } });
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

function openNewGift() {
  editingGift.value = null;
  newGift.value = {
    name: "",
    cost: 0,
    cate_id:
      props.selectedCate && props.selectedCate.id !== 0 ? props.selectedCate.id : undefined,
    image: "",
  };
  isGiftModalOpen.value = true;
  newGiftPreview.value = "";
  newGiftFile.value = null;
}
function openGiftDetail(item: any) {
  editingGift.value = item;
  newGift.value = {
    name: item.name ?? "",
    cost: item.cost ?? 0,
    cate_id: item.cate_id,
    image: item.img ?? item.image ?? "",
  };
  newGiftPreview.value = newGift.value.image
    ? getPicDisplayUrl(newGift.value.image)
    : "";
  newGiftFile.value = null;
  isGiftModalOpen.value = true;
}
function closeGiftModal() {
  isGiftModalOpen.value = false;
  editingGift.value = null;
}
function onDeleteGiftInModal() {
  if (editingGift.value) {
    emit("delete", editingGift.value);
    closeGiftModal();
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
    // 1. 若有选图：先限定尺寸（与 TTS 拍照一致）再上传
    let imageName = newGift.value.image;
    if (newGiftFile.value) {
      const resized = await resizeImageToFile(newGiftFile.value);
      const resp = await uploadPic(resized);
      imageName = resp.filename;
    }

    const isUpdate = !!editingGift.value;
    await setData("t_gift", {
      id: isUpdate ? editingGift.value.id : undefined,
      name: newGift.value.name.trim(),
      cate_id:
        newGift.value.cate_id ??
        (props.selectedCate && props.selectedCate.id !== 0 ? props.selectedCate.id : undefined),
      cost: Number(newGift.value.cost) || 0,
      enable: 1,
      image: imageName,
    });
    EventBus.$emit(C_EVENT.TOAST, isUpdate ? "更新成功" : "添加奖品成功");
    isGiftModalOpen.value = false;
    newGiftFile.value = null;
    newGiftPreview.value = "";
    emit("refresh", { target: { complete: () => { } } });
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

  // 预览：使用本地文件 blob URL，不上传
  newGiftPreview.value = URL.createObjectURL(file);
  newGiftFile.value = file;

  // 清空 input，方便重复选择同一文件
  target.value = "";
}
async function deleteCate(cate: any) {
  if (cate.id === -1 || cate.id == null) return;
  const { alertController } = await import("@ionic/vue");
  const alert = await alertController.create({
    header: "确认删除",
    message: `确定删除类别「${cate.name}」吗？`,
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async () => {
          try {
            await delData("t_gift_category", cate.id);
            EventBus.$emit(C_EVENT.TOAST, "删除成功");
            _.remove(manageCatList.value, (x) => x.id === cate.id);
            emit("refresh", { target: { complete: () => { } } });
          } catch (err) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}

function onRefresh(event: any) {
  emit("refresh", event);
}
function onCateChange(event: any) {
  emit("cate-change", event.detail.value);
}

function getCateName(cateId: number) {
  const cate = _.find(props.lotteryCatList, { id: cateId });
  return cate ? cate.name : "";
}

/** 兼容 img/image 字段，转为可展示的图片 URL */
function getGiftImgUrl(item: { img?: string; image?: string }) {
  const raw = item.img ?? item.image;
  if (!raw) return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Crect fill='%23e5e7eb' width='96' height='96'/%3E%3C/svg%3E";
  return getPicDisplayUrl(raw, PicDisplaySize.LIST, PicDisplaySize.LIST);
}
</script>
