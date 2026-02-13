<template>
  <ion-modal ref="modal" aria-hidden="false" id="main" :is-open="isOpen" @didPresent="onModalPresent"
    @willDismiss="onModalWillDismiss">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button fill="clear" @click="cancel()"> <ion-icon :icon="closeOutline" /></ion-button>
        </ion-buttons>
        <ion-title>Lottery Setting</ion-title>
        <ion-buttons slot="end">
          <ion-button @click="btnAvgCostClk">均值</ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <!-- 当前类别礼物列表（点击类别后显示） -->
      <template v-if="selectedCateForGifts">
        <div class="flex items-center gap-2 mt-0 mb-1 h-8 pr-4">
          <ion-button fill="clear" size="small" @click="backToCategoryList">
            <ion-icon :icon="chevronBackOutline" />
          </ion-button>
          <ion-label class="font-bold">{{ selectedCateForGifts.name }} — 奖品列表</ion-label>
          <ion-button class="ml-auto [--padding-bottom:0px]! [--padding-top:0px]!" size="small" fill="outline"
            color="primary" @click="openNewGiftFromSetting">
            <span class="text-[12px]">添加奖品</span>
          </ion-button>
        </div>
        <ion-list v-if="categoryGiftList.length > 0">
          <ion-item v-for="item in categoryGiftList" :key="item.id"
            :class="{ '[&::part(native)]:bg-gray-300': !item.enable }" button lines="full" @click="openGiftEdit(item)">
            <div slot="start" class="w-14 h-14 mr-2">
              <img :src="getGiftImgUrl(item)" alt="" class="w-14 h-14 object-cover rounded" />
            </div>
            <ion-label>
              <h2>[{{ item.id }}] {{ item.name }}</h2>
              <div class="flex items-center text-[12px] gap-1">
                <Icon icon="mdi:star" class="text-red-500 w-3.5 h-3.5 inline " />
                <div class="w-7">{{ item.cost }} </div>
                <ion-icon :icon="serverOutline" class=""></ion-icon>
                <div class="w-6">{{ item.stock ?? 0 }} </div>
                <div class="w-10">愿：{{ item.wish ? "是" : "否" }}</div>
                <div class="w-10">兑: {{ item.exchange ? "是" : "否" }}</div>
                <ion-icon :icon="item.enable ? checkmarkCircleOutline : checkmarkCircleOutline" class=""></ion-icon>
              </div>
            </ion-label>
          </ion-item>
        </ion-list>
        <ion-item v-else>
          <ion-label class="text-gray-500">该类别下暂无奖品</ion-label>
        </ion-item>
      </template>

      <!-- 类别列表：点击后在设置页显示该类别下的礼物 -->
      <template v-else>
        <div class="flex items-center gap-2 mb-1 h-8 p-4">
          <ion-label class="font-bold">奖品类别</ion-label>
          <ion-button class="ml-auto [--padding-bottom:0px]! [--padding-top:0px]!" size="small" fill="outline"
            @click.stop="addCate">
            <span class="text-[12px]">添加类别</span>
          </ion-button>
        </div>
        <ion-list class="mt-4">
          <ion-item v-for="cate in lotteryCatList" :key="cate.id" button detail class="py-2" @click="onCateClick(cate)">
            <ion-label>
              <h2>{{ cate.name }}</h2>
              <p v-if="cate.cost != null">消耗积分: {{ cate.cost }} </p>
            </ion-label>
            <div slot="end" class="flex gap-1" @click.stop>
              <ion-button size="small" fill="outline" @click="editCate(cate)">编辑</ion-button>
              <ion-button v-if="cate.id !== 0" size="small" fill="outline" color="danger" @click="deleteCate(cate)">
                删除
              </ion-button>
            </div>
          </ion-item>
          <ion-item v-if="lotteryCatList.length === 0">
            <ion-label class="text-gray-500">暂无类别，请先在商店页中添加</ion-label>
          </ion-item>
        </ion-list>
      </template>
    </ion-content>

    <DialogGift :is-open="isGiftDialogOpen" :editing-gift="editingGift" :lottery-cat-list="lotteryCatList"
      :selected-cate="selectedCateForGifts" :is-admin="isAdmin" @close="closeGiftDialog" @delete="onGiftDelete"
      @saved="onGiftSaved" />
  </ion-modal>
</template>

<script lang="ts" setup>
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getLotteryData, setLotteryData, getGiftAvgCost } from "@/api/lottery";
import { getPicDisplayUrl } from "@/api/pic";
import { getList, setData, delData } from "@/api/data";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import { PicDisplaySize } from "@/utils/ImgMgr";
import { computed, inject, ref } from "vue";
import { alertController, loadingController } from "@ionic/vue";
import { closeOutline, chevronBackOutline, serverOutline, checkmarkCircleOutline } from "ionicons/icons";
import { Icon } from "@iconify/vue";
import DialogGift from "./dialog-gift.vue";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: "willDismiss", event: any): void;
}>();

const globalVar: any = inject("globalVar");
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const modal = ref();
const lotteryData = ref<{ fee: number; giftList: any[] }>({
  fee: 10,
  giftList: [],
});
const lotteryCatList = ref<any[]>([]);
const bModify = ref(false);
/** 当前选中的类别（用于在设置页内显示该类别下的礼物） */
const selectedCateForGifts = ref<any>(null);
const categoryGiftList = ref<any[]>([]);
/** 礼物编辑弹窗 */
const isGiftDialogOpen = ref(false);
const editingGift = ref<any>(null);

async function btnAvgCostClk() {
  try {
    const data = await getGiftAvgCost();
    const lines = [
      `平均成本：${Number(data.avg_cost).toFixed(2)}`,
      `参与统计：${data.total_count} 件`,
      ...(data.by_category?.length
        ? [
          "",
          "按类别：",
          ...data.by_category.map((c) => {
            const rawName = (c.cate_name ?? "").trim() || "未命名";
            const maxLen = 10;
            const shortName =
              rawName.length > maxLen
                ? `${rawName.slice(0, maxLen)}…`
                : rawName;
            const label = `[${c.cate_id ?? "无"}] ${shortName}`;
            return `   ${label}： ${Number(c.avg_cost).toFixed(
              2
            )}（${c.count} 件）`;
          }),
        ]
        : []),
    ];
    const message = lines.join("\n");
    const alert = await alertController.create({
      header: "礼物均值",
      message,
      cssClass: "alert-message-preline",
      buttons: ["确定"],
    });
    await alert.present();
  } catch (err: any) {
    const alert = await alertController.create({
      header: "请求失败",
      message: getNetworkErrorMessage(err),
      buttons: ["确定"],
    });
    await alert.present();
  }
}

const cancel = async () => {
  if (bModify.value) {
    const alert = await alertController.create({
      header: "Confirm",
      message: "确认放弃修改",
      buttons: [
        {
          text: "OK",
          handler: () => {
            modal.value.$el!.dismiss({}, "cancel");
          },
        },
        "Cancel",
      ],
    });
    await alert.present();
  } else {
    modal.value.$el!.dismiss({}, "cancel");
  }
};

async function onModalPresent() {
  bModify.value = false;
  selectedCateForGifts.value = null;
  categoryGiftList.value = [];
  isGiftDialogOpen.value = false;
  editingGift.value = null;
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  Promise.all([
    getLotteryData()
      .then((data: any) => {
        if (data) {
          const parsed = JSON.parse(data);
          lotteryData.value = {
            fee: parsed.fee ?? 10,
            giftList: parsed.giftList ?? [],
          };
        }
      })
      .catch((err) => {
        EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
      }),
    getList("t_gift_category")
      .then((data: any) => {
        lotteryCatList.value = data?.data ?? [];
      })
      .catch((err: any) => {
        EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
      }),
  ]).finally(() => {
    // 在已有类别基础上插入“全部”选项
    if (lotteryCatList.value.length > 0) {
      const others = lotteryCatList.value.filter((c: any) => c.id !== 0);
      lotteryCatList.value = [
        {
          id: 0,
          name: "全部",
          cost: lotteryData.value.fee ?? 10,
        },
        ...others,
      ];
    }
    loading.dismiss();
  });
}

const onModalWillDismiss = (event: any) => {
  emit("willDismiss", event);
};

async function onCateClick(cate: any) {
  selectedCateForGifts.value = cate;
  categoryGiftList.value = [];
  const loading = await loadingController.create({ message: "加载中..." });
  await loading.present();
  const filter: Record<string, number> = {};
  if (cate.id && cate.id !== 0) {
    filter.cate_id = cate.id;
  }
  getList("t_gift", filter, 1, 200)
    .then((data: any) => {
      categoryGiftList.value = (data?.data ?? []).map((item: any) => ({
        id: item.id,
        name: item.name,
        img: item.image,
        image: item.image,
        cate_id: item.cate_id,
        cost: item.cost,
        enable: item.enable,
        exchange: item.exchange,
        stock: item.stock,
      }));
    })
    .catch((err: any) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    })
    .finally(() => loading.dismiss());
}

function backToCategoryList() {
  selectedCateForGifts.value = null;
  categoryGiftList.value = [];
}

function openGiftEdit(item: any) {
  editingGift.value = item;
  isGiftDialogOpen.value = true;
}

function openNewGiftFromSetting() {
  // 在当前类别下新增奖品
  editingGift.value = null;
  isGiftDialogOpen.value = true;
}

function closeGiftDialog() {
  isGiftDialogOpen.value = false;
  editingGift.value = null;
}

function onGiftSaved() {
  closeGiftDialog();
  if (selectedCateForGifts.value) {
    const filter: Record<string, number> = {};
    if (selectedCateForGifts.value.id && selectedCateForGifts.value.id !== 0) {
      filter.cate_id = selectedCateForGifts.value.id;
    }
    getList("t_gift", filter, 1, 200)
      .then((data: any) => {
        categoryGiftList.value = (data?.data ?? []).map((item: any) => ({
          id: item.id,
          name: item.name,
          img: item.image,
          image: item.image,
          cate_id: item.cate_id,
          cost: item.cost,
          enable: item.enable,
          exchange: item.exchange,
          stock: item.stock,
        }));
      })
      .catch((err: any) => EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err)));
  }
}

async function onGiftDelete(gift: any) {
  try {
    await delData("t_gift", gift.id);
    EventBus.$emit(C_EVENT.TOAST, "删除成功");
    categoryGiftList.value = categoryGiftList.value.filter((x: any) => x.id !== gift.id);
    closeGiftDialog();
  } catch (err: any) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

async function addCate() {
  const alert = await alertController.create({
    header: "添加类别",
    inputs: [
      { name: "name", type: "text", placeholder: "类别名称" },
      { name: "cost", type: "number", value: "0", placeholder: "消耗积分" },
    ],
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async (data: { name?: string; cost?: string }) => {
          const name = (data?.name ?? "").trim();
          if (!name) {
            EventBus.$emit(C_EVENT.TOAST, "请输入类别名称");
            return;
          }
          try {
            await setData("t_gift_category", {
              name,
              cost: Number(data?.cost) || 0,
            });
            EventBus.$emit(C_EVENT.TOAST, "添加成功");
            getList("t_gift_category")
              .then((res: any) => {
                const raw = res?.data ?? [];
                const others = raw.filter((c: any) => c.id !== 0);
                lotteryCatList.value = [
                  {
                    id: 0,
                    name: "全部",
                    cost: lotteryData.value.fee ?? 10,
                  },
                  ...others,
                ];
              })
              .catch((err: any) => {
                EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
              });
          } catch (err: any) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}

async function editCate(cate: any) {
  const costVal = String(cate.cost ?? 0);
  const alert = await alertController.create({
    header: "编辑类别",
    inputs: [
      {
        name: "id",
        type: "text",
        value: `ID: ${cate.id ?? ""}`,
        disabled: true,
      },
      {
        name: "name",
        type: "text",
        value: cate.name ?? "",
        placeholder: "类别名称",
        disabled: cate.id === 0,
      },
      { name: "cost", type: "number", value: costVal, placeholder: "消耗积分" },
    ],
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async (data: { name?: string; cost?: string }) => {
          const cost = Number(data?.cost) ?? 0;
          try {
            if (cate.id === 0) {
              await setLotteryData(
                JSON.stringify({ ...lotteryData.value, fee: cost })
              );
              lotteryData.value.fee = cost;
              const idx = lotteryCatList.value.findIndex((x: any) => x.id === 0);
              if (idx >= 0) lotteryCatList.value[idx].cost = cost;
              if (selectedCateForGifts.value?.id === 0) {
                selectedCateForGifts.value.cost = cost;
              }
            } else {
              const name = (data?.name ?? cate.name ?? "").trim();
              if (!name) {
                EventBus.$emit(C_EVENT.TOAST, "请输入类别名称");
                return;
              }
              await setData("t_gift_category", {
                id: cate.id,
                name,
                cost,
              });
              const idx = lotteryCatList.value.findIndex((x: any) => x.id === cate.id);
              if (idx >= 0) {
                lotteryCatList.value[idx].name = name;
                lotteryCatList.value[idx].cost = cost;
              }
              if (selectedCateForGifts.value?.id === cate.id) {
                selectedCateForGifts.value.name = name;
                selectedCateForGifts.value.cost = cost;
              }
            }
            EventBus.$emit(C_EVENT.TOAST, "更新成功");
          } catch (err: any) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}

async function deleteCate(cate: any) {
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
            lotteryCatList.value = lotteryCatList.value.filter((x: any) => x.id !== cate.id);
            if (selectedCateForGifts.value?.id === cate.id) {
              selectedCateForGifts.value = null;
              categoryGiftList.value = [];
            }
          } catch (err: any) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}

function getGiftImgUrl(item: { img?: string; image?: string }) {
  const raw = item.img ?? item.image;
  if (!raw)
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Crect fill='%23e5e7eb' width='96' height='96'/%3E%3C/svg%3E";
  return getPicDisplayUrl(raw, PicDisplaySize.LIST, PicDisplaySize.LIST);
}
</script>

<style scoped>
ion-modal#main::part(content) {
  max-width: 500px;
}

ion-modal#main {
  --height: 100%;
}
</style>

<style>
/* 成本均值弹窗：保留换行和空格，便于对齐 */
.alert-message-preline .alert-message {
  white-space: pre;
}
</style>
